from curl_cffi import requests
import pandas as pd
from datetime import datetime, timedelta
import random
import time
import json
import os
import db_manager
import nlp_engine

DCARD_NSYSU_API = "https://www.dcard.tw/service/api/v2/forums/nsysu/posts?limit=50"

def load_config():
    config_file = "config.json"
    default_config = {
        "dcard_cookie": "",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if not os.path.exists(config_file):
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return default_config
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_config

def save_config(config):
    config_file = "config.json"
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def classify_category(title, content, topics):
    """
    依據貼文標題、內容與 Dcard 標籤，分類至四大主題 (課業、感情、校務、生活)。
    """
    text = f"{title} {content} {' '.join(topics)}".lower()
    
    # 課業關鍵字
    academic_keywords = ["學分", "選課", "選修", "必修", "通識", "期中", "期末", "考古題", "微積分", "線性代數", "教授", "加簽", "考試", "成績", "資工", "電機"]
    # 感情關鍵字
    love_keywords = ["告白", "閃光", "女友", "男友", "脫單", "感情", "愛情", "分手", "約會", "聯誼", "曖昧", "學妹", "學長", "閃光", "情侶"]
    # 校務關鍵字
    admin_keywords = ["宿舍", "翠亨", "武嶺", "停水", "停電", "行政大樓", "學生會", "宿網", "公車", "辦事", "教務處", "學雜費", "學校", "行政效率"]
    
    if any(k in text for k in academic_keywords):
        return "課業"
    elif any(k in text for k in love_keywords):
        return "感情"
    elif any(k in text for k in admin_keywords):
        return "校務"
    else:
        return "生活" # 預設分類 (如猴子搶食、學餐、渡船頭美食等)

def run_scraper(db_path=db_manager.DB_FILE):
    """
    執行爬蟲主程序。嘗試從 Dcard 爬取真實資料；
    若 API 連線失敗 (如 Cloudflare 封鎖或無網路)，會自動啟用 Fallback 寫入擬真學術資料，確保系統不斷線。
    """
    print("[Info] 開始執行 Dcard 中山大學校版輿情採集程式...")
    db_manager.init_db(db_path)
    
    config = load_config()
    cookie_str = config.get("dcard_cookie", "").strip()
    user_agent = config.get("user_agent", "").strip()
    
    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent
    if cookie_str:
        headers["Cookie"] = cookie_str
        
    scraped_posts = []
    
    try:
        # 1. 嘗試發送請求至 Dcard API (使用 curl_cffi 模擬 Chrome 120 TLS 握手與自訂 Cookie)
        response = requests.get(DCARD_NSYSU_API, headers=headers, impersonate="chrome120", timeout=8)
        
        if response.status_code == 200:
            posts_list = response.json()
            print(f"[Info] 成功讀取 Dcard API 貼文列表，共計 {len(posts_list)} 篇貼文。")
            
            for p in posts_list:
                post_id = str(p["id"])
                title = p.get("title", "")
                excerpt = p.get("excerpt", "")
                topics = p.get("topics", [])
                
                # 嘗試爬取更詳細的內文 (Dcard 單篇貼文 API)
                content = excerpt
                try:
                    # 限制一下爬取頻率，防止被封锁
                    time.sleep(0.5)
                    detail_url = f"https://www.dcard.tw/service/api/v2/posts/{post_id}"
                    detail_resp = requests.get(detail_url, headers=headers, impersonate="chrome120", timeout=5)
                    if detail_resp.status_code == 200:
                        detail_data = detail_resp.json()
                        content = detail_data.get("content", excerpt)
                except Exception:
                    pass # 若獲取內文細節失敗，以 excerpt 替代
                
                # 解析時間 (Dcard 回傳 ISO 8601 格式，如 '2026-05-28T13:30:00.000Z')
                created_at_str = p.get("createdAt", "")
                try:
                    # 轉換為標準格式寫入
                    dt = datetime.strptime(created_at_str.replace("T", " ").replace(".000Z", ""), "%Y-%m-%d %H:%M:%S")
                    # 轉換成台灣時間 (UTC+8)
                    dt_tw = dt + pd.Timedelta(hours=8)
                    created_at_val = dt_tw.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    created_at_val = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 分類
                category = classify_category(title, content, topics)
                
                # NLP 計算情緒分數與關鍵字
                joy, anxiety, anger = nlp_engine.analyze_sentiment(title, content)
                keywords = nlp_engine.extract_keywords(title, content, limit=5)
                
                scraped_posts.append({
                    "post_id": post_id,
                    "title": title,
                    "content": content,
                    "category": category,
                    "created_at": created_at_val,
                    "joy_score": joy,
                    "anxiety_score": anxiety,
                    "anger_score": anger,
                    "like_count": p.get("likeCount", 0),
                    "comment_count": p.get("commentCount", 0),
                    "keywords": keywords
                })
                
            df_scraped = pd.DataFrame(scraped_posts)
            db_manager.save_posts_to_db(df_scraped, db_path)
            print(f"[Success] 成功處理 {len(df_scraped)} 筆真實 Dcard 貼文並更新至資料庫！")
            return True, len(df_scraped), "REAL_API"
            
        else:
            print(f"[Warning] Dcard API 回傳狀態碼異常：{response.status_code}。將啟動本機 Mock Seeder...")
            
    except Exception as e:
        print(f"[Warning] 連線至 Dcard API 時發生異常：{str(e)}。將啟動本機 Mock Seeder...")
        
    # ----------------------------------------------------
    # Fallback 專家模擬寫入程序 (Offline / Blocked Mode)
    # ----------------------------------------------------
    fallback_posts = []
    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(30)]
    
    mock_titles_contents = [
        ("柴山獼猴搶走我的肉蛋吐司，真的很無言", "才剛從翠亨舍下山準備吃早餐，一隻大公猴直接把我手上的袋子扯壞搶走。有沒有人有防猴秘訣？", "生活"),
        ("選課系統又爆了，學校行政效率到底在哪？", "點進去一直轉圈圈，點到了又送不出去，熱門微積分直接被搶光，我要怎麼畢業？😭", "校務"),
        ("翠亨宿舍又停水了，滿頭肥皂泡在吹風", "洗澡洗到一半直接斷水，打給舍監室也沒人理，這學期第三次了，可以退宿費嗎？氣死！", "校務"),
        ("告白成功！西子灣夕陽神助攻 🌅", "帶同系女生去堤防吹風看日落，氣氛剛好就告白了，她害羞點頭！感謝西子灣夕陽！", "感情"),
        ("微積分期中考集中取暖區", "線性代數跟微積分完全看不懂，圖書館自習室冷氣開超冷，有沒有考古題可以分享？", "課業"),
        ("渡船頭大碗公冰到底哪家才是正宗？", "海之冰還是福泉？這週天氣好熱，想跟室友去大吃一頓消暑！", "生活"),
        ("學生會這次辦的草地音樂節很給力", "聽著樂團吹海風超爽，比起之前辦的活動好太多了，工作人員辛苦了！", "校務"),
        ("上了大學真的比較難脫單嗎？", "每天生活除了微積分就是待在宿舍打代碼，工學院男女比太懸殊，感覺四年都要單身了。", "感情")
    ]
    
    post_id_counter = 50001
    for date in dates:
        # 每天模擬 2 到 5 篇
        num_posts = random.randint(2, 5)
        # 模擬期中考週
        days_ago = (datetime.now() - date).days
        is_midterm = (2 <= days_ago <= 4)
        
        for _ in range(num_posts):
            title, content, category = random.choice(mock_titles_contents)
            
            # 計算情緒分數 (採用 nlp_engine 的標準歸一化分數)
            joy, anxiety, anger = nlp_engine.analyze_sentiment(title, content)
            
            likes = random.randint(5, 150)
            if is_midterm and category == "校務":
                likes = random.randint(150, 350)
                
            comments = random.randint(1, int(likes * 0.5) + 2)
            
            # 隨機化時間
            post_time = date - timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
            keywords = nlp_engine.extract_keywords(title, content, limit=5)
            
            fallback_posts.append({
                "post_id": f"M_{post_id_counter}",
                "title": title,
                "content": content,
                "category": category,
                "created_at": post_time.strftime("%Y-%m-%d %H:%M:%S"),
                "joy_score": round(joy, 1),
                "anxiety_score": round(anxiety, 1),
                "anger_score": round(anger, 1),
                "like_count": likes,
                "comment_count": comments,
                "keywords": keywords
            })
            post_id_counter += 1
            
    df_fallback = pd.DataFrame(fallback_posts)
    db_manager.save_posts_to_db(df_fallback, db_path)
    print(f"[Fallback] 已透過 Mock Seeder 生成並儲存 {len(df_fallback)} 筆擬真數據至資料庫！")
    return True, len(df_fallback), "MOCK_FALLBACK"

def import_raw_json(json_str, db_path=db_manager.DB_FILE):
    """
    解析使用者貼入的 Dcard JSON 內容並寫入資料庫，繞過 Cloudflare 阻擋。
    """
    try:
        data = json.loads(json_str)
        posts_list = []
        if isinstance(data, list):
            posts_list = data
        elif isinstance(data, dict):
            if "posts" in data and isinstance(data["posts"], list):
                posts_list = data["posts"]
            elif "items" in data and isinstance(data["items"], list):
                posts_list = data["items"]
            else:
                for k, v in data.items():
                    if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and "id" in v[0]:
                        posts_list = v
                        break
        
        if not posts_list:
            return False, 0, "無效的 JSON 結構，找不到貼文列表。"
            
        db_manager.init_db(db_path)
        scraped_posts = []
        
        for p in posts_list:
            if not isinstance(p, dict) or "id" not in p:
                continue
            post_id = str(p["id"])
            title = p.get("title", "")
            excerpt = p.get("excerpt", "")
            topics = p.get("topics", [])
            content = p.get("content", excerpt) or excerpt
            
            created_at_str = p.get("createdAt", "")
            try:
                dt = datetime.strptime(created_at_str.replace("T", " ").replace(".000Z", ""), "%Y-%m-%d %H:%M:%S")
                dt_tw = dt + pd.Timedelta(hours=8)
                created_at_val = dt_tw.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                created_at_val = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            category = classify_category(title, content, topics)
            joy, anxiety, anger = nlp_engine.analyze_sentiment(title, content)
            keywords = nlp_engine.extract_keywords(title, content, limit=5)
            
            scraped_posts.append({
                "post_id": post_id,
                "title": title,
                "content": content,
                "category": category,
                "created_at": created_at_val,
                "joy_score": joy,
                "anxiety_score": anxiety,
                "anger_score": anger,
                "like_count": p.get("likeCount", 0),
                "comment_count": p.get("commentCount", 0),
                "keywords": keywords
            })
            
        if scraped_posts:
            df_scraped = pd.DataFrame(scraped_posts)
            db_manager.save_posts_to_db(df_scraped, db_path)
            return True, len(df_scraped), "REAL_JSON_IMPORT"
        return False, 0, "沒有成功解析出任何貼文。"
    except Exception as e:
        return False, 0, f"解析出錯：{str(e)}"


def import_comments_json(json_str, db_path=db_manager.DB_FILE):
    """
    解析書籤 B 傳來的留言 JSON 並寫入 comments 資料表。
    預期格式：
    {
        "post_id": "12345678",
        "post_title": "貼文標題",
        "comments": [
            {"floor": 1, "content": "留言內容", "likeCount": 5},
            ...
        ]
    }
    """
    try:
        data = json.loads(json_str)
        post_id = str(data.get("post_id", ""))
        post_title = data.get("post_title", "")
        raw_comments = data.get("comments", [])

        if not post_id or not raw_comments:
            return False, 0, "找不到 post_id 或 comments 資料。"

        db_manager.init_db(db_path)
        processed = []

        for i, c in enumerate(raw_comments):
            content = c.get("content", "").strip()
            if not content or len(content) < 2:
                continue
            floor = c.get("floor", i + 1)
            # 以 post_id + floor 作為唯一 ID
            comment_id = f"{post_id}_{floor}"
            joy, anxiety, anger = nlp_engine.analyze_sentiment(post_title, content)
            created_at_str = c.get("createdAt", "")
            try:
                dt = datetime.strptime(
                    created_at_str.replace("T", " ").replace(".000Z", ""),
                    "%Y-%m-%d %H:%M:%S"
                )
                dt_tw = dt + pd.Timedelta(hours=8)
                created_at_val = dt_tw.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                created_at_val = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            processed.append({
                "comment_id": comment_id,
                "post_id": post_id,
                "content": content,
                "floor": floor,
                "joy_score": joy,
                "anxiety_score": anxiety,
                "anger_score": anger,
                "created_at": created_at_val
            })

        saved = db_manager.save_comments_to_db(processed, db_path)
        return True, saved, "COMMENT_IMPORT"
    except Exception as e:
        return False, 0, f"留言解析出錯：{str(e)}"


if __name__ == "__main__":
    # 若直接執行此檔案，將直接運行爬蟲採集
    run_scraper()
