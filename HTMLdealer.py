import os
import json
import csv
import pandas as pd
import db_manager
import nlp_engine
import scraper

def main():
    input_file = "test.json"
    output_file = "scraped_data.txt"
    
    if not os.path.exists(input_file):
        print(f"[Core-Error] ❌ 錯誤：找不到輸入檔案 {input_file}，請先執行 dcard_fetcher.py 獲取資料！")
        return

    print(f"[Python-Core] 🪓 正在載入 Dcard 結構化 JSON 檔案...")

    with open(input_file, "r", encoding="utf-8") as f:
        posts_extracted = json.load(f)

    print(f"[Python-Core] 📡 成功讀取 {len(posts_extracted)} 篇貼文資料（含留言及標籤）。")

    # 💡 遵照指示：寫入純淨的標準表格，使用 standard csv module 防範逗號與引號溢出
    with open(output_file, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["post_id", "title", "content", "created_at", "like_count", "comment_count", "post_url"])
        
        for post in posts_extracted:
            pid = str(post["id"])
            title = post.get("title", "")
            content = post.get("content", "")
            created_at = post.get("createdAt", "")
            like_count = post.get("likeCount", 0)
            comment_count = post.get("commentCount", 0)
            post_url = f"https://www.dcard.tw/f/nsysu/p/{pid}"
            
            writer.writerow([pid, title, content, created_at, like_count, comment_count, post_url])
            print(f"[Python-Core] 🎯 [JSON解析命中] -> ID: {pid} | 標題: {title[:10]}... | 讚數: {like_count} | 留言: {comment_count} | 載入留言數: {len(post.get('comments', []))}")

    print("=" * 75)
    print(f"[Success] 🔥 實體資料解析大功告成！已成功寫入：{output_file}")
    print("=" * 75)
    
    # 💡 【資料庫寫入機制】：直接調用 nlp_engine 與 db_manager 匯入主系統 SQLite
    print("[Python-Core] 📦 正在進行情感分析與關鍵字提取，匯入 SQLite 資料庫中...")
    posts_df_list = []
    all_comments_list = []
    
    for post in posts_extracted:
        pid = str(post["id"])
        title = post.get("title", "")
        content = post.get("content", "")
        topics = post.get("topics", [])
        
        # 處理貼文時間格式
        created_at = post.get("createdAt", "")
        created_at_val = scraper.parse_dcard_date(created_at)
        
        category = scraper.classify_category(title, content, topics)
        valence, arousal = nlp_engine.analyze_sentiment(title, content)
        keywords = nlp_engine.extract_keywords(title, content, limit=5)
        
        posts_df_list.append({
            "post_id": pid,
            "title": title,
            "content": content,
            "category": category,
            "created_at": created_at_val,
            "valence_score": valence,
            "arousal_score": arousal,
            "like_count": post.get("likeCount", 0),
            "comment_count": post.get("commentCount", 0),
            "keywords": keywords
        })
        
        # 處理留言
        comments_list = post.get("comments", [])
        if comments_list and isinstance(comments_list, list):
            for c in comments_list:
                # 排除隱藏、無效或過短的留言
                if c.get("hidden") or not c.get("content") or len(c.get("content", "").strip()) < 2:
                    continue
                    
                c_content = c.get("content", "").strip()
                c_val, c_aro = nlp_engine.analyze_sentiment("", c_content)
                c_time = c.get("createdAt", "")
                c_time_val = scraper.parse_dcard_date(c_time)
                
                all_comments_list.append({
                    "comment_id": f"{pid}_{c.get('floor', 0)}",
                    "post_id": pid,
                    "content": c_content,
                    "floor": c.get("floor", 0),
                    "valence_score": c_val,
                    "arousal_score": c_aro,
                    "created_at": c_time_val
                })
        
    if posts_df_list:
        df_to_save = pd.DataFrame(posts_df_list)
        db_manager.save_posts_to_db(df_to_save)
        print(f"[Success] 🎉 貼文情感分析完成！已成功將 {len(df_to_save)} 筆真實貼文寫入資料庫。")
        
        # 儲存留言到資料庫
        if all_comments_list:
            db_manager.save_comments_to_db(all_comments_list)
            print(f"[Success] 💬 留言情感分析完成！已成功將 {len(all_comments_list)} 筆真實留言寫入資料庫並同步。")
        else:
            print("[Info] 📋 未偵測到任何有效的留言資料。")
    else:
        print("[Warning] ⚠️ 未抓取到任何有效貼文，資料庫未進行寫入。")

if __name__ == "__main__":
    main()
