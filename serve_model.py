"""
國立中山大學 Dcard AI 網友 - 本地模型 API 部署伺服器 (OpenAI 規格相容)
本腳本用於在本地載入微調後的 LoRA 模型，並啟動一個 API 伺服器供 Streamlit 介面調用。

請先安裝相依套件：
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
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = FastAPI(title="NSYSU Dcard AI Agent Server")

# ==========================================
# 1. 載入模型與 LoRA Adapter
# ==========================================
BASE_MODEL = "MediaTek-Research/Breeze-7B-Instruct-v1_0"
LORA_PATH = "./nsysu_commenter_lora"

print("⚙️ 正在載入 Tokenizer 與基底模型 (Breeze-7B)...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

# 依硬體資源決定載入方式（有 GPU 用半精度，無 GPU 慢跑 CPU）
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️ 偵測到硬體裝置: {device.upper()}")

if device == "cuda":
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
else:
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        device_map="auto",
        trust_remote_code=True
    )

# 掛載微調好的 LoRA Adapter
if os.path.exists(LORA_PATH):
    print(f"🔌 偵測到 LoRA 權重，正在掛載: {LORA_PATH} ...")
    model = PeftModel.from_pretrained(model, LORA_PATH)
    print("✅ LoRA Adapter 掛載成功！")
else:
    print("⚠️ 找不到 LoRA 權重目錄，將直接以 Breeze-7B 基底模型提供服務。")

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
        # 將輸入的對話歷史拼裝成 Breeze 格式的 Prompt
        # 格式: <s>[INST] system_prompt\n\nuser_input [/INST]
        formatted_prompt = "<s>"
        for msg in request.messages:
            if msg.role == "system":
                formatted_prompt += f"[INST] {msg.content}\n\n"
            elif msg.role == "user":
                # 若前面沒有 system 則手動補上 [INST]
                if not formatted_prompt.endswith("\n\n") and not formatted_prompt.endswith("[INST] "):
                    formatted_prompt += "[INST] "
                formatted_prompt += f"{msg.content} [/INST] "
            elif msg.role == "assistant":
                formatted_prompt += f"{msg.content} </s>"
                
        # 確保 prompt 結尾正確封裝
        if not formatted_prompt.endswith(" </s>") and not formatted_prompt.endswith("[/INST] "):
            formatted_prompt += " [/INST]"

        # 轉成 Token
        inputs = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # 產生回覆
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
            
        # 擷取生成的新文字
        input_len = inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_len:]
        response_text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        
        # 組裝相容的 JSON 回傳格式
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
    return {
        "data": [
            {
                "id": "nsysu-dcard-commenter",
                "object": "model",
                "owned_by": "nsysu"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    # 本地啟動在 8000 port
    uvicorn.run(app, host="127.0.0.1", port=8000)
