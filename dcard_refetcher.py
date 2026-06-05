import asyncio
import os
import re
import subprocess
import sys
import time
from playwright.async_api import async_playwright

def detect_platform():
    """環境偵測：確保跨平台大一統相容性"""
    try:
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    return 'wsl'
    except Exception:
        pass
    platform_str = sys.platform.lower()
    if platform_str.startswith('win'):
        return 'windows'
    elif platform_str.startswith('darwin'):
        return 'darwin'
    else:
        return 'linux'

def start_browser_env():
    """💡【核心 Fault 修正點一】：讓 Refetcher 具備自主喚醒 Chrome 滿血全開的能力"""
    current_env = detect_platform()
    chrome_args = '--remote-debugging-port=9222 --window-size=1440,900 --window-position=3000,0 --no-first-run'
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    if current_env == 'wsl':
        print("[Refetch-Core] 🪐 穿透 WSL 障壁，物理解放 Windows 外側螢幕 Chrome (GPU 全開)...")
        user_data = r'--user-data-dir="C:\chrome_dev_profile"'
        powershell_cmd = ["powershell.exe", "-Command", f'& "{chrome_path}" {chrome_args} {user_data}']
        subprocess.Popen(powershell_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif current_env == 'windows':
        print("[Refetch-Core] 🪐 偵測到原生 Windows，直接孵化 Chrome 進程 (GPU 全開)...")
        windows_cmd = [chrome_path, "--remote-debugging-port=9222", r"--user-data-dir=C:\chrome_dev_profile", "--window-size=1440,900", "--window-position=3000,0", "--no-first-run"]
        subprocess.Popen(windows_cmd, creationflags=subprocess.CREATE_NEW_CONSOLE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif current_env == 'darwin':
        mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome_Dev_Profile")
        subprocess.Popen(f'"{mac_chrome}" {chrome_args} --user-data-dir="{user_data_dir}" &', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif current_env == 'linux':
        linux_chrome = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else "/usr/bin/chromium-browser"
        user_data_dir = os.path.expanduser("~/.config/chrome_dev_profile")
        subprocess.Popen(f'"{linux_chrome}" {chrome_args} --user-data-dir="{user_data_dir}" &', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    time.sleep(2.5)
    print("[Refetch-Core] 🟢 獨立通訊 Chrome 9222 連線埠已就位。")

def kill_browser_env():
    """精準 CIM / Unix 抹除監聽程序，絕對不誤殺日常分頁"""
    current_env = detect_platform()
    try:
        if current_env in ['wsl', 'windows']:
            cim_cmd = (
                'powershell.exe -Command "'
                'Get-CimInstance Win32_Process -Filter \\"Name = \'chrome.exe\' AND CommandLine LIKE \'%--remote-debugging-port=9222%\'\\" '
                '| Invoke-CimMethod -MethodName Terminate'
                '"'
            )
            subprocess.run(cim_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[Refetch-Core] 🪐 9222 自動化 Chrome 已被 CIM 精準超渡！")
        elif current_env in ['darwin', 'linux']:
            unix_cmd = "kill -9 $(pgrep -f 'remote-debugging-port=9222')"
            subprocess.run(unix_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[Refetch-Core] 🪐 9222 自動化 Chrome 已被 Unix pgrep 精準超渡！")
    except Exception:
        pass

async def main():
    input_file = "scraped_data.txt"
    output_file = "data.csv"
    
    if not os.path.exists(input_file):
        print(f"[Refetch-Error] ❌ 錯誤：找不到中繼骨架檔案 {input_file}，請先執行前置管線！")
        return

    print(f"[Refetch-Core] 🪐 正在回溯表頭 (Rewind)，讀取基本貼文指標...")
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 提取 193 筆正牌文章 ID 序列
    post_ids = [line.split(",")[0] for line in lines[1:] if line.strip()]
    print(f"[Refetch-Core] 📡 成功加載 {len(post_ids)} 筆貼文指標，準備啟動二階段內頁 Class 探針流...")

    # 💡【核心 Fault 修正點二】：在建立 Playwright 通道前，先主動把 Chrome 安全拉起，打通物理 Port！
    start_browser_env()

    print("[Refetch-Core] 正在建立通道連線 9222 真實 Chrome 通道...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222", timeout=10000)
            default_context = browser.contexts[0]
            page = default_context.pages[0] if default_context.pages else await default_context.new_page()
            await page.bring_to_front()

            updated_posts_lines = [lines[0]]  # 保留純淨表頭
            
            for idx, pid in enumerate(post_ids):
                print(f"[🪐 探針深探 ({idx+1}/{len(post_ids)})] -> 正在物理突入內頁 ID: {pid} ...")
                try:
                    await page.goto(f"https://www.dcard.tw/f/nsysu/p/{pid}", wait_until="domcontentloaded", timeout=12000)
                    await page.wait_for_timeout(2000)  
                    
                    inner_html = await page.content()
                    
                    # 💡 直擊您指定的 class="d_xa_1c3s812 d_xj_15wmmcu d_7fkj9s" 肚子裡的 <span>
                    content_pattern = r'class="[^"]*d_xa_1c3s812 d_xj_15wmmcu d_7fkj9s[^"]*"[^>]*><span[^>]*>([\s\S]*?)</span>'
                    content_match = re.search(content_pattern, inner_html)
                    
                    if content_match:
                        from html_dealer import clean_html_tags
                        full_content = clean_html_tags(content_match.group(1))
                    else:
                        fallback_pattern = r'class="[^"]*d_tx_1g9pr05[^"]*"[^>]*><span[^>]*>([\s\S]*?)</span>'
                        fb_match = re.search(fallback_pattern, inner_html)
                        if fb_match:
                            from html_dealer import clean_html_tags
                            full_content = clean_html_tags(fb_match.group(1))
                        else:
                            full_content = "（此貼文為純圖片、轉貼連結或無內文摘要）"
                    
                    old_fields = lines[idx+1].strip().split(",")
                    if len(old_fields) >= 7:
                        old_fields[2] = full_content.replace(",", "，")  # 防禦 CSV
                        new_line = ",".join(old_fields) + "\n"
                        updated_posts_lines.append(new_line)
                        print(f"  🟢 [Class 定錨成功] -> 完整內文捕獲完成 ({len(full_content)} 字)！")
                    else:
                        updated_posts_lines.append(lines[idx+1])
                        
                except Exception as inner_err:
                    print(f"  ❌ 內頁 {pid} 突入失敗 (啟用首頁摘要自動保底): {inner_err}")
                    updated_posts_lines.append(lines[idx+1])

            # ─── PHASE 5: 生成含有 100% 完整長內文的 data.csv ───
            with open(output_file, "w", encoding="utf-8") as out_f:
                out_f.writelines(updated_posts_lines)
            print(f"\n[Success] 🔥 全量完整長內文 data.csv 順序對齊落地成功：{os.path.abspath(output_file)}")
            
            # ─── PHASE 6: 功德圓滿，呼叫 DBdealer 直灌 "nsysu_輿情.db" ───
            print("[Pipeline-Core] 🪐 正在呼叫 html_dealer.py 後置模組 (若有需要) 或直接直灌資料庫...")
            python_exec = "python3" if detect_platform() in ['darwin', 'linux'] else "python"
            os.system(f"{python_exec} DBdealer.py")
            
            await browser.close()
        except Exception as e:
            print(f"[💣 核心深探管線中斷]: {e}")
            
    kill_browser_env()

if __name__ == "__main__":
    asyncio.run(main())
