import os
import asyncio
import sys
from playwright.async_api import async_playwright

# Windows 控制台編碼重設
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

async def compile_to_pdf():
    print("[PDF-Compiler] 正在啟動 Playwright 無頭瀏覽器 (接管本地 Chrome)...")
    
    # 預設本地 Chrome 路徑
    local_chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    
    async with async_playwright() as p:
        try:
            # 檢查本地 Chrome 檔案是否存在
            if os.path.exists(local_chrome_path):
                print(f"[PDF-Compiler] 找到本地 Chrome 於 {local_chrome_path}，正在啟動...")
                browser = await p.chromium.launch(
                    executable_path=local_chrome_path,
                    headless=True
                )
            else:
                print("[PDF-Compiler] 未找到預設的 Chrome 路徑，嘗試自動啟動...")
                browser = await p.chromium.launch(headless=True)
                
            page = await browser.new_page()
            
            # 取得 HTML 的絕對路徑並轉為 file:// URL
            html_path = os.path.abspath("report/academic_report.html")
            html_url = f"file:///{html_path.replace('\\', '/')}"
            pdf_path = os.path.abspath("report/academic_report.pdf")
            
            print(f"[PDF-Compiler] 正在載入 HTML 文件：{html_url}")
            await page.goto(html_url, wait_until="load")
            
            # 等待 2 秒鐘以確保 Google Fonts 與 SVG 圖表完全加載渲染
            print("[PDF-Compiler] 等待字型與圖表渲染...")
            await page.wait_for_timeout(2000)
            
            print(f"[PDF-Compiler] 正在匯出 PDF 至：{pdf_path}")
            # 使用 A4 格式匯出，並啟用背景列印以保留漸層和網格顏色
            await page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={
                    "top": "1.5cm",
                    "bottom": "1.5cm",
                    "left": "1.5cm",
                    "right": "1.5cm"
                }
            )
            await browser.close()
            print("[PDF-Compiler] 成功！雙欄學術報告 PDF 已生成！")
        except Exception as e:
            print(f"[PDF-Compiler] 失敗！編譯過程中發生錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(compile_to_pdf())
