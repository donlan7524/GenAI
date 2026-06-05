# AI generated

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-資料庫-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Playwright](https://img.shields.io/badge/Playwright-自動化採集-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-本地API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/用途-學術展示-brightgreen)](/)

📚 **為了協助您快速上手，專案中已製作了一份完整且詳細的使用教學指南，請直接閱讀：[PROJECT_GUIDE.md](file:///c:/Users/Diego/Downloads/AI_project/PROJECT_GUIDE.md)**

---

## 📖 目錄

1. [專案背景](#-專案背景)
2. [功能總覽](#-功能總覽)
3. [專案結構與文件導覽](#-專案結構與文件導覽)
4. [NLP 情緒分析引擎與情感模型](#-nlp-情緒分析引擎與情感模型)
5. [資料庫設計與防重疊機制](#-資料庫設計與防重疊機制)
6. [自動化 CDP 採集流水線](#-自動化-cdp-採集流水線)
7. [知識蒸餾與資料集準備](#-知識蒸餾與資料集準備)
8. [大語言模型 QLoRA 微調與 FastAPI 部署](#-大語言模型-qlora-微調與-fastapi-部署)
9. [中山 AI 網友社群模擬沙盒](#-中山-ai-網友社群模擬沙盒)
10. [資料庫重設工具](#-資料庫重設工具)
11. [安裝與執行](#-安裝與執行)
12. [隱私與安全說明](#-隱私與安全說明)

---

## 📌 專案背景

本專案為學術用途的 **概念驗證（Proof of Concept）** 系統，旨在探索：
- 中山大學學生在 Dcard 上的主要情緒分佈為何？
- 貼文標題與內文所傳遞的情緒好惡，與留言回應的情緒表現是否存在落差或共鳴？
- 我們能否使用真實的論壇數據，知識蒸餾並微調出具備「中山大學學生特徵與性格」的 AI 網友進行社群互動模擬？

---

## ✨ 功能總覽

### 📊 1. 輿情分析主儀表板
* **情緒分佈與趨勢**：展示正向/負向偏向（Valence）以及冷靜/激動強度（Arousal）的百分比佔比與時間折線波動。
* **2D 輿情象限平面圖**：將貼文定位在「好惡效價」與「喚起度」二維象限中，點的尺寸與按讚數呈正相關。
* **最新留言列表**：顯示最近採集的留言，附帶百分比化的 NLP 情緒標記（如 `🟢 正向 52.0%` / `🔵 冷靜 51.6%`）。

### 🎮 2. 中山 AI 網友互動沙盒
* **歷史資料回放測試**：載入真實貼文，指派不同性格的 AI 網友針對該文發表留言。
* **自主模擬沙盒**：AI 發文 Agent 自動發表貼文，多位不同性格的 AI 留言 Agent 在下方自動進行 @樓層 留言與多輪交鋒。
* **人機大戰互動**：使用者可以親自在虛擬看板發文或留下「真人留言」，將會立刻觸發 AI 網友對您進行 @回覆。

### 🎓 3. 學術量化評估
* **TTR 詞彙多樣性**：計算 AI 生成的相異詞比率，評估其語言多樣性。
* **語氣餘弦相似度**：利用 TF-IDF 向量比較 AI 留言語料與真實 Dcard 人類語料在用詞習慣上的相似融入程度。

---

## 📂 專案結構與文件導覽

本專案的關鍵檔案配置如下：

```text
c:/Users/Diego/Downloads/AI_project/
├── app.py                      # Streamlit 儀表板主入口程式
├── pages/
├── dcard_fetcher.py            # Playwright Chrome CDP 自動化爬蟲 (隨機防封鎖延遲)
├── HTMLdealer.py               # 數據庫同步與 CSV 寫入工具
├── data_processor.py           # 知識蒸餾管線 (對話樹重建 + NumPy MLP 雜訊過濾)
├── train_lora.py               # QLoRA 4-bit 微調訓練腳本 (支援 Colab T4)
├── serve_model.py              # FastAPI OpenAI 相容本地模型 API 伺服器
├── evaluator.py                # TTR 豐富度與風格 Cosine 相似度評估工具
├── clean_db.py                 # SQLite 資料庫安全清空與壓縮工具
├── nlp_engine.py               # 2D 情感分析引擎與關鍵字詞雲生成
├── db_manager.py               # 本地 SQLite 資料庫讀寫介面
├── nsysu_舆情.db                # 本地 SQLite 資料庫 (儲存爬蟲與模擬數據)
├── PROJECT_GUIDE.md            # 本專案一站式完整使用指南 (繁中)
└── README.md                   # 專案介紹說明書 (本文件)
```

---

## 🧠 NLP 情緒分析引擎與情感模型

系統使用離線、規則式的多維情感字典與繁體中文斷詞引擎。

### 1. 2D Valence-Arousal 情感模型
*   **情緒效價 (Valence, 情緒好惡)**：範圍 $[-100.0, 100.0]$。正值代表正向（喜悅、放鬆），負值代表負向（焦慮、沮喪）。
*   **情緒喚起度 (Arousal, 生理激動度)**：範圍 $[-100.0, 100.0]$。正值代表高生理喚起（激動、緊張），負值代表低生理喚起（冷靜、消極）。

### 2. 百分比轉換公式
將 $[-100.0, 100.0]$ 的分數透過以下公式映射為 $[0\%, 100\%]$ 的分佈百分比：
$$\text{百分比} = 50.0\% + \frac{\text{原始分數}}{2.0}$$

---

## 🗄️ 資料庫設計與防重疊機制

資料庫採用 SQLite（`nsysu_舆情.db`），包含貼文主表 `posts`、留言表 `comments`、虛擬看板表 `virtual_posts` 與虛擬留言表 `virtual_comments`。

### 🔄 冪等性防重複寫入機制 (Idempotency)
若您**重複執行**爬蟲與解析腳本，系統**不會**造成資料庫混亂。
*   系統採用了 SQLite 的 `ON CONFLICT(post_id) DO UPDATE` 語意。
*   若資料庫中已經存在相同 ID 的貼文或留言，系統會自動使用最新抓取到的按讚數、留言數與情感分數進行**欄位更新**，而不會插入重複的資料，確保數據庫潔淨與時效性。

---

## 🌳 知識蒸餾與資料集準備

[data_processor.py](file:///c:/Users/Diego/Downloads/AI_project/data_processor.py) 提供將論壇非結構化數據提煉為 LLM 微調數據的資料工程管線：
*   **樹狀重建**：解析內容中的 `@B[0-9]+`，將扁平列表還原為多叉對話樹。
*   **MLP 過濾器**：採用純 NumPy 實作單隱藏層多層感知器，過濾短詞與無意義詞。
*   **數據導出**：產生發文者 `poster_dataset.jsonl` 與留言者 `commenter_dataset.jsonl`。

---

## 🧠 大語言模型 QLoRA 微調與 FastAPI 部署

為了微調出具備中山特徵的 AI 網友：
*   **微調腳本**：[train_lora.py](file:///c:/Users/Diego/Downloads/AI_project/train_lora.py) 使用 QLoRA 4-bit 量化與 SFTTrainer 在 GPU 上進行高效微調（支援 Google Colab T4 執行）。
*   **API 部署**：[serve_model.py](file:///c:/Users/Diego/Downloads/AI_project/serve_model.py) 採用 FastAPI 連接微調好的 LoRA Adapter 並啟動本地端伺服器（Port 8000），提供完全相容 OpenAI Chat Completion 格式的接口。

---

## 🎮 中山 AI 網友社群模擬沙盒

程式位於 [pages/1_🤖_中山AI網友沙盒.py](file:///c:/Users/Diego/Downloads/AI_project/pages/1_%F0%9F%A4%96_%E4%B8%AD%E5%B1%B1AI%E7%B6%B2%E5%8F%8B%E6%B2%99%E7%9B%92.py)，提供：
*   **多樣性格**：酸民嘴砲（愛反諷）、理智學霸（務實理性）、搞笑迷因（獼猴話題）、熱心溫和（溫柔鼓勵）。
*   **對話樹模擬**：使用 Streamlit `st.chat_message` 完美呈現多層留言樹。
*   **雙連線模式**：支援填入本地 API 啟用您微調的 LoRA 模型，若未啟用則自動退回高質感的「本地校園規則範本模式」進行離線測試。

---

## 🚀 安裝與快速執行

1. **安裝相依套件**：
   ```bash
   pip install streamlit pandas plotly jieba wordcloud curl_cffi playwright fastapi uvicorn torch transformers peft accelerate datasets bitsandbytes
   playwright install chromium
   ```
2. **啟動除錯模式 Chrome (防封鎖)**：
   ```powershell
   & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_dev_profile" --no-first-run
   ```
3. **執行採集與解析**：
   ```bash
   python dcard_fetcher.py
   python HTMLdealer.py
   ```
4. **啟動 Web 儀表板與沙盒**：
   ```bash
   streamlit run app.py
   ```
   *啟動後在側邊欄切換至 `1_🤖_中山AI網友沙盒` 頁面即可體驗！*

---

## 🛡️ 隱私與安全說明

1. **本地安全**：本機 SQLite 資料庫已加入 `.gitignore`，確保您抓取的數據與個人 Cookie 資訊（位於 `config.json`）不會推送到公開的 GitHub 倉庫中。其他使用者 clone 專案後，會在他們本地重新建立自己專屬的資料庫。
2. **防封鎖安全延遲**：爬蟲已加入隨機間隔，模擬真人閱讀行為，大幅降低 IP 被封鎖的風險。

---
📝 **詳細的實作細節與模型訓練指南，請即刻閱讀：[PROJECT_GUIDE.md](file:///c:/Users/Diego/Downloads/AI_project/PROJECT_GUIDE.md)**
