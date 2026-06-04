# 國立中山大學社群輿情與 AI 網友沙盒模擬專案 - 完整使用教學指南

本指南旨在提供一站式、由淺入深的實作步驟，協助您完整操作本專案的所有功能——從**原始資料爬取、情感分析儀表板、數據知識蒸餾、LLM 微調訓練、FastAPI 本地部署，到 AI 網友自主社群沙盒與學術量化評估**。

---

## 📖 專案功能模組導覽

整個專案由五大模組串聯而成：
1. **輿情數據採集**：透過 Playwright CDP 繞過 Cloudflare 抓取中山版最新貼文、標籤與留言。
2. **情緒維度儀表板**：提供 2D 象限平面圖、時間趨勢圖、情感百分比與關鍵字詞雲。
3. **對話樹知識蒸餾**：用自建的 NumPy MLP 分類器過濾垃圾，將扁平留言還原為階層樹，生成微調 JSONL。
4. **模型微調與部署**：在 Google Colab 上進行 QLoRA 微調，並在本地使用 FastAPI 開啟相容 OpenAI 規格的 API。
5. **AI 看板互動沙盒**：提供真實貼文回放測試、AI 自主發文留言、人機聊天室，以及 TTR 多樣性評估。

---

## 🛠️ 第一階段：安裝相依套件與環境準備

請在您的電腦終端機（或 PowerShell）中依序執行以下指令：

### 1. 安裝 Python 庫
```bash
pip install streamlit pandas plotly jieba wordcloud curl_cffi playwright fastapi uvicorn torch transformers peft accelerate datasets bitsandbytes
```

### 2. 初始化 Playwright 驅動
```bash
playwright install chromium
```

---

## 📡 第二階段：Dcard 輿情數據採集與資料庫管理

為了讓儀表板有豐富的中山大學 Dcard 真實數據，我們需要執行資料採集。

### 步驟 1：啟動 Chrome 開發者除錯埠口 (防 Cloudflare 阻擋關鍵)
1. 關閉您電腦上所有的 Chrome 視窗。
2. 開啟 PowerShell 或 CMD，執行以下指令啟動除錯 Chrome：
   ```powershell
   & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_dev_profile" --no-first-run
   ```
3. 在新開啟的 Chrome 視窗中，瀏覽至 [Dcard 首頁](https://www.dcard.tw) 並保持登入狀態（這可確保能抓到完整內容）。

### 步驟 2：執行自動化爬蟲流水線
在專案根目錄下依序執行：
```bash
# 1. 自動接管 Chrome 並採集最新 20 篇富文本及留言，產出 test.json (內含防封鎖限流延遲)
python dcard_fetcher.py

# 2. 解析 test.json、執行情感分析並同步匯入 SQLite 資料庫 (nsysu_舆情.db)
python HTMLdealer.py
```

### 步驟 3：重設/清空資料庫 (備用)
如果您想清空舊資料、重新開始採集，請執行：
```bash
python clean_db.py
```
*提示：輸入 `y` 確認後，會刪除所有資料表資料並執行 `VACUUM` 釋放硬碟空間，但會保留完整的表格 Schema 架構。*

---

## 📊 第三階段：啟動與操作情緒維度分析儀表板

本儀表板將情感分類升級為學術界通用的 **Valence-Arousal 二維情緒維度模型**。

1. **啟動儀表板**：
   ```bash
   streamlit run app.py
   ```
2. **瀏覽網頁**：瀏覽器會自動開啟 `http://localhost:8501`。
3. **功能操作**：
   * **輿情檢索與下鑽**：在左側欄篩選日期或分類（課業/生活/感情/校務），點擊貼文卡片能直接查看原文與情感百分比（如 `🟢 正向 52.0%`）。
   * **2D 輿情象限平面圖**：點的尺寸代表讚數。Hover 懸停可預覽該貼文的情感坐標落點。
   * **留言情緒深度分析**：拉到頁面底部，可分析原PO發文語氣與留言網友反應的情感落差（偏離對角線代表作者與讀者有情感落差）。

---

## 🌳 第四階段：知識蒸餾與微調資料集生成

本階段將非結構化的 Dcard 貼文與留言蒸餾為 AI 訓練語料。

1. **執行蒸餾管線**：
   ```bash
   python data_processor.py
   ```
2. **程式背後做的事**：
   * **NLP 過濾**：載入我們用 NumPy 自建的 MLP 分類器，自動過濾掉無意義的短留言（如「卡」、「推」、「笑死」）。
   * **樹狀重建**：解析留言中的 `@B1` 等標記，重建階層對話鏈。
   * **生成微調集**：在本地產出 poster_dataset.jsonl（發文者）與 commenter_dataset.jsonl（留言者）。

---

## 🧠 第五階段：模型微調與本地部署 (LoRA & FastAPI)

將資料集餵給模型進行微調，並在本地運行您專屬的「中山 AI 網友」模型。

### 步驟 1：在 Google Colab 上進行微調訓練 (免顯卡成本)
1. 前往 [Google Colab](https://colab.research.google.com/)，切換執行階段類型為 **T4 GPU**。
2. 上傳您本地的 `commenter_dataset.jsonl` 與 train_lora.py 至 Colab 檔案區。
3. 執行安裝套件與微調指令：
   ```bash
   !pip install -q torch transformers peft trl accelerate bitsandbytes datasets
   !python train_lora.py
   ```
4. 微調完畢後，將產生的 `nsysu_commenter_lora` 資料夾壓縮下載。
5. 解壓縮後放回本地專案根目錄下，命名為 `nsysu_commenter_lora`。

### 步驟 2：在本地啟動 FastAPI 模型伺服器
在本地終端機執行部署程式：
```bash
python serve_model.py
```
*伺服器將在 `http://127.0.0.1:8000/v1` 啟動，自動讀取 Breeze-7B 並插上您的微調 LoRA Adapter，提供 OpenAI 相容的推理介面。*

---

## 🎮 第六階段：AI 網友沙盒互動與人機聊天

1. 確保 `streamlit run app.py` 運作中，在網頁左側邊欄點選 **`1_🤖_中山AI網友沙盒`** 頁面。
2. **串接您的微調模型**：
   在側邊欄的「LLM 連線設定」中，填入：
   * **OpenAI / Llama API Key**: `local-test` (任意填)
   * **模型名稱**: `nsysu-dcard-commenter`
   * **API Base URL**: `http://127.0.0.1:8000/v1`
   * 點選 **儲存並套用 LLM 設定**。*(若未填，預設退回本地規則範本，一樣可以進行互動測試)*。
3. **頁籤一：歷史回放與測試**：選擇真實貼文，讓 AI 網友進行留言；或由您扮演原PO與 AI 網友對答。
4. **頁籤二：模擬沙盒**：
   * 點擊「🎲 觸發自主發文與留言互動」，AI 發文者會開新貼文，AI 網友們會自動在下方 @樓層 展開論戰。
   * 您可親自發新文，或在留言框寫下「真人留言」，點擊發送後，會立刻觸發 AI 網友對您進行回覆，體驗與中山 AI 的人機對戰！

---

## 🎓 第七階段：量化評估 (Evaluation)

為了檢驗 AI 網友生成留言的品質與相似度，本專案提供學術量化評估腳本。

1. **執行評估指令**：
   ```bash
   python evaluator.py
   ```
2. **分析指標**：
   * **TTR (Type-Token Ratio)**：詞彙多樣性度量。數值越高，代表 AI 生成的詞彙越豐富，沒有陷入反覆說「好喔、笑死」的罐頭式重複。
   * **風格餘弦相似度 (Cosine Similarity)**：利用 TF-IDF 比較 AI 留言語料與真實 Dcard 人類語料的用詞重合度，相似度越高代表 AI 的用詞習慣越貼近真實中山學生的風格。

---

## 🛠️ 附錄：環境配置與常見問題排解 (Troubleshooting Guide)

要順利地在本地端進行 GPU 模型部署（如執行 `serve_model.py`）或進行微調，有幾個關鍵的系統級環境配置需要注意：

### 1. 本地 GPU (CUDA) 與 PyTorch 環境配置
如果您的電腦配有 NVIDIA 顯示卡，並想在本地以 GPU 加速運行模型：
* **確認 CUDA 驅動**：在終端機輸入 `nvidia-smi`。確認您的 CUDA 版本（例如 `12.x` 或 `11.x`）。
* **安裝對應的 PyTorch**：請勿直接使用 `pip install torch`。請至 [PyTorch 官網](https://pytorch.org/get-started/locally/) 複製對應您 CUDA 版本的安裝指令。例如，針對 CUDA 12.1 應執行：
  ```bash
  pip install torch --index-url https://download.pytorch.org/whl/cu121
  ```
* **驗證 GPU 是否可用**：
  執行命令：`python -c "import torch; print(torch.cuda.is_available())"`。若回傳 `True` 代表 GPU 設定成功。

### 2. Windows 系統下的 bitsandbytes 量化庫報錯
bitsandbytes 是 QLoRA 4-bit 量化的核心庫，但在 Windows 上的支援度有時會遇到缺少 `cudart64_XX.dll` 的報錯。
* **解決方法**：如果您在執行 `serve_model.py` 或微調時遇到此類報錯，請安裝社群專為 Windows 編譯的最佳化分支：
  ```bash
  pip uninstall bitsandbytes
  pip install bitsandbytes --index-url https://jllllll.github.io/bitsandbytes-windows-webui
  ```

### 3. Hugging Face 被保護模型之權限申請 (Gated Models)
如果您未選用聯發科的 Breeze-7B，而是改為使用 Meta 的官方模型（例如 `meta-llama/Meta-Llama-3-8B-Instruct`）：
* **申請使用權限**：您必須先在 Hugging Face 官網註冊，進入該模型頁面，點選並同意授權條款以申請存取權限。
* **設定驗證 Token**：
  申請通過後，至 Hugging Face 設定頁面產生一個 `Read` 權限的 Access Token。在執行微調或載入模型前，於終端機登入：
  ```bash
  pip install huggingface_hub
  huggingface-cli login
  ```
  或者在 Python 程式碼中設置環境變數：
  ```python
  import os
  os.environ["HF_TOKEN"] = "您的_HUGGINGFACE_TOKEN"
  ```
  *注意：聯發科的 Breeze-7B 模型目前為公開存取，無需進行上述驗證 Token 設定即可直接下載運行。*

