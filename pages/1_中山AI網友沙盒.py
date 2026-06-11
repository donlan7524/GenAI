import streamlit as st
import pandas as pd
import random
import sys
import io
from datetime import datetime

# Windows 終端編碼處理
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


# 載入本機模組
import db_manager
import nlp_engine
import simulation_engine
from simulation_engine import VirtualBoard, PosterAgent, CommenterAgent, Persona, LLMDriver

# ==========================================
# 1. 頁面基本配置與樣式設計
# ==========================================
st.set_page_config(
    page_title="中山 AI 網友社群模擬沙盒",
    page_icon=None,
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
        margin-bottom: 1.5rem;
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
</style>
""", unsafe_allow_html=True)

# 初始化沙盒引擎
if "board" not in st.session_state:
    st.session_state.board = VirtualBoard()
    
# 初始化 LLM 驅動設定
if "llm_api_key" not in st.session_state:
    st.session_state.llm_api_key = ""
if "llm_model" not in st.session_state:
    st.session_state.llm_model = "gpt-4o-mini"
if "llm_url" not in st.session_state:
    st.session_state.llm_url = "https://api.openai.com/v1"

# ==========================================
# 2. 側邊欄設定 (API 控制面板 & 健康監控)
# ==========================================
with st.sidebar:
    st.markdown("### 本地 API 伺服器狀態")
    import requests
    
    local_url = "http://127.0.0.1:8000/v1"
    is_local_online = False
    local_models = []
    
    try:
        res = requests.get(f"{local_url}/models", timeout=1.5)
        if res.status_code == 200:
            is_local_online = True
            local_models = [m["id"] for m in res.json().get("data", [])]
    except Exception:
        pass
        
    if is_local_online:
        st.success("🟢 **已連線**")
        st.caption(f"**本機伺服器**: `{local_url}`")
        st.caption(f"**偵測到適配器**: `{', '.join(local_models)}`")
        
        # 檢查當前是否已使用本地 API
        current_url = st.session_state.llm_url.rstrip("/")
        if "127.0.0.1:8000" not in current_url and "localhost:8000" not in current_url:
            if st.button("一鍵切換至本地 API 伺服器", type="primary", use_container_width=True):
                st.session_state.llm_url = local_url
                st.session_state.llm_model = local_models[0] if local_models else "nsysu-dcard-commenter"
                st.session_state.board.llm_driver = LLMDriver(
                    api_key=st.session_state.llm_api_key,
                    base_url=local_url,
                    model_name=st.session_state.llm_model
                )
                st.success("已切換至本地雙 LoRA 伺服器！")
                st.rerun()
    else:
        st.error("🔴 **未啟動 (Port 8000)**")
        st.caption("已自動降級為本地規則/詞庫引擎 Fallback")
        st.caption("請於終端機執行 `python serve_model.py` 啟動伺服器。")
        
    st.markdown("---")
    st.markdown("### 智能體 LLM 連線設定")
    st.info("若使用本地伺服器，免金鑰即可套用設定。若使用 OpenAI 等雲端 API，請輸入金鑰。")
    
    api_key_input = st.text_input("OpenAI / Llama API Key", value=st.session_state.llm_api_key, type="password")
    model_input = st.text_input("模型名稱", value=st.session_state.llm_model)
    url_input = st.text_input("API Base URL", value=st.session_state.llm_url)
    
    if st.button("儲存並套用 LLM 設定"):
        st.session_state.llm_api_key = api_key_input
        st.session_state.llm_model = model_input
        st.session_state.llm_url = url_input
        st.session_state.board.llm_driver = LLMDriver(
            api_key=api_key_input,
            base_url=url_input,
            model_name=model_input
        )
        st.success("LLM 驅動器設定成功！")

# 實體化當前使用的 LLM Driver
active_driver = st.session_state.board.llm_driver

# ==========================================
# 3. 主頁面標題
# ==========================================
st.markdown('<div class="main-title">中山 AI 網友社群模擬沙盒</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">基於 Dcard 中山大學版真實語料蒸餾，模擬發文者與留言者間的論壇互動與社群動力學。</div>', unsafe_allow_html=True)

# ==========================================
# 4. [新增] 即時推播與通知管理模組 (Event Poller)
# ==========================================
unread_notifs = st.session_state.board.get_unread_notifications()
if unread_notifs:
    # 1. 逐一彈出 st.toast 推播
    for notif in unread_notifs:
        st.toast(notif["message"])
        
    # 2. 顯示頂部未讀通知控制欄
    with st.expander(f"訊息通知中心 (您有 {len(unread_notifs)} 則新回覆！)", expanded=True):
        for notif in unread_notifs:
            st.markdown(f"* {notif['message']} *(時間: {notif['created_at']})*")
        
        if st.button("標記所有通知為已讀"):
            st.session_state.board.mark_notifications_as_read()
            st.rerun()

# 分頁標籤
tab1, tab2 = st.tabs(["歷史回放與 AI 留言測試 (Replay & Test)", "中山 AI 社群自主模擬沙盒 (Simulation Sandbox)"])

# ==========================================
# 5. 頁籤一：歷史回放與 AI 留言測試
# ==========================================
with tab1:
    st.markdown("### 歷史貼文回放與 AI 網友即時互動")
    st.markdown("在這裡，您可以選擇中山大學 Dcard 版上真實抓取到的貼文，讓 AI 網友進行情緒模擬留言，或與 AI 網友在真實背景下展開對答。")
    
    if not db_manager.has_data():
        st.warning("⚠️ 目前資料庫中無任何真實貼文資料，請先執行爬蟲抓取資料，或利用 `HTMLdealer.py` 載入模擬種子資料。")
    else:
        conn = db_manager.get_connection()
        df_real_posts = pd.read_sql_query("SELECT post_id, title, category, like_count, comment_count FROM posts ORDER BY created_at DESC LIMIT 50", conn)
        conn.close()
        
        post_options = [f"【{row['category']}】{row['title']} ({row['like_count']} | {row['comment_count']}) - ID: {row['post_id']}" for _, row in df_real_posts.iterrows()]
        
        selected_post_str = st.selectbox("選擇一篇真實貼文進行回放與測試：", post_options)
        
        if selected_post_str:
            selected_post_id = selected_post_str.split(" - ID: ")[-1]
            
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT title, content, category, created_at, valence_score, arousal_score, like_count FROM posts WHERE post_id = ?", (selected_post_id,))
            p_data = cursor.fetchone()
            
            cursor.execute("SELECT floor, content, valence_score, arousal_score FROM comments WHERE post_id = ? ORDER BY floor ASC", (selected_post_id,))
            real_comments = [{"floor": r[0], "author": "中山大學同學", "content": r[1], "valence": r[2], "arousal": r[3]} for r in cursor.fetchall()]
            conn.close()
            
            if p_data:
                title, content, category, created_at, v_score, a_score, likes = p_data
                author = "國立中山大學同學"
                
                col_left, col_right = st.columns([1, 1])
                
                with col_left:
                    st.markdown("#### Dcard 原文內容")
                    st.markdown(f"""
                    <div class="post-container">
                        <h3>【{category}】{title}</h3>
                        <p style="color:#777; font-size:0.9rem;">發文者: {author or '國立中山大學同學'} | 發表時間: {created_at} | {likes} 個讚</p>
                        <hr style="border-top:1px solid #eee;">
                        <p style="font-size:1.05rem; white-space: pre-wrap;">{content}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    v_p = 50.0 + (v_score / 2.0)
                    a_p = 50.0 + (a_score / 2.0)
                    st.markdown(f"**原文情感維度**：效價 `{v_score:+.1f}` ({v_p:.1f}%) | 喚起 `{a_score:+.1f}` ({a_p:.1f}%)")
                    
                    st.markdown("**真實人類留言列表**")
                    if not real_comments:
                        st.info("此貼文目前沒有採集到真實留言。")
                    else:
                        for rc in real_comments:
                            st.markdown(f"**B{rc['floor']} ({rc['author']})**：{rc['content']}")
                            
                with col_right:
                    st.markdown("#### AI 網友模擬互動區")
                    
                    st.markdown("##### 1. 指派 AI 網友對此文留言")
                    st.markdown("**自訂 AI 網友性格參數：**")
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        rationality_val = st.slider("理智度 (Rationality)", 0, 100, 50, key="replay_rat") / 100.0
                    with col_s2:
                        trolling_val = st.slider("嘴砲度 (Trolling)", 0, 100, 50, key="replay_troll") / 100.0
                    with col_s3:
                        humor_val = st.slider("幽默/迷因度 (Humor)", 0, 100, 50, key="replay_humor") / 100.0
                    
                    if st.button("觸發 AI 留言"):
                        persona = Persona(rationality=rationality_val, trolling=trolling_val, humor=humor_val)
                        
                        st.markdown(f"""
                        <div class="persona-card">
                            <strong>智能體已指派：{persona.get_display_name()}</strong><br>
                            理智度: {persona.rationality*100:.0f}% | 嘴砲度: {persona.trolling*100:.0f}% | 幽默度: {persona.humor*100:.0f}%
                        </div>
                        """, unsafe_allow_html=True)
                        
                        commenter = CommenterAgent(persona=persona, llm_driver=active_driver)
                        
                        status_box = st.status("AI 網友行動中...", expanded=True)
                        def log_update(msg):
                            status_box.write(msg)
                            
                        log_update(f"智能體已指派：{persona.get_display_name()}，理智度 {persona.rationality*100:.0f}% | 嘴砲度 {persona.trolling*100:.0f}% | 幽默度 {persona.humor*100:.0f}%")
                        log_update("AI 網友正瀏覽 Dcard 原文及歷史留言...")
                        
                        history = [{"floor": c["floor"], "author": c["author"], "content": c["content"]} for c in real_comments]
                        
                        import time
                        start_time = time.time()
                        ai_comment = commenter.generate_comment(title, content, history, status_callback=log_update)
                        elapsed = time.time() - start_time
                        
                        log_update("正在使用情緒分析引擎評估生成留言...")
                        val, aro = nlp_engine.analyze_sentiment("", ai_comment)
                        val_p = 50.0 + (val / 2.0)
                        aro_p = 50.0 + (aro / 2.0)
                        
                        status_box.update(state="complete", label=f"AI 網友行動完成 (耗時 {elapsed:.1f} 秒)")
                        
                        st.success(f"**AI 網友 (理{persona.rationality*100:.0f}%|嘴{persona.trolling*100:.0f}%|迷{persona.humor*100:.0f}%) 發表了留言**：")
                        st.info(ai_comment)
                        st.markdown(f"**留言分析**：效價 `{val_p:.1f}%` | 喚起 `{aro_p:.1f}%`")
                            
                    st.markdown("---")
                    st.markdown("##### 2. 人機對話測試（向 AI 網友發問）")
                    st.write("您可以扮演「原PO」寫下一句回應，並自訂對手 AI 網友的性格參數：")
                    
                    user_input = st.text_input("您的原PO回覆：", placeholder="例如：感謝大家的建議，那如果是機械系熱力學呢？")
                    
                    col_ds1, col_ds2, col_ds3 = st.columns(3)
                    with col_ds1:
                        target_rat = st.slider("對手理智度 (Rationality)", 0, 100, 50, key="dialogue_rat") / 100.0
                    with col_ds2:
                        target_troll = st.slider("對手嘴砲度 (Trolling)", 0, 100, 50, key="dialogue_troll") / 100.0
                    with col_ds3:
                        target_humor = st.slider("對手幽默/迷因度 (Humor)", 0, 100, 50, key="dialogue_humor") / 100.0
                    
                    if st.button("送出並等待 AI 回應") and user_input:
                        user_persona = Persona(rationality=0.8, trolling=0.1, humor=0.3, name="原PO")
                        ai_persona = Persona(rationality=target_rat, trolling=target_troll, humor=target_humor)
                        
                        st.markdown(f"**原PO**: {user_input}")
                        
                        commenter = CommenterAgent(persona=ai_persona, llm_driver=active_driver)
                        history = [{"floor": 1, "author": "原PO", "content": user_input}]
                        
                        status_box = st.status("AI 網友思考中...", expanded=True)
                        def log_update(msg):
                            status_box.write(msg)
                        
                        log_update(f"對手智能體已指派：{ai_persona.get_display_name()}，理智度 {ai_persona.rationality*100:.0f}% | 嘴砲度 {ai_persona.trolling*100:.0f}% | 幽默度 {ai_persona.humor*100:.0f}%")
                        log_update("AI 網友正在分析對話脈絡並擬定回覆...")
                        
                        import time
                        start_time = time.time()
                        ai_reply = commenter.generate_comment(title, content, history, reply_to_floor=1, status_callback=log_update)
                        elapsed = time.time() - start_time
                        
                        status_box.update(state="complete", label=f"AI 網友思考完成 (耗時 {elapsed:.1f} 秒)")
                        
                        st.markdown(f"**AI 網友 {ai_persona.get_display_name()} (理{ai_persona.rationality*100:.0f}%|嘴{ai_persona.trolling*100:.0f}%|迷{ai_persona.humor*100:.0f}%)**:")
                        st.info(ai_reply)
 
 
# ==========================================
# 6. 頁籤二：中山 AI 社群自主模擬沙盒
# ==========================================
with tab2:
    st.markdown("### 中山 AI 看板自主模擬沙盒")
    st.markdown("發文智能體 (Poster) 與留言智能體 (Commenter) 將在**虛擬看板**展開對答。您也可以親自發文或參與留言，AI 網友將對您進行 @回覆 並觸發即時通知！")
    
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 1])
    
    with col_ctrl1:
        if st.button("觸發一輪 AI 網友自主發文與留言互動", type="primary", use_container_width=True):
            status_box = st.status("自主社群動力學模擬進行中...", expanded=True)
            def log_update(msg):
                status_box.write(msg)
                
            log_update("開始模擬中山校版社群動力學流程...")
            
            import time
            start_time = time.time()
            post_id = st.session_state.board.run_autonomous_simulation_step(num_commenters=random.randint(2, 4), status_callback=log_update)
            elapsed = time.time() - start_time
            
            status_box.update(state="complete", label=f"模擬完成！新貼文已成功發布並討論完畢 (耗時 {elapsed:.1f} 秒)")
            st.success(f"模擬完成！新貼文已加入虛擬看板！")
            st.rerun()
                
    with col_ctrl2:
        if st.button("清空虛擬看板的所有資料", use_container_width=True):
            st.session_state.board.clear_virtual_board()
            st.success("虛擬看板與通知已完全清空！")
            st.rerun()
            
    with col_ctrl3:
        st.write("")
        
    st.markdown("---")
    
    v_posts = st.session_state.board.get_board_posts()
    
    if not v_posts:
        st.info("目前虛擬看板空空如也。請點擊上方按鈕觸發 AI 網友自主發文，或在下方親自撰寫第一篇貼文！")
    else:
        col_list, col_detail = st.columns([2, 3])
        
        with col_list:
            st.markdown("#### 虛擬 Dcard 看板貼文列表")
            
            v_post_options = {
                p["post_id"]: f"【{p['category']}】{p['title']} ({p['like_count']} | {p['comment_count']}) By {p['author_name'].split(' ')[-1]} - ({p['personality']})"
                for p in v_posts
            }
            
            selected_v_post_id = st.radio(
                "選擇貼文以查看留言與互動樹：",
                options=list(v_post_options.keys()),
                format_func=lambda x: v_post_options[x]
            )
            
        with col_detail:
            if selected_v_post_id:
                post_details = st.session_state.board.get_post_details(selected_v_post_id)
                
                if post_details:
                    st.markdown(f"""
                    <div class="post-container" style="border-color:#FF8F00;">
                        <span class="badge-positive" style="background:#fff3e0; color:#e65100;">虛擬沙盒模擬</span>
                        <h3>【{post_details['category']}】{post_details['title']}</h3>
                        <p style="color:#777; font-size:0.9rem;">作者: {post_details['author_name']} ({post_details['personality']}) | 發表於: {post_details['created_at']} | 👍 {post_details['like_count']}</p>
                        <hr style="border-top:1px solid #eee;">
                        <p style="font-size:1.05rem; white-space: pre-wrap;">{post_details['content']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("**AI 網友留言對話串 (互動模擬牆)**")
                    
                    if not post_details["comments"]:
                        st.info("此貼文目前尚無任何 AI 留言。")
                    else:
                        for c in post_details["comments"]:
                            reply_label = f" 回覆 B{c['reply_to_floor']}" if c['reply_to_floor'] else ""
                            with st.chat_message("user" if "學長" in c["author_name"] or "您" in c["author_name"] else "assistant"):
                                st.markdown(f"**B{c['floor']} - {c['author_name']} ({c['personality']})** {reply_label}")
                                st.write(c["content"])
                                st.caption(f"👍 {c['like_count']} | 時間: {c['created_at']}")
                                
                    st.markdown("---")
                    
                    st.markdown("##### 設定對此對話串進行互動")
                    col_act1, col_act2 = st.columns([1, 1])
                    
                    with col_act1:
                        if st.button("觸發另一位 AI 網友留言", use_container_width=True):
                            random_persona = Persona(
                                rationality=random.random(),
                                trolling=random.random(),
                                humor=random.random()
                            )
                            commenter = CommenterAgent(persona=random_persona, llm_driver=active_driver)
                            reply_floor = None
                            if post_details["comments"]:
                                reply_floor = random.choice(post_details["comments"])["floor"]
                                
                            status_box = st.status("正在召喚另一位 AI 網友...", expanded=True)
                            def log_update(msg):
                                status_box.write(msg)
                                
                            log_update(f"召喚智能體：{random_persona.get_display_name()}，理智度 {random_persona.rationality*100:.0f}% | 嘴砲度 {random_persona.trolling*100:.0f}% | 幽默度 {random_persona.humor*100:.0f}%")
                            
                            import time
                            start_time = time.time()
                            st.session_state.board.post_comment(commenter, selected_v_post_id, reply_to_floor=reply_floor, status_callback=log_update)
                            elapsed = time.time() - start_time
                            
                            status_box.update(state="complete", label=f"AI 留言生成完成 (耗時 {elapsed:.1f} 秒)")
                            st.rerun()
                            
                    with col_act2:
                        if st.button("重新載入對話樹", use_container_width=True):
                            st.rerun()
                            
                    st.write("")
                    user_comment_input = st.text_input("以「真人同學」身份在此發布留言：", placeholder="輸入您的回覆留言，按下送出後會觸發 AI 網友對您進行回覆！")
                    
                    if st.button("送出留言", key="send_v_comment") and user_comment_input:
                        # 1. 寫入使用者的留言 (標記為 真人同學)
                        conn = db_manager.get_connection()
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
                        
                        # 2. 自動觸發一個 AI 網友回覆使用者所在樓層 (此動作會觸發寫入未讀通知)
                        random_persona = Persona(
                            rationality=random.random(),
                            trolling=random.random(),
                            humor=random.random()
                        )
                        ai_commenter = CommenterAgent(persona=random_persona, llm_driver=active_driver)
                        
                        status_box = st.status(f"真人送出留言，正在觸發 AI 網友回應您...", expanded=True)
                        def log_update(msg):
                            status_box.write(msg)
                            
                        log_update(f"已指派 AI 回應網友：中山{random_persona.department}，性格: 理{random_persona.rationality*100:.0f}%|嘴{random_persona.trolling*100:.0f}%|迷{random_persona.humor*100:.0f}%")
                        
                        import time
                        start_time = time.time()
                        st.session_state.board.post_comment(ai_commenter, selected_v_post_id, reply_to_floor=next_floor, status_callback=log_update)
                        elapsed = time.time() - start_time
                        
                        status_box.update(state="complete", label=f"AI 回應完成 (耗時 {elapsed:.1f} 秒)")
                        st.rerun()

    # 7. 使用者撰寫新貼文區
    st.markdown("---")
    st.markdown("### 我要在虛擬看板發表貼文")
    
    col_form1, col_form2 = st.columns([1, 2])
    with col_form1:
        new_post_cat = st.selectbox("選擇貼文分類：", ["生活", "課業", "校務"])
        new_post_author = st.text_input("您的暱稱：", value="理智學長")
    with col_form2:
        new_post_title = st.text_input("貼文標題：", placeholder="例如：西子灣防坡堤的貓貓今天超可愛！")
        new_post_content = st.text_area("貼文內文：", placeholder="今天下午去長堤吹風，發現有好幾隻親人的貓貓躺在消波塊曬太陽，有人常常去餵牠們嗎？")
        
    if st.button("發布貼文至虛擬看板") and new_post_title and new_post_content:
        post_id = f"V_{int(datetime.now().timestamp() * 1000)}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        # 標記作者為 真人同學
        cursor.execute("""
        INSERT INTO virtual_posts (post_id, title, content, author_name, personality, category, created_at, like_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (post_id, new_post_title, new_post_content, f"真人同學 ({new_post_author})", "真人", new_post_cat, created_at, 0))
        conn.commit()
        conn.close()
        
        status_box = st.status(f"貼文發表成功，正在觸發 2 位 AI 網友前來留言討論...", expanded=True)
        def log_update(msg):
            status_box.write(msg)
            
        import time
        start_time = time.time()
        
        # 發表後自動觸發 2 位 AI 網友來留言
        ai_commenter1 = CommenterAgent(persona=Persona(rationality=random.random(), trolling=random.random(), humor=random.random()), llm_driver=active_driver)
        ai_commenter2 = CommenterAgent(persona=Persona(rationality=random.random(), trolling=random.random(), humor=random.random()), llm_driver=active_driver)
        
        log_update("[AI網友 1/2] 正在閱讀貼文並生成留言...")
        st.session_state.board.post_comment(ai_commenter1, post_id, status_callback=log_update)
        
        log_update("[AI網友 2/2] 正在閱讀貼文並生成留言...")
        st.session_state.board.post_comment(ai_commenter2, post_id, status_callback=log_update)
        
        elapsed = time.time() - start_time
        status_box.update(state="complete", label=f"AI 網友對答生成完畢 (共耗時 {elapsed:.1f} 秒)")
        
        st.success(f"貼文發表成功！AI 網友已前來留言討論！")
        st.rerun()
