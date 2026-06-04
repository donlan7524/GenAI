import sqlite3
import re
import jieba
import numpy as np
import math
import sys
import io
import os
from collections import Counter

# Windows 控制台編碼重設
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_FILE = "nsysu_舆情.db"

# ==========================================
# 1. 詞彙多樣性度量 (TTR - Type-Token Ratio)
# ==========================================

def calculate_ttr(texts):
    """
    計算一組文本的詞彙多樣性 (TTR)
    texts: List[str]
    """
    if not texts:
        return 0.0, 0, 0
        
    # 合併所有文字並進行斷詞
    all_content = " ".join(texts)
    # 過濾標點符號與空白
    tokens = [t.strip() for t in jieba.lcut(all_content) if t.strip() and not re.match(r'[^\w\s]', t)]
    
    if not tokens:
        return 0.0, 0, 0
        
    num_tokens = len(tokens)
    num_types = len(set(tokens))
    ttr = num_types / num_tokens
    
    return ttr, num_types, num_tokens

# ==========================================
# 2. 風格相似度比對 (Cosine Similarity)
# ==========================================

def compute_cosine_similarity(text_list_a, text_list_b):
    """
    計算兩組文本間的 TF-IDF 風格餘弦相似度
    """
    if not text_list_a or not text_list_b:
        return 0.0
        
    # 斷詞並統計詞頻
    def get_word_freq(texts):
        all_words = []
        for t in texts:
            words = [w.strip() for w in jieba.lcut(t) if w.strip() and not re.match(r'[^\w\s]', w)]
            all_words.extend(words)
        return Counter(all_words)
        
    freq_a = get_word_freq(text_list_a)
    freq_b = get_word_freq(text_list_b)
    
    # 建立合併詞彙表
    all_vocab = set(list(freq_a.keys()) + list(freq_b.keys()))
    if not all_vocab:
        return 0.0
        
    # 建立詞頻向量
    vector_a = []
    vector_b = []
    
    for word in all_vocab:
        vector_a.append(freq_a.get(word, 0))
        vector_b.append(freq_b.get(word, 0))
        
    # 計算 Cosine Similarity
    v_a = np.array(vector_a)
    v_b = np.array(vector_b)
    
    dot_product = np.dot(v_a, v_b)
    norm_a = np.linalg.norm(v_a)
    norm_b = np.linalg.norm(v_b)
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)

# ==========================================
# 3. 整合評估報告生成
# ==========================================

def run_evaluation_report():
    if not os.path.exists(DB_FILE):
        print(f"❌ 找不到資料庫 {DB_FILE}，無法評估。")
        return
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. 載入真實人類留言
    cursor.execute("SELECT content FROM comments WHERE content IS NOT NULL AND content != ''")
    real_texts = [r[0] for r in cursor.fetchall()]
    
    # 2. 載入 AI 網友模擬留言
    # 檢查 virtual_comments 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='virtual_comments'")
    table_exists = cursor.fetchone()
    
    ai_texts = []
    if table_exists:
        cursor.execute("SELECT content FROM virtual_comments WHERE content IS NOT NULL AND content != ''")
        ai_texts = [r[0] for r in cursor.fetchall()]
        
    conn.close()
    
    print("=" * 60)
    print("       🎓 中山 AI 網友社群模擬 - 學術評估量度報告")
    print("=" * 60)
    
    print(f"📊 樣本規模：")
    print(f"   - 真實人類留言數：{len(real_texts)} 筆")
    print(f"   - AI 網友留言數  ：{len(ai_texts)} 筆")
    print("-" * 60)
    
    import re
    # 計算 TTR
    real_ttr, real_types, real_tokens = calculate_ttr(real_texts)
    ai_ttr, ai_types, ai_tokens = calculate_ttr(ai_texts)
    
    print(f"🔑 詞彙豐富度 (Type-Token Ratio, TTR)：")
    print(f"   - 真實人類留言：TTR = {real_ttr:.4f} (相異詞 {real_types} / 總詞數 {real_tokens})")
    print(f"   - AI 網友留言  ：TTR = {ai_ttr:.4f} (相異詞 {ai_types} / 總詞數 {ai_tokens})")
    print("   *提示：TTR 越高代表詞彙越豐富多樣，無重複灌水罐頭留言。*")
    print("-" * 60)
    
    # 計算風格餘弦相似度
    similarity = compute_cosine_similarity(real_texts, ai_texts)
    print(f"🔗 語氣風格融入度比對 (TF-IDF Cosine Similarity)：")
    print(f"   - AI 網友與真實人類留言風格相似度：{similarity * 100:.2f}%")
    print("   *提示：相似度高於 60% 代表 AI 網友的用詞習慣與中山 Dcard 真人高度融入共鳴。*")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluation_report()
