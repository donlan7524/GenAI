"""
國立中山大學 Dcard AI 網友 - 本地模型 API 部署伺服器 (OpenAI 規格相容，支援多 LoRA 路由)
本腳本用於載入基底模型，並同時掛載發文者與留言者 LoRA Adapter，依請求動態路由。

安裝相依套件：
pip install fastapi uvicorn torch transformers peft accelerate
"""

import os
import torch
import sys
import io
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Windows 控制台編碼
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


app = FastAPI(title="NSYSU Dcard AI Agent Server - Multi-LoRA")

# ==========================================
# 1. 載入模型與多個 LoRA Adapters
# ==========================================
BASE_MODEL = "MediaTek-Research/Breeze-7B-Instruct-v1_0"
COMMENTER_LORA_PATH = "./nsysu_commenter_lora"
POSTER_LORA_PATH = "./nsysu_poster_lora"

print("⚙️ 正在載入 Tokenizer 與基底模型 (Breeze-7B)...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

# 依硬體資源決定載入方式
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️ 偵測到硬體裝置: {device.upper()}")

if device == "cuda":
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
else:
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        device_map="auto",
        trust_remote_code=True
    )

model = None
has_commenter = False
has_poster = False

# 掛載第一個 Adapter (留言者)
if os.path.exists(COMMENTER_LORA_PATH):
    print(f"🔌 正在掛載留言者 LoRA Adapter: {COMMENTER_LORA_PATH} ...")
    model = PeftModel.from_pretrained(base_model, COMMENTER_LORA_PATH, adapter_name="commenter")
    has_commenter = True
    print("✅ 留言者 Adapter 掛載成功！")
else:
    print("⚠️ 找不到留言者 LoRA 權重，將以基底模型初始化 PEFT。")

# 掛載第二個 Adapter (發文者)
if os.path.exists(POSTER_LORA_PATH):
    if model is None:
        print(f"🔌 正在掛載發文者 LoRA Adapter: {POSTER_LORA_PATH} ...")
        model = PeftModel.from_pretrained(base_model, POSTER_LORA_PATH, adapter_name="poster")
        has_poster = True
        print("✅ 發文者 Adapter 掛載成功！")
    else:
        print(f"🔌 正在載入發文者 LoRA Adapter: {POSTER_LORA_PATH} ...")
        model.load_adapter(POSTER_LORA_PATH, adapter_name="poster")
        has_poster = True
        print("✅ 發文者 Adapter 載入並掛載成功！")
else:
    print("⚠️ 找不到發文者 LoRA 權重。")

# 如果兩個都沒有載入，退回基底模型
if model is None:
    model = base_model
    print("ℹ️ 未加載任何 LoRA Adapter，將僅使用 Breeze-7B 基底模型提供服務。")
else:
    model.eval()

# ==========================================
# 2. 定義 OpenAI 相容之 API Pydantic 格式
# ==========================================
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 200

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]

# ==========================================
# 3. 實作 OpenAI Chat/Completions 接口
# ==========================================
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    try:
        # 動態路由決定使用哪一個 LoRA Adapter
        target_model_name = request.model.lower()
        
        if isinstance(model, PeftModel):
            if "poster" in target_model_name:
                if has_poster:
                    model.set_adapter("poster")
                    print("[Router] 🔀 路由選定 ➔ 發文者 Adapter (poster)")
                else:
                    # 退回 commenter 或預設
                    if has_commenter:
                        model.set_adapter("commenter")
                        print("[Router] ⚠️ 找不到發文者 Adapter，退回使用 ➔ 留言者 Adapter")
            else:
                if has_commenter:
                    model.set_adapter("commenter")
                    print("[Router] 🔀 路由選定 ➔ 留言者 Adapter (commenter)")
                elif has_poster:
                    model.set_adapter("poster")
                    print("[Router] ⚠️ 找不到留言者 Adapter，退回使用 ➔ 發文者 Adapter")

        # 拼接對話
        formatted_prompt = "<s>"
        for msg in request.messages:
            if msg.role == "system":
                formatted_prompt += f"[INST] {msg.content}\n\n"
            elif msg.role == "user":
                if not formatted_prompt.endswith("\n\n") and not formatted_prompt.endswith("[INST] "):
                    formatted_prompt += "[INST] "
                formatted_prompt += f"{msg.content} [/INST] "
            elif msg.role == "assistant":
                formatted_prompt += f"{msg.content} </s>"
                
        if not formatted_prompt.endswith(" </s>") and not formatted_prompt.endswith("[/INST] "):
            formatted_prompt += " [/INST]"

        inputs = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
            
        input_len = inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_len:]
        response_text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(torch.randint(0, 100000, (1,))[0])}",
            object="chat.completion",
            created=1234567,
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    message=Message(role="assistant", content=response_text),
                    finish_reason="stop"
                )
            ]
        )
    except Exception as e:
        print(f"❌ 生成錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    """提供可用的模型列表"""
    models_list = []
    if has_commenter:
        models_list.append({"id": "nsysu-dcard-commenter", "object": "model", "owned_by": "nsysu"})
    if has_poster:
        models_list.append({"id": "nsysu-dcard-poster", "object": "model", "owned_by": "nsysu"})
    if not models_list:
        models_list.append({"id": "nsysu-breeze-base", "object": "model", "owned_by": "nsysu"})
        
    return {"data": models_list}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
