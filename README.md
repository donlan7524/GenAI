# 國立中山大學社群輿情與情緒起伏儀表板 (Dcard Sentiment Dashboard)

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-資料庫-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![License](https://img.shields.io/badge/用途-學術展示-brightgreen)](/)

本專案為針對國立中山大學 Dcard 校版開發的學術輿情分析儀表板。系統由離散情緒分類全面升級為學術界廣泛認可的 **Valence-Arousal (VA) 二維情緒維度模型**，提供精緻的 HSL 視覺化、2D 象限平面分布圖、情緒百分比分佈條，以及繞過 Cloudflare 防護的瀏覽器書籤採集器。

---

## 📖 目錄

1. [專案背景](#-專案背景)
2. [功能總覽](#-功能總覽)
3. [系統架構](#-系統架構)
4. [NLP 情緒分析引擎與情感模型](#-nlp-情緒分析引擎與情感模型)
5. [資料庫設計](#-資料庫設計)
6. [書籤採集工具](#-書籤採集工具)
7. [安裝與執行](#-安裝與執行)
8. [使用流程](#-使用流程)
9. [隱私與安全說明](#-隱私與安全說明)

---

## 📌 專案背景

本專案為學術用途的 **概念驗證（Proof of Concept）** 系統，旨在探索：
- 中山大學學生在 Dcard 上的主要情緒分佈為何？
- 貼文標題與內文所傳遞的情緒好惡，與留言回應的情緒表現是否存在落差或共鳴？

---

## ✨ 功能總覽

### 📊 儀表板主頁

| 功能區塊 | 說明 |
|----------|------|
| **整體情緒指標卡** | 今日校園氛圍綜合判定（積極興奮 🚀 / 焦慮憤怒 🌋 / 沮喪無奈 ❄️ / 放鬆愜意 🌊） |
| **情緒分佈比例條** | 直觀展示當前篩選數據中，正向/負向偏向（Valence）以及冷靜/激動強度（Arousal）的百分比佔比 |
| **情緒起伏趨勢圖** | 繪製雙折線圖，展示情緒效價（Valence）與情緒喚起（Arousal）隨時間的起伏波動 |
| **2D 輿情象限平面圖** | 以散點圖將貼文標定位在四個情緒象限中，點的尺寸與按讚數呈正相關，支援 Hover 懸停互動 |
| **熱門關鍵字詞雲** | 以 TF-IDF 提取的高頻特徵詞彙雲圖 |

### 💬 留言情緒深度分析

| 功能 | 說明 |
|------|------|
| **留言平均情緒指標** | 留言數、留言平均效價、平均喚起強度與留言主要氛圍指標卡 |
| **留言情緒分佈比例條** | 展示所有已採集留言中，正/負向及冷靜/激動的百分比比例 |
| **各貼文留言分佈圖** | 以分組條型圖對比呈現各貼文留言的平均效價與平均喚起度 |
| **貼文 vs 留言對比圖** | 橫軸為貼文效價，縱軸為留言平均效價，落點偏離對角線代表作者與讀者情緒有落差 |
| **最新留言列表** | 顯示最近採集的留言，附帶百分比化的 NLP 情緒標記（如 `🟢 正向 52.0%` / `🔵 冷靜 51.6%`） |

### 🔍 貼文下鑽搜尋

- 依 **主題分類**（課業 / 感情 / 校務 / 生活）篩選
- 依 **日期範圍** 篩選（可分析期中考週、選課週等特定時期）
- **全文關鍵字搜尋**（如「猴子」、「停水」、「選課」）
- 支援依 **時間、按讚數、喚起激動度、負向度** 等維度進行排序
- 真實貼文卡片附有直連 Dcard 原文連結 🔗

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                     瀏覽器（使用者端）                       │
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

---

## 🧠 NLP 情緒分析引擎與情感模型

系統使用離線、規則式的多維情感字典與繁體中文斷詞引擎。

### 1. 2D Valence-Arousal 情感模型
我們棄用簡單的二元正負情緒或不具空間連續性的離散模型，升級為學術界通用的二維維度模型：
*   **情緒效價 (Valence, 情緒好惡)**：範圍 $[-100.0, 100.0]$。正值代表正向偏向（喜悅、滿意、放鬆），負值代表負向偏向（焦慮、憤怒、沮喪）。
*   **情緒喚起度 (Arousal, 生理激動度)**：範圍 $[-100.0, 100.0]$。正值代表高生理喚起（激動、緊張、亢奮），負值代表低生理喚起（冷靜、放鬆、消極）。

### 2. 百分比轉換公式
為了讓使用者能直觀感受單篇貼文的情感強度，系統將 $[-100.0, 100.0]$ 的原始分數透過以下公式映射為 $[0\%, 100\%]$ 的分佈百分比：
$$\text{百分比} = 50.0\% + \frac{\text{原始分數}}{2.0}$$
*   若 $\text{Valence} \ge 0$，顯示 `🟢 正向 P%`；若 $< 0$，顯示 `🔴 負向 P%`。
*   若 $\text{Arousal} \ge 0$，顯示 `🟠 激動 P%`；若 $< 0$，顯示 `🔵 冷靜 P%`。

### 3. 校園特定特徵詞彙
結合 [Jieba](https://github.com/fxsjy/jieba) 斷詞，系統登錄了中山大學特有詞彙（如「柴山獼猴」、「選課系統」、「停水」），並針對特定校園事件註冊了專屬的情感權重向量偏移（Bias），例如：
*   「停水」、「宿網斷線」：極高負效價、高喚起（焦慮憤怒）
*   「選課當機」：高負效價、高喚起（焦慮）
*   「西子灣看夕陽」：高正效價、低喚起（平靜放鬆）

---

## 🗄️ 資料庫設計

資料庫採用 SQLite（`nsysu_輿情.db`），包含以下結構：

```sql
-- 貼文主表
CREATE TABLE posts (
    post_id       TEXT PRIMARY KEY,  -- Dcard 文章 ID（真實貼文為純數字，模擬為 M_ 開頭）
    title         TEXT,
    content       TEXT,
    category      TEXT,              -- 課業 / 感情 / 校務 / 生活
    created_at    TEXT,
    valence_score REAL DEFAULT 0.0,  -- 效價分數 [-100.0, 100.0]
    arousal_score REAL DEFAULT 0.0,  -- 喚起度分數 [-100.0, 100.0]
    like_count    INTEGER,
    comment_count INTEGER
);

-- 關鍵字表
CREATE TABLE keywords (
    post_id TEXT,
    word    TEXT,
    weight  REAL,
    PRIMARY KEY (post_id, word),
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
);

-- 留言表
CREATE TABLE comments (
    comment_id    TEXT PRIMARY KEY,
    post_id       TEXT NOT NULL,
    content       TEXT,
    floor         INTEGER,
    valence_score REAL DEFAULT 0.0,
    arousal_score REAL DEFAULT 0.0,
    created_at    TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
);

-- 每日統計快取表
CREATE TABLE daily_summary (
    date        TEXT PRIMARY KEY,
    avg_valence REAL DEFAULT 0.0,
    avg_arousal REAL DEFAULT 0.0,
    total_posts INTEGER
);
```

---

## ⚡ 書籤採集工具

為繞過 Dcard 對自動化爬蟲的 Cloudflare WAF 阻擋，系統採用**同源 JavaScript 瀏覽器書籤**採集資料：

1.  **書籤 A（大量貼文採集）**：前往 Dcard 中山大學版面點擊，腳本將呼叫 Dcard 原生相對路徑 API `/_api/forums/{forumName}/posts` 並帶上標頭 `'x-client-type': 'web'` 來模擬官方前端載入。
2.  **書籤 B（單篇留言採集）**：前往單篇 Dcard 貼文頁面點擊，呼叫相對路徑 API `/_api/posts/{postId}/comments` 下載該文所有留言。
3.  **資料同步**：書籤採集到的資料會被發送至本地後端伺服器（Port 8002），透過 NLP 引擎分析後安全寫入 SQLite 資料庫中。

---

## 🚀 安裝與執行

### 1. 安裝相依套件
請於終端機執行：
```bash
pip install streamlit pandas plotly jieba wordcloud curl_cffi
```

### 2. 啟動儀表板
```bash
streamlit run app.py
```
執行後瀏覽器將自動開啟 `http://localhost:8501`。後台接收伺服器會在背景啟動並監聽 `http://127.0.0.1:8002`，系統會在 Streamlit 重載時自動釋放並重啟埠口，防止執行緒衝突。

---

## 📋 使用流程

```
 執行 streamlit run app.py 啟動系統
 │
 ├─ 1. 在儀表板側邊欄「⚡ Dcard 書籤工具」區塊中：
 │      ├─ 複製「書籤 A」代碼，建立瀏覽器書籤（命名：Dcard 大量採集）
 │      └─ 複製「書籤 B」代碼，建立瀏覽器書籤（命名：Dcard 留言採集）
 │
 ├─ 2. 在瀏覽器中開啟 Dcard 中山大學看板 (https://www.dcard.tw/f/nsysu)
 │      └─ 點擊瀏覽器中的「Dcard 大量採集」書籤 
 │             → 等待數秒出現「🎉 同步成功」提示後，切回儀表板重整頁面 (F5)
 │
 └─ 3. 點擊儀表板中任一篇真實貼文連結 🔗 開啟 Dcard 原文頁面
        └─ 待留言載入完成後，點擊「Dcard 留言採集」書籤
               → 看到「💬 留言同步成功」後即可在儀表板底部看到該文的留言情緒對比分析！
```

---

## 🛡️ 隱私與安全說明

1.  **本地運作**：所有資料皆儲存於本地 SQLite，情感引擎採用離線計算，無外部雲端資料洩漏風險。
2.  **安全設定**：敏感設定檔 `config.json` 與資料庫檔案已寫入 `.gitignore`，確保不會意外推播至公開儲存庫。
3.  **本機伺服器熱重載保護**：背景 HTTPServer 引入了執行緒生命週期追蹤，重啟服務時會先安全釋放舊埠口，保證代碼熱更新正常執行。
