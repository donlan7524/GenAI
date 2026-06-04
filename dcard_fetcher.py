import asyncio
import os
import json
from playwright.async_api import async_playwright

async def download_full_posts_with_comments():
    print("[Test-Core] 正在建立通道連線 Windows 實體真實 Chrome (Port: 9222)...")
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222", timeout=5000)
            default_context = browser.contexts[0]
            
            # 尋找已開啟的 Dcard 標籤頁
            page = None
            for p_instance in default_context.pages:
                if "dcard.tw" in p_instance.url:
                    page = p_instance
                    break
            
            if page:
                print(f"[Test-Core] 🟢 偵測到已開啟的 Dcard 頁面：{page.url}，將直接在該標籤頁執行深度採集...")
                await page.bring_to_front()
            else:
                print("[Test-Core] 🟡 未偵測到已開啟的 Dcard 頁面，將建立新頁面並導航...")
                page = await default_context.new_page()
                await page.goto("https://www.dcard.tw/f/nsysu", wait_until="load", timeout=8000)
                await page.wait_for_timeout(2000)
            
            # 💡 設定抓取最新 20 篇以防被 Dcard 阻擋頻率限制
            limit_posts = 20
            print(f"[Test-Core] 📡 正在透過 Chrome 同源環境深度採集前 {limit_posts} 篇貼文之完整內文、標籤及留言...")
            
            posts_data = await page.evaluate(r"""
            async (limit) => {
                const pathM = location.pathname.match(/\/f\/([^/]+)/);
                const forumName = pathM ? pathM[1] : 'nsysu';
                
                // 1. 取得貼文列表大綱
                const listUrl = '/service/api/v2/forums/' + forumName + '/posts?limit=' + limit;
                const listRes = await fetch(listUrl, { headers: { 'x-client-type': 'web' } });
                if (!listRes.ok) throw new Error('無法取得貼文列表: ' + listRes.status);
                const postsList = await listRes.json();
                
                const richPosts = [];
                
                // 2. 遍歷並深度抓取每篇貼文的詳情與留言
                for (const p of postsList) {
                    const pid = p.id;
                    const detailUrl = '/service/api/v2/posts/' + pid;
                    const commentUrl = '/service/api/v2/posts/' + pid + '/comments?limit=100';
                    
                    let detailData = {};
                    let commentsData = [];
                    
                    // 抓取詳情 (獲取完整內文與標籤)
                    try {
                        const detailRes = await fetch(detailUrl, { headers: { 'x-client-type': 'web' } });
                        if (detailRes.ok) {
                            detailData = await detailRes.json();
                        }
                    } catch (e) {}
                    
                    await new Promise(r => setTimeout(r, 800 + Math.random() * 1000)); // 隨機等待 0.8~1.8 秒，防止 API 限制
                    
                    // 抓取留言
                    try {
                        const commentRes = await fetch(commentUrl, { headers: { 'x-client-type': 'web' } });
                        if (commentRes.ok) {
                            commentsData = await commentRes.json();
                        }
                    } catch (e) {}
                    
                    richPosts.push({
                        ...p,
                        content: detailData.content || p.excerpt || "",
                        topics: detailData.topics || p.topics || [],
                        comments: commentsData || []
                    });
                    
                    await new Promise(r => setTimeout(r, 1500 + Math.random() * 1500)); // 貼文與貼文之間隨機等待 1.5~3 秒，模擬真人閱讀
                }
                
                return richPosts;
            }
            """, limit_posts)
            
            if not posts_data:
                print("[💣 錯誤] 未能取得任何貼文資料，請確認您已登入 Dcard 且無驗證碼阻擋。")
                return
                
            target_file = os.path.join(os.path.dirname(__file__), "test.json")
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(posts_data, f, indent=4, ensure_ascii=False)
                
            print(f"\n[Success] 🔥 成功取得 {len(posts_data)} 篇富文本貼文及留言！已導出至：{target_file}")
            print(f"[Test-Core] 最終檔案大小：{os.path.getsize(target_file) / 1024:.2f} KB")
            
        except Exception as e:
            print(f"\n[💣 測試下載失敗]: {e}")

if __name__ == "__main__":
    asyncio.run(download_full_posts_with_comments())
