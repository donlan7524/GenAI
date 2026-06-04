"""
國立中山大學 Dcard AI 網友 - LoRA 4-bit 微調訓練腳本 (QLoRA Fine-Tuning)
本腳本設計用於 Google Colab (T4 GPU) 或任何配備 16GB 以上 VRAM 的地端 GPU 伺服器。

請先安裝以下相依套件：
pip install torch transformers peft trl acceleration bitsandbytes datasets
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer

# ==========================================
# 1. 參數設定
# ==========================================
# 推薦基底模型（針對台灣繁體中文優化）
BASE_MODEL = "MediaTek-Research/Breeze-7B-Instruct-v1_0" 
# 微調資料集路徑
DATASET_PATH = "commenter_dataset.jsonl"
# 訓練後 LoRA Adapter 儲存路徑
OUTPUT_DIR = "./nsysu_commenter_lora"

def train():
    print("🚀 啟動 中山 AI 網友 LoRA 微調訓練流程...")
    
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"❌ 找不到微調資料集：{DATASET_PATH}，請確認已執行過 data_processor.py。")

    # ==========================================
    # 2. 4-bit 量化設定 (QLoRA 關鍵，防止 16GB 顯存 OOM)
    # ==========================================
    print("📦 載入 4-bit 量化設定...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )

    # ==========================================
    # 3. 載入 Tokenizer 與 Model
    # ==========================================
    print(f"📥 正在從 Hugging Face 下載/載入基底模型: {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right" # 預防生成時長度混亂

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    
    # ==========================================
    # 4. LoRA 結構設定
    # ==========================================
    print("🛠️ 設定 LoRA 參數...")
    peft_config = LoraConfig(
        r=16,                       # LoRA Rank
        lora_alpha=32,              # LoRA Alpha
        target_modules=[            # 針對 Attention 機制所有投影矩陣進行微調
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters() # 顯示可訓練參數佔比 (通常小於 1%)

    # ==========================================
    # 5. 載入與預處理 JSONL 資料集
    # ==========================================
    print("📖 載入微調資料集...")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    def format_prompts(batch):
        """
        將 instruction + input + output 格式化為 Breeze 聊天格式的 Prompt
        """
        formatted_texts = []
        for inst, inp, out in zip(batch["instruction"], batch["input"], batch["output"]):
            # 套用 Breeze 的對話格式: <s>[INST] system_prompt\n\nuser_input [/INST] assistant_reply </s>
            text = f"<s>[INST] {inst}\n\n{inp} [/INST] {out} </s>"
            formatted_texts.append(text)
        return {"text": formatted_texts}

    dataset = dataset.map(format_prompts, batched=True)
    print(f"📊 資料集預處理完成，共有 {len(dataset)} 筆訓練樣本。")

    # ==========================================
    # 6. 訓練超參數設定
    # ==========================================
    print("⚙️ 設定訓練參數...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=4,      # 每次訓練批次 (T4 GPU 建議 2 或 4)
        gradient_accumulation_steps=4,      # 梯度累積，達到等效 Batch Size = 16
        learning_rate=2e-4,                 # 學習率
        logging_steps=10,
        num_train_epochs=5,                 # 訓練輪數 (建議 3 ~ 5 輪以充分收斂)
        fp16=True,                          # 使用半精度混合訓練
        save_strategy="epoch",
        optim="paged_adamw_32bit",          # QLoRA 專用優化器
        report_to="none"                    # 關閉無謂日誌上傳
    )

    # ==========================================
    # 7. 啟動 SFT 訓練器
    # ==========================================
    print("🔥 開始 SFT 訓練...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=512,                 # 最大 Token 長度限制
        tokenizer=tokenizer,
        args=training_args,
        peft_config=peft_config
    )

    # 執行訓練
    trainer.train()

    # 儲存 LoRA Adapter
    print(f"💾 訓練完成！正在儲存 LoRA 權重至: {OUTPUT_DIR}...")
    trainer.model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("🎉 QLoRA 微調訓練大功告成！")

if __name__ == "__main__":
    train()
