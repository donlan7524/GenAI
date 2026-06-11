import sqlite3
import nlp_engine
import sys

# Windows console encoding helper
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DB_FILE = "nsysu_舆情.db"

def main():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. 取得舊的中性貼文統計
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_posts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM posts WHERE ABS(valence_score - 5.0) < 2.0")
    old_neutral_posts = cursor.fetchone()[0]
    
    print(f"📊 目前資料庫中共有 {total_posts} 篇貼文。")
    print(f"👉 舊情緒分析下，中性貼文（Valence 接近 5.0）數量：{old_neutral_posts} 篇 ({old_neutral_posts/total_posts*100:.1f}%)")
    
    # 2. 開始重算 posts 情緒分數
    print("🔄 正在重新計算所有貼文的情緒分數...")
    cursor.execute("SELECT post_id, title, content FROM posts")
    posts = cursor.fetchall()
    
    for post_id, title, content in posts:
        val, aro = nlp_engine.analyze_sentiment(title, content)
        cursor.execute("""
            UPDATE posts 
            SET valence_score = ?, arousal_score = ? 
            WHERE post_id = ?
        """, (val, aro, post_id))
        
        # 將計算出來的情緒自動傳播給該篇貼文的關鍵字，並傳遞給後續貼文計算
        nlp_engine.propagate_sentiment_to_keywords(title, content, val, aro, cursor=cursor)
        
    conn.commit()
    print("✅ 貼文情緒分數更新完成且自學習情緒傳播完畢！")
    
    # 3. 開始重算 comments 情緒分數
    print("🔄 正在重新計算所有留言的情緒分數...")
    cursor.execute("SELECT comment_id, content FROM comments")
    comments = cursor.fetchall()
    
    for comment_id, content in comments:
        val, aro = nlp_engine.analyze_sentiment("", content)
        cursor.execute("""
            UPDATE comments 
            SET valence_score = ?, arousal_score = ? 
            WHERE comment_id = ?
        """, (val, aro, comment_id))
        
    conn.commit()
    print("✅ 留言情緒分數更新完成！")
    
    # 4. 重新計算並更新 daily_summary 資料表
    print("📊 正在更新每日情緒統計 (daily_summary)...")
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
    print("✅ 每日情緒統計更新完成！")
    
    # 5. 取得新的中性貼文統計
    cursor.execute("SELECT COUNT(*) FROM posts WHERE ABS(valence_score - 5.0) < 2.0")
    new_neutral_posts = cursor.fetchone()[0]
    print(f"👉 新情緒分析下，中性貼文（Valence 接近 5.0）數量：{new_neutral_posts} 篇 ({new_neutral_posts/total_posts*100:.1f}%)")
    
    # 6. VACUUM
    print("🧹 執行資料庫重組 (VACUUM)...")
    cursor.execute("VACUUM")
    conn.commit()
    conn.close()
    print("🎉 所有操作順利完成！資料庫更新已就緒。")

if __name__ == "__main__":
    main()
