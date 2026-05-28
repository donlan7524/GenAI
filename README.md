# 情緒分析儀表板
其readme內容為AI產生，並未進行整理。   

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-資料庫-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/用途-學術展示-brightgreen)](/)


---

## 📖 目錄

1. [專案背景](#-專案背景)
2. [功能總覽](#-功能總覽)
3. [系統架構](#-系統架構)
4. [NLP 情緒分析引擎](#-nlp-情緒分析引擎)
5. [資料庫設計](#-資料庫設計)
6. [書籤採集工具](#-書籤採集工具)
7. [安裝與執行](#-安裝與執行)
8. [使用流程](#-使用流程)
9. [隱私說明](#-隱私說明)
10. [開發限制與未來展望](#-開發限制與未來展望)

---

## 📌 專案背景

本專案為學術用途的 **概念驗證（Proof of Concept）** 系統，旨在探索：


**研究問題：**
- 中山大學學生在 Dcard 上的主要情緒分佈為何？
- 貼文標題所傳遞的情緒，是否與留言回應的情緒一致？

---

## ✨ 功能總覽

### 📊 儀表板主頁

| 功能區塊 | 說明 |
|----------|------|
| **整體情緒指標卡** | 歡樂 / 焦慮 / 憤怒三維情緒的加權平均百分比，以及最高互動貼文統計 |
| **情緒分佈圓餅圖** | 當前篩選期間內，三種情緒在所有貼文中的總佔比 |
| **每日情緒趨勢折線圖** | 可觀察情緒隨時間的變化，例如期中考前後的焦慮曲線攀升 |
| **類別情緒雷達圖** | 比較課業、感情、校務、生活四大類別在三種情緒上的平均分佈 |
| **熱門關鍵字詞雲** | 以 TF-IDF 提取的高頻詞彙，字體大小代表詞頻權重 |
| **按讚數 vs 情緒散點圖** | 探索高互動貼文的情緒特徵 |

### 💬 留言情緒深度分析（頁面底部）

| 功能 | 說明 |
|------|------|
| **留言情緒橫條圖** | 每篇已採集留言的貼文，其所有留言的平均歡樂/焦慮/憤怒分佈 |
| **貼文 vs 留言情緒落差散點圖** | X 軸為貼文本身焦慮分，Y 軸為留言平均焦慮分，落點偏離對角線越遠，代表讀者與原作者的情緒感受落差越大 |
| **最新留言列表** | 顯示最近採集的留言，含 NLP 情緒標記（🟢歡樂 / 🟡焦慮 / 🔴憤怒） |

### 🔍 貼文下鑽搜尋

- 依**主題分類**篩選（課業 / 感情 / 校務 / 生活）
- 依**日期範圍**篩選（可分析特定時期，如期中考週）
- **全文關鍵字搜尋**（如「猴子」、「停水」、「選課」）
- 依**按讚數、發文時間、焦慮分數、憤怒分數**排序
- 真實貼文附有 Dcard 原文連結 🔗

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                     瀏覽器（使用者）                          │
│  ┌──────────────┐          ┌───────────────────────────────┐ │
│  │  Dcard 網站  │          │  Streamlit 儀表板             │ │
│  │  (書籤執行)  │          │  app.py                       │ │
│  └──────┬───────┘          └────────────┬──────────────────┘ │
│         │ HTTP POST                      │                    │
│         │ (JSON)                         │ 讀取/渲染           │
└─────────┼────────────────────────────────┼────────────────────┘
          │                                │
          ▼                                ▼
   ┌──────────────┐              ┌──────────────────┐
   │ HTTPServer   │              │  SQLite 資料庫    │
   │ Port 8002    │──寫入──────▶│  nsysu_輿情.db   │
   │ (背景執行緒) │              │                  │
   └──────┬───────┘              │  - posts         │
          │                      │  - comments      │
          │ 呼叫                 │  - keywords      │
          ▼                      │  - daily_summary │
   ┌──────────────┐              └──────────────────┘
   │  scraper.py  │
   │  (解析JSON)  │──呼叫──▶  nlp_engine.py
   └──────────────┘           (情緒分析 + 關鍵字)
```

### 各模組職責

| 檔案 | 職責 |
|------|------|
| `app.py` | Streamlit 前端渲染、側邊欄控制、HTTPServer 背景執行緒（Port 8002）接收書籤 POST |
| `scraper.py` | JSON 解析、`import_raw_json()`、`import_comments_json()`、Dcard API 採集（備用）|
| `db_manager.py` | SQLite CRUD、`init_db()`、`save_posts_to_db()`、`save_comments_to_db()`、`load_data_from_db()` |
| `nlp_engine.py` | 繁中斷詞（Jieba）、TF-IDF 關鍵字提取、三維情緒詞典專家系統 |

---

## 🧠 NLP 情緒分析引擎

本系統採用**全離線、規則式情緒詞典專家系統**，無需外部 API 即可穩定運作。

### 斷詞與關鍵字提取

使用 [Jieba](https://github.com/fxsjy/jieba) 進行繁體中文斷詞，並以 **TF-IDF 演算法**提取每篇貼文的前 5 個代表性關鍵詞。

為確保中山大學特有詞彙（如地名、校園事件）不被切碎，系統預先註冊了以下自訂詞：

> 西子灣、翠亨宿舍、武嶺宿舍、柴山獼猴、選課系統、期中考古題、雙主修、通識課、草地音樂會、逸仙館、渡船頭、海之冰 …等

### 三維情緒模型

情緒分析採用三個並行維度（而非正/負二元分類），每個維度獨立計分後進行歸一化，使三者加總恆等於 100%：

| 維度 | 代表性觸發詞（部分） | 特殊校園事件加權 |
|------|----------------------|------------------|
| 🟢 **歡樂** | 開心、推薦、告白成功、音樂會、夕陽… | 告白 / 西子灣夕陽 → +50 分 |
| 🟡 **焦慮** | 爆肝、崩潰、期中考、微積分、二一… | 期末考 / 選課當機 → +35～40 分 |
| 🔴 **憤怒** | 停水、幹、超爛、氣死、態度差… | 停水 → +40 分；獼猴搶食 → +20 分 |

**計分流程：**
```
1. 基礎詞頻計數 × 權重係數
2. 加上校園特殊事件加權分
3. 加入小幅隨機噪聲（±4 分，增加擬真度）
4. 裁剪至 [0, 100] 範圍
5. 歸一化：三維度加總 → 各自除以總分 × 100%
```

---

## 🗄️ 資料庫設計

使用 **SQLite** 單一檔案資料庫（`nsysu_輿情.db`），包含四張資料表：

```sql
-- 貼文主表
CREATE TABLE posts (
    post_id       TEXT PRIMARY KEY,  -- Dcard 文章 ID（真實貼文為純數字）
    title         TEXT,
    content       TEXT,
    category      TEXT,              -- 課業 / 感情 / 校務 / 生活
    created_at    TEXT,
    joy_score     REAL,              -- 歡樂佔比 (0-100%)
    anxiety_score REAL,              -- 焦慮佔比 (0-100%)
    anger_score   REAL,              -- 憤怒佔比 (0-100%)
    like_count    INTEGER,
    comment_count INTEGER
);

-- 關鍵字表（一對多，每篇貼文最多 5 個）
CREATE TABLE keywords (
    post_id TEXT,
    word    TEXT,
    weight  REAL,
    PRIMARY KEY (post_id, word)
);

-- 留言表（書籤 B 採集後寫入）
CREATE TABLE comments (
    comment_id    TEXT PRIMARY KEY,   -- post_id + 樓層號
    post_id       TEXT,
    content       TEXT,
    floor         INTEGER,            -- 留言樓層
    joy_score     REAL,
    anxiety_score REAL,
    anger_score   REAL,
    created_at    TEXT
);

-- 每日情緒統計快取（自動重算）
CREATE TABLE daily_summary (
    date        TEXT PRIMARY KEY,
    avg_joy     REAL,
    avg_anxiety REAL,
    avg_anger   REAL,
    total_posts INTEGER
);
```

---

## ⚡ 書籤採集工具

由於 Dcard 設有 Cloudflare WAF 防護，直接的 HTTP 爬蟲請求會被封鎖（403 Forbidden）。本系統採用**瀏覽器書籤 JavaScript** 作為資料採集橋接，合法地讀取使用者瀏覽器中已渲染的 DOM 內容。

### 書籤 A：大量貼文採集（自動滾動）

- **觸發時機**：在 `dcard.tw/f/nsysu`（中山大學版面）點擊
- **運作原理**：
  1. 掃描頁面上所有 `<a href>` 找出 `/p/{post_id}` 格式的連結
  2. 從連結的父層 DOM 容器向上爬找標題元素（最多 6 層）
  3. 自動 `window.scrollTo(bottom)` 觸發無限捲動載入新貼文
  4. 重複 8 輪，每輪等待 1.8 秒讓 React 渲染完成
  5. 蒐集完成後一次性 POST 至 `http://127.0.0.1:8002/import`
- **目標產出**：單次執行採集 **50～100+ 篇**貼文（依網速而定）

### 書籤 B：單篇貼文留言採集

- **觸發時機**：在 `dcard.tw/f/nsysu/p/{post_id}`（個別貼文頁面）點擊
- **運作原理**：
  1. 從 URL 解析當前 `post_id`
  2. 以多種 CSS 選擇器（`[class*=comment]`、葉節點文字）掃描頁面上的留言元素
  3. 過濾掉 UI 按鈕文字（「讚」「回覆」「檢舉」等）
  4. POST 至 `http://127.0.0.1:8002/import_comments`
- **目標產出**：採集該篇貼文的所有可見留言並進行 NLP 情緒分析

### 資料接收伺服器

儀表板啟動時，會在背景執行緒自動開啟一個 `HTTPServer` 監聽 Port **8002**：

| 路由 | 方法 | 功能 |
|------|------|------|
| `/import` | POST | 接收書籤 A 的貼文 JSON，呼叫 `scraper.import_raw_json()` 解析後存入 DB |
| `/import_comments` | POST | 接收書籤 B 的留言 JSON，呼叫 `scraper.import_comments_json()` 進行 NLP 後存入 DB |

---

## 🚀 安裝與執行

### 環境需求

- Python **3.9 或以上**
- 現代瀏覽器（Chrome / Edge / Firefox）

### 安裝相依套件

```bash
pip install streamlit pandas plotly jieba wordcloud curl_cffi
```

| 套件 | 用途 |
|------|------|
| `streamlit` | 互動式資料儀表板框架 |
| `pandas` | 資料處理與 SQLite 查詢結果轉換 |
| `plotly` | 互動式圖表（折線圖、圓餅圖、散點圖、雷達圖）|
| `jieba` | 繁體中文斷詞引擎 |
| `wordcloud` | 關鍵字詞雲生成 |
| `curl_cffi` | 模擬瀏覽器 TLS 握手的 HTTP 客戶端（備用 API 採集用）|

### 啟動儀表板

```bash
# 在專案目錄下執行
streamlit run app.py
```

瀏覽器會自動開啟 `http://localhost:8501`，同時背景伺服器會監聽 Port **8002**。

---

## 📋 使用流程

```
第一次使用
│
├─ 1. 執行 streamlit run app.py
│
├─ 2. 在側邊欄展開「⚡ Dcard 書籤工具」
│      ├─ 複製「書籤 A」代碼 → 建立瀏覽器書籤（命名：Dcard 大量採集）
│      └─ 複製「書籤 B」代碼 → 建立瀏覽器書籤（命名：Dcard 留言採集）
│
├─ 3. 開啟 https://www.dcard.tw/f/nsysu
│      └─ 點擊「書籤 A」→ 等待藍色進度條自動滾動（約 15 秒）
│             → 看到「🎉 已儲存 N 篇」後切回儀表板按 F5
│
└─ 4. 在儀表板點擊任一真實貼文連結 🔗
       └─ 等頁面與留言全部載入後，點擊「書籤 B」
              → 看到「💬 已儲存 N 則留言」後切回儀表板底部查看
```

---

## 🛡️ 隱私說明

1. **不採集個人資訊**：系統僅記錄貼文的公開標題、內容摘要與情緒分數，不儲存任何使用者帳號、頭像或個人識別資料。
2. **敏感檔案不上傳**：`config.json`（可能含瀏覽器 Cookie）與 `.db` 資料庫檔案已加入 `.gitignore`，不會出現在版本庫中。
3. **僅限學術研究**：本工具蒐集的資料僅供課程研究展示，不作任何商業用途。
4. **資料來源為公開看板**：Dcard 中山大學板為公開板面，任何人皆可匿名瀏覽，本工具僅自動化讀取使用者已可見之內容。

---

## 🔭 開發限制與未來展望

### 當前限制

| 限制 | 說明 |
|------|------|
| **Cloudflare WAF** | Dcard 使用 Cloudflare 防護，直接程式請求會被封鎖（403），目前透過書籤繞過 |
| **情緒詞典覆蓋率** | 規則式詞典對新詞、諷刺語氣、表情符號的辨識能力有限 |
| **留言 DOM 結構** | Dcard 為 React 應用，DOM 結構可能隨版本更新而改變，書籤需相應調整 |
| **歷史資料有限** | 書籤只能採集當下頁面上的貼文，無法回溯歷史資料 |

）
