import os
import re
import sqlite3
import sys
import pandas as pd
from datetime import datetime

# Windows 控制台編碼重設
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 加入專案目錄到 path 確保導入正常
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db_manager
import nlp_engine
import scraper

DB_FILE = "nsysu_舆情.db"
CSV_FILE = "content.csv"

def clear_db(cursor):
    print("🧹 正在清空資料庫中的舊資料...")
    # 清空所有主要表格
    tables = ["posts", "comments", "keywords", "daily_summary", "virtual_posts", "virtual_comments", "virtual_notifications", "custom_lexicon"]
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"  - 清空表格 {table}")
        except sqlite3.OperationalError as e:
            # 有些虛擬表可能不存在，略過即可
            print(f"  - 跳過表格 {table} (原因: {e})")

def parse_and_import():
    if not os.path.exists(CSV_FILE):
        print(f"❌ 錯誤：找不到 CSV 檔案 {CSV_FILE}")
        return

    # 連接資料庫並初始化
    print(f"🎬 啟動資料庫重設與資料導入管線...")
    db_manager.init_db(DB_FILE)
    conn = db_manager.get_connection(DB_FILE)
    cursor = conn.cursor()

    # 清空資料庫
    clear_db(cursor)
    conn.commit()

    print(f"📖 正在用 pandas 解析 {CSV_FILE}（標準單行格式）...")

    # 新版 CSV 為標準格式：每篇貼文一行，直接用 pandas 讀取
    try:
        df = pd.read_csv(CSV_FILE, encoding='utf-8', dtype=str, keep_default_na=False)
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig', dtype=str, keep_default_na=False)

    # 欄位名稱正規化（去除 BOM 或多餘空格）
    df.columns = df.columns.str.strip().str.lstrip('\ufeff')

    # 確認必要欄位存在
    required = ['post_id', 'title', 'content', 'created_at', 'like_count', 'comment_count']
    for col in required:
        if col not in df.columns:
            print(f"❌ 缺少必要欄位：{col}，請確認 CSV 格式。現有欄位：{list(df.columns[:10])}")
            conn.close()
            return

    # 找出所有留言欄（comment001 ~ comment100）
    comment_cols = [c for c in df.columns if c.startswith('comment')]

    print(f"✅ 解析完成！共偵測到 {len(df)} 篇貼文，留言欄位 {len(comment_cols)} 個。正在匯入資料庫...")

    post_success = 0
    comment_success = 0

    for idx, row in df.iterrows():
        try:
            pid = str(row['post_id']).strip()
            title = str(row['title']).strip()
            content = str(row['content']).strip()
            created_at = str(row['created_at']).strip()
            like_count = int(row['like_count']) if str(row['like_count']).isdigit() else 0
            comment_count = int(row['comment_count']) if str(row['comment_count']).isdigit() else 0

            # 解析分類
            category = scraper.classify_category(title, content, topics=[])

            # NLP 情感分析與自學習傳播
            valence, arousal = nlp_engine.analyze_sentiment(title, content)
            nlp_engine.propagate_sentiment_to_keywords(title, content, valence, arousal, cursor=cursor)
            keywords = nlp_engine.extract_keywords(title, content, limit=5)

            # 寫入 posts 表
            cursor.execute("""
            INSERT INTO posts (post_id, title, content, category, created_at, valence_score, arousal_score, like_count, comment_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (pid, title, content, category, created_at, valence, arousal, like_count, comment_count))

            # 寫入 keywords 表
            for word in keywords:
                cursor.execute("""
                INSERT OR IGNORE INTO keywords (post_id, word, weight)
                VALUES (?, ?, ?)
                """, (pid, word, 1.0))

            post_success += 1

            # 處理留言匯入
            for floor, col in enumerate(comment_cols, start=1):
                comment_content = str(row.get(col, '')).strip()
                if comment_content and comment_content.lower() != 'nan':
                    cid = f"{pid}_{floor}"
                    c_val, c_aro = nlp_engine.analyze_sentiment("", comment_content)

                    try:
                        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                        c_time = (dt + pd.Timedelta(seconds=floor * 10)).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        c_time = created_at

                    cursor.execute("""
                    INSERT INTO comments (comment_id, post_id, content, floor, valence_score, arousal_score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (cid, pid, comment_content, floor, c_val, c_aro, c_time))
                    comment_success += 1

        except Exception as e:
            print(f"⚠️ 匯入第 {idx+1} 筆時出錯 (ID: {row.get('post_id', '?')}): {e}")

    conn.commit()

    # 重新計算 daily_summary
    print("📊 正在更新每日情緒統計 (daily_summary)...")
    cursor.execute("""
    INSERT INTO daily_summary (date, avg_valence, avg_arousal, total_posts)
    SELECT
        strftime('%Y-%m-%d', created_at) as post_date,
        round(avg(valence_score), 1) as avg_valence,
        round(avg(arousal_score), 1) as avg_arousal,
        count(*) as total_posts
    FROM posts
    GROUP BY post_date
    """)
    conn.commit()

    # VACUUM 資料庫
    print("🧹 執行資料庫重組 (VACUUM)...")
    cursor.execute("VACUUM")
    conn.commit()

    conn.close()

    print(f"🎉 導入完畢！成功寫入 {post_success} 篇貼文與 {comment_success} 則留言到 {DB_FILE} 中！")

if __name__ == "__main__":
    parse_and_import()
