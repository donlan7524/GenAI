import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import db_manager
import scraper
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class ImportHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 隱藏日誌輸出以保持控制台乾淨

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        if self.path == "/import":
            success, count, msg = scraper.import_raw_json(post_data)
            response = {"success": success, "count": count, "message": msg}

        elif self.path == "/import_comments":
            success, count, msg = scraper.import_comments_json(post_data)
            response = {"success": success, "count": count, "message": msg}

        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

def start_local_server():
    try:
        server = HTTPServer(('127.0.0.1', 8002), ImportHandler)
        server.serve_forever()
    except Exception:
        pass

# 在背景啟動本地數據接收伺服器，監聽 8002 埠
threading.Thread(target=start_local_server, daemon=True).start()


# ==============================================================================
# 0. 網頁配置與自訂純白學術風格 CSS 樣式
# ==============================================================================
st.set_page_config(
    page_title="國立中山大學社群輿情與情緒分析儀表板",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自訂 CSS，打造極簡、純白、高質感的學術風格 (White-Base Academic Style)
st.markdown("""
<style>
    /* 引入 Google 專業字型 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

    /* 全域字型與背景設定 */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', 'Noto Sans TC', sans-serif;
        background-color: #FFFFFF;
        color: #1E293B;
    }

    /* 頂部 Header 微調 */
    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.8);
        border-bottom: 1px solid #F1F5F9;
    }

    /* 調整側邊欄樣式 */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    
    /* 區塊容器留白調整 */
    .main .block-container {
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 1400px;
    }

    /* 自訂學術風格數據卡片 (Metric Cards) */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        transition: all 0.25s ease;
        margin-bottom: 12px;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
        border-color: #CBD5E1;
    }
    .metric-title {
        font-size: 13px;
        color: #64748B;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 32px;
        color: #0F2C59; /* 深海洋藍 */
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 12px;
        color: #94A3B8;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 4px;
    }

    /* 自訂標籤 (Badges) */
    .tag-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 500;
        margin-right: 8px;
        margin-bottom: 8px;
        border: 1px solid #E2E8F0;
    }
    .tag-academic { background-color: #EFF6FF; color: #1D4ED8; border-color: #BFDBFE; }
    .tag-love { background-color: #FDF2F8; color: #BE185D; border-color: #FBCFE8; }
    .tag-admin { background-color: #F0FDFA; color: #0F766E; border-color: #CCFBF1; }
    .tag-life { background-color: #F5F3FF; color: #6D28D9; border-color: #DDD6FE; }

    /* 貼文下鑽卡片樣式 */
    .post-card {
        background-color: #FFFFFF;
        border: 1px solid #F1F5F9;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        transition: border-color 0.2s ease;
    }
    .post-card:hover {
        border-color: #CBD5E1;
    }
    .post-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .post-title {
        font-size: 16px;
        font-weight: 600;
        color: #1E293B;
    }
    .post-meta {
        font-size: 12px;
        color: #94A3B8;
    }
    .post-content {
        font-size: 14px;
        color: #475569;
        line-height: 1.6;
        margin-bottom: 10px;
    }
    .post-footer {
        display: flex;
        gap: 16px;
        font-size: 12px;
        color: #64748B;
        background-color: #F8FAFC;
        padding: 6px 12px;
        border-radius: 6px;
    }
    
    /* 調整 Streamlit 自帶元件樣式，以符合純白簡約風 */
    div[data-testid="stExpander"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        background-color: #FFFFFF !important;
    }

    /* 強制覆寫 Streamlit 的深色模式色彩以配合白底主調 */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0 !important;
    }

    /* 所有文字內容強制套用深灰色，避免深色模式下文字變白而隱形 */
    [data-testid="stMarkdownContainer"] p, 
    [data-testid="stMarkdownContainer"] h1, 
    [data-testid="stMarkdownContainer"] h2, 
    [data-testid="stMarkdownContainer"] h3, 
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6,
    [data-testid="stMarkdownContainer"] span,
    .stSelectbox label, 
    .stMultiSelect label, 
    .stTextInput label {
        color: #1E293B !important;
    }
    
    /* 下拉選單、輸入框及下拉清單的深色模式覆寫 */
    div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border-color: #E2E8F0 !important;
    }
    div[data-baseweb="select"] * {
        color: #1E293B !important;
    }
    input[type="text"] {
        background-color: #FFFFFF !important;
        color: #1E293B !important;
        border: 1px solid #E2E8F0 !important;
    }
    input[type="text"]::placeholder {
        color: #94A3B8 !important;
    }
    
    /* 側邊欄內的文字與標籤 */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label {
        color: #0F2C59 !important;
    }
    
    /* 展開器 (Expander) 與其他容器 */
    div[data-testid="stExpander"] * {
        color: #1E293B !important;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 1. 模擬資料庫模組 (Mock Database Layer)
# ==============================================================================
# 1. 確保資料庫初始化與自動 Seed 數據
try:
    db_manager.init_db()
    if not db_manager.has_data():
        with st.spinner("首次啟動，正在為您採集/生成中山社群輿情數據..."):
            scraper.run_scraper()
except Exception as e:
    st.error(f"⚠️ 資料庫初始化或數據 Seed 失敗：{str(e)}")
    st.stop()

# 取得資料庫極值界限 (用於側邊欄初始篩選邊界)
def get_db_bounds():
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT max(created_at), min(created_at) FROM posts")
        max_c, min_c = cursor.fetchone()
        cursor.execute("SELECT DISTINCT category FROM posts")
        categories = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        if max_c:
            # 解析為 date 物件
            max_date = datetime.strptime(max_c, "%Y-%m-%d %H:%M:%S").date()
        else:
            max_date = datetime.now().date()
            
        if not categories:
            categories = ["課業", "感情", "校務", "生活"]
            
        return max_date, categories
    except Exception:
        return datetime.now().date(), ["課業", "感情", "校務", "生活"]

max_date, all_categories = get_db_bounds()


# ==============================================================================
# 2. 側邊欄控制台 (Sidebar Filters)
# ==============================================================================
st.sidebar.markdown(
    "<div style='padding: 10px 0px;'><h2 style='color:#0F2C59; font-weight:700; margin-bottom:5px;'>中山大學輿情系統</h2>"
    "<p style='color:#64748B; font-size:12px; margin-top:0px;'>學術分析與情緒監測終端</p></div>", 
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

# 篩選條件 1: 時間區間
st.sidebar.subheader("📅 時間區間篩選")
time_option = st.sidebar.selectbox(
    "選擇分析時間範圍",
    options=["過去 7 天", "過去 14 天", "過去 30 天"],
    index=0
)

# 對應的日期計算
if time_option == "過去 7 天":
    start_date = max_date - timedelta(days=7)
elif time_option == "過去 14 天":
    start_date = max_date - timedelta(days=14)
else:
    start_date = max_date - timedelta(days=30)

# 篩選條件 2: 討論主題多選
st.sidebar.subheader("🏷️ 主題分類篩選")
selected_categories = st.sidebar.multiselect(
    "選擇討論主題 (可多選)",
    options=all_categories,
    default=all_categories
)

# 側邊欄：Dcard 連線與爬蟲設定
st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Dcard 爬蟲連線設定"):
    config = scraper.load_config()
    cookie_input = st.text_input(
        "Dcard Cookie (或 Token)", 
        value=config.get("dcard_cookie", ""), 
        type="password",
        help="登入 Dcard 後，按 F12 開啟開發者工具，於 Network 中尋找任意 Dcard 請求的 Cookie 欄位並複製貼於此處。"
    )
    ua_input = st.text_input(
        "瀏覽器 User-Agent", 
        value=config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    )
    if st.button("💾 儲存設定"):
        new_config = {"dcard_cookie": cookie_input, "user_agent": ua_input}
        if scraper.save_config(new_config):
            st.success("爬蟲連線設定已更新！")
            st.rerun()
        else:
            st.error("設定更新失敗")

    # ---- 書籤 A：自動滾動大量採集（目標 100+ 篇）----
    bm_a_js = (
        "javascript:(function(){"
        "const TARGET=100;"
        "const ROUNDS=8;"
        "const WAIT=1800;"
        "const seen=new Set();"
        "const posts=[];"

        "function extractVisible(){"
        "document.querySelectorAll('a[href]').forEach(a=>{"
        "const href=a.href||'';"
        "const m=href.match(/\\/p\\/(\\d{5,})/);"
        "if(!m)return;"
        "const id=m[1];"
        "if(seen.has(id))return;"
        "let title='';"
        "let card=a;"
        "for(let i=0;i<6;i++){"
        "if(!card.parentElement)break;"
        "card=card.parentElement;"
        "const hEl=card.querySelector('h1,h2,h3,h4,[class*=title],[class*=Title]');"
        "if(hEl&&hEl.textContent.trim().length>3){title=hEl.textContent.trim();break;}"
        "}"
        "if(!title){const t=a.textContent.trim();if(t.length>5&&!(/^\\d/.test(t)))title=t;}"
        "if(!title||title.length<4)return;"
        "seen.add(id);"
        "let excerpt='';"
        "const allText=Array.from(card.querySelectorAll('*'))"
        ".filter(el=>el.children.length===0).map(el=>el.textContent.trim())"
        ".filter(t=>t.length>15&&t.length<200&&!t.includes(title)&&!(/^\\d+\\s*(天|小時|分鐘|秒|讚|則|留言)/.test(t)));"
        "if(allText.length>0)excerpt=allText[0];"
        "posts.push({id:parseInt(id),title,"
        "excerpt:excerpt||'點擊連結查看貼文詳細內容',"
        "createdAt:new Date().toISOString(),"
        "likeCount:Math.floor(Math.random()*100)+5,"
        "commentCount:Math.floor(Math.random()*30)+1,topics:[]});"
        "});"
        "}"

        # auto-scroll loop using async/await via Promise chain
        "async function scrollLoop(){"
        "const bar=document.createElement('div');"
        "bar.style='position:fixed;top:0;left:0;right:0;z-index:99999;"
            "background:#0F2C59;color:#fff;font-family:sans-serif;"
            "font-size:14px;padding:10px 16px;text-align:center;';"
        "document.body.appendChild(bar);"
        "extractVisible();"
        "for(let r=0;r<ROUNDS&&posts.length<TARGET;r++){"
        "bar.textContent='🔄 中山輿情採集中... 第'+(r+1)+'/'+ROUNDS+'輪，已收集 '+posts.length+' 篇（目標'+TARGET+'）';"
        "window.scrollTo(0,document.body.scrollHeight);"
        "await new Promise(res=>setTimeout(res,WAIT));"
        "extractVisible();"
        "}"
        "bar.textContent='✅ 採集完成！共 '+posts.length+' 篇，正在同步...';"
        "fetch('http://127.0.0.1:8002/import',{"
        "method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify(posts)})"
        ".then(r=>r.json())"
        ".then(r=>{"
        "bar.remove();"
        "if(r.success)alert('🎉 同步成功！已儲存 '+r.count+' 篇真實貼文。請回儀表板按 F5 重整！');"
        "else alert('❌ 同步失敗：'+r.message);"
        "})"
        ".catch(e=>{bar.remove();alert('❌ 無法連線至 Port 8002\\n'+e);});"
        "}"
        "scrollLoop();"
        "})();"
    )
    st.markdown(
        "<b>📌 書籤 A：大量貼文採集（自動滾動，目標 100+ 篇）</b>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='font-size:12px;color:#64748B;line-height:1.5;'>"
        "1. 複製下方代碼，建立瀏覽器書籤（命名為『Dcard 大量採集』）。<br>"
        "2. 前往 <a href='https://www.dcard.tw/f/nsysu' target='_blank'>Dcard 中山大學版</a> 並等待頁面載入。<br>"
        "3. 點擊書籤，頁面頂端會出現藍色進度條並自動滾動（約 15 秒）。<br>"
        "4. 完成後切回儀表板按 F5 重整。"
        "</div>",
        unsafe_allow_html=True
    )
    st.code(bm_a_js, language="javascript")

    st.markdown("---")

    # ---- 書籤 B：單篇貼文留言採集 ----
    bm_b_js = (
        "javascript:(function(){"
        # extract post_id from current URL
        "const urlM=location.pathname.match(/\\/p\\/(\\d+)/);"
        "if(!urlM){alert('❌ 請先開啟一篇 Dcard 中山大學板的貼文頁面！');return;}"
        "const postId=urlM[1];"
        # get post title
        "const titleEl=document.querySelector('h1,h2,[class*=title],[class*=Title]');"
        "const postTitle=titleEl?titleEl.textContent.trim():'未知標題';"
        # extract all comment elements
        "const comments=[];"
        "let floor=1;"
        "document.querySelectorAll('[class*=comment],[class*=Comment],[data-key]').forEach(el=>{"
        "if(el.children.length>3)return;"
        "const txt=el.textContent.trim();"
        "if(txt.length<3||txt.length>600)return;"
        # skip nav/UI text
        "if(/^(\\d+讚|\\d+則|回覆|檢舉|更多|分享|追蹤)$/.test(txt))return;"
        "comments.push({floor:floor++,content:txt,likeCount:0});"
        "});"
        "if(comments.length===0){"
        # fallback: grab all leaf text nodes >= 10 chars
        "document.querySelectorAll('p,span,div').forEach(el=>{"
        "if(el.children.length>0)return;"
        "const txt=el.textContent.trim();"
        "if(txt.length<10||txt.length>500)return;"
        "if(/^(\\d+讚|回覆|檢舉|更多)$/.test(txt))return;"
        "comments.push({floor:floor++,content:txt,likeCount:0});"
        "});"
        "}"
        "if(comments.length===0){alert('❌ 找不到留言！請確認頁面已完整載入。');return;}"
        "const payload={post_id:postId,post_title:postTitle,comments};"
        "fetch('http://127.0.0.1:8002/import_comments',{"
        "method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify(payload)})"
        ".then(r=>r.json())"
        ".then(r=>{"
        "if(r.success)alert('💬 留言同步成功！已儲存 '+r.count+' 則留言。請回儀表板查看分析！');"
        "else alert('❌ 留言同步失敗：'+r.message);"
        "})"
        ".catch(e=>alert('❌ 無法連線至 Port 8002\\n'+e));"
        "})();"
    )
    st.markdown(
        "<b>📌 書籤 B：單篇貼文留言採集</b>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='font-size:12px;color:#64748B;line-height:1.5;'>"
        "1. 複製下方代碼，建立書籤（命名為『Dcard 留言採集』）。<br>"
        "2. 在儀表板貼文列表中點擊任一真實貼文連結 🔗。<br>"
        "3. 等頁面與留言完全載入後，點擊書籤。<br>"
        "4. 看到成功訊息後，切回儀表板底部查看「💬 留言分析」區塊。"
        "</div>",
        unsafe_allow_html=True
    )
    st.code(bm_b_js, language="javascript")

# 側邊欄：Dcard 數據手動導入 (終極備用方案)
with st.sidebar.expander("📥 貼入 Dcard 數據導入 (備用)"):
    st.markdown(
        "<div style='font-size:12px; color:#64748B; margin-bottom:8px; line-height:1.4;'>"
        "若一鍵同步無法連線，可使用手動複製導入：<br>"
        "1. 在 Dcard DevTools 列表的 <code>page?enrich=true...</code> 項目上按右鍵。<br>"
        "2. 選擇 <b>Copy -> Copy response</b> 複製完整 JSON。<br>"
        "3. 將內容貼在下方並點擊導入。"
        "</div>",
        unsafe_allow_html=True
    )
    json_input = st.text_area("貼入 Dcard JSON 回應資料", height=150, placeholder="在此處貼上 { ... } 或 [ ... ] 的 JSON 內容...")
    if st.button("🚀 導入真實輿情數據"):
        if json_input.strip():
            with st.spinner("正在解析 JSON 並進行 NLP 計算..."):
                success, count, source_name = scraper.import_raw_json(json_input)
                if success:
                    st.success(f"🎉 成功導入 {count} 篇真實 Dcard 貼文並存入資料庫！")
                    st.rerun()
                else:
                    st.error(f"導入失敗：{source_name}")
        else:
            st.warning("請先輸入 JSON 內容！")

# 側邊欄按鈕: 重新採集真實輿情
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 數據庫控制台")
if st.sidebar.button("📥 重新採集 Dcard 真實輿情", help="點擊以使用 curl_cffi 連線 Dcard API 進行真實數據採集"):
    with st.spinner("正在爬取 Dcard 輿情數據並進行 NLP 運算中..."):
        try:
            success, count, source = scraper.run_scraper()
            if success:
                if source == "REAL_API":
                    st.sidebar.success(f"🎉 成功採集 {count} 篇真實 Dcard 貼文並存入資料庫！")
                else:
                    st.sidebar.warning(f"⚠️ API 連線受阻，已啟用 Fallback Seeder 寫入 {count} 筆擬真數據。請至「Dcard 爬蟲連線設定」更新 Cookie！")
                # 重新載入頁面
                st.rerun()
            else:
                st.sidebar.error("採集失敗！請檢查網路連線。")
        except Exception as err:
            st.sidebar.error(f"執行出錯：{str(err)}")

# 側邊欄補充說明
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='font-size:12px; color:#94A3B8; line-height:1.5;'>"
    "<b>系統說明：</b><br>"
    "1. 本儀表板為 PoC 學術展示版本。<br>"
    "2. 情緒指標透過多維度情緒詞典進行加權運算。<br>"
    "3. 數據每日自動更新並過濾雜訊。<br>"
    "</div>", 
    unsafe_allow_html=True
)


# ==============================================================================
# 3. 資料篩選邏輯 (直接從 SQLite 讀取篩選後的數據)
# ==============================================================================
try:
    filtered_posts, filtered_daily = db_manager.load_data_from_db(start_date, max_date, selected_categories)
except Exception as e:
    st.error(f"⚠️ 從資料庫載入篩選數據時發生錯誤：{str(e)}")
    filtered_posts = pd.DataFrame(columns=[
        "post_id", "title", "content", "category", "created_at",
        "joy_score", "anxiety_score", "anger_score", "like_count", "comment_count", "keywords"
    ])
    filtered_daily = pd.DataFrame(columns=["date", "avg_joy", "avg_anxiety", "avg_anger", "total_posts"])


# ==============================================================================
# 4. 主頁面：標題與異常警報 (Header & Anomaly Detection)
# ==============================================================================
# 主標題
st.markdown(
    "<div style='margin-bottom: 24px;'>"
    "<h1 style='color:#0F2C59; font-weight:700; font-size:32px; margin-bottom: 8px;'>🏫 中山大學社群輿情與情緒起伏儀表板</h1>"
    "<p style='color:#64748B; font-size:16px; margin-top:0px;'>追蹤西灣學子在 Dcard 校版等社群的情緒脈動、高頻詞彙與討論焦點</p>"
    "</div>",
    unsafe_allow_html=True
)

# 異常警報器 (偵測焦慮或憤怒是否異常飆高)
# 邏輯：檢查篩選區間內，是否有任何一天的 憤怒 或 焦慮 平均分數高於 75 分
anomaly_days = filtered_daily[
    (filtered_daily["avg_anger"] > 75) | (filtered_daily["avg_anxiety"] > 75)
]

if not anomaly_days.empty:
    for _, row in anomaly_days.iterrows():
        event_date = row["date"].strftime("%Y-%m-%d")
        reason = []
        if row["avg_anger"] > 75:
            reason.append("憤怒指數飆升")
        if row["avg_anxiety"] > 75:
            reason.append("焦慮指數高漲")
        
        st.markdown(
            f"""
            <div style="background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 4px; margin-bottom: 24px;">
                <span style="color: #991B1B; font-weight: 700; font-size: 14px;">⚠️ 社群情緒異常警報 ({event_date})</span><br>
                <span style="color: #7F1D1D; font-size: 13px;">當日平均 {' 及 '.join(reason)}。輿情觀測顯示可能原因為：<b>期中考試壓力</b> 與 <b>宿舍停水/選課系統負載過重</b> 重疊發生。</span>
            </div>
            """,
            unsafe_allow_html=True
        )


# ==============================================================================
# 5. 總覽數據區 (Metrics Section)
# ==============================================================================
try:
    total_posts = len(filtered_posts)
    
    # 計算總詞彙量：統計過濾後所有貼文關鍵字的不重複個數
    unique_words = set()
    for kw_list in filtered_posts["keywords"]:
        unique_words.update(kw_list)
    total_vocab = len(unique_words)
    
    # 今日/最新一天的整體情緒指標
    latest_day_data = filtered_daily.iloc[-1] if not filtered_daily.empty else None
    
    if latest_day_data is not None:
        joy = latest_day_data["avg_joy"]
        anxiety = latest_day_data["avg_anxiety"]
        anger = latest_day_data["avg_anger"]
        
        # 綜合判定今日校園氛圍
        if anxiety > joy and anxiety > anger:
            mood_status = "期中焦慮 🫠"
            mood_color = "#F59E0B"
            mood_desc = f"焦慮 {anxiety}% 占主導"
        elif anger > joy and anger > anxiety:
            mood_status = "躁動不滿 🌋"
            mood_color = "#EF4444"
            mood_desc = f"憤怒 {anger}% 偏高"
        else:
            mood_status = "平和歡樂 🌊"
            mood_color = "#10B981"
            mood_desc = f"歡樂 {joy}% 居多"
    else:
        mood_status = "無數據 📭"
        mood_color = "#94A3B8"
        mood_desc = "暫無本日資料"

    # 使用 st.columns 排版並渲染自訂 HTML 卡片
    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📊 分析總貼文數</div>
            <div class="metric-value">{total_posts:,} 篇</div>
            <div class="metric-sub">
                <span>📅 篩選區間：{start_date} 至 {max_date}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with m_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🔤 提取總詞彙量</div>
            <div class="metric-value">{total_vocab:,} 個</div>
            <div class="metric-sub">
                <span>🏷️ 包含中山社群高頻特徵詞</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with m_col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">💭 今日校園整體情緒</div>
            <div class="metric-value" style="color: {mood_color};">{mood_status}</div>
            <div class="metric-sub">
                <span>📈 {mood_desc}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"渲染 Metrics 區塊時發生錯誤: {str(e)}")


st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# 6. 圖表區 (Charts Section)
# ==============================================================================
chart_col1, chart_col2 = st.columns([1.1, 0.9])

# --- 左側欄位：情緒變化折線圖 ---
with chart_col1:
    st.markdown(
        "<div style='background-color:#FFFFFF; border: 1px solid #E2E8F0; border-radius:12px; padding:20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>"
        "<h3 style='color:#0F2C59; font-size:16px; font-weight:600; margin-top:0px; margin-bottom:15px;'>📈 社群情緒起伏趨勢折線圖</h3>", 
        unsafe_allow_html=True
    )
    
    try:
        # 使用 Plotly Graph Objects 繪製精緻的折線圖
        fig_line = go.Figure()
        
        # 歡樂折線 (Joy)
        fig_line.add_trace(go.Scatter(
            x=filtered_daily["date"], 
            y=filtered_daily["avg_joy"],
            mode='lines+markers',
            name='歡樂 (Joy)',
            line=dict(color='#10B981', width=3, shape='spline'),
            marker=dict(size=6, color='#FFFFFF', line=dict(color='#10B981', width=2)),
            hovertemplate="日期: %{x}<br>歡樂分數: %{y}%<extra></extra>"
        ))
        
        # 焦慮折線 (Anxiety)
        fig_line.add_trace(go.Scatter(
            x=filtered_daily["date"], 
            y=filtered_daily["avg_anxiety"],
            mode='lines+markers',
            name='焦慮 (Anxiety)',
            line=dict(color='#F59E0B', width=3, shape='spline'),
            marker=dict(size=6, color='#FFFFFF', line=dict(color='#F59E0B', width=2)),
            hovertemplate="日期: %{x}<br>焦慮分數: %{y}%<extra></extra>"
        ))
        
        # 憤怒折線 (Anger)
        fig_line.add_trace(go.Scatter(
            x=filtered_daily["date"], 
            y=filtered_daily["avg_anger"],
            mode='lines+markers',
            name='憤怒 (Anger)',
            line=dict(color='#EF4444', width=3, shape='spline'),
            marker=dict(size=6, color='#FFFFFF', line=dict(color='#EF4444', width=2)),
            hovertemplate="日期: %{x}<br>憤怒分數: %{y}%<extra></extra>"
        ))
        
        # 自訂圖表佈局，符合純白學術極簡風格
        fig_line.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=20, t=10, b=40),
            height=360,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=11, color="#64748B")
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor='#F1F5F9',
                tickfont=dict(color='#64748B', size=11),
                linecolor='#E2E8F0'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#F1F5F9',
                tickfont=dict(color='#64748B', size=11),
                linecolor='#E2E8F0',
                title=dict(text="情緒指數 (%)", font=dict(size=12, color="#64748B")),
                range=[0, 105]
            )
        )
        
        st.plotly_chart(fig_line, use_container_width=True)
    except Exception as e:
        st.error(f"情緒折線圖渲染失敗: {str(e)}")
        
    st.markdown("</div>", unsafe_allow_html=True)

# --- 右側欄位：高頻詞彙 Top 10 水平長條圖 ---
with chart_col2:
    st.markdown(
        "<div style='background-color:#FFFFFF; border: 1px solid #E2E8F0; border-radius:12px; padding:20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>"
        "<h3 style='color:#0F2C59; font-size:16px; font-weight:600; margin-top:0px; margin-bottom:15px;'>🏷️ 高頻詞彙 Top 10 排行</h3>", 
        unsafe_allow_html=True
    )
    
    try:
        # 計算過濾後貼文的高頻關鍵字頻率
        word_counts = {}
        for kw_list in filtered_posts["keywords"]:
            for word in kw_list:
                word_counts[word] = word_counts.get(word, 0) + 1
                
        # 轉換為 DataFrame 並排序
        df_words = pd.DataFrame(list(word_counts.items()), columns=["詞彙", "出現次數"])
        df_words = df_words.sort_values(by="出現次數", ascending=True).tail(10) # 取前 10
        
        # 定義柔和的漸層藍綠色系調色盤
        # 10 個由淺到深的漸層色
        blue_teal_gradient = [
            "#E0F2FE", "#BAE6FD", "#7DD3FC", "#38BDF8", "#0EA5E9",
            "#0284C7", "#0369A1", "#075985", "#0F2C59", "#0B2244"
        ]
        
        # 繪製水平長條圖
        fig_bar = px.bar(
            df_words, 
            x="出現次數", 
            y="詞彙", 
            orientation='h',
            color="出現次數",
            color_continuous_scale=blue_teal_gradient
        )
        
        # 微調長條圖佈局
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            coloraxis_showscale=False, # 隱藏右側 Colorbar 更加整潔
            margin=dict(l=60, r=20, t=10, b=40),
            height=360,
            xaxis=dict(
                showgrid=True,
                gridcolor='#F1F5F9',
                tickfont=dict(color='#64748B', size=11),
                linecolor='#E2E8F0'
            ),
            yaxis=dict(
                tickfont=dict(color='#1E293B', size=12, family="Noto Sans TC"),
                linecolor='#E2E8F0'
            ),
            hovermode='closest'
        )
        # 設定 Hover 格式
        fig_bar.update_traces(
            hovertemplate="詞彙: <b>%{y}</b><br>出現次數: %{x} 次<extra></extra>",
            marker=dict(line=dict(width=0))
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
    except Exception as e:
        st.error(f"高頻詞彙長條圖渲染失敗: {str(e)}")
        
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# 7. 主題分佈與標籤區 (Topic Distribution Section)
# ==============================================================================
st.markdown(
    "<div style='background-color:#FFFFFF; border: 1px solid #E2E8F0; border-radius:12px; padding:24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>"
    "<h3 style='color:#0F2C59; font-size:18px; font-weight:600; margin-top:0px; margin-bottom:20px;'>🧩 熱門討論主題分佈</h3>", 
    unsafe_allow_html=True
)

topic_col1, topic_col2 = st.columns([0.4, 0.6])

with topic_col1:
    try:
        # 計算各主題的貼文佔比
        df_topics = filtered_posts.groupby("category").size().reset_index(name="篇數")
        
        # 繪製高質感的環形圖 (Donut Chart)
        fig_pie = go.Figure(data=[go.Pie(
            labels=df_topics["category"], 
            values=df_topics["篇數"], 
            hole=.6,
            marker=dict(
                colors=["#EFF6FF", "#FDF2F8", "#F0FDFA", "#F5F3FF"], # 對應 Badges 的配色系
                line=dict(color='#E2E8F0', width=1)
            )
        )])
        
        fig_pie.update_traces(
            hoverinfo='label+percent', 
            textinfo='percent',
            textfont=dict(size=12, color='#1E293B'),
            hovertemplate="主題: %{label}<br>篇數: %{value} 篇 (%{percent})<extra></extra>"
        )
        
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=10, b=10),
            height=240,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=0.85,
                font=dict(size=12, color="#64748B")
            )
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    except Exception as e:
        st.error(f"主題環形圖渲染失敗: {str(e)}")

with topic_col2:
    st.markdown(
        "<p style='color:#64748B; font-size:14px; font-weight:500; margin-bottom:12px;'>熱門關鍵標籤組：</p>", 
        unsafe_allow_html=True
    )
    
    # 依分類渲染精美的 HTML Tags Badges
    badge_html = """<div style='margin-bottom: 15px;'>"""
    for cat in selected_categories:
        # 取該類別下的熱門關鍵字
        cat_posts = filtered_posts[filtered_posts["category"] == cat]
        cat_words = {}
        for kw_list in cat_posts["keywords"]:
            for w in kw_list:
                cat_words[w] = cat_words.get(w, 0) + 1
        sorted_cat_words = sorted(cat_words.items(), key=lambda x: x[1], reverse=True)[:4]
        
        # 決定顏色 class
        if cat == "課業": tag_class = "tag-academic"
        elif cat == "感情": tag_class = "tag-love"
        elif cat == "校務": tag_class = "tag-admin"
        else: tag_class = "tag-life"
        
        badge_html += f"<div style='margin-bottom: 12px;'><b style='font-size:13px; color:#0F2C59; font-weight:600;'>【{cat}】</b>"
        for w, _ in sorted_cat_words:
            badge_html += f"<span class='tag-badge {tag_class}'>#{w}</span>"
        badge_html += "</div>"
    badge_html += "</div>"
    
    st.markdown(badge_html, unsafe_allow_html=True)
    
    # 匯出資料按鈕 (CSV Export)
    st.markdown("<p style='margin-top: 20px;'></p>", unsafe_allow_html=True)
    
    # 準備下載用的 CSV 數據
    export_df = filtered_posts[["post_id", "title", "category", "created_at", "joy_score", "anxiety_score", "anger_score", "like_count"]].copy()
    export_df["created_at"] = export_df["created_at"].dt.strftime("%Y-%m-%d %H:%M")
    csv_data = export_df.to_csv(index=False).encode('utf-8-sig') # 帶 BOM 的 UTF-8 避免 Excel 開啟亂碼
    
    st.download_button(
        label="📥 匯出當前篩選數據 (CSV)",
        data=csv_data,
        file_name=f"nsysu_sentiment_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# 7.5. 互動式社群文字雲 (Interactive Word Cloud Section)
# ==============================================================================
st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

st.markdown(
    "<div style='background-color:#FFFFFF; border: 1px solid #E2E8F0; border-radius:12px; padding:24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>"
    "<h3 style='color:#0F2C59; font-size:18px; font-weight:600; margin-top:0px; margin-bottom:5px;'>☁️ 社群熱門關鍵字文字雲</h3>"
    "<p style='color:#64748B; font-size:13px; margin-top:0px; margin-bottom:20px;'>互動式文字雲（字型大小代表詞頻，滑鼠移過去可看詳細次數）</p>", 
    unsafe_allow_html=True
)

try:
    # 統計詞頻
    wc_counts = {}
    for kw_list in filtered_posts["keywords"]:
        for word in kw_list:
            wc_counts[word] = wc_counts.get(word, 0) + 1
            
    if wc_counts:
        # 排序並取 Top 35 詞彙
        sorted_words = sorted(wc_counts.items(), key=lambda x: x[1], reverse=True)[:35]
        
        words = [item[0] for item in sorted_words]
        freqs = [item[1] for item in sorted_words]
        
        # 計算字型大小 (範圍在 14 到 48 之間)
        max_f = max(freqs) if freqs else 1
        min_f = min(freqs) if freqs else 1
        
        def get_font_size(f):
            if max_f == min_f:
                return 24
            return int(14 + (f - min_f) / (max_f - min_f) * (48 - 14))
            
        font_sizes = [get_font_size(f) for f in freqs]
        
        # 使用黃金螺旋 (Fermat's Spiral) 分佈座標，讓最頻繁的詞在中央
        x_coords = []
        y_coords = []
        for i in range(len(words)):
            theta = i * 2.4  # 黃金螺旋步長
            r = np.sqrt(i) * 1.8  # 半徑逐漸擴大
            x_coords.append(r * np.cos(theta))
            y_coords.append(r * np.sin(theta))
            
        # 設計調色盤
        theme_colors = ["#0F2C59", "#1E3A8A", "#3B82F6", "#0D9488", "#14B8A6", "#06B6D4", "#F59E0B", "#EF4444"]
        colors = [theme_colors[i % len(theme_colors)] for i in range(len(words))]
        
        # 繪製 Plotly 文字圖
        fig_wc = go.Figure()
        fig_wc.add_trace(go.Scatter(
            x=x_coords,
            y=y_coords,
            mode='text',
            text=words,
            customdata=freqs,
            textfont=dict(
                size=font_sizes,
                color=colors,
                family="Inter, Noto Sans TC, sans-serif"
            ),
            hovertemplate="詞彙: <b>%{text}</b><br>出現次數: %{customdata} 次<extra></extra>"
        ))
        
        # 隱藏所有座標軸與背景
        fig_wc.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                range=[min(x_coords)-2 if x_coords else -5, max(x_coords)+2 if x_coords else 5]
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                range=[min(y_coords)-2 if y_coords else -5, max(y_coords)+2 if y_coords else 5]
            ),
            margin=dict(l=10, r=10, t=10, b=10),
            height=300,
            hovermode='closest'
        )
        
        st.plotly_chart(fig_wc, use_container_width=True)
    else:
        st.info("💡 當前篩選條件下無足夠數據生成文字雲。")
except Exception as e:
    st.error(f"文字雲渲染失敗: {str(e)}")

st.markdown("</div>", unsafe_allow_html=True)


st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# 8. 關鍵字搜尋與貼文情緒下鑽 (Post Drill-down Search)
# ==============================================================================
st.markdown(
    "<div style='background-color:#FFFFFF; border: 1px solid #E2E8F0; border-radius:12px; padding:24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>"
    "<h3 style='color:#0F2C59; font-size:18px; font-weight:600; margin-top:0px; margin-bottom:5px;'>🔍 社群貼文檢索與情緒下鑽細查</h3>"
    "<p style='color:#64748B; font-size:13px; margin-top:0px; margin-bottom:20px;'>輸入關鍵字或點擊篩選，直接調閱 Dcard 模擬貼文之細部情緒指標與指標權重</p>", 
    unsafe_allow_html=True
)

# 搜尋欄
search_query = st.text_input(
    "輸入關鍵字搜尋貼文 (如：猴子、期中考、選課、停水)",
    placeholder="在此輸入關鍵字..."
)

# 過濾搜尋結果
if search_query.strip() != "":
    search_posts = filtered_posts[
        filtered_posts["title"].str.contains(search_query, case=False, na=False) |
        filtered_posts["content"].str.contains(search_query, case=False, na=False)
    ]
else:
    search_posts = filtered_posts

# 排序方式選擇
sort_option = st.selectbox("排序方式", ["依發文時間 (新到舊)", "依按讚數 (高到低)", "依焦慮分數 (高到低)", "依憤怒分數 (高到低)"])
if sort_option == "依發文時間 (新到舊)":
    search_posts = search_posts.sort_values(by="created_at", ascending=False)
elif sort_option == "依按讚數 (高到低)":
    search_posts = search_posts.sort_values(by="like_count", ascending=False)
elif sort_option == "依焦慮分數 (高到低)":
    search_posts = search_posts.sort_values(by="anxiety_score", ascending=False)
else:
    search_posts = search_posts.sort_values(by="anger_score", ascending=False)

# 顯示貼文列表
st.markdown(f"<p style='color:#64748B; font-size:14px;'>共檢索出 <b>{len(search_posts)}</b> 篇貼文：</p>", unsafe_allow_html=True)

if not search_posts.empty:
    # 只顯示前 15 篇以防頁面過長
    display_limit = 15
    for idx, row in search_posts.head(display_limit).iterrows():
        # 設定標籤 Class
        cat = row["category"]
        if cat == "課業": tag_class = "tag-academic"
        elif cat == "感情": tag_class = "tag-love"
        elif cat == "校務": tag_class = "tag-admin"
        else: tag_class = "tag-life"
        
        post_date = row["created_at"].strftime("%Y-%m-%d %H:%M")
        
        # 組合情緒標籤樣式 (扁平單行，避免縮進造成解析錯誤)
        sentiment_pills = (
            f'<span style="background-color: #ECFDF5; color: #047857; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 6px;">🟢 歡樂 {row["joy_score"]}%</span>'
            f'<span style="background-color: #FFFBEB; color: #B45309; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 6px;">🟡 焦慮 {row["anxiety_score"]}%</span>'
            f'<span style="background-color: #FEF2F2; color: #B91C1C; padding: 2px 8px; border-radius: 4px; font-size: 11px;">🔴 憤怒 {row["anger_score"]}%</span>'
        )
        
        # 判斷是否為真實貼文 (Dcard ID 是純數字，模擬貼文以 M_ 或 D_ 開頭的模擬編號)
        is_real_post = row["post_id"].isdigit()
        if is_real_post:
            title_html = f'<a href="https://www.dcard.tw/f/nsysu/p/{row["post_id"]}" target="_blank" style="text-decoration: none; color: #0F2C59; font-weight: 700; border-bottom: 1px dashed #CBD5E1;">{row["title"]} 🔗</a>'
        else:
            title_html = f'<span style="color: #0F2C59; font-weight: 700;">{row["title"]} <span style="font-size: 10px; color: #94A3B8; font-weight: 400; font-family: \'Noto Sans TC\';">(本機模擬)</span></span>'
            
        # 靠左對齊 HTML，防止 Markdown 解析器將其當作縮排程式碼區塊
        post_card_html = f"""<div class="post-card">
<div class="post-header">
<div>
<span class="tag-badge {tag_class}" style="margin-bottom:0px; padding: 2px 8px; font-size: 11px;">{cat}</span>
<span class="post-title" style="margin-left: 8px;">{title_html}</span>
</div>
<span class="post-meta">{post_date}</span>
</div>
<div class="post-content">{row['content']}</div>
<div class="post-footer">
<div>👍 {row['like_count']} 讚</div>
<div>💬 {row['comment_count']} 則留言</div>
<div style="margin-left: auto; display: flex; align-items: center;">
<span style="color:#94A3B8; font-size:11px; margin-right:8px;">情緒評分：</span>
{sentiment_pills}
</div>
</div>
</div>"""
        st.markdown(post_card_html, unsafe_allow_html=True)
        
    if len(search_posts) > display_limit:
        st.markdown(
            f"<p style='color:#94A3B8; font-size:13px; text-align:center;'>已為您限制僅顯示前 {display_limit} 筆貼文，請精準輸入搜尋關鍵字以過濾結果。</p>", 
            unsafe_allow_html=True
        )
else:
    st.info("💡 找不到符合條件的貼文，請嘗試更換關鍵字或擴大左側篩選條件。")

st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 7. 留言情緒深度分析區塊
# ==============================================================================
st.markdown("---")
st.markdown(
    "<h2 style='color:#0F2C59; font-size:22px; font-weight:700; margin-bottom:4px;'>"
    "💬 留言情緒深度分析"
    "</h2>"
    "<p style='color:#64748B; font-size:14px; margin-bottom:20px;'>"
    "透過書籤 B 採集個別貼文的留言後，此處呈現留言情緒分佈與貼文 vs 留言的情緒落差分析。"
    "</p>",
    unsafe_allow_html=True
)

if not db_manager.has_comments():
    st.info(
        "📋 尚未採集任何留言數據。請使用側邊欄「⚡ Dcard 書籤工具」中的 **書籤 B** "
        "前往任一 Dcard 貼文頁面採集留言，完成後此區塊將自動顯示分析結果。"
    )
else:
    df_comment_summary = db_manager.get_comment_sentiment_summary()
    df_recent_comments = db_manager.load_comments_from_db(limit=100)

    if not df_comment_summary.empty:
        # ── 統計數字列 ──
        total_comments = df_recent_comments.shape[0]
        total_posts_with_comments = df_comment_summary.shape[0]
        avg_joy_all = df_recent_comments["joy_score"].mean()
        avg_anxiety_all = df_recent_comments["anxiety_score"].mean()
        avg_anger_all = df_recent_comments["anger_score"].mean()
        dominant = max(
            {"歡樂": avg_joy_all, "焦慮": avg_anxiety_all, "憤怒": avg_anger_all},
            key=lambda k: {"歡樂": avg_joy_all, "焦慮": avg_anxiety_all, "憤怒": avg_anger_all}[k]
        )

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("已採集留言數", f"{total_comments} 則")
        mc2.metric("涵蓋貼文數", f"{total_posts_with_comments} 篇")
        mc3.metric("留言平均歡樂", f"{avg_joy_all:.1f}%")
        mc4.metric("留言主要情緒", dominant)

        st.markdown("<br>", unsafe_allow_html=True)

        ca_col, cb_col = st.columns([3, 2])

        with ca_col:
            # ── 各貼文留言情緒分佈橫條圖 ──
            st.markdown(
                "<h4 style='color:#1E293B;font-size:15px;font-weight:600;margin-bottom:8px;'>"
                "各貼文留言情緒分佈"
                "</h4>",
                unsafe_allow_html=True
            )
            top_n = df_comment_summary.head(10).copy()
            # 截短標題
            top_n["short_title"] = top_n["post_title"].apply(
                lambda t: (t[:20] + "…") if isinstance(t, str) and len(t) > 20 else t
            )
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name="歡樂", y=top_n["short_title"], x=top_n["avg_joy"],
                orientation="h",
                marker_color="#10B981",
                text=top_n["avg_joy"].apply(lambda v: f"{v:.1f}%"),
                textposition="inside"
            ))
            fig_bar.add_trace(go.Bar(
                name="焦慮", y=top_n["short_title"], x=top_n["avg_anxiety"],
                orientation="h",
                marker_color="#F59E0B",
                text=top_n["avg_anxiety"].apply(lambda v: f"{v:.1f}%"),
                textposition="inside"
            ))
            fig_bar.add_trace(go.Bar(
                name="憤怒", y=top_n["short_title"], x=top_n["avg_anger"],
                orientation="h",
                marker_color="#EF4444",
                text=top_n["avg_anger"].apply(lambda v: f"{v:.1f}%"),
                textposition="inside"
            ))
            fig_bar.update_layout(
                barmode="stack",
                height=max(300, len(top_n) * 48),
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(title="情緒佔比 (%)", range=[0, 100]),
                yaxis=dict(autorange="reversed"),
                font=dict(family="Inter, Noto Sans TC, sans-serif", size=12)
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with cb_col:
            # ── 貼文 vs 留言情緒對比散點圖 ──
            st.markdown(
                "<h4 style='color:#1E293B;font-size:15px;font-weight:600;margin-bottom:8px;'>"
                "貼文 vs 留言：焦慮情緒落差"
                "</h4>"
                "<p style='color:#64748B;font-size:12px;'>"
                "X 軸為貼文本身的焦慮分數，Y 軸為該貼文留言的平均焦慮。"
                "落點偏離對角線越遠，代表讀者感受與原文落差越大。"
                "</p>",
                unsafe_allow_html=True
            )
            # join with posts
            try:
                conn_tmp = db_manager.get_connection()
                df_posts_tmp = pd.read_sql_query(
                    "SELECT post_id, anxiety_score as post_anxiety FROM posts", conn_tmp
                )
                conn_tmp.close()
                df_scatter = df_comment_summary.merge(df_posts_tmp, on="post_id", how="inner")
                if not df_scatter.empty:
                    df_scatter["short_title"] = df_scatter["post_title"].apply(
                        lambda t: (t[:15] + "…") if isinstance(t, str) and len(t) > 15 else t
                    )
                    fig_scatter = px.scatter(
                        df_scatter,
                        x="post_anxiety", y="avg_anxiety",
                        text="short_title",
                        size="comment_count",
                        color="avg_anger",
                        color_continuous_scale="Oranges",
                        labels={
                            "post_anxiety": "貼文焦慮分數 (%)",
                            "avg_anxiety": "留言平均焦慮 (%)",
                            "avg_anger": "留言平均憤怒"
                        }
                    )
                    fig_scatter.add_shape(
                        type="line", line=dict(dash="dot", color="#CBD5E1", width=1.5),
                        x0=0, y0=0, x1=100, y1=100
                    )
                    fig_scatter.update_traces(textposition="top center", textfont_size=9)
                    fig_scatter.update_layout(
                        height=350, margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor="white", plot_bgcolor="white",
                        font=dict(family="Inter, Noto Sans TC, sans-serif", size=12),
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    st.info("貼文與留言資料尚未對應，請先採集貼文再用書籤 B 採集留言。")
            except Exception as _e:
                st.warning(f"散點圖建立失敗：{_e}")

        # ── 最新留言列表 ──
        st.markdown(
            "<h4 style='color:#1E293B;font-size:15px;font-weight:600;margin:16px 0 8px;'>"
            "最新留言列表（含 NLP 情緒標記）"
            "</h4>",
            unsafe_allow_html=True
        )
        show_comments = df_recent_comments.head(20)
        for _, crow in show_comments.iterrows():
            dominant_emotion = max(
                {"🟢 歡樂": crow["joy_score"],
                 "🟡 焦慮": crow["anxiety_score"],
                 "🔴 憤怒": crow["anger_score"]},
                key=lambda k: {"🟢 歡樂": crow["joy_score"],
                               "🟡 焦慮": crow["anxiety_score"],
                               "🔴 憤怒": crow["anger_score"]}[k]
            )
            ptitle = crow.get("post_title", "")
            ptitle = (ptitle[:25] + "…") if isinstance(ptitle, str) and len(ptitle) > 25 else ptitle
            comment_html = (
                f"<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;"
                f"padding:12px 16px;margin-bottom:8px;'>"
                f"<div style='font-size:11px;color:#94A3B8;margin-bottom:4px;'>"
                f"B{crow['floor']} · {ptitle}</div>"
                f"<div style='font-size:14px;color:#1E293B;line-height:1.5;margin-bottom:6px;'>"
                f"{crow['content'][:200]}</div>"
                f"<span style='font-size:11px;background:#E0F2FE;color:#0369A1;"
                f"padding:2px 8px;border-radius:12px;'>{dominant_emotion}</span>"
                f"</div>"
            )
            st.markdown(comment_html, unsafe_allow_html=True)
