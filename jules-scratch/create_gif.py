import os
import shutil
from playwright.sync_api import sync_playwright, expect

def run_gif_creation(playwright):
    # --- Setup ---
    frames_dir = "jules-scratch/gif_frames"
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 1440, "height": 900})
    file_path = os.path.abspath('demo-page.html')
    page.goto(f'file://{file_path}')

    frame_count = 0
    def take_screenshot(name):
        nonlocal frame_count
        page.screenshot(path=os.path.join(frames_dir, f"frame_{frame_count:03d}_{name}.png"))
        frame_count += 1
        page.wait_for_timeout(500) # Default delay

    # --- Start Capture ---
    print("Starting GIF frame capture...")

    # 1. Login
    take_screenshot("01_login_page")
    page.locator("#login-form").get_by_label("帳號").fill("admin")
    page.locator("#login-form").get_by_label("密碼").fill("admin")
    page.get_by_role("button", name="登入").click()
    expect(page.locator("#app")).to_be_visible()
    print("- Logged in")
    page.wait_for_timeout(1000)

    # 2. Dashboard
    take_screenshot("02_dashboard")
    print("- Captured Dashboard")
    page.wait_for_timeout(1000)

    # 3. Resource Batch Operations
    print("- Navigating to Resource Management...")
    page.locator("button.submenu-toggle", has_text="資源").click()
    page.wait_for_timeout(500)
    page.locator('a[data-page="resources"]').click()
    expect(page.locator("#page-resources")).to_be_visible()
    page.wait_for_timeout(1000)
    take_screenshot("03_resources_page")

    print("- Selecting resources for batch operation...")
    page.locator('.resource-checkbox[data-resource-id="1"]').check()
    page.wait_for_timeout(200)
    page.locator('.resource-checkbox[data-resource-id="2"]').check()
    page.wait_for_timeout(200)
    page.locator('.resource-checkbox[data-resource-id="5"]').check()
    expect(page.locator("#batch-operations-bar")).to_be_visible()
    page.wait_for_timeout(500)
    take_screenshot("04_resources_batch_selection")
    print("- Captured resource batch operations bar")
    page.wait_for_timeout(1000)

    # 4. Personnel Management Modal
    print("- Navigating to Personnel Management...")
    page.locator("button.submenu-toggle", has_text="組織").click()
    page.wait_for_timeout(500)
    page.locator('a[data-page="personnel"]').click()
    expect(page.locator("#page-personnel")).to_be_visible()
    page.wait_for_timeout(1000)
    take_screenshot("05_personnel_page")

    print("- Opening 'Add Personnel' modal...")
    page.locator('#add-user-btn').click()
    expect(page.locator("#form-modal")).to_be_visible()
    page.wait_for_timeout(500)
    take_screenshot("06_add_personnel_modal")
    print("- Captured 'Add Personnel' modal")
    page.locator("#form-modal .close-modal-btn").first.click()
    page.wait_for_timeout(500)

    # 5. Alarm Rule Folding Interface
    print("- Navigating to Alarm Rules...")
    page.locator("button.submenu-toggle", has_text="告警").click()
    page.wait_for_timeout(500)
    page.locator('a[data-page="rules"]').click()
    expect(page.locator("#page-rules")).to_be_visible()
    page.wait_for_timeout(1000)
    take_screenshot("07_rules_page")

    print("- Opening 'Add Rule' modal and showing accordion...")
    page.locator('#add-rule-btn').click()
    expect(page.locator("#form-modal")).to_be_visible()
    page.wait_for_timeout(800)
    take_screenshot("08_add_rule_modal")

    # Expand Automation section
    page.locator('.accordion-header').nth(0).click()
    page.locator('.accordion-header').nth(1).click()
    page.locator('#automation-script-select').select_option(label='重啟 Web 服務')
    page.wait_for_timeout(500)
    take_screenshot("09_add_rule_modal_automation_expanded")

    # Expand Notification section
    page.locator('.accordion-header').nth(1).click()
    page.locator('.accordion-header').nth(2).click()
    page.wait_for_timeout(500)
    take_screenshot("10_add_rule_modal_all_expanded")
    print("- Captured alarm rule accordion interface")
    page.locator("#form-modal .close-modal-btn").first.click()
    page.wait_for_timeout(500)

    # 6. AI Log Analysis
    print("- Navigating to Logs page...")
    page.locator('a[data-page="logs"]').click()
    expect(page.locator("#page-logs")).to_be_visible()
    page.wait_for_timeout(1000)
    take_screenshot("11_logs_page")

    print("- Selecting logs for AI analysis...")
    page.locator('.log-checkbox[data-index="0"]').check()
    page.wait_for_timeout(200)
    page.locator('.log-checkbox[data-index="1"]').check()
    expect(page.locator("#generate-report-btn")).to_be_enabled()
    page.wait_for_timeout(500)
    take_screenshot("12_logs_selected")

    print("- Generating AI report...")
    page.locator('#generate-report-btn').click()
    expect(page.locator("#gemini-modal")).to_be_visible()
    page.wait_for_timeout(2000) # Wait for "AI analysis"
    take_screenshot("13_logs_ai_report")
    print("- Captured AI report modal")
    page.locator("#close-gemini-modal").click()
    page.wait_for_timeout(500)

    # 7. Automation Page Tabs
    print("- Navigating to Automation page...")
    page.locator("button.submenu-toggle", has_text="分析與自動化").click()
    page.wait_for_timeout(500)
    page.locator('a[data-page="automation"]').click()
    expect(page.locator("#page-automation")).to_be_visible()
    page.wait_for_timeout(1000)
    take_screenshot("14_automation_scripts_tab")

    print("- Switching to Execution Logs tab...")
    page.locator('#execution-logs-tab').click()
    page.wait_for_timeout(500)
    take_screenshot("15_automation_logs_tab")
    print("- Captured Automation page tabs")

    # 8. Capacity Planning Analysis
    print("- Navigating to Capacity Planning page...")
    page.locator('a[data-page="capacity"]').click()
    expect(page.locator("#page-capacity")).to_be_visible()
    page.wait_for_timeout(1000)
    take_screenshot("16_capacity_planning_page")

    print("- Running analysis...")
    page.locator('#capacity-target-group').select_option(label='核心交換器')
    page.wait_for_timeout(200)
    page.locator('#capacity-metric').select_option(label='磁碟使用率')
    page.wait_for_timeout(200)
    page.locator('#analyze-capacity-btn').click()
    expect(page.locator("#capacity-results")).to_be_visible()
    page.wait_for_timeout(2500) # Wait for "analysis" and chart animation
    take_screenshot("17_capacity_planning_results")
    print("- Captured Capacity Planning analysis results")

    # 9. Personal Profile Tabs
    print("- Navigating to Profile page...")
    page.locator('a[data-page="profile"]').first.click()
    expect(page.locator("#page-profile")).to_be_visible()
    page.wait_for_timeout(1000)
    take_screenshot("18_profile_info_tab")

    print("- Switching to Security tab...")
    page.locator('.profile-tab[data-tab="security"]').click()
    page.wait_for_timeout(500)
    take_screenshot("19_profile_security_tab")

    print("- Switching to Notifications tab...")
    page.locator('.profile-tab[data-tab="notifications"]').click()
    page.wait_for_timeout(500)
    take_screenshot("20_profile_notifications_tab")
    print("- Captured Profile page tabs")

    # 10. Logout
    page.wait_for_timeout(1000)
    page.locator("#logout-btn").click()
    expect(page.locator("#login-page")).to_be_visible()
    take_screenshot("21_logout")
    print("- Logged out")

    print(f"\nCaptured {frame_count} frames in '{frames_dir}'")
    browser.close()

with sync_playwright() as playwright:
    run_gif_creation(playwright)

print("GIF frame capture script finished successfully.")
