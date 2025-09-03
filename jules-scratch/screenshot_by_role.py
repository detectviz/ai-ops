import os
from playwright.sync_api import sync_playwright, expect

def take_role_based_screenshots():
    """
    Logs in as each role (admin, manager, member) and takes screenshots
    of the pages visible to that role, saving them with a role suffix.
    """
    file_path = f"file://{os.path.abspath('demo-page.html')}"
    output_dir = "jules-scratch/screenshot_by_role/verification" # Save to the verification sub-directory

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    roles_config = {
        "admin": {
            "user": "admin",
            "pass": "admin",
            "pages": ["dashboard", "resources", "groups", "teams", "rules", "personnel", "profile", "settings", "channels"]
        },
        "manager": {
            "user": "manager",
            "pass": "manager",
            "pages": ["dashboard", "resources", "groups", "teams", "rules", "personnel", "profile"]
        },
        "member": {
            "user": "member",
            "pass": "member",
            "pages": ["dashboard", "resources", "groups", "rules", "profile"]
        }
    }

    with sync_playwright() as p:
        for role, config in roles_config.items():
            print(f"--- Capturing screenshots for role: {role} ---")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})

            # Login
            page.goto(file_path)
            login_form = page.locator("#login-form")
            login_form.get_by_label("帳號").fill(config["user"])
            login_form.get_by_label("密碼").fill(config["pass"])
            login_form.get_by_role("button", name="登入").click()
            expect(page.locator("#app")).to_be_visible()
            print(f"  - Logged in as {role}.")

            # Take screenshots for the specified pages
            for page_id in config["pages"]:
                print(f"  - Navigating to page: {page_id}")
                # Use a robust selector for sidebar links
                link_locator = page.locator(f'nav > a.sidebar-link[data-page="{page_id}"]')

                if link_locator.is_visible():
                    link_locator.click()
                    # Wait a bit for content to render
                    page.wait_for_timeout(500)
                    screenshot_path = os.path.join(output_dir, f"{page_id}-{role}.png")
                    page.screenshot(path=screenshot_path)
                    print(f"    - Saved screenshot: {os.path.basename(screenshot_path)}")
                else:
                    print(f"    - WARNING: Link for page '{page_id}' not visible for role '{role}'. Skipping.")

            browser.close()
            print(f"--- Finished screenshots for role: {role} ---\n")

    print("All role-based screenshots have been captured.")

if __name__ == "__main__":
    take_role_based_screenshots()
