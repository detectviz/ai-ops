import re
from playwright.sync_api import sync_playwright, Page, expect

def verify_alert_rules_page(page: Page):
    """
    This test verifies the full CRUD functionality of the Alert Rules page.
    It adds, edits, and deletes an alert rule.
    """
    # 1. Arrange: Go to the login page and log in.
    page.goto("http://localhost:8081/auth/login")
    page.get_by_placeholder("使用者名稱 (dev: admin)").fill("admin")
    page.get_by_placeholder("密碼 (dev: admin)").fill("admin")
    page.get_by_role("button", name="登入").click()
    expect(page.locator("nav a[href='/']")).to_be_visible(timeout=15000)

    # 2. Act: Navigate to the Alert Rules page.
    # Explicitly go to the URL to bypass the apparent routing bug.
    page.goto("http://localhost:8081/alerts")

    # Assert that we are on the correct page by checking the heading.
    expect(page.get_by_role("heading", name="告警規則")).to_be_visible(timeout=10000)

    # 3. Act & Assert: Add a new alert rule.
    page.get_by_role("button", name="新增告警規則").click()
    expect(page.get_by_role("heading", name="新增告警規則")).to_be_visible()

    # Fill out the form in the accordion
    page.get_by_label("規則名稱").fill("Test Rule: High Latency")
    page.get_by_label("描述").fill("Test rule for high latency on routers.")
    page.get_by_label("監控目標 (資源群組)").select_option(label="所有路由器")
    page.get_by_role("button", name="儲存規則").click()

    # Assert that the new rule is in the list and the page refreshed
    expect(page.get_by_role("cell", name="Test Rule: High Latency")).to_be_visible()

    # 4. Act & Assert: Edit the newly created rule.
    new_rule_row = page.get_by_role("row", name=re.compile("Test Rule: High Latency"))
    new_rule_row.get_by_role("button", name="編輯").click()

    expect(page.get_by_role("heading", name="編輯告警規則")).to_be_visible()
    page.get_by_label("規則名稱").fill("Test Rule: CRITICAL Latency")
    page.get_by_role("button", name="儲存規則").click()

    # Assert that the row is updated
    expect(page.get_by_role("cell", name="Test Rule: High Latency")).not_to_be_visible()
    expect(page.get_by_role("cell", name="Test Rule: CRITICAL Latency")).to_be_visible()

    # 5. Act & Assert: Delete the rule.
    edited_rule_row = page.get_by_role("row", name=re.compile("Test Rule: CRITICAL Latency"))
    edited_rule_row.get_by_role("button", name="刪除").click()

    expect(page.get_by_role("heading", name=re.compile("您確定要刪除"))).to_be_visible()
    page.get_by_role("button", name="是的，我確定").click()

    # Assert that the row is now gone and the page has refreshed
    expect(page.get_by_role("heading", name="告警規則")).to_be_visible()
    expect(page.get_by_role("row", name=re.compile("Test Rule: CRITICAL Latency"))).not_to_be_visible()

    # 6. Screenshot: Capture the final state.
    page.screenshot(path="jules-scratch/verification/alerts_page_final.png")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        verify_alert_rules_page(page)
        browser.close()

if __name__ == "__main__":
    main()
