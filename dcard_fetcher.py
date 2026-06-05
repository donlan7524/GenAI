import asyncio
import os
import subprocess
import time
import sys
from playwright.async_api import async_playwright

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
        
async def download_scrolled_html():
    print("[Test-Core] 正在建立通道連線 Windows 實體真實 Chrome (Port: 9222)...")
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222", timeout=5000)
            default_context = browser.contexts[0]
            page = default_context.pages[0] if default_context.pages else await default_context.new_page()
            await page.bring_to_front()
            
            print("[Test-Core] 🟢 正在前往西灣版首頁...")
            try:
                # 💡 【資工系強健度優化】：
                # 1. 加上時間戳記（?t=...）進行快取阻斷 (Cache Busting)，強迫 Dcard 吐出全新乾淨網頁
                # 2. 將超時從 8000ms 放寬至 25000ms (25秒)，給予 React 渲染與網路波動充足的寬限期
                # 3. 改用 "domcontentloaded"（DOM 樹建好就放行），不等那些花俏的圖片和廣告，速度直接快 3 倍！
                await page.goto(
                    "https://www.dcard.tw/f/nsysu?t=" + str(int(time.time())), 
                    wait_until="domcontentloaded", 
                    timeout=25000
                )
                # 原地安全傻等 3 秒，讓 React 把文章卡片大包裹（article）整整齊齊渲染出來
                await page.wait_for_timeout(3000)
                
            except Exception as goto_err:
                print(f"[Pipeline-Warning] ⚠️ 首頁載入略有延遲，啟動二線保底方案再試一次: {goto_err}")
                # 如果極端情況下連 domcontentloaded 都逾時，降級用最暴力的 commit 模式（握手成功就放行）
                await page.goto("https://www.dcard.tw/f/nsysu", wait_until="commit", timeout=15000)
                await page.wait_for_timeout(4000)
            
            # 💡 【核心黑魔法】：連續滾動轟炸流！模擬真人類瘋狂向下刷動 5 次，強迫 React 吐出大量貼文
            scroll_times = 30
            for i in range(scroll_times):
                print(f"[Test-Core] 👤 真人類模擬：正在進行第 {i+1}/{scroll_times} 次物理向下滾動...")
                # 每次向下滾動 1200 像素
                await page.mouse.wheel(0, 1200)
                # 💡 極度重要：每次滾動後必須傻傻等待 2 秒，給予 Dcard 的 Ajax 充足時間去載入新貼文！
                await page.wait_for_timeout(2000)
                
            print("[Test-Core] 📥 滾動結束！正在執行 HTML 物理拔罐，抽取完整 OuterHTML...")
            html_source = await page.content()
            
            target_file = os.path.join(os.path.dirname(__file__), "test.html")
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(html_source)
                
            print(f"\n[Success] 🔥 連續滾動下載成功！實體網頁已導出至：{target_file}")
            print(f"[Test-Core] 最終檔案大小：{os.path.getsize(target_file) / 1024:.2f} KB (容量變大代表成功塞入更多貼文！)")
            
        except Exception as e:
            print(f"\n[💣 測試下載失敗]: {e}")

if __name__ == "__main__":
    start_browser_env()
    asyncio.run(download_scrolled_html())
    kill_browser_env()
