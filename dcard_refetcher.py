import asyncio
import os
import re
import subprocess
import sys
import time
import random
from playwright.async_api import async_playwright
from html_dealer import clean_html_tags  # 確保大剪刀就位

def detect_platform():
    """
    極度精準的四維時空環境偵測器
    回傳字串: 'wsl', 'windows', 'darwin' (macOS), 'linux'
    """
    # 1. 先驗屍是否為 WSL
    try:
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    return 'wsl'
    except Exception:
        pass

    # 2. 偵測原生作業系統類型
    platform_str = sys.platform.lower()
    if platform_str.startswith('win'):
        return 'windows'
    elif platform_str.startswith('darwin'):
        return 'darwin'  # macOS 核心
    else:
        return 'linux'   # 原生 Linux 看板

def start_browser_env():
    current_env = detect_platform()
    chrome_args = '--remote-debugging-port=9222 --window-size=1440,900 --window-position=3000,0 --no-first-run'
    
    # 🚀 因地制宜：根據不同宇宙配置專屬的 Chrome 物理路徑與孵化手勢
    if current_env == 'wsl':
        print("[Pipeline-Core] 🪐 偵測環境：【WSL 虛擬化】-> 穿透障壁物理解放 Windows 外側螢幕 Chrome (GPU 全開)...")
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        user_data = r'--user-data-dir="C:\chrome_dev_profile"'
        powershell_cmd = ["powershell.exe", "-Command", f'& "{chrome_path}" {chrome_args} {user_data}']
        subprocess.Popen(powershell_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elif current_env == 'windows':
        print("[Pipeline-Core] 🪐 偵測環境：【Native Windows】-> 直接孵化原生 Chrome 進程 (GPU 全開)...")
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        # 原生 Windows 參數陣列切分優化
        windows_cmd = [
            chrome_path, "--remote-debugging-port=9222", 
            r"--user-data-dir=C:\chrome_dev_profile", 
            "--window-size=1440,900", "--window-position=3000,0", "--no-first-run"
        ]
        subprocess.Popen(windows_cmd, creationflags=subprocess.CREATE_NEW_CONSOLE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elif current_env == 'darwin':
        print("[Pipeline-Core] 🪐 偵測環境：【macOS】-> 正在調用 Unix 核心拉起應用程式 Chrome...")
        # macOS 標準安裝路徑與獨立沙盒環境配置
        # 💡 因為本機沒有 Google Chrome，這裡動態使用 Playwright 下載的 Chromium
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            mac_chrome = p.chromium.executable_path
        user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome_Dev_Profile")
        mac_cmd = f'"{mac_chrome}" {chrome_args} --user-data-dir="{user_data_dir}" &'
        subprocess.Popen(mac_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    elif current_env == 'linux':
        print("[Pipeline-Core] 🪐 偵測環境：【Native Linux】-> 正在調用 X11/Wayland 核心拉起實體 Chrome...")
        # Linux 常見 chrome / chromium 軟連結路徑
        linux_chrome = "/usr/bin/google-chrome"
        if not os.path.exists(linux_chrome):
            linux_chrome = "/usr/bin/chromium-browser"  # 保底方案
        user_data_dir = os.path.expanduser("~/.config/chrome_dev_profile")
        linux_cmd = f'"{linux_chrome}" {chrome_args} --user-data-dir="{user_data_dir}" &'
        subprocess.Popen(linux_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 統一原地給予 2.5 秒物理寬限期，讓各平台的 Chrome 在記憶體中張開 9222 埠口
    time.sleep(2.5)
    print("[Pipeline-Core] 🟢 跨平台 Chrome 顯示卡加速 9222 連線埠已就位。")

def kill_browser_env():
    current_env = detect_platform()
    print("[Pipeline-Core] 🪐 任務完全終結，正在執行精準特徵程序抹除...")

    try:
        if current_env in ['wsl', 'windows']:
            # 💡 【您的神級一發入魂寫法】：利用 Windows CIM 命令行參數特徵精準狙擊，絕不傷及主螢幕日常分頁！
            cim_cmd = (
                'powershell.exe -Command "'
                'Get-CimInstance Win32_Process -Filter \\"Name = \'chrome.exe\' AND CommandLine LIKE \'%--remote-debugging-port=9222%\'\\" '
                '| Invoke-CimMethod -MethodName Terminate'
                '"'
            )
            subprocess.run(cim_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[Pipeline-Core] 🪐 9222 自動化 Chrome 已被 CIM 精準超渡！")
            
        elif current_env in ['darwin', 'linux']:
            # 💡 macOS 與 Linux 的 Unix 終極對位狙擊：利用 pgrep 反查命令列內含有 9222 參數的特定 PID 進行 kill
            # 絕對不會誤殺使用者平常開著寫 Code、看論文的正常瀏覽器！
            unix_cmd = "kill -9 $(pgrep -f 'remote-debugging-port=9222')"
            subprocess.run(unix_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[Pipeline-Core] 🪐 9222 自動化 Chrome 已被 Unix pgrep 精準超渡！")

    except Exception as e:
        print(f"[Pipeline-Core] 🟡 程序釋放完畢或已自行關閉: {e}")

async def main():
    input_file = "scraped_data.txt"
    output_file = "data.csv"
    
    if not os.path.exists(input_file):
        print(f"[Refetch-Error] ❌ 錯誤：找不到中繼骨架檔案 {input_file}！")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 提取所有正牌文章 ID 序列
    post_ids = [line.split(",")[0] for line in lines[1:] if line.strip()]
    total_posts = len(post_ids)
    print(f"[Refetch-Core] 📡 成功加載 {total_posts} 筆貼文指標，準備發動「5頁籤環形輪詢轉向管線」...")

    start_browser_env()

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222", timeout=10000)
            default_context = browser.contexts[0]
            
            # 💡 【核心手勢一：硬核開闢 5 個固定頁籤陣列 (Round-Robin Buffer)】
            CONCURRENCY = 5
            tabs = []
            print(f"[Pipeline-Core] 🚀 正在實體初始化 {CONCURRENCY} 個常駐分頁頁籤...")
            for i in range(CONCURRENCY):
                page = await default_context.new_page()
                tabs.append(page)
            
            results_dict = {}
            
            # ─── 💡 【第一波大連擊：1 到 5 名排隊就位，同時發射】 ───
            # 讓 5 個 Tab 分別非同步地去加載前 5 筆 URL，不互相等待
            initial_launches = []
            for i in range(min(CONCURRENCY, total_posts)):
                pid = post_ids[i]
                print(f"  [第一波發射] Tab {i} 正在背景突入 ID: {pid}")
                initial_launches.append(
                    tabs[i].goto(f"https://www.dcard.tw/f/nsysu/p/{pid}", wait_until="domcontentloaded", timeout=35000)
                )
            # 讓前 5 發 Request 同時在分散式網路上重疊跑加載
            await asyncio.gather(*initial_launches, return_exceptions=True)
            
            # ─── 💡 【核心手勢二：環形壽司調度指針大迴圈】 ───
            # 下一發要加載的全新貼文索引從第 5 筆開始 (也就是您說的 1 + 5 軌道)
            next_post_idx = CONCURRENCY 
            
            # 只要還有任何一頁沒解剖完，指針就在 5 個固定 Tab 裡循環輪詢
            posts_processed = 0
            while posts_processed < total_posts:
                for tab_id in range(CONCURRENCY):
                    # 計算目前這個 Tab 正在處理哪一個原始貼文索引 (idx)
                    # 依據線性推進，它就是 posts_processed 的目前進度
                    current_job_idx = posts_processed
                    if current_job_idx >= total_posts:
                        break
                        
                    pid = post_ids[current_job_idx]
                    page = tabs[tab_id]
                    temp_html_path = f"temp_tab_{tab_id}.html"
                    
                    print(f"[{time.strftime('%H:%M:%S')}] 🍣 [指針交接] -> 輪詢到 Tab {tab_id}，開始收割目前 ID: {pid} ...")
                    
                    try:
                        # 鋼鐵定錨探針，死等目前分頁的文字注入 DOM 樹
                        try:
                            await page.wait_for_selector('div.d_xa_1c3s812.d_xj_15wmmcu.d_7fkj9s span', state="visible", timeout=4000)
                        except Exception:
                            pass
                        
                        # 沙盒落地與解剖
                        page_source = await page.content()
                        with open(temp_html_path, "w", encoding="utf-8") as temp_f:
                            temp_f.write(page_source)
                            
                        with open(temp_html_path, "r", encoding="utf-8") as temp_f:
                            static_html = temp_f.read()
                            
                        fragment_pattern = r'class="[^"]*d_7fkj9s[^"]*"[^>]*><span[^>]*>([\s\S]*?)</span>'
                        all_fragments = re.findall(fragment_pattern, static_html)
                        cleaned_fragments = [clean_html_tags(frag).replace(",", "，").strip() for frag in all_fragments if frag.strip()]
                        
                        if cleaned_fragments:
                            full_content = cleaned_fragments[0].replace("\n", " ")  # 鋼鐵對齊
                            all_comments = cleaned_fragments[1:]
                        else:
                            full_content = "（此貼文為純圖片、轉貼連結或無內文摘要）"
                            all_comments = []
                            
                        all_comments = all_comments[:100]
                        while len(all_comments) < 100:
                            all_comments.append("")
                            
                        # 精確對齊骨架二維欄位
                        old_line = lines[current_job_idx + 1]
                        old_fields = old_line.strip().split(",")
                        if len(old_fields) >= 7:
                            old_fields[2] = full_content
                            pure_base_fields = old_fields[:7]
                            new_line_str = ",".join(pure_base_fields) + "," + ",".join(all_comments) + "\n"
                            results_dict[current_job_idx] = new_line_str
                            print(f"    🟢 [Tab-{tab_id} 收割完成] -> ID {pid} 完美聚合歸位！")
                        else:
                            results_dict[current_job_idx] = old_line
                            
                    except Exception as err:
                        print(f"    ❌ [Tab-{tab_id} 發生 Fault] -> ID {pid} 實施斷點保底: {err}")
                        fake_padding = "," * 100
                        results_dict[current_job_idx] = lines[current_job_idx + 1].strip() + fake_padding + "\n"
                    finally:
                        if os.path.exists(temp_html_path):
                            os.remove(temp_html_path)
                    
                    # ─── 💡 【核心手勢三：收割完畢，立刻命令該 Tab 轉向下一發全新 URL】 ───
                    posts_processed += 1
                    if next_post_idx < total_posts:
                        next_pid = post_ids[next_post_idx]
                        print(f"    🔄 [Tab-{tab_id} 留駐轉向] -> 立刻下令突入下一發新任務 ID: {next_pid} (索引: {next_post_idx})")
                        
                        # 💡 【極度硬核】：這裡「絕對不使用 await」！
                        # 我們直接發動 page.goto 任務，讓它丟給 Chromium 背景線程自己去跑網路跳轉與 I/O 等待，
                        # 主線程的指針一秒都不停留，直接解綁、往下一個 Tab 2 推進！這就是真非阻塞時空多工！
                        asyncio.create_task(page.goto(f"https://www.dcard.tw/f/nsysu/p/{next_pid}", wait_until="domcontentloaded", timeout=35000))
                        
                        next_post_idx += 1
                        # 給予 Cloudflare 一小道 1.5 秒的真人防偵測隨機變速雜訊
                        await asyncio.sleep(random.uniform(1.2, 2.2))
                    else:
                        # 如果後面已經沒有新貼文了，這個 Tab 功德圓滿，不用轉向，指針繼續收割剩下的 Tab
                        pass

            # ─── 二維標準表格重組防線 ───
            # 遵照蔡同學最高指示：儲存格肚子裡 100% 乾乾淨淨，絕對不夾帶任何 Row 或 Column 標籤！
            base_header = lines[0].strip()
            comment_headers = [f"comment{i:03d}" for i in range(1, 101)]
            final_csv_lines = [base_header + "," + ",".join(comment_headers) + "\n"]
            
            for idx in range(total_posts):
                if idx in results_dict:
                    final_csv_lines.append(results_dict[idx])

            with open(output_file, "w", encoding="utf-8") as out_f:
                out_f.writelines(final_csv_lines)
            print(f"\n[Success] 🔥 環形輪詢大滿貫！data.csv 順序完美對齊落地：{os.path.abspath(output_file)}")
                        
            # 關閉常駐分頁
            for page in tabs:
                await page.close()
            await browser.close()
        except Exception as e:
            print(f"[💣 核心深探輪詢管線中斷]: {e}")
    kill_browser_env()

if __name__ == "__main__":
    asyncio.run(main())
