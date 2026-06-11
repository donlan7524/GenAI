import os
import re
import random
import jieba
import jieba.analyse

# ==============================================================================
# 1. 初始化 中山大學專屬詞彙 與 斷詞引擎
# ==============================================================================
# 註冊校園特有詞彙，防止被 jieba 切碎，以確保文字雲與關鍵字品質
NSYSU_WORDS = [
    "西子灣", "翠亨宿舍", "武嶺宿舍", "柴山獼猴", "柴山", "獼猴", 
    "大碗公冰", "選課系統", "期中考古題", "考古題", "期中考", "期末考", 
    "雙主修", "通識課", "學費", "學餐", "逸仙館", "防波堤", "草地音樂會",
    "學生會", "教務處", "宿管處", "海之冰", "渡船頭"
]

for word in NSYSU_WORDS:
    jieba.add_word(word)

# 繁體中文常用停用詞
STOP_WORDS = {
    "的", "了", "在", "是", "我", "你", "他", "我們", "你們", "他們",
    "這個", "那個", "一個", "而且", "但是", "因為", "所以", "有人", "真的",
    "覺得", "比較", "哈哈", "一個", "二個", "三個", "一個", "什麼", "怎麼",
    "就是", "可以", "也是", "有沒有", "大家", "今天", "明天", "昨天", "結果",
    "大家", "請問", "想問", "分享", "謝謝", "知道", "現在", "已經", "還是"
}

def extract_keywords(title, content, limit=5):
    """
    結合 Jieba 的 TF-IDF 演算法從貼文的標題與內容中提取出關鍵詞，並過濾停用詞。
    """
    text = f"{title} {content}"
    
    # 提取候選詞彙 (取得更多，以防被停用詞過濾掉)
    candidates = jieba.analyse.extract_tags(text, topK=limit * 3)
    
    # 過濾停用詞與單字詞、標點符號
    filtered_keywords = []
    for word in candidates:
        word_clean = re.sub(r"[^\w]", "", word).strip()
        # 長度大於 1 且不在停用詞庫中
        if len(word_clean) > 1 and word_clean not in STOP_WORDS:
            filtered_keywords.append(word_clean)
        if len(filtered_keywords) >= limit:
            break
            
    # 若過濾後不夠，用基本詞填補
    if len(filtered_keywords) < limit:
        # fallback 隨便抽一點主題詞
        fallbacks = [w for w in NSYSU_WORDS if w in text and w not in filtered_keywords]
        filtered_keywords.extend(fallbacks[:limit - len(filtered_keywords)])
        
    return filtered_keywords


# ==============================================================================
# 2. 情緒分析模型 (Sentiment Analysis Module - Valence-Arousal)
# ==============================================================================
# 定義詞彙的情緒向量值 (Valence, Arousal)
# Valence 範圍在 [-100, 100]：正值代表愉快/正面，負值代表不愉快/負面
# Arousal 範圍在 [-100, 100]：正值代表激動/興奮/焦慮，負值代表冷靜/放鬆/沮喪
EMOTION_VECTORS = {
    # 正向高興 / 興奮類 (Valence > 0, Arousal > 0)
    "開心": (75.0, 45.0), "高興": (70.0, 40.0), "爽": (85.0, 65.0), "好棒": (70.0, 50.0),
    "告白成功": (90.0, 80.0), "超甜": (80.0, 50.0), "音樂會": (60.0, 45.0), "喜悅": (75.0, 40.0),
    "笑": (60.0, 30.0), "樂趣": (65.0, 30.0), "正面": (50.0, 10.0), "順利": (60.0, 20.0),
    "成功": (75.0, 40.0), "謝謝": (50.0, 15.0), "感恩": (60.0, 15.0), "推": (40.0, 10.0),
    "強": (55.0, 25.0), "神": (70.0, 40.0), "超讚": (80.0, 45.0), "厲害": (65.0, 30.0),
    "感動": (70.0, 25.0), "喜歡": (65.0, 30.0), "棒": (55.0, 20.0), "哈哈": (50.0, 30.0),
    "愛": (75.0, 35.0), "好笑": (60.0, 35.0), "有趣": (55.0, 20.0), "期待": (60.0, 40.0),
    "恭喜": (75.0, 45.0), "進步": (50.0, 15.0), "歐趴": (80.0, 50.0), "過關": (60.0, 20.0),
    "好聽": (60.0, 15.0), "好看": (60.0, 15.0), "方便": (50.0, 10.0), "酷": (60.0, 25.0),
    "優": (50.0, 10.0), "讚": (60.0, 10.0), "推爆": (85.0, 60.0), "超推": (75.0, 35.0),
    "大推": (70.0, 30.0), "甜課": (70.0, 10.0), "脫單": (85.0, 60.0), "閃光": (70.0, 40.0),
    "閃": (60.0, 30.0), "朝盛": (60.0, 40.0), "無敵": (80.0, 50.0), "招財": (50.0, 10.0),
    
    # 正向放鬆 / 平靜類 (Valence > 0, Arousal < 0)
    "舒服": (70.0, -45.0), "平靜": (60.0, -60.0), "冷靜": (50.0, -50.0), "放鬆": (70.0, -55.0),
    "愜意": (75.0, -50.0), "溫和": (50.0, -40.0), "沒事": (30.0, -30.0), "推薦": (40.0, 10.0),
    "感謝": (70.0, 15.0), "夕陽": (65.0, -30.0), "休閒": (50.0, -35.0), "安靜": (40.0, -50.0),
    "涼課": (60.0, -30.0), "超涼": (70.0, -40.0), "溫馨": (65.0, -10.0),
    
    # 負向焦慮 / 緊張類 (Valence < 0, Arousal > 0)
    "焦慮": (-60.0, 65.0), "擔心": (-50.0, 45.0), "爆肝": (-70.0, 80.0), "崩潰": (-80.0, 85.0),
    "壓力": (-65.0, 70.0), "期中考": (-30.0, 50.0), "期末考": (-35.0, 55.0), "考古題": (-10.0, 30.0),
    "微積分": (-25.0, 40.0), "延畢": (-80.0, 75.0), "二一": (-85.0, 80.0), "當掉": (-75.0, 70.0),
    "被當": (-75.0, 70.0), "三一": (-90.0, 85.0), "失眠": (-60.0, 60.0), "遲到": (-50.0, 65.0),
    "緊張": (-45.0, 70.0), "怕": (-55.0, 60.0), "憂鬱": (-70.0, 30.0), "無助": (-65.0, 40.0),
    "轉圈圈": (-30.0, 45.0), "排隊": (-30.0, 40.0), "痛苦": (-80.0, 70.0), "害怕": (-60.0, 65.0),
    "慌張": (-50.0, 70.0), "疑惑": (-20.0, 30.0), "困惑": (-20.0, 30.0), "討厭": (-70.0, 55.0),
    "必修": (30.0, 20.0), "被吉": (-60.0, 70.0), "雷課": (-70.0, 50.0), "超雷": (-80.0, 60.0),
    "雷": (-50.0, 40.0),
    
    # 負向憤怒 / 躁動類 (Valence < 0, Arousal > 0)
    "生氣": (-85.0, 80.0), "怒": (-90.0, 85.0), "幹": (-95.0, 95.0), "超爛": (-85.0, 75.0),
    "爛": (-75.0, 65.0), "爛透了": (-85.0, 80.0), "停水": (-80.0, 70.0), "當機": (-75.0, 75.0),
    "不爽": (-80.0, 75.0), "搶走": (-65.0, 60.0), "搶": (-40.0, 45.0), "漲價": (-50.0, 50.0),
    "垃圾": (-85.0, 80.0), "效率極慢": (-70.0, 60.0), "態度很差": (-80.0, 70.0), "氣死": (-90.0, 85.0),
    "抱怨": (-60.0, 50.0), "不滿": (-65.0, 55.0), "態度差": (-75.0, 65.0), "靠北": (-80.0, 80.0),
    "傻眼": (-60.0, 60.0), "超ㄏ": (-50.0, 45.0), "扯": (-40.0, 45.0), "誇張": (-45.0, 40.0),
    "瞎": (-50.0, 45.0), "可惡": (-75.0, 70.0), "欠檢舉": (-70.0, 60.0), "吵": (-45.0, 50.0),
    "髒": (-50.0, 40.0), "臭": (-50.0, 40.0), "檢舉": (-40.0, 40.0), "學店": (-60.0, 45.0),
    "笑死": (-20.0, 50.0), "哭啊": (-60.0, 45.0), "吉": (-40.0, 55.0), "無腦": (-70.0, 60.0),
    
    # 負向消極 / 沮喪類 (Valence < 0, Arousal < 0)
    "無奈": (-45.0, -30.0), "沮喪": (-70.0, -25.0), "難過": (-65.0, -20.0), "心碎": (-80.0, -10.0),
    "累": (-40.0, -50.0), "疲憊": (-50.0, -45.0), "無聊": (-25.0, -40.0), "孤單": (-50.0, -25.0),
    "邊緣": (-45.0, -20.0), "沒人理": (-50.0, -15.0), "悲哀": (-60.0, -15.0), "悲劇": (-55.0, 10.0),
    "可憐": (-55.0, -10.0), "難吃": (-60.0, 10.0), "受不了": (-65.0, 40.0), "哭": (-60.0, -10.0),
    "母單": (-45.0, -20.0), "魯蛇": (-50.0, -20.0)
}

EMOJI_VECTORS = {
    # 正向 Emoji
    "👍": (60.0, 10.0), "❤️": (80.0, 20.0), "🎉": (80.0, 70.0), "😂": (40.0, 30.0),
    "🤣": (50.0, 40.0), "😍": (80.0, 50.0), "🙏": (40.0, 0.0), "😎": (50.0, 20.0),
    "🥰": (80.0, 30.0), "🥳": (85.0, 60.0), "✨": (40.0, 20.0), "🤩": (85.0, 65.0),
    "🔥": (70.0, 60.0), "👏": (60.0, 35.0), "😊": (50.0, 10.0), "😆": (55.0, 25.0),
    "😸": (60.0, 25.0), "💯": (80.0, 40.0), "💪": (65.0, 35.0), "🎈": (60.0, 30.0),
    
    # 負向 Emoji
    "😭": (-70.0, 45.0), "😡": (-85.0, 80.0), "😠": (-80.0, 75.0), "🙄": (-50.0, 40.0),
    "😱": (-60.0, 80.0), "💔": (-80.0, -10.0), "💩": (-70.0, 30.0), "👿": (-75.0, 60.0),
    "😰": (-60.0, 60.0), "😢": (-65.0, -15.0), "😤": (-60.0, 65.0), "👎": (-60.0, 20.0),
    "🤢": (-70.0, 50.0), "🤮": (-75.0, 60.0), "💀": (-50.0, 40.0), "🤡": (-40.0, 30.0),
    "🥺": (-40.0, -10.0), "😑": (-30.0, -10.0), "😩": (-60.0, 50.0), "😓": (-50.0, 40.0),
    "😔": (-50.0, -30.0), "😕": (-30.0, 20.0)
}

def analyze_sentiment(title, content):
    """
    分析貼文與標題，估算 Valence 與 Arousal 情緒分數，並回傳 (valence_score, arousal_score)。
    """
    text = f"{title} {content}"
    
    sum_val = 0.0
    sum_aro = 0.0
    weight_total = 0.0
    
    # 1. 詞典比對與加權計分 (包含多字與單字情緒詞)
    for word, (val, aro) in EMOTION_VECTORS.items():
        if word in text:
            cnt = text.count(word)
            # 以字數與詞頻做加權權重
            weight = cnt * (len(word) ** 0.5)
            sum_val += val * weight
            sum_aro += aro * weight
            weight_total += weight
            
    # 2. 表情符號 (Emoji) 特徵匹配
    for emoji_char, (val, aro) in EMOJI_VECTORS.items():
        if emoji_char in text:
            cnt = text.count(emoji_char)
            # Emoji 給予較高權重
            weight = cnt * 3.0
            sum_val += val * weight
            sum_aro += aro * weight
            weight_total += weight

    # 3. 事實性文章與未命中詞彙的自適應預設值 (避免全部擠在 (5.0, 0.0))
    if weight_total > 0:
        valence = sum_val / weight_total
        arousal = sum_aro / weight_total
    else:
        # 事實性貼文的自適應偏置：
        # 根據內文字數和問號分布，使散點在 2D 圖上稍微分散
        text_len = len(text)
        
        # 預設基準
        valence = 5.0
        arousal = 0.0
        
        # 如果有問號，通常代表求問/疑惑 (Arousal 稍微上升，Valence 稍微下修)
        if "?" in text or "？" in text:
            valence -= 8.0
            arousal += 15.0
        
        # 長文代表認真討論，短文可能偏水，給予隨機偏置
        valence += (text_len % 7 - 3.5) * 1.5  # 分散範圍約 [-5.25, 5.25]
        arousal += (text_len % 5 - 2.0) * 2.0  # 分散範圍約 [-4.0, 4.0]
        
    # 4. 語氣與標點符號微調 (Arousal)
    # 統計感嘆號數量，增加激動度 (Arousal)
    exclamation_count = text.count("！") + text.count("!")
    if exclamation_count > 0:
        arousal_boost = min(exclamation_count * 5.0, 30.0)
        arousal += arousal_boost
        
    # 5. 校園特定重大事件向量偏置 (Bias)
    bias_val = 0.0
    bias_aro = 0.0
    
    if "停水" in text:
        bias_val -= 35.0
        bias_aro += 40.0
    if "選課" in text and ("當機" in text or "轉圈圈" in text or "搶" in text):
        bias_val -= 40.0
        bias_aro += 45.0
    if "期中" in text or "期末" in text or "考古題" in text:
        bias_val -= 15.0
        bias_aro += 30.0
    if "告白" in text or "西子灣夕陽" in text or "音樂會" in text:
        bias_val += 45.0
        bias_aro += 15.0
    if "獼猴" in text or "猴子" in text:
        if "搶" in text:
            bias_val -= 25.0
            bias_aro += 35.0
        else:
            bias_val -= 5.0
            bias_aro += 15.0
            
    valence += bias_val
    arousal += bias_aro
    
    # 6. 加上些許隨機微噪聲，增強資料在散點圖上的分佈與真實度
    valence += random.uniform(-4.0, 4.0)
    arousal += random.uniform(-4.0, 4.0)
    
    # 7. 限幅於 [-100.0, 100.0]
    valence = max(-100.0, min(100.0, valence))
    arousal = max(-100.0, min(100.0, arousal))
    
    return round(valence, 1), round(arousal, 1)

import sqlite3

def load_custom_lexicon():
    """
    從 SQLite 資料庫中載入使用者自訂的情緒詞彙，並合併/覆寫至 EMOTION_VECTORS。
    """
    try:
        conn = sqlite3.connect("nsysu_舆情.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS custom_lexicon (word TEXT PRIMARY KEY, valence REAL, arousal REAL)")
        cursor.execute("SELECT word, valence, arousal FROM custom_lexicon")
        rows = cursor.fetchall()
        for word, val, aro in rows:
            EMOTION_VECTORS[word] = (val, aro)
            jieba.add_word(word)
        conn.close()
    except Exception as e:
        print(f"[nlp_engine] 載入自訂詞庫失敗: {e}")

def save_custom_word(word, valence, arousal):
    """
    儲存自訂情緒詞至資料庫，並即時更新記憶體中的詞庫。
    """
    try:
        conn = sqlite3.connect("nsysu_舆情.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS custom_lexicon (word TEXT PRIMARY KEY, valence REAL, arousal REAL)")
        cursor.execute("""
            INSERT INTO custom_lexicon (word, valence, arousal)
            VALUES (?, ?, ?)
            ON CONFLICT(word) DO UPDATE SET valence=excluded.valence, arousal=excluded.arousal
        """, (word, valence, arousal))
        conn.commit()
        conn.close()
        
        # 即時更新記憶體中的詞庫與斷詞字典
        EMOTION_VECTORS[word] = (valence, arousal)
        jieba.add_word(word)
        return True
    except Exception as e:
        print(f"[nlp_engine] 儲存自訂詞彙失敗: {e}")
        return False

def propagate_sentiment_to_keywords(title, content, valence, arousal, cursor=None):
    """
    自動將本篇貼文的情緒分數傳播至其關鍵字，並寫入資料庫 custom_lexicon，留給下一次計算使用。
    """
    # 只有當貼文情緒強度足夠時才傳播，避免事實性文章的噪聲干擾
    if abs(valence) < 15.0 and abs(arousal) < 15.0:
        return
        
    keywords = extract_keywords(title, content, limit=5)
    if not keywords:
        return
        
    local_cursor = cursor
    conn = None
    
    try:
        if local_cursor is None:
            conn = sqlite3.connect("nsysu_舆情.db")
            local_cursor = conn.cursor()
            
        local_cursor.execute("CREATE TABLE IF NOT EXISTS custom_lexicon (word TEXT PRIMARY KEY, valence REAL, arousal REAL)")
        
        # 衰減率 (Decay Factor)：詞彙繼承貼文情緒的 40%
        decay_factor = 0.4
        propagated_val = valence * decay_factor
        propagated_aro = arousal * decay_factor
        
        for word in keywords:
            # 確保不會覆寫寫死在代碼裡的優質核心詞彙
            if word in EMOTION_VECTORS:
                continue
                
            # 讀取資料庫中現有的數值（如果之前有其他貼文也傳過這個詞）
            local_cursor.execute("SELECT valence, arousal FROM custom_lexicon WHERE word = ?", (word,))
            row = local_cursor.fetchone()
            if row:
                # 取移動平均，平滑多次傳播的值
                old_val, old_aro = row
                new_val = old_val * 0.7 + propagated_val * 0.3
                new_aro = old_aro * 0.7 + propagated_aro * 0.3
            else:
                new_val = propagated_val
                new_aro = propagated_aro
                
            local_cursor.execute("""
                INSERT INTO custom_lexicon (word, valence, arousal)
                VALUES (?, ?, ?)
                ON CONFLICT(word) DO UPDATE SET valence=excluded.valence, arousal=excluded.arousal
            """, (word, round(new_val, 1), round(new_aro, 1)))
            
            # 同時動態更新記憶體中的詞表
            EMOTION_VECTORS[word] = (round(new_val, 1), round(new_aro, 1))
            jieba.add_word(word)
            
        if conn:
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"[nlp_engine] 情緒自動傳播失敗: {e}")
        if conn:
            conn.close()

# 初始化時自動載入自訂詞彙
load_custom_lexicon()
