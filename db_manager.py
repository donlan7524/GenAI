import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

DB_FILE = "nsysu_舆情.db"

def get_connection(db_path=DB_FILE):
    """
    建立 SQLite 資料庫連接。
    """
    return sqlite3.connect(db_path)

def init_db(db_path=DB_FILE):
    """
    初始化資料表：posts, keywords, daily_summary, comments，並建立 Valence-Arousal 模型欄位。
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 建立新結構的貼文主表

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        post_id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        category TEXT,
        created_at TEXT,
        valence_score REAL DEFAULT 0.0,
        arousal_score REAL DEFAULT 0.0,
        like_count INTEGER,
        comment_count INTEGER
    )
    """)
    
    # 建立關鍵字表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keywords (
        post_id TEXT,
        word TEXT,
        weight REAL,
        PRIMARY KEY (post_id, word),
        FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
    )
    """)
    
    # 建立每日情緒統計表 (Valence-Arousal 版)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_summary (
        date TEXT PRIMARY KEY,
        avg_valence REAL DEFAULT 0.0,
        avg_arousal REAL DEFAULT 0.0,
        total_posts INTEGER
    )
    """)

    # 建立留言表 (Valence-Arousal 版)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        comment_id   TEXT PRIMARY KEY,
        post_id      TEXT NOT NULL,
        content      TEXT,
        floor        INTEGER,
        valence_score REAL DEFAULT 0.0,
        arousal_score REAL DEFAULT 0.0,
        created_at   TEXT,
        FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

def save_posts_to_db(df_posts, db_path=DB_FILE):
    """
    將 DataFrame 格式的貼文及其關鍵字存入資料庫，並自動重算每日情緒統計 (daily_summary)。
    """
    if df_posts.empty:
        return
        
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. 寫入或更新貼文
    for _, row in df_posts.iterrows():
        created_str = row["created_at"]
        if isinstance(created_str, datetime):
            created_str = created_str.strftime("%Y-%m-%d %H:%M:%S")
            
        cursor.execute("""
        INSERT INTO posts (post_id, title, content, category, created_at, valence_score, arousal_score, like_count, comment_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_id) DO UPDATE SET
            title=excluded.title,
            content=excluded.content,
            category=excluded.category,
            like_count=excluded.like_count,
            comment_count=excluded.comment_count,
            valence_score=excluded.valence_score,
            arousal_score=excluded.arousal_score
        """, (
            row["post_id"], row["title"], row["content"], row["category"], created_str,
            row["valence_score"], row["arousal_score"], row["like_count"], row["comment_count"]
        ))
        
        # 2. 寫入或更新該貼文的關鍵字
        if "keywords" in row and isinstance(row["keywords"], list):
            # 先清除舊的關鍵字關聯
            cursor.execute("DELETE FROM keywords WHERE post_id = ?", (row["post_id"],))
            for word in row["keywords"]:
                cursor.execute("""
                INSERT OR IGNORE INTO keywords (post_id, word, weight)
                VALUES (?, ?, ?)
                """, (row["post_id"], word, 1.0))
                
    conn.commit()
    
    # 3. 重新計算並更新 daily_summary 資料表 (Valence-Arousal 版)
    cursor.execute("""
    DELETE FROM daily_summary
    """)
    
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
    conn.close()

def load_data_from_db(start_date, end_date, selected_categories, db_path=DB_FILE):
    """
    從資料庫讀取篩選後的 DataFrame 資料 (貼文與每日統計)。
    """
    conn = get_connection(db_path)
    
    # 轉換日期為字串
    start_str = start_date.strftime("%Y-%m-%d 00:00:00")
    end_str = end_date.strftime("%Y-%m-%d 23:59:59")
    
    # 建構分類篩選條件 SQL
    if not selected_categories:
        categories_cond = "1=0" # 都不選
        params = [start_str, end_str]
    else:
        placeholders = ",".join(["?"] * len(selected_categories))
        categories_cond = f"category IN ({placeholders})"
        params = [start_str, end_str] + list(selected_categories)
        
    # 讀取符合篩選的貼文
    posts_query = f"""
    SELECT * FROM posts 
    WHERE created_at >= ? AND created_at <= ? AND {categories_cond}
    """
    df_posts = pd.read_sql_query(posts_query, conn, params=params)
    
    # 轉換日期型態
    if not df_posts.empty:
        df_posts["created_at"] = pd.to_datetime(df_posts["created_at"])
    else:
        df_posts = pd.DataFrame(columns=[
            "post_id", "title", "content", "category", "created_at",
            "valence_score", "arousal_score", "like_count", "comment_count", "keywords"
        ])
        
    # 為每篇貼文掛載 keywords
    cursor = conn.cursor()
    post_keywords = {}
    cursor.execute("SELECT post_id, word FROM keywords")
    for pid, word in cursor.fetchall():
        if pid not in post_keywords:
            post_keywords[pid] = []
        post_keywords[pid].append(word)
        
    df_posts["keywords"] = df_posts["post_id"].map(lambda pid: post_keywords.get(pid, []))
    
    # 讀取符合篩選時間的 daily_summary 趨勢資料 (Valence-Arousal 版)
    summary_query = f"""
    SELECT 
        strftime('%Y-%m-%d', created_at) as date_str,
        round(avg(valence_score), 1) as avg_valence,
        round(avg(arousal_score), 1) as avg_arousal,
        count(*) as total_posts
    FROM posts
    WHERE created_at >= ? AND created_at <= ? AND {categories_cond}
    GROUP BY date_str
    ORDER BY date_str ASC
    """
    df_daily = pd.read_sql_query(summary_query, conn, params=params)
    if not df_daily.empty:
        df_daily["date"] = pd.to_datetime(df_daily["date_str"]).dt.date
    else:
        df_daily = pd.DataFrame(columns=["date", "avg_valence", "avg_arousal", "total_posts"])
        
    conn.close()
    return df_posts, df_daily

def save_comments_to_db(comments_list, db_path=DB_FILE):
    """
    將留言清單存入 comments 資料表。
    comments_list: List[dict]，每個 dict 包含:
        comment_id, post_id, content, floor, valence_score, arousal_score, created_at
    """
    if not comments_list:
        return 0
    conn = get_connection(db_path)
    cursor = conn.cursor()
    saved = 0
    for c in comments_list:
        try:
            cursor.execute("""
            INSERT INTO comments
                (comment_id, post_id, content, floor, valence_score, arousal_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(comment_id) DO UPDATE SET
                content=excluded.content,
                valence_score=excluded.valence_score,
                arousal_score=excluded.arousal_score
            """, (
                str(c.get("comment_id", "")),
                str(c.get("post_id", "")),
                c.get("content", ""),
                c.get("floor", 0),
                float(c.get("valence_score", 0.0)),
                float(c.get("arousal_score", 0.0)),
                c.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            ))
            saved += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return saved


def load_comments_from_db(post_id=None, limit=200, db_path=DB_FILE):
    """
    讀取留言資料。
    若指定 post_id，只回傳該篇貼文的留言；否則回傳最新 limit 筆。
    """
    conn = get_connection(db_path)
    if post_id:
        query = """
        SELECT c.*, p.title as post_title
        FROM comments c
        LEFT JOIN posts p ON c.post_id = p.post_id
        WHERE c.post_id = ?
        ORDER BY c.floor ASC
        """
        df = pd.read_sql_query(query, conn, params=[str(post_id)])
    else:
        query = """
        SELECT c.*, p.title as post_title
        FROM comments c
        LEFT JOIN posts p ON c.post_id = p.post_id
        ORDER BY c.created_at DESC
        LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=[limit])
    conn.close()
    return df


def get_comment_sentiment_summary(db_path=DB_FILE):
    """
    取得各篇貼文的留言情緒聚合統計，用於儀表板圖表 (Valence-Arousal 版)。
    回傳 DataFrame：post_id, post_title, comment_count,
                    avg_valence, avg_arousal
    """
    conn = get_connection(db_path)
    query = """
    SELECT
        c.post_id,
        p.title AS post_title,
        COUNT(*)          AS comment_count,
        ROUND(AVG(c.valence_score), 1)  AS avg_valence,
        ROUND(AVG(c.arousal_score), 1)  AS avg_arousal
    FROM comments c
    LEFT JOIN posts p ON c.post_id = p.post_id
    GROUP BY c.post_id
    ORDER BY comment_count DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def has_comments(db_path=DB_FILE):
    """檢查 comments 表是否有資料。"""
    if not os.path.exists(db_path):
        return False
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM comments")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def has_data(db_path=DB_FILE):
    """
    檢查資料庫是否有數據。
    """
    if not os.path.exists(db_path):
        return False
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM posts")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False
