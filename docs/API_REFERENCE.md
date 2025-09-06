# SRE Platform API 參考文件

**版本:** 1.0.0
**最後更新:** 2025-09-05

本文件為 SRE Platform 的 API 提供了包含 UI 截圖的全面參考，旨在建立前端功能與後端 API 之間的清晰對照。平台由兩個主要服務組成，每個服務都有其獨立的 API。

- **Control Plane API**: 管理資源、使用者、事件並協調任務。
- **SRE Assistant API**: 一個無介面的、由 AI 驅動的診斷與分析引擎。

關於請求/回應的詳細資料模型，請參考各服務獨立的 OpenAPI 規格檔案。

---

## 1. Control Plane API

- **基礎 URL:** `http://localhost:8081`
- **規格文件:** [`pkg/api/control-plane-openapi.yaml`](../pkg/api/control-plane-openapi.yaml)

### 1.1. 儀表板 (Dashboard)

儀表板提供系統健康狀況的宏觀視圖，整合了告警、資源和關鍵績效指標的摘要。

![儀表板](jules-scratch/gif_frames/frame_001_02_dashboard.png)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `GET` | `/api/v1/dashboard/summary` | 獲取儀表板摘要數據 |
| `GET` | `/api/v1/dashboard/trends` | 獲取指標趨勢數據 |
| `GET` | `/api/v1/dashboard/resource-distribution` | 獲取資源分佈統計 |

### 1.2. 資源管理 (Resource Management)

集中管理所有受監控的資源，支援探索、查詢、CRUD 和批次操作。

![資源管理](jules-scratch/gif_frames/frame_007_08_resources_page.png)
![資源批次操作](jules-scratch/gif_frames/frame_010_11_resources_batch_selection.png)
![網段掃描](jules-scratch/gif_frames/frame_008_09_scan_network_initial_modal.png)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `GET` | `/api/v1/resources` | 獲取資源列表 |
| `POST` | `/api/v1/resources` | 創建新資源 |
| `GET` | `/api/v1/resources/{resourceId}` | 獲取特定資源詳情 |
| `PUT` | `/api/v1/resources/{resourceId}` | 更新資源資訊 |
| `DELETE` | `/api/v1/resources/{resourceId}` | 刪除資源 |
| `POST` | `/api/v1/resources/batch` | 批次操作資源 |
| `POST` | `/api/v1/resources/scan` | 掃描網段以發現新資源 |
| `GET` | `/api/v1/resources/scan/{taskId}` | 獲取網段掃描結果 |

### 1.3. 告警與事件管理 (Incidents & Logs)

提供一個集中介面來查看、篩選、管理所有告警事件，並利用 AI 生成分析報告。

![告警紀錄](jules-scratch/gif_frames/frame_003_04_logs_page.png)
![AI 輔助報告](jules-scratch/gif_frames/frame_006_07_logs_ai_report.png)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `GET` | `/api/v1/incidents` | 獲取事件列表 |
| `POST` | `/api/v1/incidents` | 手動創建事件 |
| `GET` | `/api/v1/incidents/{incidentId}` | 獲取事件詳情 |
| `POST` | `/api/v1/incidents/{incidentId}/acknowledge` | 確認事件 |
| `POST` | `/api/v1/incidents/{incidentId}/resolve` | 解決事件 |
| `POST` | `/api/v1/incidents/{incidentId}/assign` | 指派處理人員 |
| `POST` | `/api/v1/incidents/{incidentId}/comments` | 新增註記 |
| `POST` | `/api/v1/incidents/generate-report` | **(SRE Assistant 驅動)** AI 生成事件報告 |

### 1.4. 告警規則 (Alert Rules)

定義告警觸發條件，並可綁定自動化腳本進行響應。

![告警規則](jules-scratch/gif_frames/frame_022_23_rules_page.png)
![新增告警規則](jules-scratch/gif_frames/frame_023_24_add_rule_modal.png)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `GET` | `/api/v1/alert-rules` | 獲取告警規則列表 |
| `POST` | `/api/v1/alert-rules` | 創建告警規則 |
| `GET` | `/api/v1/alert-rules/{ruleId}` | 獲取規則詳情 |
| `PUT` | `/api/v1/alert-rules/{ruleId}` | 更新告警規則 |
| `DELETE` | `/api/v1/alert-rules/{ruleId}` | 刪除告警規則 |
| `POST` | `/api/v1/alert-rules/{ruleId}/test` | 測試告警規則 |

### 1.5. 自動化 (Automation)

管理自動化腳本庫與查看執行歷史。

![自動化腳本庫](jules-scratch/gif_frames/frame_026_27_automation_scripts_tab.png)
![自動化日誌](jules-scratch/gif_frames/frame_027_28_automation_logs_tab.png)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `GET` | `/api/v1/automation/scripts` | 獲取腳本列表 |
| `POST` | `/api/v1/automation/scripts` | 創建腳本 |
| `PUT` | `/api/v1/automation/scripts/{scriptId}` | 更新腳本 |
| `POST` | `/api/v1/automation/execute` | 執行腳本 |
| `GET` | `/api/v1/automation/executions` | 查詢執行歷史 |

### 1.6. 組織管理 (Organization)

管理平台中的人員、團隊及其權限。

![人員管理](jules-scratch/gif_frames/frame_015_16_personnel_page.png)
![團隊管理](jules-scratch/gif_frames/frame_018_19_teams_page.png)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `GET` | `/api/v1/users` | 獲取使用者列表 |
| `POST` | `/api/v1/users` | 創建使用者 |
| `PUT` | `/api/v1/users/{userId}` | 更新使用者 |
| `DELETE` | `/api/v1/users/{userId}` | 刪除使用者 |
| `GET` | `/api/v1/teams` | 獲取團隊列表 |
| `POST` | `/api/v1/teams` | 創建團隊 |
| `PUT` | `/api/v1/teams/{teamId}` | 更新團隊 |
| `POST` | `/api/v1/teams/{teamId}/members` | 管理團隊成員 |

### 1.7. 通知與設定 (Notifications & Settings)

管理通知管道、個人資料與系統級設定。

![通知管道](jules-scratch/gif_frames/frame_020_21_channels_page.png)
![個人通知設定](jules-scratch/gif_frames/frame_034_35_profile_notifications_tab.png)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `GET` | `/api/v1/notification-channels` | 獲取通知管道列表 |
| `POST` | `/api/v1/notification-channels` | 創建通知管道 |
| `PUT` | `/api/v1/notification-channels/{channelId}` | 更新通知管道 |
| `POST` | `/api/v1/notification-channels/{channelId}/test` | 測試通知管道 |
| `GET` | `/api/v1/users/profile` | 獲取個人資料 |
| `PUT` | `/api/v1/users/profile` | 更新個人資料 |
| `GET` | `/api/v1/settings` | 獲取系統設定 |
| `PUT` | `/api/v1/settings` | 更新系統設定 |

---

## 2. SRE Assistant API

- **基礎 URL:** `http://localhost:8000`
- **規格文件:** [`pkg/api/sre-assistant-openapi.yaml`](../pkg/api/sre-assistant-openapi.yaml)

### 2.1. 診斷 (Diagnostics)

SRE Assistant 的核心功能，提供由 AI 驅動的非同步診斷與分析服務。

![容量規劃](jules-scratch/gif_frames/frame_029_30_capacity_planning_page.png)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `POST` | `/api/v1/diagnostics/deployment` | **(非同步)** 觸發部署診斷 |
| `POST` | `/api/v1/diagnostics/alerts` | **(非同步)** 觸發告警分析 |
| `POST` | `/api/v1/diagnostics/capacity` | **(同步)** 執行容量分析與預測 |
| `GET` | `/api/v1/diagnostics/{sessionId}/status` | 查詢非同步任務的狀態與結果 |
| `GET` | `/api/v1/diagnostics/history` | 查詢歷史診斷記錄 |
| `POST` | `/api/v1/execute` | 處理自然語言查詢 |

### 2.2. 核心與輔助 (Core & Support)

| 方法 | 端點 | 摘要 |
|---|---|---|
| `GET` | `/api/v1/healthz` | 服務健康檢查 |
| `GET` | `/api/v1/readyz` | 服務就緒檢查 |
| `GET` | `/api/v1/metrics` | Prometheus 指標 |
| `GET` | `/api/v1/workflows/templates` | 獲取可用的工作流模板 |
| `GET` | `/api/v1/tools/status` | 檢查所有外部工具的連線狀態 |
