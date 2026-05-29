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
    "成功": (75.0, 40.0),
    
    # 正向放鬆 / 平靜類 (Valence > 0, Arousal < 0)
    "舒服": (70.0, -45.0), "平靜": (60.0, -60.0), "冷靜": (50.0, -50.0), "放鬆": (70.0, -55.0),
    "愜意": (75.0, -50.0), "溫和": (50.0, -40.0), "沒事": (30.0, -30.0), "推薦": (40.0, 10.0),
    "感謝": (70.0, 15.0), "讚": (60.0, 10.0), "夕陽": (65.0, -30.0),
    
    # 負向焦慮 / 緊張類 (Valence < 0, Arousal > 0)
    "焦慮": (-60.0, 65.0), "擔心": (-50.0, 45.0), "爆肝": (-70.0, 80.0), "崩潰": (-80.0, 85.0),
    "壓力": (-65.0, 70.0), "期中考": (-30.0, 50.0), "期末考": (-35.0, 55.0), "考古題": (-10.0, 30.0),
    "微積分": (-25.0, 40.0), "延畢": (-80.0, 75.0), "二一": (-85.0, 80.0), "失眠": (-60.0, 60.0),
    "遲到": (-50.0, 65.0), "緊張": (-45.0, 70.0), "怕": (-55.0, 60.0), "憂鬱": (-70.0, 30.0),
    "無助": (-65.0, 40.0), "轉圈圈": (-30.0, 45.0), "排隊": (-30.0, 40.0),
    
    # 負向憤怒 / 躁動類 (Valence < 0, Arousal > 0)
    "生氣": (-85.0, 80.0), "怒": (-90.0, 85.0), "幹": (-95.0, 95.0), "超爛": (-85.0, 75.0),
    "停水": (-80.0, 70.0), "當機": (-75.0, 75.0), "不爽": (-80.0, 75.0), "搶走": (-65.0, 60.0),
    "漲價": (-50.0, 50.0), "垃圾": (-85.0, 80.0), "效率極慢": (-70.0, 60.0), "態度很差": (-80.0, 70.0),
    "氣死": (-90.0, 85.0), "抱怨": (-60.0, 50.0), "不滿": (-65.0, 55.0), "態度差": (-75.0, 65.0),
    "靠北": (-80.0, 80.0), "傻眼": (-60.0, 60.0),
    
    # 負向消極 / 沮喪類 (Valence < 0, Arousal < 0)
    "無奈": (-45.0, -30.0), "沮喪": (-70.0, -25.0), "難過": (-65.0, -20.0), "心碎": (-80.0, -10.0),
    "累": (-40.0, -50.0), "疲憊": (-50.0, -45.0), "無聊": (-25.0, -40.0), "孤單": (-50.0, -25.0)
}

def analyze_sentiment(title, content):
    """
    分析貼文與標題，估算 Valence 與 Arousal 情緒分數，並回傳 (valence_score, arousal_score)。
    """
    text = f"{title} {content}"
    
    sum_val = 0.0
    sum_aro = 0.0
    weight_total = 0.0
    
    # 1. 詞典比對與加權計分
    for word, (val, aro) in EMOTION_VECTORS.items():
        if word in text:
            cnt = text.count(word)
            # 以字數與詞頻做加權權重
            weight = cnt * (len(word) ** 0.5)
            sum_val += val * weight
            sum_aro += aro * weight
            weight_total += weight
            
    # 2. 中性預設值
    if weight_total > 0:
        valence = sum_val / weight_total
        arousal = sum_aro / weight_total
    else:
        # 當無任何情緒詞命中，給予微幅正面與平靜預設值
        valence = 5.0
        arousal = 0.0
        
    # 3. 校園特定重大事件向量偏置 (Bias)
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
    
    # 4. 加上些許隨機微噪聲，增強資料在散點圖上的分佈與真實度
    valence += random.uniform(-4.0, 4.0)
    arousal += random.uniform(-4.0, 4.0)
    
    # 5. 限幅於 [-100.0, 100.0]
    valence = max(-100.0, min(100.0, valence))
    arousal = max(-100.0, min(100.0, arousal))
    
    return round(valence, 1), round(arousal, 1)
