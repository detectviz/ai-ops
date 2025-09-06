import os
import subprocess
import time
from playwright.sync_api import sync_playwright, expect

def verify_dev_login_flow():
    """
    Tests the dev login/logout flow and screenshots the resources page.
    """
    server_process = None
    # Add AUTH_MODE=dev to the environment
    env = os.environ.copy()
    env["AUTH_MODE"] = "dev"

    try:
        # --- 1. Start the server in dev mode ---
        server_dir = "services/control-plane"
        server_command = ["go", "run", "cmd/server/main.go"]

        print(f"🚀 Starting server in '{server_dir}' with AUTH_MODE=dev...")
        server_process = subprocess.Popen(
            server_command,
            cwd=server_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
            env=env
        )

        print("⏳ Waiting for server to become ready (15 seconds)...")
        time.sleep(15)

        # Check if the server started successfully
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print("❌ Server failed to start.")
            print("--- STDERR ---")
            print(stderr.decode('utf-8'))
            print("--- STDOUT ---")
            print(stdout.decode('utf-8'))
            return

        print("✅ Server is running in dev mode.")

        # --- 2. Run Playwright ---
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})

            # The middleware should redirect to /auth/login
            print("Navigating to http://localhost:8081/resources...")
            page.goto("http://localhost:8081/resources", timeout=15000)

            print("Waiting for redirection to login page...")
            expect(page).to_have_url(lambda url: "/auth/login" in url, timeout=10000)
            print("✅ Successfully redirected to login page.")

            print("Filling in credentials (admin/admin)...")
            page.locator("#username").fill("admin")
            page.locator("#password").fill("admin")

            print("Submitting login form...")
            page.get_by_role("button", name="登入").click()

            print("Waiting for navigation to dashboard...")
            expect(page).to_have_url("http://localhost:8081/", timeout=10000)
            print("✅ Successfully logged in and redirected to dashboard.")

            print("Navigating to /resources page again...")
            page.goto("http://localhost:8081/resources")
            expect(page.locator("#resources-grid")).to_be_visible(timeout=10000)
            print("✅ Successfully navigated to resources page.")

            time.sleep(2) # Wait for grid.js to potentially render

            screenshot_path = "resources_page_dev_auth.png"
            page.screenshot(path=screenshot_path)
            print(f"📸 Screenshot of resources page saved to '{screenshot_path}'")

            browser.close()

    finally:
        # --- 3. Stop the server ---
        if server_process:
            print("🛑 Stopping server...")
            os.killpg(os.getpgid(server_process.pid), 9)
            print("✅ Server stopped.")

if __name__ == "__main__":
    verify_dev_login_flow()
