import os
import subprocess
import time
from playwright.sync_api import sync_playwright, expect

def verify_dev_login_flow():
    """
    測試開發模式的登入/登出流程，並截取資源頁面的螢幕截圖。
    """
    server_process = None
    # 將 AUTH_MODE=dev 加入環境變數
    env = os.environ.copy()
    env["AUTH_MODE"] = "dev"

    try:
        # --- 1. 在開發模式下啟動伺服器 ---
        server_dir = "services/control-plane"
        server_command = ["go", "run", "cmd/server/main.go"]

        print(f"🚀 在 '{server_dir}' 中以 AUTH_MODE=dev 啟動伺服器...")
        server_process = subprocess.Popen(
            server_command,
            cwd=server_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
            env=env
        )

        print("⏳ 等待伺服器就緒 (15 秒)...")
        time.sleep(15)

        # 檢查伺服器是否成功啟動
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print("❌ 伺服器啟動失敗。")
            print("--- STDERR ---")
            print(stderr.decode('utf-8'))
            print("--- STDOUT ---")
            print(stdout.decode('utf-8'))
            return

        print("✅ 伺服器正在開發模式下運行。")

        # --- 2. 執行 Playwright ---
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            
            # 中介軟體應將我們重定向到 /auth/login
            print("導航至 http://localhost:8081/resources...")
            page.goto("http://localhost:8081/resources", timeout=15000)
            
            print("等待重定向至登入頁面...")
            expect(page).to_have_url(lambda url: "/auth/login" in url, timeout=10000)
            print("✅ 成功重定向至登入頁面。")

            print("填寫憑證 (admin/admin)...")
            page.locator("#username").fill("admin")
            page.locator("#password").fill("admin")

            print("提交登入表單...")
            page.get_by_role("button", name="登入").click()

            print("等待導航至儀表板...")
            expect(page).to_have_url("http://localhost:8081/", timeout=10000)
            print("✅ 成功登入並重定向至儀表板。")

            print("再次導航至 /resources 頁面...")
            page.goto("http://localhost:8081/resources")
            expect(page.locator("#resources-grid")).to_be_visible(timeout=10000)
            print("✅ 成功導航至資源頁面。")
            
            time.sleep(2) # 等待 grid.js 渲染

            screenshot_path = "resources_page_dev_auth.png"
            page.screenshot(path=screenshot_path)
            print(f"📸 資源頁面截圖已儲存至 '{screenshot_path}'")
            
            browser.close()

    finally:
        # --- 3. 停止伺服器 ---
        if server_process:
            print("🛑 停止伺服器...")
            os.killpg(os.getpgid(server_process.pid), 9)
            print("✅ 伺服器已停止。")

if __name__ == "__main__":
    verify_dev_login_flow()
