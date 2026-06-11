"""
從 nsysu_舆情.db 直接產生 LoRA 微調訓練資料集
輸出：
  - poster_dataset.jsonl   (發文者訓練資料，含數據增強)
  - commenter_dataset.jsonl (留言者訓練資料，含對話上下文)
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import os
import json
import random
import sqlite3

DB_FILE = "nsysu_舆情.db"
POSTER_OUT = "poster_dataset.jsonl"
COMMENTER_OUT = "commenter_dataset.jsonl"

random.seed(42)

# ==========================================
# 性格增強模板（保留原本 data_processor.py 的設計）
# ==========================================
AUGMENTED_TEMPLATES = {
    "酸民嘴砲": [
        ("【抱怨】這學校真的沒救了：{}", "到底是要多扯？{}。學校每年收我們這麼多錢，連基本設施都搞不好，大家真的還吞得下去喔？"),
        ("有沒有{}的八卦，快被氣死", "如題，{}。真的是學店發揮無極限，不爽的快來取暖。")
    ],
    "搞笑迷因": [
        ("【爆卦】驚！{}！兇手居然是...", "今天親眼目睹現場：{}。我敢肯定這絕對又是柴山獼猴特工隊在搞鬼！🐒 有沒有人要一起去大自然跟猴王談判的？"),
        ("【閒聊】{}，難道又是猴子幹的？", "笑死，剛剛看到{}。這肯定是工學院那邊的野生阿猴拔的，超無言！😅")
    ],
    "熱心溫和": [
        ("【分享】關於{}的一些生活指引與建議", "大家好，看到最近很多人在討論{}，希望能提供大家一些幫助。大家期末加油，有問題都可以問喔！❤️"),
        ("【閒聊】{}，希望大家不要太慌張！", "看到大家因為{}很焦慮，推薦去西子灣看個夕陽吹吹風放鬆一下，會沒事的，加油！👍")
    ],
    "認真分析": [
        ("關於{}這件事，我有些想法", "仔細想想{}這件事，我覺得問題的核心在於學校的制度設計。大家可以從多角度來看這個問題，歡迎討論。"),
        ("有人了解{}的實際情況嗎？", "最近看到很多關於{}的討論，想請教一下實際狀況。如果有人有第一手資訊麻煩分享，感謝！")
    ]
}

CAMPUS_KEYWORDS = ["停水", "選課", "獼猴", "猴子", "網大", "宿舍", "西子灣", "翠亨", "武嶺",
                   "期末", "期中", "被當", "學分", "老師", "教授", "米羅", "元福", "海堤"]

def get_core_issue(title, content):
    for key in CAMPUS_KEYWORDS:
        if key in title or key in (content or ""):
            return key
    return title[:8] if title else "校園生活"

def generate_poster_records(posts):
    records = []
    for post in posts:
        title = (post["title"] or "").strip()
        content = (post["content"] or "").strip()
        if not title:
            continue

        # A. 原始資料
        records.append({
            "instruction": "請以中山大學學生的身份發布一篇校園討論貼文。",
            "input": f"主題焦點：{title[:15]}",
            "output": f"標題：{title}\n\n{content}"
        })

        # B. 數據增強（每篇抽 2 種性格）
        core = get_core_issue(title, content)
        personas = random.sample(list(AUGMENTED_TEMPLATES.keys()), 2)
        for persona in personas:
            title_tpl, body_tpl = random.choice(AUGMENTED_TEMPLATES[persona])
            aug_title = title_tpl.format(core)
            aug_body = body_tpl.format(content[:40].replace('\n', ' ') if content else core)
            records.append({
                "instruction": "請以中山大學學生的身份發布一篇校園討論貼文。",
                "input": f"主題焦點：{core}（{persona}）",
                "output": f"標題：{aug_title}\n\n{aug_body}"
            })

    return records

def generate_commenter_records(conn):
    records = []
    cursor = conn.cursor()

    # 取得所有有留言的貼文
    cursor.execute("""
        SELECT p.post_id, p.title, p.content
        FROM posts p
        WHERE EXISTS (SELECT 1 FROM comments c WHERE c.post_id = p.post_id)
        ORDER BY p.created_at
    """)
    posts = cursor.fetchall()

    for post_id, title, content in posts:
        title = (title or "").strip()
        content = (content or "").strip()

        # 取得此貼文的所有留言，按樓層排序
        cursor.execute("""
            SELECT floor, content FROM comments
            WHERE post_id = ?
            ORDER BY floor ASC
        """, (post_id,))
        comments = cursor.fetchall()

        if not comments:
            continue

        # 建立對話上下文，逐步累積
        root_context = f"原PO（標題：{title}）：{content[:200]}"
        context_lines = [root_context]

        for floor, comment_content in comments:
            if not comment_content or len(comment_content.strip()) < 3:
                continue

            comment_content = comment_content.strip()
            context_str = "\n".join(context_lines[-6:])  # 最多保留最近 6 層上下文

            records.append({
                "instruction": "您是中山大學的 AI 學生網友。請根據下方的 Dcard 貼文與留言上下文，給出合適且帶有中山大學校園文化色彩的回覆留言。",
                "input": f"=== 對話上下文 ===\n{context_str}",
                "output": comment_content
            })

            # 累積上下文
            context_lines.append(f"B{floor}：{comment_content}")

    return records

def main():
    if not os.path.exists(DB_FILE):
        print(f"❌ 找不到資料庫：{DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"📖 從 {DB_FILE} 讀取資料...")
    cursor.execute("SELECT post_id, title, content FROM posts ORDER BY created_at")
    posts = [dict(r) for r in cursor.fetchall()]
    print(f"   貼文數：{len(posts)}")

    # ── Poster 資料集 ──
    print("\n🖊️ 產生發文者 (Poster) 訓練資料...")
    poster_records = generate_poster_records(posts)
    with open(POSTER_OUT, "w", encoding="utf-8") as f:
        for r in poster_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"   ✅ {POSTER_OUT}：{len(poster_records)} 筆（含數據增強）")

    # ── Commenter 資料集 ──
    print("\n💬 產生留言者 (Commenter) 訓練資料...")
    commenter_records = generate_commenter_records(conn)
    with open(COMMENTER_OUT, "w", encoding="utf-8") as f:
        for r in commenter_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"   ✅ {COMMENTER_OUT}：{len(commenter_records)} 筆")

    conn.close()
    print(f"\n🎉 訓練資料集產生完畢！")
    print(f"   - {POSTER_OUT}：{len(poster_records)} 筆")
    print(f"   - {COMMENTER_OUT}：{len(commenter_records)} 筆")
    print(f"\n請將這兩個 .jsonl 檔案上傳至 Google Colab 進行訓練。")

if __name__ == "__main__":
    main()
