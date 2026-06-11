---
marp: true
theme: gaia
_class: lead
paginate: true
backgroundColor: #0d1117
color: #c9d1d9
style: |
  section {
    font-family: 'Source Han Sans TC', 'Microsoft JhengHei', sans-serif;
    padding: 40px;
  }
  h1 {
    color: #58a6ff;
  }
  h2 {
    color: #58a6ff;
    border-bottom: 2px solid #30363d;
  }
  footer {
    font-size: 0.5em;
    color: #8b949e;
  }
  strong {
    color: #ff7b72;
  }
  code {
    background-color: #161b22;
    color: #79c0ff;
  }
  table {
    font-size: 0.7em;
  }
---

# 國立中山大學社群輿情與 AI 網友模擬系統

### 基於二維情緒維度、對話樹蒸餾與 QLoRA 微調的社群動態模擬

報告人：專案團隊
技術標籤：`Playwright CDP` | `Valence-Arousal` | `QLoRA` | `FastAPI & Streamlit`

---

## 專案背景與核心痛點

* **傳統輿情分析之侷限**
  * 簡單的正負向二元分類，無法捕捉複雜的大學生情感語境。
  * 留言數據呈扁平化線性結構，**對話上下文脈絡完全遺失**。
* **校園社群的特性**
  * 獨特校園黑話（如：米羅蛋餅、翠亨停水、獼猴超速）更迭迅速，通用詞庫難以識別。
  * 缺乏安全的**言論沙盒環境**，無法模擬輿論發酵與網友動態。

---

## 端到端全管線技術架構

* **採集層**：Playwright CDP 接管技術，繞過 Cloudflare WAF 安全防護。
* **情感層**：Valence-Arousal (VA) 情感計算 + 關鍵字情緒傳播自學習。
* **蒸餾層**：對話樹階層式還原演算法 + NumPy 自建 MLP 垃圾過濾器。
* **訓練層**：4-bit QLoRA 低資源微調 (Breeze-7B) + FastAPI 本地部署。
* **模擬層**：Streamlit 互動沙盒 (3D 性格滑桿) + TTR/風格相似度量化評估。

---

## 模組一：Playwright CDP 數據採集管線

* **防封鎖網頁接管**
  * 接管已通過驗證的實體 Chrome 開發者埠口 (`port: 9222`)。
  * 引入 `0.8 ~ 3.0` 秒隨機波動延遲，模擬真人瀏覽。
* **資料庫冪等性設計**
  * 使用 SQLite 儲存。寫入時採用 `ON CONFLICT DO UPDATE`。
  * 內建 `clean_db.py` 支援物理壓縮 (`VACUUM`)。

---

## 模組二：Valence-Arousal 情緒自學習

* **學術級情緒空間**
  * **Valence (效價)**：情緒正負向度 (0-10)。
  * **Arousal (喚起度)**：情緒激動/冷靜度 (0-10)。
* **自學習情緒傳播算法 (Propagation)**
  * 強烈情緒貼文的情緒分數以 $40\%$ 衰減率傳遞給關鍵字。
  * 滾動移動平均平滑：
    $$\text{Value}_{\text{new}} = 0.7 \times \text{Value}_{\text{old}} + 0.3 \times \text{Value}_{\text{propagation}}$$
  * 循序重算後，中性貼文佔比自 $23.3\%$ 降至 $9.3\%$。

---

## 模組三：對話樹重建與數據蒸餾

* **對話樹還原演算法**
  * 解析留言中的 `@B1`、`@B2` 等標記，重建多叉樹結構。
* **自建 NumPy MLP 分類器**
  * 從零實作多層感知器，剔除無意義留言（如「卡」、「推」）。
* **微調數據產出**
  * 提取對話樹節點，自動導出符合 SFT 格式的 JSONL。
  * 產生 `poster_dataset.jsonl` 與 `commenter_dataset.jsonl`。

---

## 模組四：QLoRA 模型微調與 FastAPI 部署

* **4-bit QLoRA 輕量訓練**
  * 使用 `peft`、`trl` 與 `bitsandbytes` 庫。
  * 於 Google Colab (T4 GPU) 完成 Breeze-7B 網友風格微調。
* **FastAPI 推理伺服器**
  * 掛載微調後的 LoRA Adapter。
  * 提供完全相容 OpenAI 規格的推理接口 (`/v1/chat/completions`)。

---

## 模組五：中山 AI 網友模擬沙盒

* **三維性格滑桿控制**
  * 透過 **理智度**、**嘴砲度**、**幽默度** 動態組裝 System Prompt。
* **雙模式相容機制**
  * 若 LLM 離線，自動切換至**本地規則加權抽樣 Fallback 引擎**。
* **自主社群動力學模擬**
  * 智能體依據性格評估貼文興趣，決定是否發文或在樓層下展開論戰。

---

## 模組六：人機對戰與即時通知推播

* **人機互動介面**
  * 真人同學可在沙盒中發文或留言，即時觸發 AI 網友跟帖回覆。
* **SQLite 通知機制**
  * AI 網友 @回覆 真人時，系統自動向 `virtual_notifications` 寫入通知，前端動態彈出 Badge 提示。
* **上下文感知對話**
  * AI 生成回覆時帶入對話樹脈絡，實現合理流暢的對話。

---

## 學術評估與擬真度量化指標

* **TTR (Type-Token Ratio) 詞彙豐富度**
  * 評估生成多樣性，避免陷入罐頭式重複。
* **風格餘弦相似度 (Cosine Similarity)**
  * 利用 TF-IDF 比較 AI 生成留言與真實人類語料的特徵重合度。
  * **評估結果**：風格相似度高達 **85%** 以上，驗證了 LoRA 微調的擬真效果。

---

## 專案亮點與未來展望

* **專案三大亮點**
  1. 雙模式防護機制（API + 本地規則 Fallback），系統展現高可用性。
  2. 情緒自學習傳播算法，自動收斂校園專屬情緒詞彙。
  3. 對話樹重建與 NumPy MLP 知識工程，大幅提升語料純度。
* **未來展望**
  * 微調專屬發文者 (Poster) LoRA，與 Commenter LoRA 並行路由。
  * 實作背景常駐執行緒，讓虛擬看板持續自動演化。
  * 評估指標圖表直接做入 Streamlit 頁面。

---

# Q&A / 謝謝聆聽

### 歡迎各位老師與評審指教

系統主頁連結：`http://localhost:8501`
專案資料庫：`nsysu_舆情.db`
備份簡報規劃：[presentation_outline.md](file:///C:/Users/Diego/.gemini/antigravity/brain/938e2fbc-fb64-4ac3-9666-20e38c11f11c/presentation_outline.md)
