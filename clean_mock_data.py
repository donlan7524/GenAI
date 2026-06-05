import sqlite3
import os
import sys

# Windows 控制台編碼重設
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DB_FILE = "nsysu_舆情.db"

def clean_mock_data():
    if not os.path.exists(DB_FILE):
        print(f"❌ 找不到資料庫檔案 {DB_FILE}。")
        return
        
    print(f"🧹 正在從 SQLite 資料庫 ({DB_FILE}) 中清除所有假資料 (ID 開頭為 M_)...")
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. 取得刪除前筆數
        cursor.execute("SELECT count(*) FROM posts WHERE post_id LIKE 'M_%'")
        mock_posts_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT count(*) FROM comments WHERE post_id LIKE 'M_%'")
        mock_comments_count = cursor.fetchone()[0]
        
        if mock_posts_count == 0:
            print("ℹ️ 資料庫中已無任何 ID 開頭為 M_ 的假貼文，無需清除。")
            return
            
        # 2. 刪除假資料
        print(f"🗑️ 正在刪除 {mock_posts_count} 篇假貼文與 {mock_comments_count} 筆假留言...")
        cursor.execute("DELETE FROM comments WHERE post_id LIKE 'M_%'")
        cursor.execute("DELETE FROM keywords WHERE post_id LIKE 'M_%'")
        cursor.execute("DELETE FROM posts WHERE post_id LIKE 'M_%'")
        conn.commit()
        
        # 3. 重新計算並更新 daily_summary 資料表
        print("📊 正在重新計算並更新每日情緒統計數據 (daily_summary)...")
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
        
        # 4. 收縮資料庫以釋放硬碟空間
        cursor.execute("VACUUM")
        conn.commit()
        
        print("🎉 假資料已成功清除，且實體 Dcard 數據的統計值已重新計算完成！")
        
    except Exception as e:
        print(f"❌ 清除假資料時發生錯誤: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    clean_mock_data()
