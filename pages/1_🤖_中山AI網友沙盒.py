import streamlit as st
import pandas as pd
import random
import sys
import io
from datetime import datetime

# Windows 終端編碼處理
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 載入本機模組
import db_manager
import nlp_engine
import simulation_engine
from simulation_engine import VirtualBoard, PosterAgent, CommenterAgent, Persona, LLMDriver

# ==========================================
# 1. 頁面基本配置與樣式設計
# ==========================================
st.set_page_config(
    page_title="🤖 中山 AI 網友社群模擬沙盒",
    page_icon="🤖",
    layout="wide"
)

# 套用精美 CSS 樣式
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+TC:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', 'Noto Sans TC', sans-serif;
    }
    
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FF4B4B, #FF8F00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .sub-title {
        color: #707070;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .persona-card {
        background: rgba(255, 75, 75, 0.05);
        border-left: 5px solid #FF4B4B;
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    
    .post-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        background: #ffffff;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
        margin-bottom: 1rem;
    }
    
    .badge-positive {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    .badge-negative {
        background-color: #ffebee;
        color: #c62828;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_value=True)

# 初始化沙盒引擎
if "board" not in st.session_state:
    st.session_state.board = VirtualBoard()
    
# 初始化 LLM 驅動設定 (放在 Session state 供多個頁籤共用)
if "llm_api_key" not in st.session_state:
    st.session_state.llm_api_key = ""
if "llm_model" not in st.session_state:
    st.session_state.llm_model = "gpt-4o-mini"
if "llm_url" not in st.session_state:
    st.session_state.llm_url = "https://api.openai.com/v1"

# ==========================================
# 2. 側邊欄設定 (API 控制面板)
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ 智能體 LLM 連線設定")
    st.info("💡 預設使用本地範本規則進行模擬。若需呼叫真實 LLM 產生更彈性對話，請在下方輸入 API Key。")
    
    api_key_input = st.text_input("OpenAI / Llama API Key", value=st.session_state.llm_api_key, type="password")
    model_input = st.text_input("模型名稱", value=st.session_state.llm_model)
    url_input = st.text_input("API Base URL", value=st.session_state.llm_url)
    
    if st.button("💾 儲存並套用 LLM 設定"):
        st.session_state.llm_api_key = api_key_input
        st.session_state.llm_model = model_input
        st.session_state.llm_url = url_input
        st.session_state.board.llm_driver = LLMDriver(
            api_key=api_key_input,
            base_url=url_input,
            model_name=model_input
        )
        st.success("🎉 LLM 驅動器設定成功！")

# 實體化當前使用的 LLM Driver
active_driver = st.session_state.board.llm_driver

# ==========================================
# 3. 主頁面標題與分頁 (Tabs)
# ==========================================
st.markdown('<div class="main-title">🤖 中山 AI 網友社群模擬沙盒</div>', unsafe_allow_value=True)
st.markdown('<div class="sub-title">基於 Dcard 中山大學版真實語料蒸餾，模擬發文者與留言者間的論壇互動與社群動力學。</div>', unsafe_allow_value=True)

tab1, tab2 = st.tabs(["📚 歷史回放與 AI 留言測試 (Replay & Test)", "🎮 中山 AI 社群自主模擬沙盒 (Simulation Sandbox)"])

# ==========================================
# 4. 頁籤一：歷史回放與 AI 留言測試
# ==========================================
with tab1:
    st.markdown("### 📚 歷史貼文回放與 AI 網友即時互動")
    st.markdown("在這裡，您可以選擇中山大學 Dcard 版上**真實抓取到的貼文**，讓 AI 網友進行情緒模擬留言，或與 AI 網友在真實背景下展開對答。")
    
    # 檢查是否有真實貼文資料
    if not db_manager.has_data():
        st.warning("⚠️ 目前資料庫中無任何真實貼文資料，請先執行爬蟲抓取資料，或利用 `HTMLdealer.py` 載入模擬種子資料。")
    else:
        # 讀取真實貼文列表 (載入前 50 筆)
        conn = db_manager.get_connection()
        df_real_posts = pd.read_sql_query("SELECT post_id, title, category, like_count, comment_count FROM posts ORDER BY created_at DESC LIMIT 50", conn)
        conn.close()
        
        post_options = [f"【{row['category']}】{row['title']} (👍 {row['like_count']} | 💬 {row['comment_count']}) - ID: {row['post_id']}" for _, row in df_real_posts.iterrows()]
        
        selected_post_str = st.selectbox("🎯 選擇一篇真實貼文進行回放與測試：", post_options)
        
        if selected_post_str:
            # 提取 post_id
            selected_post_id = selected_post_str.split(" - ID: ")[-1]
            
            # 載入詳細資訊
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT title, content, category, author_name, created_at, valence_score, arousal_score, like_count FROM posts WHERE post_id = ?", (selected_post_id,))
            p_data = cursor.fetchone()
            
            # 載入真實留言
            cursor.execute("SELECT floor, author_name, content, valence_score, arousal_score FROM comments WHERE post_id = ? ORDER BY floor ASC", (selected_post_id,))
            real_comments = [{"floor": r[0], "author": r[1], "content": r[2], "valence": r[3], "arousal": r[4]} for r in cursor.fetchall()]
            conn.close()
            
            if p_data:
                title, content, category, author, created_at, v_score, a_score, likes = p_data
                
                # 介面分左右兩欄
                col_left, col_right = st.columns([1, 1])
                
                with col_left:
                    st.markdown("#### 📄 Dcard 原文內容")
                    st.markdown(f"""
                    <div class="post-container">
                        <h3>【{category}】{title}</h3>
                        <p style="color:#777; font-size:0.9rem;">發文者: {author or '國立中山大學同學'} | 發表時間: {created_at} | 👍 {likes} 個讚</p>
                        <hr style="border-top:1px solid #eee;">
                        <p style="font-size:1.05rem; white-space: pre-wrap;">{content}</p>
                    </div>
                    """, unsafe_allow_value=True)
                    
                    # 顯示原文情緒指標
                    v_p = 50.0 + (v_score / 2.0)
                    a_p = 50.0 + (a_score / 2.0)
                    st.markdown(f"**📊 原文情感維度**：效價 `{v_score:+.1f}` ({'🟢 正向' if v_score>=0 else '🔴 負向'} {v_p:.1f}%) | 喚起 `{a_score:+.1f}` ({'🟠 激動' if a_score>=0 else '🔵 冷靜'} {a_p:.1f}%)")
                    
                    # 顯示真實留言
                    st.markdown("💬 **真實人類留言列表**")
                    if not real_comments:
                        st.info("此貼文目前沒有採集到真實留言。")
                    else:
                        for rc in real_comments:
                            st.markdown(f"**B{rc['floor']} ({rc['author']})**：{rc['content']}")
                            
                with col_right:
                    st.markdown("#### 🤖 AI 網友模擬互動區")
                    
                    # 選擇 AI 性格進行留言
                    st.markdown("##### 1. 指派 AI 網友對此文留言")
                    p_type = st.selectbox("選擇 AI 網友性格：", ["隨機挑選", "酸民嘴砲", "理智學霸", "搞笑迷因", "熱心溫和"])
                    
                    if st.button("💬 觸發 AI 留言"):
                        if p_type == "隨機挑選":
                            persona = Persona()
                        else:
                            persona = Persona(personality_type=p_type)
                            
                        # 顯示 Persona 卡片
                        st.markdown(f"""
                        <div class="persona-card">
                            <strong>智能體已指派：{persona.get_display_name()}</strong><br>
                            性格特質：{persona.personality_type} ({persona.style_desc})
                        </div>
                        """, unsafe_allow_value=True)
                        
                        # 呼叫 CommenterAgent 留言
                        commenter = CommenterAgent(persona=persona, llm_driver=active_driver)
                        
                        with st.spinner("AI 網友瀏覽貼文中..."):
                            # 格式化留言歷史以供 LLM 參考
                            history = [{"floor": c["floor"], "author": c["author"], "content": c["content"]} for c in real_comments]
                            ai_comment = commenter.generate_comment(title, content, history)
                            
                            # 進行情緒分析
                            val, aro = nlp_engine.analyze_sentiment("", ai_comment)
                            val_p = 50.0 + (val / 2.0)
                            aro_p = 50.0 + (aro / 2.0)
                            
                            st.success(f"🤖 **AI 網友 ({persona.personality_type}) 發表了留言**：")
                            st.info(ai_comment)
                            st.markdown(f"🎨 **留言分析**：效價 `{'🟢 正向' if val>=0 else '🔴 負向'} {val_p:.1f}%` | 喚起 `{'🟠 激動' if aro>=0 else '🔵 冷靜'} {aro_p:.1f}%`")
                            
                    st.markdown("---")
                    st.markdown("##### 2. 人機對話測試（向 AI 網友發問）")
                    st.write("您可以扮演「原PO」寫下一句回應，並指定一位 AI 網友來回覆您。")
                    
                    user_input = st.text_input("您的原PO回覆：", placeholder="例如：感謝大家的建議，那如果是機械系熱力學呢？")
                    target_p = st.selectbox("指定回覆您的 AI 性格：", ["酸民嘴砲", "理智學霸", "搞笑迷因", "熱心溫和"], key="user_target_p")
                    
                    if st.button("🚀 送出並等待 AI 回應") and user_input:
                        user_persona = Persona(name="原PO", personality_type="理智學霸")
                        ai_persona = Persona(personality_type=target_p)
                        
                        st.markdown(f"**原PO**: {user_input}")
                        
                        commenter = CommenterAgent(persona=ai_persona, llm_driver=active_driver)
                        history = [{"floor": 1, "author": "原PO", "content": user_input}]
                        
                        with st.spinner("AI 網友思考中..."):
                            ai_reply = commenter.generate_comment(title, content, history, reply_to_floor=1)
                            
                            st.markdown(f"💬 **AI 網友 {ai_persona.get_display_name()} ({ai_persona.personality_type})**:")
                            st.info(ai_reply)

# ==========================================
# 5. 頁籤二：中山 AI 社群自主模擬沙盒
# ==========================================
with tab2:
    st.markdown("### 🎮 中山 AI 看板自主模擬沙盒")
    st.markdown("在這裡，發文智能體 (Poster) 與留言智能體 (Commenter) 將在一個完全**虛擬的 Dcard 中山大學版**展開自主發文與回覆互動，您也可以親自發文或參與留言討論！")
    
    # 看板引擎操作按鈕
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 1])
    
    with col_ctrl1:
        if st.button("🎲 觸發一輪 AI 網友自主發文與留言互動", type="primary", use_container_width=True):
            with st.spinner("虛擬社群運作中..."):
                post_id = st.session_state.board.run_autonomous_simulation_step(num_commenters=random.randint(2, 4))
                st.success(f"🎉 模擬完成！新貼文 (ID: {post_id}) 已加入虛擬看板！")
                
    with col_ctrl2:
        if st.button("🧹 清空虛擬看板的所有資料", use_container_width=True):
            st.session_state.board.clear_virtual_board()
            st.success("🧹 虛擬看板已完全重設！")
            
    with col_ctrl3:
        st.write("") # 留空
        
    st.markdown("---")
    
    # 載入所有虛擬貼文
    v_posts = st.session_state.board.get_board_posts()
    
    if not v_posts:
        st.info("📋 目前虛擬看板空空如也。請點擊上方按鈕觸發 AI 網友自主發文，或在下方親自撰寫第一篇貼文！")
    else:
        col_list, col_detail = st.columns([2, 3])
        
        with col_list:
            st.markdown("#### 📰 虛擬 Dcard 看板貼文列表")
            
            # 使用 radio 來呈現可點選的虛擬貼文
            v_post_options = {
                p["post_id"]: f"【{p['category']}】{p['title']} (👍 {p['like_count']} | 💬 {p['comment_count']}) By {p['author_name'].split(' ')[-1]} - ({p['personality']})"
                for p in v_posts
            }
            
            # 選擇目前要觀看的虛擬貼文
            selected_v_post_id = st.radio(
                "選擇貼文以查看留言與互動樹：",
                options=list(v_post_options.keys()),
                format_func=lambda x: v_post_options[x]
            )
            
        with col_detail:
            if selected_v_post_id:
                # 載入該貼文詳情
                post_details = st.session_state.board.get_post_details(selected_v_post_id)
                
                if post_details:
                    # 顯示主貼文
                    st.markdown(f"""
                    <div class="post-container" style="border-color:#FF8F00;">
                        <span class="badge-positive" style="background:#fff3e0; color:#e65100;">虛擬沙盒模擬</span>
                        <h3>【{post_details['category']}】{post_details['title']}</h3>
                        <p style="color:#777; font-size:0.9rem;">作者: {post_details['author_name']} ({post_details['personality']}) | 發表於: {post_details['created_at']} | 👍 {post_details['like_count']}</p>
                        <hr style="border-top:1px solid #eee;">
                        <p style="font-size:1.05rem; white-space: pre-wrap;">{post_details['content']}</p>
                    </div>
                    """, unsafe_allow_value=True)
                    
                    # 顯示留言列表 (對話樹結構)
                    st.markdown("💬 **AI 網友留言對話串 (互動模擬牆)**")
                    
                    if not post_details["comments"]:
                        st.info("此貼文目前尚無任何 AI 留言。")
                    else:
                        for c in post_details["comments"]:
                            reply_label = f" ➡️ 回覆 B{c['reply_to_floor']}" if c['reply_to_floor'] else ""
                            with st.chat_message("user" if "學長" in c["author_name"] else "assistant"):
                                st.markdown(f"**B{c['floor']} - {c['author_name']} ({c['personality']})** {reply_label}")
                                st.write(c["content"])
                                st.caption(f"👍 {c['like_count']} | 時間: {c['created_at']}")
                                
                    st.markdown("---")
                    
                    # 自主模擬與人機交互區
                    st.markdown("##### ⚙️ 對此對話串進行互動")
                    col_act1, col_act2 = st.columns([1, 1])
                    
                    with col_act1:
                        if st.button("💬 觸發另一位 AI 網友留言", use_container_width=True):
                            commenter = CommenterAgent(llm_driver=active_driver)
                            # 隨機決定是否回覆特定樓層
                            reply_floor = None
                            if post_details["comments"]:
                                reply_floor = random.choice(post_details["comments"])["floor"]
                            st.session_state.board.post_comment(commenter, selected_v_post_id, reply_to_floor=reply_floor)
                            st.rerun()
                            
                    with col_act2:
                        if st.button("🔄 重新載入對話樹", use_container_width=True):
                            st.rerun()
                            
                    # 使用者親自留言區
                    st.write("")
                    user_comment_input = st.text_input("✍️ 以「真人同學」身份在此發布留言：", placeholder="輸入您的回覆留言，按下送出後會觸發 AI 網友對您進行回覆！")
                    
                    if st.button("🚀 送出留言", key="send_v_comment") and user_comment_input:
                        # 1. 寫入使用者的留言
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        next_floor = len(post_details["comments"]) + 1
                        comment_id = f"VC_USER_{selected_v_post_id}_{next_floor}"
                        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        cursor.execute("""
                        INSERT INTO virtual_comments (comment_id, post_id, floor, author_name, personality, content, created_at, like_count, reply_to_floor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (comment_id, selected_v_post_id, next_floor, "真人同學 (您)", "真人", user_comment_input, created_at, 0, None))
                        conn.commit()
                        conn.close()
                        
                        # 2. 自動觸發一個 AI 網友對使用者的留言進行回覆
                        ai_commenter = CommenterAgent(llm_driver=active_driver)
                        st.session_state.board.post_comment(ai_commenter, selected_v_post_id, reply_to_floor=next_floor)
                        
                        st.success("留言發布成功，AI 網友已對您進行回覆！")
                        st.rerun()

    # 4. 使用者撰寫新貼文區
    st.markdown("---")
    st.markdown("### ✍️ 我要在虛擬看板發表貼文")
    
    col_form1, col_form2 = st.columns([1, 2])
    with col_form1:
        new_post_cat = st.selectbox("選擇貼文分類：", ["生活", "課業", "校務"])
        new_post_author = st.text_input("您的暱稱：", value="理智學長")
    with col_form2:
        new_post_title = st.text_input("貼文標題：", placeholder="例如：西子灣防坡堤的貓貓今天超可愛！")
        new_post_content = st.text_area("貼文內文：", placeholder="今天下午去長堤吹風，發現有好幾隻親人的貓貓躺在消波塊曬太陽，有人常常去餵牠們嗎？")
        
    if st.button("🚀 發布貼文至虛擬看板") and new_post_title and new_post_content:
        post_id = f"V_{int(datetime.now().timestamp() * 1000)}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO virtual_posts (post_id, title, content, author_name, personality, category, created_at, like_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (post_id, new_post_title, new_post_content, f"國立中山大學 {new_post_author}", "真人", new_post_cat, created_at, 0))
        conn.commit()
        conn.close()
        
        # 發表後自動觸發 2 位 AI 網友來留言
        ai_commenter1 = CommenterAgent(llm_driver=active_driver)
        ai_commenter2 = CommenterAgent(llm_driver=active_driver)
        st.session_state.board.post_comment(ai_commenter1, post_id)
        st.session_state.board.post_comment(ai_commenter2, post_id)
        
        st.success(f"🎉 貼文發表成功！AI 網友已前來留言討論！")
        st.rerun()
