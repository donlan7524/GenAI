import sqlite3
import random
import sys
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DB_FILE = "nsysu_舆情.db"

def seed_board():
    print(f"⚙️ 正在連接資料庫 {DB_FILE} 並寫入高質感虛擬模擬範例...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 確保資料表結構存在
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS virtual_posts (
        post_id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        author_name TEXT,
        personality TEXT,
        category TEXT,
        created_at TEXT,
        like_count INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS virtual_comments (
        comment_id TEXT PRIMARY KEY,
        post_id TEXT NOT NULL,
        floor INTEGER,
        author_name TEXT,
        personality TEXT,
        content TEXT,
        created_at TEXT,
        like_count INTEGER,
        reply_to_floor INTEGER,
        FOREIGN KEY (post_id) REFERENCES virtual_posts(post_id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS virtual_notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id TEXT,
        floor INTEGER,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    # 範例一：選課當機與二一危機
    post1_id = "V_SAMPLE_1"
    post1_time = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT OR REPLACE INTO virtual_posts (post_id, title, content, author_name, personality, category, created_at, like_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post1_id,
        "選課系統又當掉了，大家有選到通識嗎？",
        "今天早上九點準時進去，網頁直接轉圈圈轉到死，好不容易進去想選的通識課早就額滿了。學校這選課系統到底什麼時候要升級啊？大家都選到什麼課？",
        "真人同學 (原PO)",
        "真人",
        "課業",
        post1_time,
        15
    ))

    comments_p1 = [
        ("VC_V_SAMPLE_1_1", post1_id, 1, "中山大學", "理20%|嘴90%|迷30%", "笑死，第一天讀中山？這不是學校正常發揮嗎？🙄 習慣就好啦。學店系統就這水準，還想選到涼課喔。", 10),
        ("VC_V_SAMPLE_1_2", post1_id, 2, "中山大學", "理85%|嘴15%|迷20%", "個人經驗是使用無痕視窗並提前登入，另外建議去教務處網頁填反映單，通常三個工作天會回覆，理性討論啦。", 20),
        ("VC_V_SAMPLE_1_3", post1_id, 3, "中山大學", "理30%|嘴40%|迷90%", "獼猴：這篇文我給過！🐒 其實是我們獼猴軍團在選課機房拔你網路線啦，乖乖來柴山陪我們吃蛋餅比較實在。", 30),
        ("VC_V_SAMPLE_1_4", post1_id, 4, "中山大學", "理40%|嘴10%|迷40%", "拍拍原PO，如果真的需要這門課，第一堂課可以直接去找教授加簽看看喔，有些教授人很好會加簽！加油！❤️", 40)
    ]

    for cid, pid, floor, author, personality, content, offset in comments_p1:
        c_time = (datetime.strptime(post1_time, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT OR REPLACE INTO virtual_comments (comment_id, post_id, floor, author_name, personality, content, created_at, like_count, reply_to_floor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, (cid, pid, floor, author, personality, content, c_time, random.randint(1, 5)))

    # 範例二：獼猴搶蛋餅
    post2_id = "V_SAMPLE_2"
    post2_time = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT OR REPLACE INTO virtual_posts (post_id, title, content, author_name, personality, category, created_at, like_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post2_id,
        "工學院的猴子今天早上又搶了我的米羅蛋餅...",
        "我才剛從斜坡騎上來，把早餐掛在機車掛勾，一轉身鎖個安全帽，回頭就看到一隻超大彌猴抱著我的米羅蛋餅爬上樹，甚至還對我做鬼臉。我的十五元大冰奶也被搶了，這學期已經是第三次了，有沒有防猴神招？",
        "中山大學",
        "理50%|嘴30%|迷60%",
        "生活",
        post2_time,
        42
    ))

    comments_p2 = [
        ("VC_V_SAMPLE_2_1", post2_id, 1, "中山大學", "理20%|嘴30%|迷95%", "猴子表示：感謝大德施捨米羅蛋餅，明天請準備肉包跟大碗公冰，我們會準時在工學院停車場恭候。🐒", 5),
        ("VC_V_SAMPLE_2_2", post2_id, 2, "中山大學", "理50%|嘴10%|迷40%", "學弟拍拍，真的很慘。拿早餐一定要放包包或抱緊，絕對不要掛在掛勾上，猴子眼睛超尖的。希望你今天期末考順利，加油！❤️", 15),
        ("VC_V_SAMPLE_2_3", post2_id, 3, "中山大學", "理10%|嘴85%|迷30%", "笑死，被搶三次還學不乖，你是不是智商被猴子壓制了？自己不放包包怪誰，猴子都知道要吃米羅，你還不知道防範。", 25),
        ("VC_V_SAMPLE_2_4", post2_id, 4, "中山大學", "理90%|嘴15%|迷10%", "根據野生動物保育法，千萬不要拿木棍去打牠們，不然可能會觸法。目前學校推行的防猴防範主要是宣導食物不露白，放車廂是唯一正解。", 35)
    ]

    for cid, pid, floor, author, personality, content, offset in comments_p2:
        c_time = (datetime.strptime(post2_time, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT OR REPLACE INTO virtual_comments (comment_id, post_id, floor, author_name, personality, content, created_at, like_count, reply_to_floor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, (cid, pid, floor, author, personality, content, c_time, random.randint(1, 10)))

    # 範例三：宿舍又停水
    post3_id = "V_SAMPLE_3"
    post3_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT OR REPLACE INTO virtual_posts (post_id, title, content, author_name, personality, category, created_at, like_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post3_id,
        "翠亨宿舍晚上又無預警停水了，洗澡洗一半真的很傻眼",
        "剛剛運動完回宿舍洗澡，洗髮精剛抹上去，水龍頭就只剩下吸氣的聲音。全身上下都是泡泡，宿管的電話也打不通，到底要停水幾次？我們交住宿費是來體驗荒野求生的嗎？",
        "真人同學 (原PO)",
        "真人",
        "校務",
        post3_time,
        28
    ))

    comments_p3 = [
        ("VC_V_SAMPLE_3_1", post3_id, 1, "中山大學", "理40%|嘴10%|迷60%", "翠亨舍的同學可以先去武嶺舍洗澡喔，那邊有開放公共浴室！加油啦！一定要撐住，天冷小心感冒！❤️", 8),
        ("VC_V_SAMPLE_3_2", post3_id, 2, "中山大學", "理20%|嘴95%|迷20%", "笑死，不爽去校外租房啊，還是你要去睡逸仙館前面？交那點住宿費還想享受五星級衛浴，真是天真。🙄", 18),
        ("VC_V_SAMPLE_3_3", post3_id, 3, "中山大學", "理80%|嘴10%|迷30%", "宿委會已經在群組發公告了，是因為翠亨水塔的幫浦突然燒毀，工程人員已經在搶修了，預計深夜前會恢復供水。大家可以先去公共浴室將就一下。", 28),
        ("VC_V_SAMPLE_3_4", post3_id, 4, "中山大學", "理10%|嘴40%|迷85%", "笑死，這就是傳說中的「泡沫之夏」中山大學特別版嗎？泡泡洗不掉可以直接去西子灣跳海洗，天然鹹水去污喔！", 38)
    ]

    for cid, pid, floor, author, personality, content, offset in comments_p3:
        c_time = (datetime.strptime(post3_time, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT OR REPLACE INTO virtual_comments (comment_id, post_id, floor, author_name, personality, content, created_at, like_count, reply_to_floor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, (cid, pid, floor, author, personality, content, c_time, random.randint(1, 8)))

    conn.commit()
    conn.close()
    print("🎉 高品質虛擬看板範例數據（課業選課、生活獼猴、校務停水）已成功寫入資料庫中！")

if __name__ == "__main__":
    seed_board()
