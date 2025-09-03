# Control Plane - 使用者指南

歡迎使用 Control Plane！本指南將引導您了解本平台的各項功能與操作方式，協助您快速上手，高效地進行系統維運與管理。

## 目錄

- [1. 核心理念](#1-核心理念)
- [2. 快速導覽](#2-快速導覽)
  - [2.1. 登入與主介面](#21-登入與主介面)
  - [2.2. 側邊導覽列](#22-側邊導覽列)
  - [2.3. 頁首功能區](#23-頁首功能區)
- [3. 儀表板 (Dashboard)](#3-儀表板-dashboard)
- [4. 資源管理 (Resource Management)](#4-資源管理-resource-management)
  - [4.1. 總覽與批次操作](#41-總覽與批次操作)
  - [4.2. 網段掃描與探索](#42-網段掃描與探索)
- [5. 組織與權限管理](#5-組織與權限管理)
  - [5.1. 人員管理 (Personnel)](#51-人員管理-personnel)
  - [5.2. 團隊管理 (Teams)](#52-團隊管理-teams)
- [6. 告警規則 (Alert Rules)](#6-告警規則-alert-rules)
- [7. 自動化 (Automation)](#7-自動化-automation)
  - [7.1. 腳本庫 (Scripts)](#71-腳本庫-scripts)
  - [7.2. 執行日誌 (Execution Logs)](#72-執行日誌-execution-logs)
- [8. 容量規劃 (Capacity Planning)](#8-容量規劃-capacity-planning)
- [9. 告警紀錄 (Logs/Incidents)](#9-告警紀錄-logsincidents)
  - [9.1. 檢視與篩選](#91-檢視與篩選)
  - [9.2. AI 輔助生成報告](#92-ai-輔助生成報告)
- [10. 通知管道 (Notification Channels)](#10-通知管道-notification-channels)
- [11. 個人資料與系統設定](#11-個人資料與系統設定)
  - [11.1. 個人資料 (Profile)](#111-個人資料-profile)
  - [11.2. 系統設定 (Settings)](#112-系統設定-settings)

---

## 1. 核心理念

Control Plane 是一個以後端驅動 (Backend-Driven) 為核心理念的現代化維運平台。我們致力於將複雜的邏輯處理集中在穩定高效的 Go 後端，並藉由 HTMX 技術，在不犧牲使用者體驗的前提下，打造一個輕量、快速且易於維護的前端介面。

## 2. 快速導覽

### 2.1. 登入與主介面

當您首次造訪平台時，系統會將您導向至統一的登入頁面。成功登入後，您將看到系統的主介面，包含了左側的「側邊導覽列」與上方的「頁首功能區」。

![登入頁面](jules-scratch/gif_frames/frame_000_01_login_page.png)

### 2.2. 側邊導覽列

位於畫面左側，提供全站的主要功能導覽，是您穿梭於各功能模組的主要入口。當前所在的頁面會在導覽列上以高亮樣式顯示。

### 2.3. 頁首功能區

位於畫面頂部，固定顯示，包含：
- **頁面標題**: 顯示您目前所在的功能頁面名稱。
- **通知中心**: 以鈴鐺圖示呈現，點擊可查看最新的系統通知。
- **使用者選單**: 點擊您的頭像或名稱，可進行登出或前往「個人資料」頁面。

## 3. 儀表板 (Dashboard)

儀表板是您登入後看到的第一個畫面，它以視覺化的圖表和卡片，彙整了系統當前最重要的狀態摘要。主要包含：
- **狀態趨勢卡片**: 醒目地顯示「新告警」、「處理中」、「今日已解決」的數量，並與昨日數據比較呈現增長或下降趨勢。
- **關鍵績效指標 (KPI)**: 包含「資源妥善率」、「總資源數」等核心指標。
- **圖表區**: 透過「資源群組狀態總覽」長條圖與「資源狀態分佈」圓餅圖，讓您能快速從宏觀角度掌握整體系統的健康度。

![儀表板](jules-scratch/screenshot_pages/dashboard.png)

## 4. 資源管理 (Resource Management)

### 4.1. 總覽與批次操作

此頁面集中呈現了所有受監控的資源列表。您可以透過搜尋功能快速找到特定資源，並查看其基本資訊與狀態。為了提升管理效率，我們提供了強大的批次操作功能：
1.  在資源列表的每一行前方勾選您想操作的資源。
2.  勾選後，列表頂部會出現「批次操作欄」。
3.  您可以選擇將這些資源「批次刪除」、「批次加入群組」或「批次移出群組」。

![資源管理](jules-scratch/screenshot_pages/resources.png)
![資源批次操作](jules-scratch/gif_frames/frame_003_04_resources_batch_selection.png)

### 4.2. 網段掃描與探索

除了手動新增資源，您還可以透過「掃描網段」功能，自動探索網路中的未知資源。
1.  點擊「掃描網段」按鈕，輸入目標網段與掃描方式。
2.  系統會回報掃描結果，您可以勾選希望匯入的資源。
3.  點擊「匯入資源」即可完成批次新增。

![網段掃描初始畫面](jules-scratch/screenshot_modals/modal_scan_network_initial.png)
![網段掃描結果](jules-scratch/screenshot_modals/modal_scan_network_results.png)


## 5. 組織與權限管理

### 5.1. 人員管理 (Personnel)

此頁面用於管理系統的使用者帳號與組織權限。身為管理者，您可以在此新增或編輯人員，並設定其「角色」與「團隊歸屬」。

**請注意**: 使用者的個人聯絡方式（如 Email、LINE）與通知偏好，已移至使用者自己的「個人資料」頁面進行管理，以符合職責分離原則。

![人員管理](jules-scratch/screenshot_pages/personnel.png)
![新增人員](jules-scratch/gif_frames/frame_005_06_add_personnel_modal.png)

### 5.2. 團隊管理 (Teams)

「團隊」是權限賦予與通知訂閱的核心單位。在此頁面，您可以：
- 建立團隊並加入成員。
- 將「資源群組」的查看權限授予團隊。
- 設定團隊的「通知訂閱者」，決定告警訊息要發送給哪些「人員」或「通知管道」。

![團隊管理](jules-scratch/screenshot_pages/teams.png)
![編輯團隊](jules-scratch/screenshot_modals/modal_edit_team.png)

## 6. 告警規則 (Alert Rules)

您可以針對特定的「資源群組」自訂告警觸發的條件。點擊「新增規則」後，會彈出一個整合式的設定視窗，所有選項都清晰地組織在可摺疊的區塊中，方便您進行配置。

![告警規則頁面](jules-scratch/screenshot_pages/rules.png)

在「新增/編輯告警規則」的彈出視窗中，您可以設定所有與規則相關的參數。我們採用了摺疊式介面，將複雜的設定拆分為三個區塊，讓整體設定流程更加清晰有條理：

1.  **基本設定 (Basic Settings)**:
    *   **規則名稱**: 為您的規則取一個易於識別的名稱。
    *   **描述**: (選填) 簡要說明此規則的目的。
    *   **資源群組**: 選擇此規則要應用的資源群組。
    *   **條件**: 設定觸發告警的具體條件，例如 `CPU 使用率 > 80%`。

    ![新增告警規則的彈出視窗，完整展示所有設定選項](jules-scratch/gif_frames/frame_007_08_add_rule_modal.png)

2.  **自動化響應 (Automated Response)**:
    *   (選填) 您可以選擇性地為此規則綁定一個預先定義好的「自動化腳本」。
    *   當告警觸發時，系統將自動執行您指定的腳本（例如：重啟服務、清理磁碟），實現秒級的故障自動排除。

    ![新增告警規則的彈出視窗，完整展示所有設定選項](jules-scratch/gif_frames/frame_008_09_add_rule_modal_automation_expanded.png)

3.  **通知內容自定義 (Custom Notification Content)**:
    *   (選填) 系統允許您客製化告警通知的標題與內容。
    *   您可以使用 `{{ .ResourceName }}`、`{{ .MetricValue }}` 等變數來動態插入告警的上下文資訊，讓收到的通知更具可讀性與參考價值。

    ![新增告警規則的彈出視窗，完整展示所有設定選項](jules-scratch/gif_frames/frame_009_10_add_rule_modal_all_expanded.png)

## 7. 自動化 (Automation)

此功能是實現「事件驅動自動化」的核心。

![自動化頁面](jules-scratch/screenshot_pages/automation.png)

### 7.1. 腳本庫 (Scripts)

管理者可在此上傳、編輯或刪除用於自動化響應的腳本（如 Shell Script, Ansible Playbook），並定義腳本所需的參數。

![自動化 - 腳本庫](jules-scratch/gif_frames/frame_013_14_automation_scripts_tab.png)

### 7.2. 執行日誌 (Execution Logs)

此頁籤記錄了每一次自動化腳本的執行歷史，包含觸發原因、執行時間、狀態與結果。點擊「查看輸出」按鈕，可以檢視該次執行的詳細 Log，方便您追蹤與除錯。

![自動化 - 執行日誌](jules-scratch/screenshot_pages/automation_execution_logs.png)

## 8. 容量規劃 (Capacity Planning)

本平台提供主動式的資源規劃工具。您可以選擇一個「資源群組」和一個關鍵指標（如 CPU 或磁碟使用率），系統將分析歷史數據並預測未來的資源趨勢。

![容量規劃](jules-scratch/screenshot_pages/capacity.png)

分析結果將以易懂的卡片和圖表呈現，例如：「預計將在 45 天後達到 80% 警戒線」，幫助您提前應對潛在的容量瓶頸。


![容量規劃結果](jules-scratch/gif_frames/frame_016_17_capacity_planning_results.png)

## 9. 告警紀錄 (Logs/Incidents)

此頁面是所有告警事件的集中地，您可以在此查看、搜尋、處理所有歷史與當前的告警。點擊任一筆紀錄即可開啟「事件詳情」視窗進行處理。

![告警紀錄](jules-scratch/screenshot_pages/logs.png)

### 9.1. 檢視與篩選

提供基於時間範圍、告警等級與處理狀態的進階篩選功能。點擊單筆告警可查看詳細資訊，並進行確認 (Acknowledge) 或解決 (Resolve) 等操作。

![事件詳情](jules-scratch/screenshot_modals/modal_incident_details.png)

### 9.2. AI 輔助生成報告

您可以勾選多筆相關的告警事件，點擊「生成事件報告」。系統會呼叫 Gemini AI，自動為您產出一份結構化的事件根本原因分析報告，大幅縮短撰寫報告的時間。

![AI 輔助報告](jules-scratch/gif_frames/frame_012_13_logs_ai_report.png)

## 10. 通知管道 (Notification Channels)

為了靈活地發送通知，您可以設定多種類型的「通知管道」。

![通知管道](jules-scratch/screenshot_pages/channels.png)

在新增管道時，您可以選擇 `Email`, `Webhook`, `Slack`, `LINE Notify` 或 `SMS`。系統會根據您的選擇，動態顯示對應的設定欄位，例如：
- **Slack**: 需要填寫 `Incoming Webhook URL`。
- **LINE Notify**: 需要填寫 `存取權杖 (Access Token)`。

![通知管道](jules-scratch/screenshot_modals/modal_edit_channel.png)

## 11. 個人資料與系統設定

### 11.1. 個人資料 (Profile)

此頁面採用頁籤式設計，讓您能方便地管理個人資訊：
- **個人資訊**: 查看您的姓名、角色、所屬團隊。
![個人資料](jules-scratch/screenshot_pages/profile.png)

- **密碼安全**: 變更您的登入密碼。
![個人資料 - 密碼安全](jules-scratch/gif_frames/frame_018_19_profile_security_tab.png)

- **通知設定**:
  - **聯絡方式**: 設定並「驗證」您接收告警的 Email、LINE 或 SMS。**系統只會將通知發送到已驗證的管道**。
  - **通知偏好**: 選擇您希望接收哪些嚴重等級的告警。
![個人資料 - 通知設定](jules-scratch/gif_frames/frame_019_20_profile_notifications_tab.png)


### 11.2. 系統設定 (Settings)

此頁面僅供系統管理員存取，同樣採用頁籤式設計，用於管理全域設定。

- **整合設定**: 設定與外部系統（如 Grafana）的串接參數。
![系統設定 - 整合設定](jules-scratch/screenshot_pages/settings.png)
- **通知設定**: 設定系統用於發送通知的後端服務，如郵件伺服器 (SMTP) 或 SMS 閘道。由於內容較長，此分頁可向下滾動檢視所有設定。
![系統設定 - 通知設定](jules-scratch/screenshot_pages/settings_notification_tab.png)
