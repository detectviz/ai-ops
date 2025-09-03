import os
import time
from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))
    page.set_viewport_size({"width": 1440, "height": 900})

    # 取得 HTML 檔案的絕對路徑
    file_path = os.path.abspath('demo-page.html')
    page.goto(f'file://{file_path}')

    # --- 登入 ---
    page.locator("#login-form").get_by_label("帳號").fill("admin")
    page.locator("#login-form").get_by_label("密碼").fill("admin")
    page.get_by_role("button", name="登入").click()
    expect(page.locator("#app")).to_be_visible()
    print("登入成功。")

    # --- 截圖各個主要頁面 ---
    # 這個列表確保了遍歷的順序並包含所有頁面
    pages_to_visit = [
        "dashboard", "resources", "groups", "teams", "rules", "personnel",
        "channels", "maintenance", "automation", "capacity", "logs",
        "profile", "settings"
    ]

    for page_id in pages_to_visit:
        print(f"正在導航至頁面: {page_id}")

        # Directly call the JavaScript function to show the page and update the UI
        page.evaluate(f"""
            // 1. Show the target page
            showPage('{page_id}');

            // 2. Update the sidebar link's active state
            document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
            const link = document.querySelector(`.sidebar-link[data-page="{page_id}"]`);
            if (link) {{
                link.classList.add('active');

                // 3. Open parent accordion if necessary
                const parentSubmenu = link.closest('.submenu');
                if (parentSubmenu) {{
                    const toggle = parentSubmenu.previousElementSibling;
                    if (toggle && toggle.classList.contains('submenu-toggle')) {{
                        toggle.classList.add('open');
                    }}
                }}
            }}

            // 4. Update breadcrumb
            const breadcrumb = document.getElementById('breadcrumb');
            if (breadcrumb && link) {{
                breadcrumb.textContent = link.textContent.trim();
            }}
        """)

        # Wait for the page to be visible
        expect(page.locator(f'#page-{page_id}')).to_be_visible()
        page.wait_for_timeout(200) # Small delay for render

        page.screenshot(path=f"jules-scratch/screenshot_pages/{page_id}.png")
        print(f"  - 已儲存截圖: {page_id}.png")

        # Special handling for the 'automation' page tabs
        if page_id == 'automation':
            execution_logs_tab = page.locator("#execution-logs-tab")
            if execution_logs_tab.is_visible():
                execution_logs_tab.click()
                page.wait_for_timeout(500)
                page.screenshot(path=f"jules-scratch/screenshot_pages/automation_execution_logs.png")
                print(f"  - 已儲存截圖: automation_execution_logs.png")

        # Special handling for the 'settings' page tabs
        if page_id == 'settings':
            notification_tab = page.locator("button[data-tab='notification']")
            if notification_tab.is_visible():
                notification_tab.click()
                page.wait_for_timeout(500)
                page.screenshot(path=f"jules-scratch/screenshot_pages/settings_notification_tab.png")
                print(f"  - 已儲存截圖: settings_notification_tab.png")

                # Scroll down to show SMS Gateway settings
                main_content_area = page.locator("main > div.overflow-y-auto")
                main_content_area.evaluate("node => node.scrollTo(0, node.scrollHeight)")
                page.wait_for_timeout(500)
                page.screenshot(path=f"jules-scratch/screenshot_pages/settings_notification_tab_scrolled.png")
                print(f"  - 已儲存截圖: settings_notification_tab_scrolled.png")

    print("已完成所有主要頁面的截圖。")
    browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)

print("頁面截圖腳本執行成功。")
