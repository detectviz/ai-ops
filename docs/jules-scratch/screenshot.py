#!/usr/bin/env python3
"""
統一截圖腳本 - 整合所有截圖功能
包含角色權限截圖和 GIF 幀生成
"""

import os
import shutil
from playwright.sync_api import sync_playwright, expect
from typing import Dict


class ScreenshotManager:
    """統一的截圖管理器"""
    
    def __init__(self, headless: bool = True, viewport_size: Dict = None):
        self.headless = headless
        self.viewport_size = viewport_size or {"width": 1440, "height": 900}
        self.file_path = f"file://{os.path.abspath('demo-page.html')}"
        self.base_dir = "docs/jules-scratch"
        self.frame_count = 0
        
        # 角色配置
        self.roles_config = {
            "admin": {
                "user": "admin",
                "pass": "admin",
                "pages": ["dashboard", "logs", "resources", "groups", "personnel", "teams", "channels", "rules", "maintenance", "automation", "capacity", "profile", "settings"]
            },
            "manager": {
                "user": "manager", 
                "pass": "manager",
                "pages": ["dashboard", "logs", "resources", "groups", "personnel", "teams", "rules", "maintenance", "automation", "capacity", "profile"]
            },
            "member": {
                "user": "member",
                "pass": "member", 
                "pages": ["dashboard", "logs", "resources", "groups", "rules", "profile"]
            }
        }
        
    def setup_directories(self):
        """設置輸出目錄"""
        directories = [
            f"{self.base_dir}/screenshot_by_role",
            f"{self.base_dir}/gif_frames"
        ]
        
        for dir_path in directories:
            os.makedirs(dir_path, exist_ok=True)
            
        # 清理 gif_frames 目錄
        gif_dir = f"{self.base_dir}/gif_frames"
        if os.path.exists(gif_dir):
            shutil.rmtree(gif_dir)
        os.makedirs(gif_dir)
        
    def login(self, page, username: str, password: str):
        """統一的登入邏輯"""
        page.goto(self.file_path)
        page.locator("#login-form").get_by_label("帳號").fill(username)
        page.locator("#login-form").get_by_label("密碼").fill(password)
        page.get_by_role("button", name="登入").click()
        expect(page.locator("#app")).to_be_visible()
        print(f"  - 以 {username} 身份登入成功")
        
    def navigate_to_page(self, page, page_id: str, wait_for_selector=None):
        """導航到指定頁面並等待載入"""
        print(f"  - 導航至頁面: {page_id}")
        
        # 特殊處理：在訪問「分析與自動化」頁面前收合「組織」選單
        if page_id == "automation":
            print("    - 收合「組織」選單")
            page.evaluate("""
                // 找到「組織」選單的切換按鈕
                const orgToggle = Array.from(document.querySelectorAll('.submenu-toggle')).find(toggle => {
                    const span = toggle.querySelector('span');
                    return span && span.textContent.trim() === '組織';
                });
                
                // 如果找到且是展開狀態，則收合它
                if (orgToggle && orgToggle.classList.contains('open')) {
                    orgToggle.classList.remove('open');
                }
            """)
            page.wait_for_timeout(200)
        
        # 使用 JavaScript 直接切換頁面（更可靠）
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
        
        # 等待頁面可見
        expect(page.locator(f'#page-{page_id}')).to_be_visible()
        
        # 特殊處理：個人檔案頁面和系統設定頁面需要額外的等待時間以確保標籤內容渲染完成
        if page_id in ["profile", "settings"]:
            page.wait_for_timeout(500)
        
        # 如果指定了額外的等待元素，也要等待
        if wait_for_selector:
            expect(page.locator(wait_for_selector)).to_be_visible()
            
        page.wait_for_timeout(200)  # 小延遲確保渲染完成
        
    def take_gif_frame(self, page, name: str, delay: int = 500):
        """為 GIF 拍攝幀"""
        frames_dir = f"{self.base_dir}/gif_frames"
        page.screenshot(path=os.path.join(frames_dir, f"frame_{self.frame_count:03d}_{name}.png"))
        self.frame_count += 1
        page.wait_for_timeout(delay)
        
    def interact_with_tom_select(self, page, select_id: str, option_text: str):
        """與 Tom Select 元素互動的通用函數"""
        try:
            # 嘗試找到 Tom Select 控制項
            ts_control = page.locator(f'#{select_id}').locator('..').locator('.ts-control')
            
            if ts_control.is_visible():
                # 點擊打開下拉選單
                ts_control.click()
                page.wait_for_timeout(300)
                
                # 選擇選項
                option = page.locator('.ts-dropdown .option', has_text=option_text)
                if option.is_visible():
                    option.click()
                    page.wait_for_timeout(200)
                    return True
                else:
                    print(f"    - 找不到選項：{option_text}")
                    return False
            else:
                # 嘗試直接使用原生 select（如果 Tom Select 未初始化）
                native_select = page.locator(f'#{select_id}')
                if native_select.is_visible():
                    native_select.select_option(label=option_text)
                    page.wait_for_timeout(200)
                    return True
                else:
                    print(f"    - {select_id} 不可見")
                    return False
                    
        except Exception as e:
            print(f"    - 警告：無法與 {select_id} 互動：{e}")
            return False
        
    def capture_pages(self, browser):
        """截取所有主要頁面"""
        print("=== 開始頁面截圖 ===")
        page = browser.new_page()
        page.set_viewport_size(self.viewport_size)
        
        # 登入
        self.login(page, "admin", "admin")
        page.wait_for_timeout(500)
        
        # 頁面列表 - 按照選單順序排列
        pages_to_visit = [
            "dashboard", "logs", "resources", "groups", "personnel", "teams", 
            "channels", "rules", "maintenance", "automation", "capacity", 
            "profile", "settings"
        ]
        
        for page_id in pages_to_visit:
            print(f"正在截取頁面: {page_id}")
            self.navigate_to_page(page, page_id)
            
            page.screenshot(path=f"{self.base_dir}/screenshot_pages/{page_id}.png")
            print(f"  - 已儲存: {page_id}.png")
            
            # 特殊頁面的額外截圖
            if page_id == 'automation':
                execution_logs_tab = page.locator("#execution-logs-tab")
                if execution_logs_tab.is_visible():
                    execution_logs_tab.click()
                    page.wait_for_timeout(500)
                    page.screenshot(path=f"{self.base_dir}/screenshot_pages/automation_execution_logs.png")
                    print(f"  - 已儲存: automation_execution_logs.png")
                    
            elif page_id == 'settings':
                notification_tab = page.locator("button[data-tab='notification']")
                if notification_tab.is_visible():
                    notification_tab.click()
                    page.wait_for_timeout(500)
                    page.screenshot(path=f"{self.base_dir}/screenshot_pages/settings_notification_tab.png")
                    print(f"  - 已儲存: settings_notification_tab.png")
                    
                    # 滾動顯示 SMS Gateway 設置
                    main_content_area = page.locator("main > div.overflow-y-auto")
                    main_content_area.evaluate("node => node.scrollTo(0, node.scrollHeight)")
                    page.wait_for_timeout(500)
                    page.screenshot(path=f"{self.base_dir}/screenshot_pages/settings_notification_tab_scrolled.png")
                    print(f"  - 已儲存: settings_notification_tab_scrolled.png")
        
        page.close()
        print("頁面截圖完成\n")
        
    def capture_modals(self, browser):
        """截取所有模態框"""
        print("=== 開始模態框截圖 ===")
        page = browser.new_page()
        page.set_viewport_size(self.viewport_size)
        
        # 登入
        self.login(page, "admin", "admin")
        page.wait_for_timeout(500)
        
        # 定義具體的設置函數
        def setup_notifications():
            print("    - 點擊通知按鈕...")
            # 先檢查按鈕是否存在和可見
            btn = page.locator("#notification-btn")
            if btn.count() == 0:
                raise Exception("通知按鈕不存在")
            print(f"    - 通知按鈕狀態：{btn.get_attribute('class')}")
            btn.click()
            page.wait_for_timeout(800)  # 增加等待時間
            # 檢查下拉選單狀態
            dropdown = page.locator("#notification-dropdown")
            print(f"    - 下拉選單狀態：{dropdown.get_attribute('class')}")
            # 如果仍然隱藏，嘗試再次點擊
            if 'hidden' in (dropdown.get_attribute('class') or ''):
                print("    - 重試點擊通知按鈕...")
                btn.click()
                page.wait_for_timeout(500)
            
        def setup_add_resource():
            print("    - 導航到資源頁面...")
            self.navigate_to_page(page, "resources", "#resources-grid")
            print("    - 點擊新增資源按鈕...")
            page.get_by_role("button", name="新增資源").click()
            
        def setup_confirm_delete():
            print("    - 導航到資源頁面...")
            self.navigate_to_page(page, "resources", "#resources-grid")
            print("    - 點擊刪除按鈕...")
            expect(page.locator("#resources-grid .delete-resource-btn").first).to_be_visible()
            page.locator("#resources-grid .delete-resource-btn").first.click()
            
        def setup_edit_team():
            print("    - 導航到團隊頁面...")
            self.navigate_to_page(page, "teams", "#teams-grid")
            print("    - 點擊編輯團隊按鈕...")
            expect(page.locator("#teams-grid .edit-team-btn").first).to_be_visible()
            page.locator("#teams-grid .edit-team-btn").first.click()
            
        def setup_edit_personnel():
            print("    - 導航到人員頁面...")
            self.navigate_to_page(page, "personnel", "#personnel-grid")
            print("    - 點擊編輯人員按鈕...")
            expect(page.locator("#personnel-grid .edit-user-btn").first).to_be_visible()
            page.locator("#personnel-grid .edit-user-btn").first.click()
            
        def setup_edit_channel():
            print("    - 導航到通知管道頁面...")
            self.navigate_to_page(page, "channels", "#channels-grid")
            print("    - 點擊編輯管道按鈕...")
            expect(page.locator("#channels-grid .edit-channel-btn").first).to_be_visible()
            page.locator("#channels-grid .edit-channel-btn").first.click()
            
        def setup_add_rule():
            print("    - 導航到規則頁面...")
            self.navigate_to_page(page, "rules", "#rules-grid")
            print("    - 點擊新增告警規則按鈕...")
            page.get_by_role("button", name="新增告警規則").click()
            
        def setup_expand_rule():
            print("    - 展開告警規則手風琴...")
            page.wait_for_timeout(500)
            page.locator(".accordion-header").nth(1).click()
            page.wait_for_timeout(500)
            
        def setup_incident_details():
            print("    - 導航到日誌頁面...")
            self.navigate_to_page(page, "logs", "#logs-grid")
            print("    - 打開事件詳情...")
            page.locator("#logs-grid .view-incident-btn").first.click()
            
        def setup_gemini_report():
            print("    - 選擇日誌以啟用按鈕（若需要）...")
            # 若按鈕為 disabled，嘗試勾選前兩筆；若無 checkbox 則直接點擊
            btn = page.get_by_role("button", name="✨ 生成事件報告")
            if btn.get_attribute("disabled") is not None:
                if page.locator("#logs-grid .log-checkbox").count() >= 2:
                    page.locator("#logs-grid .log-checkbox").nth(0).check()
                    page.locator("#logs-grid .log-checkbox").nth(1).check()
                    page.wait_for_timeout(200)
            print("    - 點擊生成報告按鈕...")
            expect(btn).to_be_enabled()
            btn.click()
            
        def setup_feedback():
            print("    - 導航到個人檔案頁面...")
            self.navigate_to_page(page, "profile", "#profile-name-input")
            print("    - 修改名稱觸發反饋...")
            page.locator("#profile-name-input").fill("Test Name")
            page.get_by_role("button", name="更新資訊").click()
            
        def setup_scan_network_initial():
            print("    - 導航到資源頁面...")
            self.navigate_to_page(page, "resources", "#resources-grid")
            print("    - 點擊掃描網段按鈕...")
            page.get_by_role("button", name="掃描網段").click()
            
        def setup_scan_network_results():
            print("    - 執行掃描...")
            # 確保按鈕可見後再點擊
            expect(page.locator("#form-modal")).to_be_visible()
            btn = page.locator("#form-modal-save-btn")
            btn.scroll_into_view_if_needed()
            expect(btn).to_be_visible()
            btn.click()
            
        def setup_execution_log():
            print("    - 導航到自動化頁面...")
            self.navigate_to_page(page, "automation", "#scripts-content")
            print("    - 切換到執行日誌標籤...")
            page.locator("#execution-logs-tab").click()
            page.wait_for_timeout(200)  # 等待標籤切換
            print("    - 點擊查看輸出按鈕...")
            expect(page.locator("#execution-logs-grid .view-output-btn").first).to_be_visible()
            page.locator("#execution-logs-grid .view-output-btn").first.click()
            
        modal_configs = [
            {
                "name": "notifications",
                "description": "通知中心下拉選單",
                "setup": setup_notifications,
                "wait_for": "#notification-dropdown",
                "cleanup": lambda: page.locator("#notification-btn").click()
            },
            {
                "name": "add_resource",
                "description": "新增資源彈窗", 
                "setup": setup_add_resource,
                "wait_for": "#form-modal",
                "cleanup": lambda: page.locator("#form-modal .close-modal-btn").first.click()
            },
            {
                "name": "confirm_delete",
                "description": "刪除確認彈窗",
                "setup": setup_confirm_delete,
                "wait_for": "#confirm-modal",
                "cleanup": lambda: page.locator("#cancel-action-btn").click()
            },
            {
                "name": "edit_team",
                "description": "編輯團隊彈窗",
                "setup": setup_edit_team,
                "wait_for": "#form-modal",
                "cleanup": lambda: page.locator("#form-modal .close-modal-btn").first.click()
            },
            {
                "name": "edit_personnel",
                "description": "編輯人員彈窗",
                "setup": setup_edit_personnel,
                "wait_for": "#form-modal",
                "cleanup": lambda: page.locator("#form-modal .close-modal-btn").first.click()
            },
            {
                "name": "edit_channel",
                "description": "編輯通知管道彈窗",
                "setup": setup_edit_channel,
                "wait_for": "#form-modal",
                "cleanup": lambda: page.locator("#form-modal .close-modal-btn").first.click()
            },
            {
                "name": "add_rule_collapsed",
                "description": "新增告警規則彈窗（折疊）",
                "setup": setup_add_rule,
                "wait_for": "#form-modal",
                "cleanup": None  # 會在下一個模態框中處理
            },
            {
                "name": "add_rule_expanded", 
                "description": "新增告警規則彈窗（展開）",
                "setup": setup_expand_rule,
                "wait_for": None,  # 已經打開
                "cleanup": lambda: page.locator("#form-modal .close-modal-btn").first.click()
            },
            {
                "name": "incident_details",
                "description": "事件詳情彈窗",
                "setup": setup_incident_details,
                "wait_for": "#incident-modal",
                "cleanup": lambda: page.locator("#incident-modal .close-modal-btn").first.click()
            },
            {
                "name": "gemini_report",
                "description": "Gemini AI 分析報告彈窗",
                "setup": setup_gemini_report,
                "wait_for": "#gemini-modal",
                "additional_wait": lambda: expect(page.locator("#gemini-modal-content h3")).to_be_visible(timeout=5000),
                "cleanup": lambda: page.locator("#close-gemini-modal").click()
            },
            {
                "name": "feedback",
                "description": "操作成功反饋提示",
                "setup": setup_feedback,
                "wait_for": "#feedback-modal",
                "cleanup": lambda: page.locator("#app").click()
            },
            {
                "name": "scan_network_initial",
                "description": "網段掃描彈窗（初始）",
                "setup": setup_scan_network_initial,
                "wait_for": "#form-modal",
                "cleanup": None  # 會在下一個中處理
            },
            {
                "name": "scan_network_results",
                "description": "網段掃描彈窗（結果）",
                "setup": setup_scan_network_results,
                "wait_for": "#form-modal",
                "additional_wait": lambda: expect(page.locator("#form-modal-body")).to_contain_text("掃描結果", timeout=7000),
                "cleanup": lambda: page.wait_for_timeout(2000)  # 等待自動關閉
            },
            {
                "name": "execution_log_output",
                "description": "自動化執行日誌輸出彈窗",
                "setup": setup_execution_log,
                "wait_for": "#form-modal",
                "cleanup": lambda: page.locator("#form-modal .close-modal-btn").first.click()
            }
        ]
        
        for modal_config in modal_configs:
            try:
                print(f"正在截取彈窗: {modal_config['description']}")
                
                # 設置彈窗
                setup = modal_config['setup']
                setup()  # 執行設置函數
                    
                # 等待彈窗出現
                if modal_config['wait_for']:
                    try:
                        expect(page.locator(modal_config['wait_for'])).to_be_visible(timeout=10000)
                    except Exception as e:
                        print(f"  ⚠️ 警告：等待元素 '{modal_config['wait_for']}' 超時")
                        # 檢查元素狀態進行調試
                        element = page.locator(modal_config['wait_for'])
                        if element.count() > 0:
                            print(f"  - 元素存在但不可見，類別：{element.get_attribute('class')}")
                        else:
                            print(f"  - 元素不存在")
                        # 繼續執行，可能元素已經存在但有其他問題
                    
                # 額外等待條件
                if 'additional_wait' in modal_config and modal_config['additional_wait']:
                    try:
                        modal_config['additional_wait']()
                    except Exception as e:
                        print(f"  ⚠️ 警告：額外等待條件失敗：{e}")
                        
                page.wait_for_timeout(300)  # 增加等待時間
                
                # 截圖
                page.screenshot(path=f"{self.base_dir}/screenshot_modals/modal_{modal_config['name']}.png")
                print(f"  - 已儲存: modal_{modal_config['name']}.png")
                
                # 清理
                if modal_config['cleanup']:
                    try:
                        modal_config['cleanup']()
                        page.wait_for_timeout(500)
                    except Exception as e:
                        print(f"  ⚠️ 警告：清理失敗：{e}")
                        
            except Exception as e:
                print(f"  ❌ 錯誤：截取 {modal_config['description']} 失敗：{e}")
                print(f"  - 跳過此模態框，繼續下一個...")
                continue
                
        page.close()
        print("模態框截圖完成\n")
        
    def capture_by_roles(self, browser):
        """根據角色權限截圖"""
        print("=== 開始角色權限截圖 ===")
        output_dir = f"{self.base_dir}/screenshot_by_role/verification"
        
        for role, config in self.roles_config.items():
            print(f"正在截取角色: {role}")
            page = browser.new_page()
            page.set_viewport_size(self.viewport_size)
            
            # 登入
            self.login(page, config["user"], config["pass"])
            
            # 截取該角色可見的頁面
            for page_id in config["pages"]:
                print(f"  - 截取頁面: {page_id}")
                
                try:
                    self.navigate_to_page(page, page_id)
                    page.wait_for_timeout(500)
                    screenshot_path = os.path.join(output_dir, f"{page_id}-{role}.png")
                    page.screenshot(path=screenshot_path)
                    print(f"    - 已儲存: {os.path.basename(screenshot_path)}")
                except Exception as e:
                    print(f"    - 警告: 頁面 '{page_id}' 對角色 '{role}' 不可見或出錯: {e}")
                    
            page.close()
            print(f"角色 {role} 截圖完成")
            
        print("角色權限截圖完成\n")
        
    def capture_gif_frames(self, browser):
        """捕獲 GIF 動畫幀"""
        print("=== 開始 GIF 幀捕獲 ===")
        page = browser.new_page()
        page.set_viewport_size(self.viewport_size)
        
        # 1. 登入頁面
        page.goto(self.file_path)
        self.take_gif_frame(page, "01_login_page")
        
        page.locator("#login-form").get_by_label("帳號").fill("admin")
        page.locator("#login-form").get_by_label("密碼").fill("admin")
        page.get_by_role("button", name="登入").click()
        expect(page.locator("#app")).to_be_visible()
        print("- 已登入")
        page.wait_for_timeout(1000)
        
        # 2. 儀表板
        self.take_gif_frame(page, "02_dashboard", 1000)
        print("- 捕獲儀表板")
        
        # 3. 通知中心下拉選單
        print("- 打開通知中心下拉選單...")
        page.locator("#notification-btn").click()
        expect(page.locator("#notification-dropdown")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "03_notification_dropdown")
        page.locator("#notification-btn").click()
        page.wait_for_timeout(500)
        
        # 4. AI 日誌分析
        print("- 導航至日誌頁面...")
        self.navigate_to_page(page, "logs", "#logs-grid")
        self.take_gif_frame(page, "04_logs_page")
        
        # 5. 事件詳情彈窗
        print("- 打開事件詳情彈窗...")
        page.locator('#logs-grid .view-incident-btn').first.click()
        expect(page.locator("#incident-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "05_incident_details_modal")
        page.locator("#incident-modal .close-modal-btn").first.click()
        page.wait_for_timeout(500)
        
        print("- 選擇日誌進行 AI 分析...")
        # 在 Grid.js 容器內定位，避免嚴格模式衝突
        if page.locator('#logs-grid .log-checkbox').count() >= 2:
            page.locator('#logs-grid .log-checkbox').nth(0).check()
            page.wait_for_timeout(200)
            page.locator('#logs-grid .log-checkbox').nth(1).check()
            expect(page.locator("#generate-report-btn")).to_be_enabled()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "06_logs_selected")
        
        print("- 生成 AI 報告...")
        page.locator('#generate-report-btn').click()
        expect(page.locator("#gemini-modal")).to_be_visible()
        page.wait_for_timeout(2000)
        self.take_gif_frame(page, "07_logs_ai_report")
        page.locator("#close-gemini-modal").click()
        page.wait_for_timeout(500)
        
        # 6. 資源批量操作
        print("- 導航至資源管理...")
        self.navigate_to_page(page, "resources", "#resources-grid")
        self.take_gif_frame(page, "08_resources_page")
        
        # 7. 網段掃描彈窗
        print("- 打開網段掃描彈窗...")
        page.locator('#scan-network-btn').click()
        expect(page.locator("#form-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "09_scan_network_initial_modal")
        
        print("- 執行掃描...")
        page.locator("#form-modal-save-btn").click()
        page.wait_for_timeout(3000)
        self.take_gif_frame(page, "10_scan_network_results_modal")
        # 等待自動關閉
        page.wait_for_timeout(2000)
        
        print("- 選擇資源進行批量操作...")
        page.locator('#resources-grid .resource-checkbox[data-resource-id="1"]').first.check()
        page.wait_for_timeout(200)
        page.locator('#resources-grid .resource-checkbox[data-resource-id="2"]').first.check()
        page.wait_for_timeout(200)
        page.locator('#resources-grid .resource-checkbox[data-resource-id="5"]').first.check()
        expect(page.locator("#batch-operations-bar")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "11_resources_batch_selection", 1000)
        print("- 捕獲資源批量操作欄")
        
        # 8. 新增資源彈窗
        print("- 打開新增資源彈窗...")
        page.locator('#add-resource-btn').click()
        expect(page.locator("#form-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "12_add_resource_modal")
        page.locator("#form-modal .close-modal-btn").first.click()
        page.wait_for_timeout(500)
        
        # 9. 刪除資源確認彈窗
        print("- 打開刪除資源確認彈窗...")
        page.locator('#resources-grid .delete-resource-btn').first.click()
        expect(page.locator("#confirm-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "13_confirm_delete_resource_modal")
        page.locator("#cancel-action-btn").click()
        page.wait_for_timeout(500)
        
        # 10. 資源群組操作
        print("- 導航至資源群組...")
        self.navigate_to_page(page, "groups", "#groups-grid")
        self.take_gif_frame(page, "14_groups_page")
        
        print("- 選擇資源群組進行批量操作...")
        page.locator('#groups-grid .group-checkbox[data-group-id="1"]').first.check()
        page.wait_for_timeout(200)
        page.locator('#groups-grid .group-checkbox[data-group-id="2"]').first.check()
        page.wait_for_timeout(200)
        expect(page.locator("#groups-batch-operations-bar")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "15_groups_batch_selection", 1000)
        print("- 捕獲資源群組批量操作欄")
        
        # 11. 人員管理
        print("- 導航至人員管理...")
        self.navigate_to_page(page, "personnel", "#personnel-grid")
        self.take_gif_frame(page, "16_personnel_page")
        
        # 12. 新增人員彈窗
        print("- 打開新增人員彈窗...")
        page.locator('#add-user-btn').click()
        expect(page.locator("#form-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "17_add_personnel_modal")
        page.locator("#form-modal .close-modal-btn").first.click()
        page.wait_for_timeout(500)
        
        # 13. 編輯人員彈窗
        print("- 打開編輯人員彈窗...")
        page.locator('#personnel-grid .edit-user-btn').first.click()
        expect(page.locator("#form-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "18_edit_personnel_modal")
        page.locator("#form-modal .close-modal-btn").first.click()
        page.wait_for_timeout(500)
        
        # 14. 團隊管理
        print("- 導航至團隊管理...")
        self.navigate_to_page(page, "teams", "#teams-grid")
        self.take_gif_frame(page, "19_teams_page")
        
        # 15. 編輯團隊彈窗
        print("- 打開編輯團隊彈窗...")
        page.locator('#teams-grid .edit-team-btn').first.click()
        expect(page.locator("#form-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "20_edit_team_modal")
        page.locator("#form-modal .close-modal-btn").first.click()
        page.wait_for_timeout(500)
        
        # 16. 通知管道
        print("- 導航至通知管道...")
        self.navigate_to_page(page, "channels", "#channels-grid")
        self.take_gif_frame(page, "21_channels_page")
        
        # 17. 編輯通知管道彈窗
        print("- 打開編輯通知管道彈窗...")
        page.locator('#channels-grid .edit-channel-btn').first.click()
        expect(page.locator("#form-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "22_edit_channel_modal")
        page.locator("#form-modal .close-modal-btn").first.click()
        page.wait_for_timeout(500)
        
        # 18. 告警規則折疊介面
        print("- 導航至告警規則...")
        self.navigate_to_page(page, "rules", "#rules-grid")
        self.take_gif_frame(page, "23_rules_page")
        
        print("- 打開「新增規則」模態框並展示折疊...")
        page.locator('#add-rule-btn').click()
        expect(page.locator("#form-modal")).to_be_visible()
        page.wait_for_timeout(800)
        self.take_gif_frame(page, "24_add_rule_modal")
        
        # 展開自動化部分
        page.locator('.accordion-header').nth(1).click()
        page.wait_for_timeout(500)
        
        # 使用 Tom Select 選擇自動化腳本
        if not self.interact_with_tom_select(page, 'automation-script-select', '重啟 Web 服務'):
            print("    - 跳過自動化腳本選擇")
        
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "25_add_rule_modal_automation_expanded")
        
        # 展開通知部分
        page.locator('.accordion-header').nth(2).click()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "26_add_rule_modal_all_expanded")
        page.locator("#form-modal .close-modal-btn").first.click()
        page.wait_for_timeout(500)
        
        # 19. 自動化頁面標籤
        print("- 導航至自動化頁面...")
        self.navigate_to_page(page, "automation", "#scripts-content")
        self.take_gif_frame(page, "27_automation_scripts_tab")
        
        print("- 切換至執行日誌標籤...")
        page.locator('#execution-logs-tab').click()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "28_automation_logs_tab")
        
        # 20. 自動化執行日誌輸出彈窗
        print("- 打開自動化執行日誌輸出彈窗...")
        page.locator('#execution-logs-grid .view-output-btn').first.click()
        expect(page.locator("#form-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "29_execution_log_output_modal")
        page.locator("#form-modal .close-modal-btn").first.click()
        page.wait_for_timeout(500)
        
        # 21. 容量規劃分析
        print("- 導航至容量規劃頁面...")
        self.navigate_to_page(page, "capacity")
        self.take_gif_frame(page, "30_capacity_planning_page")
        
        print("- 運行分析...")
        
        # 使用 Tom Select 選擇目標群組和指標
        self.interact_with_tom_select(page, 'capacity-target-group', '核心交換器')
        self.interact_with_tom_select(page, 'capacity-metric', '磁碟使用率')
        
        page.locator('#analyze-capacity-btn').click()
        expect(page.locator("#capacity-results")).to_be_visible()
        page.wait_for_timeout(2500)
        self.take_gif_frame(page, "31_capacity_planning_results")
        
        # 22. 個人檔案標籤
        print("- 導航至個人檔案頁面...")
        self.navigate_to_page(page, "profile", "#page-profile")
        self.take_gif_frame(page, "32_profile_info_tab")
        
        # 23. 操作成功反饋提示
        print("- 觸發操作成功反饋提示...")
        # 確保激活 info 標籤
        page.locator('.profile-tab[data-tab="info"]').click()
        page.wait_for_timeout(500)
        page.locator("#profile-name-input").fill("Test Name")
        page.get_by_role("button", name="更新資訊").click()
        expect(page.locator("#feedback-modal")).to_be_visible()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "33_feedback_modal")
        page.locator("#app").click()
        page.wait_for_timeout(500)
        
        print("- 切換至安全標籤...")
        page.locator('.profile-tab[data-tab="security"]').click()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "34_profile_security_tab")
        
        print("- 切換至通知標籤...")
        page.locator('.profile-tab[data-tab="notifications"]').click()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "35_profile_notifications_tab")
        
        # 24. 系統設定標籤
        print("- 導航至系統設定頁面...")
        self.navigate_to_page(page, "settings", "#page-settings")
        self.take_gif_frame(page, "36_settings_integration_tab")
        
        print("- 切換至通知設定標籤...")
        page.locator('.settings-tab[data-tab="notification"]').click()
        page.wait_for_timeout(500)
        self.take_gif_frame(page, "37_settings_notification_tab")
        
        # 25. 登出
        page.wait_for_timeout(1000)
        page.locator("#logout-btn").click()
        expect(page.locator("#login-page")).to_be_visible()
        self.take_gif_frame(page, "38_logout")
        
        print(f"捕獲了 {self.frame_count} 個幀到 '{self.base_dir}/gif_frames'")
        page.close()
        print("GIF 幀捕獲完成\n")
        
    def run_all_screenshots(self):
        """執行所有截圖任務"""
        print("開始統一截圖流程...\n")
        
        # 設置目錄
        self.setup_directories()
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)
            
            try:
                # 執行各項截圖任務
                self.capture_by_roles(browser)
                self.capture_gif_frames(browser)
                
            finally:
                browser.close()
                
        print("=== 所有截圖任務完成 ===")
        print(f"輸出目錄: {self.base_dir}")
        print(f"- 角色權限截圖: {self.base_dir}/screenshot_by_role/verification/")
        print(f"- GIF 幀: {self.base_dir}/gif_frames/ ({self.frame_count} 個幀)")


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='統一截圖腳本')
    parser.add_argument('--headless', action='store_true', default=True, 
                       help='以無頭模式運行瀏覽器 (預設: True)')
    parser.add_argument('--show-browser', action='store_true', 
                       help='顯示瀏覽器視窗 (覆蓋 --headless)')
    parser.add_argument('--width', type=int, default=1440, 
                       help='瀏覽器視窗寬度 (預設: 1440)')
    parser.add_argument('--height', type=int, default=900, 
                       help='瀏覽器視窗高度 (預設: 900)')
    parser.add_argument('--roles-only', action='store_true',
                       help='僅執行角色權限截圖')
    parser.add_argument('--gif-only', action='store_true',
                       help='僅執行 GIF 幀捕獲')
    
    args = parser.parse_args()
    
    # 處理 headless 參數
    headless = args.headless and not args.show_browser
    
    # 創建截圖管理器
    screenshot_manager = ScreenshotManager(
        headless=headless,
        viewport_size={"width": args.width, "height": args.height}
    )
    
    # 設置目錄
    screenshot_manager.setup_directories()
    
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        
        try:
            # 根據參數執行特定任務
            if args.roles_only:
                screenshot_manager.capture_by_roles(browser)
            elif args.gif_only:
                screenshot_manager.capture_gif_frames(browser)
            else:
                # 執行所有任務
                screenshot_manager.capture_by_roles(browser)
                screenshot_manager.capture_gif_frames(browser)
                
        finally:
            browser.close()
    
    print("截圖腳本執行完成！")


if __name__ == "__main__":
    main()