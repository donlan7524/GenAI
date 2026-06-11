import pandas as pd
import sqlite3
import os
import sys
import db_manager
import nlp_engine
import scraper
from datetime import datetime

# Windows 控制台編碼重設
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

CSV_FILE = "data.csv"
DB_FILE = "nsysu_舆情.db"

def import_csv():
    if not os.path.exists(CSV_FILE):
        print(f"❌ 錯誤：找不到 CSV 檔案 {CSV_FILE}")
        return
        
    print(f"🎬 啟動 CSV 導入管線：讀取 {CSV_FILE} ...")
    
    # 讀取 CSV
    try:
        df = pd.read_csv(CSV_FILE)
    except Exception as e:
        print(f"❌ 讀取 CSV 失敗: {e}")
        return
        
    print(f"📡 成功讀取 {len(df)} 篇貼文資料。正在進行 NLP 情感分析與分類...")
    
    conn = db_manager.get_connection(DB_FILE)
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0
    
    for idx, row in df.iterrows():
        try:
            pid = str(row["post_id"]).strip()
            # 確保 post_id 至少是個合理字元
            if not pid or pid == "nan":
                continue
                
            title = str(row["title"]).strip() if pd.notna(row["title"]) else ""
            content = str(row["content"]).strip() if pd.notna(row["content"]) else ""
            created_at_str = str(row["created_at"]).strip() if pd.notna(row["created_at"]) else ""
            
            # 安全轉換整數，防範投票貼文等欄位偏移
            try:
                like_count = int(float(row["like_count"])) if pd.notna(row["like_count"]) else 0
            except (ValueError, TypeError):
                like_count = 0
                
            try:
                comment_count = int(float(row["comment_count"])) if pd.notna(row["comment_count"]) else 0
            except (ValueError, TypeError):
                comment_count = 0
                
            # 處理日期格式
            try:
                created_at_val = scraper.parse_dcard_date(created_at_str)
            except Exception:
                created_at_val = created_at_str
                
            # NLP 情感分析與分類
            category = scraper.classify_category(title, content, topics=[])
            valence, arousal = nlp_engine.analyze_sentiment(title, content)
            nlp_engine.propagate_sentiment_to_keywords(title, content, valence, arousal, cursor=cursor)
            keywords = nlp_engine.extract_keywords(title, content, limit=5)
            
            # 寫入 posts 表
            cursor.execute("""
            INSERT INTO posts (post_id, title, content, category, created_at, valence_score, arousal_score, like_count, comment_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET
                title=excluded.title,
                content=excluded.content,
                category=excluded.category,
                like_count=excluded.like_count,
                comment_count=excluded.comment_count,
                valence_score=excluded.valence_score,
                arousal_score=excluded.arousal_score
            """, (pid, title, content, category, created_at_val, valence, arousal, like_count, comment_count))
            
            # 寫入 keywords 表
            cursor.execute("DELETE FROM keywords WHERE post_id = ?", (pid,))
            for word in keywords:
                cursor.execute("""
                INSERT OR IGNORE INTO keywords (post_id, word, weight)
                VALUES (?, ?, ?)
                """, (pid, word, 1.0))
                
            success_count += 1
        except Exception as row_err:
            error_count += 1
            print(f"⚠️ 第 {idx+2} 行貼文解析失敗，已跳過。錯誤原因: {row_err}")
            
    conn.commit()
    
    # 重新計算並更新 daily_summary 資料表
    print("📊 正在重新計算並更新每日統計數據 (daily_summary)...")
    cursor.execute("DELETE FROM daily_summary")
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
    conn.close()
    
    print(f"🎉 CSV 數據導入完成！成功處理 {success_count} 篇貼文 (跳過 {error_count} 篇異常貼文) 並寫入 SQLite 資料庫中！")

if __name__ == "__main__":
    import_csv()
