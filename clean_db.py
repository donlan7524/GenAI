import sqlite3
import os

DB_FILE = "nsysu_輿情.db"

def clean_database():
    if not os.path.exists(DB_FILE):
        print(f"❌ 找不到資料庫檔案 {DB_FILE}，無需清空。")
        return
        
    print(f"🧹 正在清空 SQLite 資料庫 ({DB_FILE}) 中的所有資料...")
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 刪除所有資料表中的資料
        cursor.execute("DELETE FROM comments")
        cursor.execute("DELETE FROM keywords")
        cursor.execute("DELETE FROM posts")
        cursor.execute("DELETE FROM daily_summary")
        
        conn.commit()
        
        # 收縮資料庫檔案以釋放空間
        cursor.execute("VACUUM")
        conn.commit()
        
        print("🎉 資料庫已成功清空並重設為初始狀態！")
        
    except Exception as e:
        print(f"❌ 清空資料庫時發生錯誤: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    confirm = input("⚠️ 您確定要清空資料庫中的所有貼文、留言與統計資料嗎？這項動作無法復原！(y/N): ")
    if confirm.lower() == 'y':
        clean_database()
    else:
        print("❌ 操作已取消。")
