import sqlite3
import json
import random
import os
import io
import sys
import re
from datetime import datetime

# Windows 控制台編碼重設
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


DB_FILE = "nsysu_舆情.db"

# ==========================================
# 1. 虛擬看板資料庫初始化
# ==========================================

def init_virtual_tables():
    """
    初始化虛擬 Dcard 看板的資料表 (存放模擬 Agents 的互動數據與即時推播通知)
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 建立虛擬貼文表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS virtual_posts (
        post_id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        author_name TEXT,
        personality TEXT,
        category TEXT,
        created_at TEXT,
        like_count INTEGER DEFAULT 0
    )
    """)
    
    # 建立虛擬留言表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS virtual_comments (
        comment_id TEXT PRIMARY KEY,
        post_id TEXT,
        floor INTEGER,
        author_name TEXT,
        personality TEXT,
        content TEXT,
        created_at TEXT,
        like_count INTEGER DEFAULT 0,
        reply_to_floor INTEGER,
        FOREIGN KEY (post_id) REFERENCES virtual_posts(post_id) ON DELETE CASCADE
    )
    """)
    
    # 建立即時通知推播表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS virtual_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id TEXT,
        floor INTEGER,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()

# 呼叫初始化
init_virtual_tables()

# ==========================================
# 2. Persona 產生器與資料定義
# ==========================================

PERSONALITIES = {
    "酸民嘴砲": {
        "description": "說話刻薄、愛唱反調，經常使用反諷與吐槽，口頭禪是「第一天住中山？」或「笑死」。",
        "style_words": ["笑死", "破學校", "是哈囉", "無言", "學店", "🐒", "🙄"]
    },
    "理智學霸": {
        "description": "說話客觀、注重邏輯與排版，提供務實分析與選課指南，溫和友善但較為嚴肅。",
        "style_words": ["分析如下", "個人經驗", "建議", "學分", "教授", "基本功"]
    },
    "搞笑迷因": {
        "description": "說話幽默、常把事情跟中山特產「柴山獼猴」聯想在一起，喜歡打趣與調侃。",
        "style_words": ["獼猴", "壽山", "蛋餅", "猴子又在", "搶早餐", "阿猴", "🐒", "😅"]
    },
    "熱心溫和": {
        "description": "非常熱心幫助學弟妹，語氣溫柔多使用助詞「啦、喔、呦」，樂於提供生活指南。",
        "style_words": ["加油啦", "你可以", "推薦", "武嶺", "翠亨", "👍", "❤️"]
    }
}

DEPARTMENTS = [
    "電機工程學系", "資訊工程學系", "機械與機電工程學系", "海洋科學系", 
    "企業管理學系", "財務管理學系", "中國文學系", "外國語文學系", 
    "社會學系", "生物科學系", "物理學系"
]

CAMPUS_TOPICS = {
    "課業": {
        "issues": [
            ("電磁學期末調分嗎", "想問一下電機系熱門的電磁學今年會調分嗎？期中平均才40分，真的快崩潰，求學長姐開開恩..."),
            ("網大上傳系統又壞了", "作業今天截止，但網路大學上傳按了完全沒反應，有人也一樣進不去嗎？作業交不出去真的會被當。"),
            ("求推薦通識涼課", "想要湊滿畢業學分，求推薦工學院或管理學院比較涼的通識課，最好是不用報告、期末好過的～"),
        ]
    },
    "生活": {
        "issues": [
            ("又被獼猴搶早餐了", "早上在翠亨宿舍門口剛拿到的米羅蛋餅，不到三秒直接被衝下來的猴子搶走！獼猴是不是都有受過特工訓練？"),
            ("西子灣海水浴場約看夕陽", "今天西子灣的雲層很漂亮，有沒有人下午五點想一起在長堤吹風、看夕陽聊天？"),
            ("晚上求揪夜衝柴山", "宿舍待到快發霉，求揪團去柴山大自然吹風，或是騎車去大社吃宵夜！"),
        ]
    },
    "校務": {
        "issues": [
            ("翠亨宿舍又停水了", "翠亨舍已經連續兩天晚上無預警停水了，洗頭洗到一半都是泡沫真的會氣死，學校的水管是不是都沒在修？"),
            ("校內限速又被抓", "今天在工學院斜坡那邊又有教官在抓超速，大家騎車小心點，猴子超速不抓專抓學生..."),
            ("逸仙館施工太吵了吧", "期末考週逸仙館還在施工打地基，自習室裡都是電鑽聲，完全沒辦法專心讀書，學校到底在想什麼？"),
        ]
    }
}

class Persona:
    """
    自訂性格 (Persona) 類別：
    不再限制於單一性格，改由三個 0.0 ~ 1.0 的連續滑桿維度進行調配。
    """
    def __init__(self, rationality=0.5, trolling=0.5, humor=0.5, name=None, department=None, gender=None):
        self.rationality = float(rationality)
        self.trolling = float(trolling)
        self.humor = float(humor)
        self.name = name if name else f"中山大" + ("學長" if random.random() > 0.5 else "學妹")
        self.department = department if department else random.choice(DEPARTMENTS)
        self.gender = gender if gender else random.choice(["M", "F"])
        
    def get_display_name(self):
        return f"國立中山大學 {self.department}"

    def to_dict(self):
        return {
            "name": self.name,
            "rationality": self.rationality,
            "trolling": self.trolling,
            "humor": self.humor,
            "department": self.department,
            "gender": self.gender
        }

    def get_style_text(self):
        """
        將連續滑桿維度轉換成自然語言的性格特徵描述，以利注入 System Prompt
        """
        desc = f"您是一位國立中山大學學生。您的性格設定如下：\n"
        desc += f"- 理智度: {self.rationality * 100:.1f}% (數值高代表發言理性、有邏輯、排版工整並提供務實建議；數值低代表較為感性直覺)\n"
        desc += f"- 嘴砲度: {self.trolling * 100:.1f}% (數值高代表喜歡使用嘲諷、吐槽、愛唱反調與使用酸民詞彙；數值低代表溫和友善、充滿鼓勵)\n"
        desc += f"- 幽默/迷因度: {self.humor * 100:.1f}% (數值高代表說話非常風趣，喜歡提及柴山獼猴、西灣看夕陽、搶蛋餅等校園特色黑話；數值低代表規矩嚴肅)"
        return desc

# ==========================================
# 3. LLM 推論驅動器 (API / Fallback 雙模式)
# ==========================================

class LLMDriver:
    """
    雙模式 LLM 驅動器：支援真實 API 呼叫與基於規則/範本的本地 Fallback
    """
    def __init__(self, api_key=None, base_url=None, model_name=None):
        self.api_key = api_key if api_key else os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url if base_url else "https://api.openai.com/v1").rstrip("/")
        self.model_name = model_name if model_name else "gpt-4o-mini"
        
        is_local = "127.0.0.1" in self.base_url or "localhost" in self.base_url
        self.has_api = (self.api_key != "" and self.api_key is not None) or is_local

    def generate(self, system_prompt, user_prompt, fallback_data=None, model_override=None, status_callback=None):
        if self.has_api:
            try:
                import requests
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                model_to_use = self.model_name
                if model_override:
                    if "127.0.0.1" in self.base_url or "localhost" in self.base_url or self.model_name.lower().startswith("nsysu"):
                        model_to_use = model_override
                
                if status_callback:
                    status_callback(f"📡 正在向 API 伺服器發送請求... (模型: `{model_to_use}`)")
                    
                payload = {
                    "model": model_to_use,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7
                }
                
                import time
                start_time = time.time()
                res = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=8000)
                elapsed = time.time() - start_time
                
                if res.status_code == 200:
                    if status_callback:
                        status_callback(f"📥 API 回傳成功！(HTTP 200 OK，耗時 {elapsed:.1f} 秒)，正在解析生成內容...")
                    result = res.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    if status_callback:
                        status_callback(f"⚠️ API 伺服器回傳非預期狀態碼 ({res.status_code})，即將切換至本地模板 fallback...")
                    print(f"[LLM] API 回傳錯誤碼 {res.status_code}，切換至本地模板 fallback。")
            except Exception as e:
                if status_callback:
                    status_callback(f"❌ API 伺防器連線失敗 ({str(e)})，即將切換至本地模板 fallback...")
                print(f"[LLM] API 呼叫失敗 ({e})，切換至本地模板 fallback。")
                
        if status_callback:
            status_callback("🎲 已啟用本地規則引擎：根據滑桿性格設定，隨機加權抽樣留言詞庫與貼文範本...")
        return self._generate_fallback(system_prompt, user_prompt, fallback_data)

    def _generate_fallback(self, system_prompt, user_prompt, fallback_data):
        """
        本地規則/詞庫隨機加權抽樣生成器 (Fallback Generator)
        根據滑桿維度數值作為抽樣權重決定語法風格
        """
        if not fallback_data:
            return "對啊，這件事我也覺得滿扯的。🐒"
            
        mode = fallback_data.get("mode")
        persona = fallback_data.get("persona")
        category = fallback_data.get("category", "生活")
        
        # 🟢 權重隨機決定性格範本
        t_w = persona.trolling
        r_w = persona.rationality
        h_w = persona.humor
        total_w = t_w + r_w + h_w
        
        if total_w == 0:
            selected_type = "熱心溫和"
        else:
            probs = [t_w / total_w, r_w / total_w, h_w / total_w]
            selected_type = random.choices(["酸民嘴砲", "理智學霸", "搞笑迷因"], weights=probs, k=1)[0]
            
        # 1. 貼文生成 Fallback
        if mode == "post":
            issues = CAMPUS_TOPICS.get(category, CAMPUS_TOPICS["生活"])["issues"]
            selected_issue = random.choice(issues)
            title, content = selected_issue
            
            # 套用選定性格
            if selected_type == "酸民嘴砲":
                title = f"[抱怨] {title}，這學校到底？"
                content = content + "\n真的是無言，學校收這麼多學費水準就這？🙄 大家都默默吞下去喔？"
            elif selected_type == "理智學霸":
                title = f"[課業] 關於{title}的幾點分析"
                content = f"各位好，針對這件事個人有些微分析：\n" + content + "\n希望大家理性討論，祝期末順利。"
            elif selected_type == "搞笑迷因":
                title = f"[爆卦] {title}！驚人內幕！"
                content = content + "\n肯定是工學院的獼猴在搞鬼啦！🐒 有沒有人要去壽山跟猴王談判的？"
            else:
                title = f"[分享] {title}，想問問大家的看法"
                content = content + "\n大家加油，希望這件事能趕快解決，有需要幫忙的隨時說！👍"
                
            return json.dumps({"title": title, "content": content}, ensure_ascii=False)
            
        # 2. 留言生成 Fallback
        else:
            post_content = fallback_data.get("post_content", "")
            
            comments_pool = {
                "酸民嘴砲": [
                    "笑死，第一天讀中山？這不是學校正常發揮嗎？🙄",
                    "原PO是不是大一菜鳥啊？這種事吵幾年了，不爽退學啊。🐒",
                    "是哈囉？連這也拿來抱怨，這屆學弟妹越來越玻璃心了欸。",
                    "推 B2，真的是學店水準，無言。"
                ],
                "理智學霸": [
                    "建議去宿委會網站填單反映，通常行政單位於三個工作天內會回覆。",
                    "根據選課規章，期末學分主要是教授的自由裁量權，若平均過低，教授通常會微調。",
                    "個人經驗分享：網大壞掉時可以先錄影存證發信給助教，通常助會寬限截止日。",
                    "理性的說，這件事需要行政端與學生代表多溝通，希望能有個合適的解決方案。"
                ],
                "搞笑迷因": [
                    "這肯定是獼猴軍團的陰謀啦！🐒 搶完蛋餅開始搶超速罰單了。",
                    "沒事，猴子會幫你按讚的。獼猴：這篇我給過！😅",
                    "看來逸仙館電鑽的電力是猴子在跑步機發電的吧，超吵。",
                    "笑死，我剛看到一隻猴子騎腳踏車超速被教官攔下來，不知道有沒有開單。"
                ],
                "熱心溫和": [
                    "天啊好慘喔... 期末考週加油啦！👍",
                    "翠亨舍的同學可以先去武嶺舍洗，有開放公共浴室喔！❤️",
                    "別難過，這堂通識我之前修過，教授人很好，期末認真讀一下就會過啦！",
                    "推薦你去西子灣吹吹風放鬆一下，不要給自己太大壓力喔，加油！"
                ]
            }
            
            reply_templates = comments_pool.get(selected_type, comments_pool["熱心溫和"])
            selected_reply = random.choice(reply_templates)
            
            reply_to_floor = fallback_data.get("reply_to_floor")
            if reply_to_floor:
                selected_reply = f"@B{reply_to_floor} " + selected_reply
                
            return selected_reply

# ==========================================
# 4. Agent 類別實作 (Poster & Commenter)
# ==========================================

class PosterAgent:
    """
    發文智能體 (原PO)：負責產出貼文，以及在留言串中以作者身份進行回覆
    """
    def __init__(self, persona=None, llm_driver=None):
        self.persona = persona if persona else Persona()
        self.llm_driver = llm_driver if llm_driver else LLMDriver()

    def generate_post(self, category, status_callback=None):
        system_prompt = f"""
        {self.persona.get_style_text()}
        撰寫一篇在 Dcard 中山大學板上的發文。發文必須貼近真實的大學生語氣，並使用台灣繁體中文。
        輸出必須是 JSON 格式： {{"title": "貼文標題", "content": "貼文內文"}}。請直接輸出 JSON，不要包裝 markdown。
        """
        user_prompt = f"請針對【{category}】分類，撰寫一篇符合你性格的校園閒聊或抱怨貼文。"
        
        fallback_data = {
            "mode": "post",
            "persona": self.persona,
            "category": category
        }
        
        raw_res = self.llm_driver.generate(system_prompt, user_prompt, fallback_data=fallback_data, model_override="nsysu-dcard-poster", status_callback=status_callback)
        try:
            cleaned_res = re.sub(r'```json\s*|\s*```', '', raw_res).strip()
            data = json.loads(cleaned_res)
            return data.get("title", "中山閒聊"), data.get("content", "今天天氣真好。")
        except:
            return f"[閒聊] 關於{category}的一些想法", raw_res

    def generate_reply(self, post_title, post_content, comment_history, reply_to_comment, status_callback=None):
        system_prompt = f"""
        你是國立中山大學學生。你之前在 Dcard 發了這篇文：
        標題：{post_title}
        內文：{post_content}
        
        {self.persona.get_style_text()}
        請以【發文作者】的身份回覆以下網友的留言：
        網友 {reply_to_comment['author']}: 「{reply_to_comment['content']}」
        """
        user_prompt = "請寫出一句簡短的作者回覆。保持你的角色語氣與台灣口語特質。"
        
        fallback_data = {
            "mode": "comment",
            "persona": self.persona,
            "post_content": post_content,
            "reply_to_floor": reply_to_comment.get("floor")
        }
        
        return self.llm_driver.generate(system_prompt, user_prompt, fallback_data=fallback_data, model_override="nsysu-dcard-poster", status_callback=status_callback)


class CommenterAgent:
    """
    留言智能體 (網友)：負責瀏覽看板、評估興趣，並對貼文進行留言回覆
    """
    def __init__(self, persona=None, llm_driver=None):
        self.persona = persona if persona else Persona()
        self.llm_driver = llm_driver if llm_driver else LLMDriver()

    def evaluate_interest(self, post_title, post_content, category):
        # 理智度高對課業有興趣；嘴砲/迷因度高對生活與校務有興趣
        r = self.persona.rationality
        t = self.persona.trolling
        h = self.persona.humor
        
        if category == "課業" and r >= 0.6:
            return True
        if category in ["校務", "生活"] and (t >= 0.5 or h >= 0.5):
            return True
        return random.random() > 0.4

    def generate_comment(self, post_title, post_content, comment_history, reply_to_floor=None, status_callback=None):
        system_prompt = f"""
        {self.persona.get_style_text()}
        
        現在看板上有一篇貼文：
        作者：{self.persona.name}
        標題：{post_title}
        內容：{post_content}
        """
        if reply_to_floor:
            user_prompt = f"請針對第 {reply_to_floor} 樓的留言進行回覆。字數控制在 100 字內，口語化，使用台灣繁體中文。"
        else:
            user_prompt = "請針對這篇貼文寫下一句你的留言。字數控制在 100 字內，口語化，使用台灣繁體中文。"
            
        fallback_data = {
            "mode": "comment",
            "persona": self.persona,
            "post_content": post_content,
            "reply_to_floor": reply_to_floor
        }
        
        return self.llm_driver.generate(system_prompt, user_prompt, fallback_data=fallback_data, model_override="nsysu-dcard-commenter", status_callback=status_callback)

# ==========================================
# 5. VirtualBoard (虛擬 Dcard 模擬看板引擎)
# ==========================================

class VirtualBoard:
    """
    虛擬看板引擎：管理 SQLite 中的 virtual_posts 與 virtual_comments
    提供模擬事件驅動的主迴圈 (驅動互動生命週期與即時通知)
    """
    def __init__(self, llm_driver=None):
        self.llm_driver = llm_driver if llm_driver else LLMDriver()

    def create_new_post(self, poster_agent, category, status_callback=None):
        title, content = poster_agent.generate_post(category, status_callback=status_callback)
        post_id = f"V_{int(datetime.now().timestamp() * 1000)}"
        author_name = poster_agent.persona.get_display_name()
        
        # 顯示性格簡短標記
        r = poster_agent.persona.rationality
        t = poster_agent.persona.trolling
        h = poster_agent.persona.humor
        personality_label = f"理{r*100:.0f}%|嘴{t*100:.0f}%|迷{h*100:.0f}%"
        
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO virtual_posts (post_id, title, content, author_name, personality, category, created_at, like_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (post_id, title, content, author_name, personality_label, category, created_at, random.randint(0, 5)))
        conn.commit()
        conn.close()
        
        print(f"[VirtualBoard] 📝 新虛擬貼文發布成功：[{category}] {title} (ID: {post_id}) By {author_name}")
        return post_id

    def add_notification(self, post_id, floor, message):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO virtual_notifications (post_id, floor, message, is_read, created_at)
        VALUES (?, ?, ?, 0, ?)
        """, (post_id, floor, message, created_at))
        conn.commit()
        conn.close()
        print(f"[Notification] 🔔 新推播已儲存: {message}")

    def get_unread_notifications(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM virtual_notifications WHERE is_read = 0 ORDER BY created_at DESC")
        columns = [col[0] for col in cursor.description]
        notifications = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return notifications

    def mark_notifications_as_read(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE virtual_notifications SET is_read = 1 WHERE is_read = 0")
        conn.commit()
        conn.close()
        print("[Notification] 🧹 已將所有通知設為已讀")

    def post_comment(self, commenter_agent, post_id, reply_to_floor=None, status_callback=None):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT title, content, author_name FROM virtual_posts WHERE post_id = ?", (post_id,))
        post = cursor.fetchone()
        if not post:
            conn.close()
            return None
        post_title, post_content, post_author = post
        
        cursor.execute("SELECT floor, author_name, content FROM virtual_comments WHERE post_id = ? ORDER BY floor ASC", (post_id,))
        comments_history = [{"floor": r[0], "author": r[1], "content": r[2]} for r in cursor.fetchall()]
        
        next_floor = len(comments_history) + 1
        content = commenter_agent.generate_comment(post_title, post_content, comments_history, reply_to_floor, status_callback=status_callback)
        
        comment_id = f"VC_{post_id}_{next_floor}"
        author_name = commenter_agent.persona.get_display_name()
        
        r = commenter_agent.persona.rationality
        t = commenter_agent.persona.trolling
        h = commenter_agent.persona.humor
        personality_label = f"理{r*100:.0f}%|嘴{t*100:.0f}%|迷{h*100:.0f}%"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
        INSERT INTO virtual_comments (comment_id, post_id, floor, author_name, personality, content, created_at, like_count, reply_to_floor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (comment_id, post_id, next_floor, author_name, personality_label, content, created_at, random.randint(0, 3), reply_to_floor))
        
        conn.commit()
        conn.close()
        
        print(f"[VirtualBoard] 💬 B{next_floor} 留言成功: {content[:15]}... By {author_name}")
        
        # ==========================================
        # 🔔 偵測並推播通知機制
        # ==========================================
        if reply_to_floor and reply_to_floor > 0:
            target_comment = next((c for c in comments_history if c["floor"] == reply_to_floor), None)
            if target_comment and "真人同學" in target_comment["author"]:
                message = f"💬 AI 網友 {commenter_agent.persona.name} ({personality_label}) 在您 B{reply_to_floor} 樓的留言下 @回覆 了您！"
                self.add_notification(post_id, reply_to_floor, message)
        
        elif not reply_to_floor and "真人同學" in post_author:
            message = f"📰 AI 網友 {commenter_agent.persona.name} ({personality_label}) 回覆了您發布的貼文！"
            self.add_notification(post_id, 0, message)
            
        return comment_id

    def get_board_posts(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT p.*, COUNT(c.comment_id) as comment_count
        FROM virtual_posts p
        LEFT JOIN virtual_comments c ON p.post_id = c.post_id
        GROUP BY p.post_id
        ORDER BY p.created_at DESC
        """)
        columns = [col[0] for col in cursor.description]
        posts = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return posts

    def get_post_details(self, post_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM virtual_posts WHERE post_id = ?", (post_id,))
        post_row = cursor.fetchone()
        if not post_row:
            conn.close()
            return None
        columns = [col[0] for col in cursor.description]
        post = dict(zip(columns, post_row))
        
        cursor.execute("SELECT * FROM virtual_comments WHERE post_id = ? ORDER BY floor ASC", (post_id,))
        c_columns = [col[0] for col in cursor.description]
        comments = [dict(zip(c_columns, row)) for row in cursor.fetchall()]
        
        post["comments"] = comments
        conn.close()
        return post

    def clear_virtual_board(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM virtual_posts")
        cursor.execute("DELETE FROM virtual_comments")
        cursor.execute("DELETE FROM virtual_notifications")
        conn.commit()
        conn.close()
        print("[VirtualBoard] 🧹 虛擬看板與所有通知已完全清空重設！")

    def run_autonomous_simulation_step(self, num_commenters=3, status_callback=None):
        # 隨機生成帶有隨機滑桿屬性的 Poster
        poster = PosterAgent(persona=Persona(
            rationality=random.random(),
            trolling=random.random(),
            humor=random.random()
        ), llm_driver=self.llm_driver)
        
        category = random.choice(["生活", "課業", "校務"])
        if status_callback:
            status_callback(f"📝 正在隨機指派一個發文者（原PO）撰寫分類為【{category}】的貼文...")
        post_id = self.create_new_post(poster, category, status_callback=status_callback)
        
        # 隨機生成帶有隨機屬性的 Commenters
        commenters = [CommenterAgent(persona=Persona(
            rationality=random.random(),
            trolling=random.random(),
            humor=random.random()
        ), llm_driver=self.llm_driver) for _ in range(num_commenters)]
        
        for idx, commenter in enumerate(commenters):
            post_details = self.get_post_details(post_id)
            if commenter.evaluate_interest(post_details["title"], post_details["content"], category):
                reply_floor = None
                if post_details["comments"] and random.random() > 0.5:
                    target_c = random.choice(post_details["comments"])
                    reply_floor = target_c["floor"]
                
                if status_callback:
                    dept = commenter.persona.department
                    lbl = f"理{commenter.persona.rationality*100:.0f}%|嘴{commenter.persona.trolling*100:.0f}%|迷{commenter.persona.humor*100:.0f}%"
                    dest = f"回覆 B{reply_floor}" if reply_floor else "直接留言"
                    status_callback(f"💬 正在由留言者 (網友 {idx+1}/{num_commenters} 中山{dept}，性格: {lbl}) 生成{dest}...")
                
                self.post_comment(commenter, post_id, reply_to_floor=reply_floor, status_callback=status_callback)
                
        return post_id

if __name__ == "__main__":
    board = VirtualBoard()
    post_id = board.run_autonomous_simulation_step(num_commenters=3)
    details = board.get_post_details(post_id)
    print("\n--- 模擬結果預覽 ---")
    print(f"標題: {details['title']}")
    print(f"發文者: {details['author_name']} ({details['personality']})")
    print(f"內文: {details['content']}")
    print(f"留言數: {len(details['comments'])}")
    for c in details['comments']:
        reply_str = f" 回覆 B{c['reply_to_floor']}" if c['reply_to_floor'] else ""
        print(f"  B{c['floor']}{reply_str} | {c['author_name']} ({c['personality']}): {c['content']}")
