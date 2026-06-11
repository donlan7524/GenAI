"""
國立中山大學 Dcard AI 網友 - LoRA 4-bit 微調訓練腳本 (QLoRA Fine-Tuning)
支援同時訓練發文者 (Poster) 與留言者 (Commenter) 模型。

安裝相依套件：
pip install torch transformers peft trl accelerate bitsandbytes datasets
"""

import os
import argparse
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer, SFTConfig

# 推薦基底模型（針對台灣繁體中文優化）
BASE_MODEL = "MediaTek-Research/Breeze-7B-Instruct-v1_0" 

def parse_args():
    parser = argparse.ArgumentParser(description="NSYSU Dcard AI Agent Fine-Tuning")
    parser.add_argument(
        "--role",
        type=str,
        default="commenter",
        choices=["commenter", "poster"],
        help="選擇微調的角色：commenter (留言者) 或 poster (發文者)"
    )
    return parser.parse_args()

def train():
    args = parse_args()
    role = args.role
    
    # 根據角色決定資料集路徑與輸出目錄
    dataset_path = f"{role}_dataset.jsonl"
    output_dir = f"./nsysu_{role}_lora"
    
    print("=" * 60)
    print(f"🚀 啟動 中山 AI 網友【{role.upper()}】LoRA 微調訓練流程...")
    print(f"📂 使用資料集：{dataset_path}")
    print(f"💾 輸出權重目錄：{output_dir}")
    print("=" * 60)
    
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"❌ 找不到微調資料集：{dataset_path}，請確認已執行過 data_processor.py。")

    # ==========================================
    # 2. 4-bit 量化設定 (QLoRA)
    # ==========================================
    print("📦 載入 4-bit 量化設定...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # ==========================================
    # 3. 載入 Tokenizer 與 Model
    # ==========================================
    print(f"📥 正在從 Hugging Face 載入基底模型: {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True
    )
    
    # 解決基底模型 config 中 output_router_logits 被設為 True 導致 SFTTrainer 報錯的 Bug
    if hasattr(model.config, "output_router_logits"):
        model.config.output_router_logits = False
    
    # ==========================================
    # 4. LoRA 結構設定
    # ==========================================
    print("🛠️ 設定 LoRA 參數...")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )

    # ==========================================
    # 5. 載入與預處理 JSONL 資料集
    # ==========================================
    print("📖 載入微調資料集...")
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    def format_prompts(batch):
        formatted_texts = []
        for inst, inp, out in zip(batch["instruction"], batch["input"], batch["output"]):
            # 套用 Breeze 的對話格式: <s>[INST] system_prompt\n\nuser_input [/INST] assistant_reply </s>
            text = f"<s>[INST] {inst}\n\n{inp} [/INST] {out} </s>"
            formatted_texts.append(text)
        return {"text": formatted_texts}

    dataset = dataset.map(format_prompts, batched=True)
    print(f"📊 資料集預處理完成，共有 {len(dataset)} 筆訓練樣本。")

    # ==========================================
    # 6. 訓練與 SFT 參數設定
    # ==========================================
    print("⚙️ 設定訓練與 SFT 參數...")
    sft_config = SFTConfig(
        output_dir=output_dir,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        num_train_epochs=5,
        bf16=True,
        save_strategy="epoch",
        optim="paged_adamw_32bit",
        report_to="none",
        # 以下為 SFT 專屬參數
        dataset_text_field="text",
        max_length=512,
    )

    # ==========================================
    # 7. 啟動 SFT 訓練器
    # ==========================================
    print("🔥 開始 SFT 訓練...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        processing_class=tokenizer,
        args=sft_config,
        peft_config=peft_config
    )

    trainer.train()

    # 儲存 LoRA Adapter
    print(f"💾 訓練完成！正在儲存 LoRA 權重至: {output_dir}...")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"🎉 QLoRA 【{role.upper()}】微調訓練大功告成！")

if __name__ == "__main__":
    train()
