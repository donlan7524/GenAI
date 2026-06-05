import sys
import io
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


import json
import re
import os
import random
import numpy as np

# 中山校園特定詞彙庫 (用於語意加權篩選)
CAMPUS_SLANGS = [
    "獼猴", "猴子", "柴山", "西子灣", "翠亨", "武嶺", "米羅", 
    "黑店", "逸仙館", "海琴", "長堤", "宿網", "停水", "選課"
]

# ==========================================
# 1. 對話樹結構設計 (Conversation Tree Nodes)
# ==========================================

class CommentNode:
    """
    對話樹節點：代表貼文(Root)或留言(Child)
    """
    def __init__(self, node_id, floor, author, content, parent_id=None, like_count=0):
        self.node_id = str(node_id)
        self.floor = floor          # 貼文為 0，留言為 1, 2, 3...
        self.author = author        # 顯示名稱 (例如 "國立中山大學")
        self.content = content.strip()
        self.parent_id = str(parent_id) if parent_id else None
        self.like_count = like_count
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "floor": self.floor,
            "author": self.author,
            "content": self.content,
            "parent_id": self.parent_id,
            "like_count": self.like_count,
            "children": [child.to_dict() for child in self.children]
        }

# ==========================================
# 2. 輕量級 MLP 垃圾留言分類器 (Numpy-based MLP)
# ==========================================

class MLPClassifier:
    """
    使用 Numpy 從頭建構的單隱藏層多層感知器 (MLP)
    用於過濾無效、過短或灌水的論壇留言
    """
    def __init__(self, input_dim=6, hidden_dim=8, output_dim=1, lr=0.1):
        self.lr = lr
        # 初始化權重與偏置
        np.random.seed(42)
        self.W1 = np.random.randn(input_dim, hidden_dim) * 0.1
        self.b1 = np.zeros((1, hidden_dim))
        self.W2 = np.random.randn(hidden_dim, output_dim) * 0.1
        self.b2 = np.zeros((1, output_dim))
        
    def _sigmoid(self, x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))
        
    def _relu(self, x):
        return np.maximum(0, x)
        
    def _relu_deriv(self, x):
        return (x > 0).astype(float)
        
    def forward(self, X):
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self._relu(self.z1)
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.a2 = self._sigmoid(self.z2)
        return self.a2
        
    def backward(self, X, y, output):
        N = X.shape[0]
        # BCE Loss 梯度
        loss_grad = (output - y) / N
        
        dW2 = np.dot(self.a1.T, loss_grad)
        db2 = np.sum(loss_grad, axis=0, keepdims=True)
        
        da1 = np.dot(loss_grad, self.W2.T)
        dz1 = da1 * self._relu_deriv(self.z1)
        
        dW1 = np.dot(X.T, dz1)
        db1 = np.sum(dz1, axis=0, keepdims=True)
        
        # 梯度更新 (SGD)
        self.W2 -= self.lr * dW2
        self.b2 -= self.lr * db2
        self.W1 -= self.lr * dW1
        self.b1 -= self.lr * db1
        
    def fit(self, X, y, epochs=400, verbose=False):
        for epoch in range(epochs):
            output = self.forward(X)
            self.backward(X, y, output)
            if verbose and epoch % 100 == 0:
                loss = -np.mean(y * np.log(output + 1e-15) + (1 - y) * np.log(1 - output + 1e-15))
                print(f"[MLP-Train] Epoch {epoch} | Loss: {loss:.4f}")

    def predict_proba(self, X):
        return self.forward(X)

    def predict(self, X, threshold=0.5):
        proba = self.predict_proba(X)
        return (proba >= threshold).astype(int)

# ==========================================
# 3. 特徵提取與 MLP 訓練資料準備 (升級為 6 維)
# ==========================================

def extract_features(text):
    """
    為留言提取特徵向量 (維度: 6)
    """
    text = text.strip()
    if not text:
        return np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        
    length = len(text)
    # 1. 長度特徵 (正規化，設定 30 字為充實留言門檻)
    f_len = min(np.log1p(length) / np.log1p(30), 1.0)
    
    # 2. 中文字元比例
    zh_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
    f_zh = zh_chars / length if length > 0 else 0.0
    
    # 3. 標點符號與特殊字元比例 (過多代表純符號灌水)
    special_chars = len(re.findall(r'[^\w\s\u4e00-\u9fa5]', text))
    f_spec = special_chars / length if length > 0 else 0.0
    
    # 4. 垃圾/無意義縮寫詞比率 (如 "卡", "推", "笑死", "+1")
    garbage_words = ["卡", "推", "哈哈", "+1", "笑死", "傻眼", "真的", "喔", "吧", "留名", "路過"]
    garbage_count = sum(1 for w in garbage_words if w in text)
    f_garbage = min(garbage_count / 3.0, 1.0)
    
    # 5. 英文字元比例 (防範外掛廣告或純 URL 貼圖)
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    f_en = en_chars / length if length > 0 else 0.0
    
    # 6. [新增] 中山大學校園黑話密度 (特徵加權)
    slang_count = sum(1 for s in CAMPUS_SLANGS if s in text)
    f_slang = min(slang_count / 2.0, 1.0)
    
    return np.array([f_len, f_zh, f_spec, f_garbage, f_en, f_slang])

def get_trained_mlp():
    """
    使用種子資料快速訓練 MLP 並回傳 (採用 6 維輸入)
    """
    # 高品質留言 (Label = 1)
    good_samples = [
        "我覺得這堂課的評分方式有點硬，期中考比例太高了，如果不常去上課的話可能會被當。",
        "推薦你去武嶺宿舍後面的停車場找，我昨天有看到一隻黑色的排球在那邊。",
        "機械系的熱力學今年是哪個教授上的？想問一下期末會不會調分，感覺快被當了。",
        "網大最近是不是又在當機了，檔案一直上傳失敗，有人有解決辦法嗎？",
        "西子灣看夕陽真的很漂亮，下午五點多去吹海風很舒服，很適合情侶約會。",
        "今天在工學院那邊遇到猴子搶人家的蛋餅，大家拿早餐真的要拿好，超恐怖。"
    ]
    # 低品質/垃圾留言 (Label = 0)
    bad_samples = [
        "卡", "推", "哈哈", "+1", "笑死", "傻眼", "真的", "喔", "吧", "留名", "路過",
        "笑死哈哈哈", "卡位", "？？？？", "......", "推推", "先卡一個", "對啊", "不好說"
    ]
    
    X_train = []
    y_train = []
    
    for s in good_samples:
        X_train.append(extract_features(s))
        y_train.append([1.0])
    for s in bad_samples:
        X_train.append(extract_features(s))
        y_train.append([0.0])
        
    X_train = np.array(X_train)
    y_train = np.array(y_train)
    
    mlp = MLPClassifier(input_dim=6, lr=0.1)
    mlp.fit(X_train, y_train, epochs=400, verbose=False)
    return mlp

# ==========================================
# 4. 對話樹重建與資料過濾管線
# ==========================================

def rebuild_and_filter_pipeline(input_file="test.json", output_tree_file="filtered_trees.json"):
    if not os.path.exists(input_file):
        print(f"❌ 錯誤：找不到輸入檔案 {input_file}")
        return None
        
    with open(input_file, "r", encoding="utf-8") as f:
        posts_extracted = json.load(f)
        
    print(f"🎬 啟動資料工程管線：共有 {len(posts_extracted)} 篇原始貼文。")
    
    # 訓練並取得 MLP 分類器
    mlp = get_trained_mlp()
    print("🧠 MLP (6維-校園黑話加權) 留言過濾器初始化並訓練完成。")
    
    trees = []
    filtered_comments_count = 0
    total_comments_count = 0
    
    for post in posts_extracted:
        post_id = str(post["id"])
        
        # 建立貼文 Root 節點
        root = CommentNode(
            node_id=post_id,
            floor=0,
            author=post.get("school", "國立中山大學"),
            content=f"標題: {post.get('title', '')}\n內容: {post.get('content', '')}",
            parent_id=None,
            like_count=post.get("likeCount", 0)
        )
        
        floor_to_node = {0: root}
        comments = post.get("comments", [])
        total_comments_count += len(comments)
        
        # 建立留言節點並過濾
        valid_nodes = []
        for c in comments:
            if c.get("hidden") or not c.get("content"):
                continue
            
            c_content = c.get("content", "").strip()
            # 進行 MLP 過濾
            features = extract_features(c_content).reshape(1, -1)
            score = mlp.predict_proba(features)[0, 0]
            
            if score < 0.4:  # 判定為垃圾/無意義留言
                filtered_comments_count += 1
                continue
                
            c_node = CommentNode(
                node_id=c.get("id"),
                floor=c.get("floor", 0),
                author=c.get("school", "國立中山大學") + (" " + c.get("department", "") if c.get("department") else ""),
                content=c_content,
                parent_id=post_id,
                like_count=c.get("likeCount", 0)
            )
            floor_to_node[c_node.floor] = c_node
            valid_nodes.append(c_node)
            
        # 建立對話樹關聯
        for node in valid_nodes:
            # 尋找內容中的 @B...
            matches = re.findall(r'@B(\d+)', node.content)
            matched_floor = None
            if matches:
                for match in matches:
                    f_num = int(match)
                    if f_num in floor_to_node and f_num < node.floor:
                        matched_floor = f_num
                        break
            
            if matched_floor is not None:
                parent_node = floor_to_node[matched_floor]
                node.parent_id = parent_node.node_id
                parent_node.add_child(node)
            else:
                # 預設直接回覆發文
                root.add_child(node)
                
        trees.append(root)
        
    print(f"🧹 過濾完成：總留言數 {total_comments_count} 筆，MLP 過濾掉 {filtered_comments_count} 筆無效留言。")
    print(f"🌳 成功重建 {len(trees)} 棵多叉對話樹。")
    
    # 導出對話樹為 JSON
    with open(output_tree_file, "w", encoding="utf-8") as out_f:
        json.dump([t.to_dict() for t in trees], out_f, indent=4, ensure_ascii=False)
    print(f"💾 對話樹已導出至：{output_tree_file}")
    
    return trees

# ==========================================
# 5. 微調資料集導出與數據增強 (JSONL Export & Augmentation)
# ==========================================

def export_to_fine_tuning_jsonl(trees, poster_out="poster_dataset.jsonl", commenter_out="commenter_dataset.jsonl"):
    """
    將對話樹解構成發文者 (Poster) 與留言者 (Commenter) 兩個微調訓練集。
    在此處對 Poster 資料集實作話題與性格數據增強 (Data Augmentation)。
    """
    poster_records = []
    commenter_records = []
    
    # 增強性格模板對照表
    augmented_templates = {
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
        ]
    }
    
    for tree in trees:
        # 1. 產生 Poster 發文數據
        content_lines = tree.content.split("\n")
        title = content_lines[0].replace("標題: ", "")
        body = "\n".join(content_lines[1:]).replace("內容: ", "")
        
        # 🟢 A. 真實數據導入
        poster_records.append({
            "instruction": "請以中山大學學生的身份發布一篇校園討論貼文。",
            "input": f"主題焦點：{title[:10]}",
            "output": f"標題：{title}\n\n{body}"
        })
        
        # 🟢 B. [新增] 數據增強 (Data Augmentation) - 每個真實話題隨機生成 2 筆不同性格的發文語料
        # 提取話題的核心關鍵詞（如「停水」、「選課」、「獼猴」）
        core_issue = title
        for key in ["停水", "選課", "獼猴", "猴子", "網大", "排球", "宿舍"]:
            if key in title or key in body:
                core_issue = key
                break
                
        # 隨機抽取兩個性格進行數據增強
        selected_personalities = random.sample(list(augmented_templates.keys()), 2)
        for persona in selected_personalities:
            title_tpl, body_tpl = random.choice(augmented_templates[persona])
            aug_title = title_tpl.format(core_issue)
            aug_body = body_tpl.format(body[:40].replace('\n', ' '))
            
            poster_records.append({
                "instruction": "請以中山大學學生的身份發布一篇校園討論貼文。",
                "input": f"主題焦點：{core_issue} ({persona})",
                "output": f"標題：{aug_title}\n\n{aug_body}"
            })
        
        # 2. 產生 Commenter 留言回覆數據 (DFS)
        def dfs_traverse(node, path_context):
            for child in node.children:
                context_str = "\n".join(path_context)
                
                commenter_records.append({
                    "instruction": "您是中山大學的 AI 學生網友。請根據下方的 Dcard 貼文與留言上下文，給出合適且帶有中山大學校園文化色彩的回覆留言。",
                    "input": f"=== 對話上下文 ===\n{context_str}",
                    "output": child.content
                })
                
                new_path = path_context + [f"B{child.floor} ({child.author}): {child.content}"]
                dfs_traverse(child, new_path)
                
        # 啟動 DFS
        root_context = [f"原PO (標題: {title}): {body}"]
        dfs_traverse(tree, root_context)
        
    # 寫入 JSONL
    with open(poster_out, "w", encoding="utf-8") as f:
        for r in poster_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    with open(commenter_out, "w", encoding="utf-8") as f:
        for r in commenter_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    print(f"📤 發文微調數據已寫入：{poster_out} (含數據增強，共 {len(poster_records)} 筆)")
    print(f"📤 留言微調數據已寫入：{commenter_out} (共 {len(commenter_records)} 筆)")

if __name__ == "__main__":
    # 設置隨機數種子以保證可重複性
    random.seed(42)
    trees = rebuild_and_filter_pipeline()
    if trees:
        export_to_fine_tuning_jsonl(trees)
