# SRE Platform - 開發路線圖與任務清單

> **基於**: SRE Platform 專案全面審查報告 (2025-09-05)
> **當前專案成熟度**: 75/100
> **目標**: 在12週內達到生產就緒狀態
>
> **總覽**: 本文件是 SRE Platform 專案的**唯一真實來源 (Single Source of Truth)**，用於追蹤所有開發任務。它根據架構設計的階段進行組織，並整合了所有新功能、重構計畫和已知的技術債。

---

## 📋 重要同步說明

### 🔄 API 狀態同步機制
當本文件中的 **API 任務標記為完成** (`[x]`) 時，**必須同步更新** [`API_REFERENCE.md`](./API_REFERENCE.md) 中的對應端點狀態：

- ✅ **已實現**: 將端點狀態從 `🚧 僅有路由` 或 `❌ 未實現` 更新為 `✅ 已實現`
- 📊 **統計更新**: 同步更新 API 總覽統計表格中的數量和實現率
- 📝 **發現更新**: 更新關鍵發現部分以反映新的統計數據

**同步檢查清單**:
- [ ] 確認 ROADMAP.md 中的完成標記 `[x]`
- [ ] 在 API_REFERENCE.md 中找到對應端點
- [ ] 更新端點狀態為 `✅ 已實現`
- [ ] 更新統計數據 (已實現/僅有路由/未實現/實現率)
- [ ] 更新關鍵發現部分
- [ ] 驗證兩個文件的統計數據一致性

---

## Phase 1: 核心整合 (Core Integration)

- **主題**: 專注於完成 `sre-assistant` 與 `control-plane` 之間的所有技術對接工作，確保兩者能夠安全、可靠地協同工作。
- **關鍵目標**: 實現一個可由 `control-plane` 觸發並完成端到端診斷流程的最小可行產品 (MVP)。

### 主要交付物 (Key Deliverables):

- **[🚧] 1.1. API 契約符合性 (API Contract Compliance)**:
    - **任務**: 確保 `sre-assistant` 的 FastAPI 服務嚴格遵守 `pkg/api/sre-assistant-openapi.yaml` 中定義的所有端點、請求格式和回應格式。
    - **當前狀態**:
        - ✅ SRE Assistant: 91% 完成 (10/11 個端點) - 缺少 `/api/v1/metrics`
        - ⚠️ Control Plane: 49% 完成 (24/49 個端點) - 使用模擬數據實現
    - **相關子任務**:
        - [x] 在 `DiagnosticResult` 中添加 `execution_plan` 欄位
        - [x] 定義 `AlertAnalysisRequest` 資料模型
        - [x] 定義 `CapacityAnalysisRequest` 資料模型
        - [x] 定義 `ExecuteRequest` 資料模型
    - 補充參考（ADK 最佳實踐）:
        - [OpenAPI 工具指南 | ADK 文件](./references/adk-docs/tools-openapi-tools.md)
        - [契約測試與測試入門 | ADK 文件](./references/adk-docs/get-started-testing.md)
        - [OpenAPI 工具範例（程式碼片段）](./references/snippets/tools/openapi_tool.py)

- **[✅] 1.2. 服務對服務認證 (M2M Authentication)**:
    - **任務**: 完整實現基於 Keycloak 和 Client Credentials Flow 的認證機制。
    - **相關子任務**:
        - [x] 實作 `verify_token` 函數的實際 JWT 驗證
        - [x] 與 Keycloak 進行整合測試
        - [x] 處理 token 過期和刷新邏輯
    - **參考**: `docs/reference-adk-examples.md` (oauth_calendar_agent)
    - 補充參考（ADK 最佳實踐）:
        - [工具認證 | ADK 文件](./references/adk-docs/tools-authentication.md)
        - [Headless Agent 認證範例（Agent）](./references/adk-agent-samples/headless_agent_auth/agent.py)
        - [Headless Agent 認證中介層（OAuth2 Middleware）](./references/adk-agent-samples/headless_agent_auth/oauth2_middleware.py)

- **[🚧] 1.3. 核心工具開發 (`Prometheus`, `Loki`, `ControlPlane`)**:
    - **任務**: 實現 `PrometheusQueryTool`、`LokiLogQueryTool` 和 `ControlPlaneTool`，為診斷流程提供數據來源。
    - **對應 API**: 這些工具是 `/diagnostics/deployment` 端點的基礎。
    - **當前狀態**: 工具代碼已存在且包含真實 HTTP 請求邏輯 (非模擬數據)
    - **子任務 (PrometheusQueryTool)**:
        - [x] 實作實際的 Prometheus 查詢邏輯 (已完成)
        - [x] 移除模擬資料，使用真實 API 調用 (已完成)
        - [ ] 添加查詢優化和錯誤處理
        - [ ] 實作查詢結果快取機制
    - **子任務 (LokiLogQueryTool)**:
        - [x] 實作動態查詢參數設定 (已完成)
        - [ ] 添加完整的錯誤處理機制
        - [ ] 實作日誌過濾和聚合功能
    - **子任務 (ControlPlaneTool)**:
        - [ ] 查詢資源狀態 (`GET /api/v1/resources`)
        - [ ] 獲取資源詳情 (`GET /api/v1/resources/{resourceId}`)
        - [ ] 查詢資源群組 (`GET /api/v1/resource-groups`)
        - [ ] 查詢部署相關的審計日誌 (`GET /api/v1/audit-logs`)
        - [ ] 查詢相關事件 (`GET /api/v1/incidents`)
        - [ ] 獲取告警規則狀態 (`GET /api/v1/alert-rules`)
        - [ ] 查詢自動化腳本執行歷史 (`GET /api/v1/automation/executions`)
    - **參考**: `docs/reference-adk-examples.md` (jira_agent, bigquery)
    - 補充參考（ADK 最佳實踐）:
        - [工具設計與 Function Tools | ADK 文件](./references/adk-docs/tools-function-tools.md)
        - [第三方工具整合 | ADK 文件](./references/adk-docs/tools-third-party-tools.md)
        - [GitHub Toolset 範例（工具集結構與錯誤處理）](./references/adk-agent-samples/github-agent/github_toolset.py)

- **[🚧] 1.4. 端到端流程實作與測試**:
    - **任務**: 在 `SREWorkflow` 中整合所有核心工具，並建立一個完整的整合測試，以驗證 `/diagnostics/deployment` 的端到端流程。
    - **對應 API**: `/diagnostics/deployment`。
    - **相關子任務**:
        - [x] **修復工作流程錯誤處理**: `asyncio.gather` 中已添加異常處理、容錯、超時和重試機制。
        - [ ] **API 整合測試**: 端到端診斷流程測試, 非同步任務狀態追蹤測試, 錯誤情境測試。
        - [ ] **外部服務整合測試**: Prometheus, Loki, Keycloak 整合測試。
    - **參考**: `docs/reference-adk-examples.md` (parallel_functions, workflow_agent_seq)
    - 補充參考（ADK 最佳實踐）:
        - [平行工作流代理 | ADK 文件](./references/adk-docs/agents-workflow-agents-parallel-agents.md)
        - [平行工作流範例（程式碼）](./references/adk-agent-samples/google-adk-workflows/parallel/agent.py)
        - [自我校驗工作流範例（Self-Critic）](./references/adk-agent-samples/google-adk-workflows/self_critic/agent.py)

- **[✅] 1.5. 核心服務本地化與持久化**:
    - **任務**: 確保開發環境使用 PostgreSQL 作為會話後端，ChromaDB 作為記憶體後端，並能穩定啟動與互動。
    - **相關子任務**:
        - [x] **實作任務狀態持久化**: 使用 Redis 替代記憶體存儲任務狀態。
        - [x] **環境變數化配置**: 將硬編碼的 URL 移至環境變數。
    - **參考**: `docs/reference-adk-examples.md` (history_management, session_state_agent)
    - 補充參考（ADK 最佳實踐）:
        - [Sessions 與狀態管理 | ADK 文件](./references/adk-docs/sessions-state.md)
        - [記憶體型會話 | ADK 文件](./references/adk-docs/sessions-memory.md)
        - [FastAPI + ADK Runner 實作（含 Session 管理）](./references/adk-agent-samples/personal-expense-assistant-adk/backend.py)

---

## Phase 2: Control Plane 功能擴展與 UI 整合

- **主題**: 專注於擴充 `sre-assistant` 的後端能力，並為這些能力在 `control-plane` 上提供對應的 UI 操作介面。
- **關鍵目標**: 讓使用者能夠透過 UI 觸發 `sre-assistant` 的各項核心診斷功能。

### 主要交付物 (Key Deliverables):

- **[ ] 2.1. 實現診斷後端邏輯**:
    - **任務**: 完整實現 `SREWorkflow` 中的 `_diagnose_alerts`, `_analyze_capacity`, `_execute_query` 方法。
    - **對應 API**: `/diagnostics/alerts`, `/diagnostics/capacity`, `/execute`
    - **參考**:
        - **基本工作流**: [`docs/references/adk-examples/workflow_triage/agent.py`](./references/adk-examples/workflow_triage/agent.py)
        - **高級模式 (帶自我校驗)**: [`docs/references/adk-agent-samples/google-adk-workflows/self_critic/`](./references/adk-agent-samples/google-adk-workflows/self_critic/)
        - **SRE 理論 - 事件響應**: [`docs/references/google-sre-book/Chapter-13-Emergency-Response.md`](./references/google-sre-book/Chapter-13-Emergency-Response.md)
        - **SRE 理論 - 事後剖析**: [`docs/references/google-sre-book/Chapter-15-Postmortem-CultureLearning-from-Failure.md`](./references/google-sre-book/Chapter-15-Postmortem-CultureLearning-from-Failure.md)
    - 補充參考（ADK 最佳實踐）:
        - [工作流代理總覽 | ADK 文件](./references/adk-docs/agents-workflow-agents.md)
        - [序列式工作流代理 | ADK 文件](./references/adk-docs/agents-workflow-agents-sequential-agents.md)
        - [Dispatcher 工作流範例（程式碼）](./references/adk-agent-samples/google-adk-workflows/dispatcher/agent.py)

- **[ ] 2.2. 資料庫架構設計與實現 (Database Architecture & Implementation)**:
    - **任務**: 設計並實現完整的 PostgreSQL 資料庫架構，包含所有業務實體的 schema、關聯和 migration 腳本。
    - **前置條件**: Phase 1.5 核心服務本地化完成
    - **相關子任務**:
        - [ ] 設計核心實體 schema (Resources, Incidents, AlertRules, Users, Teams)
        - [ ] 定義實體間關聯和約束 (Foreign Keys, Indexes)
        - [ ] 實作資料庫 migration 腳本 (Up/Down migrations)
        - [ ] 建立資料庫連接池和配置管理
        - [ ] 實作基本的 CRUD Repository 層
    - **參考**:
        - **SRE 理論 - 資料庫設計**: [`docs/references/google-sre-book/Chapter-18-Databases.md`](./references/google-sre-book/Chapter-18-Databases.md)
        - **專案結構範本**: [`docs/references/agent-starter-pack/src/`](./references/agent-starter-pack/src/)
    - 補充參考（ADK 最佳實踐）:
        - [ADK 專案結構指南 | ADK 文件](./references/adk-docs/get-started-about.md)

- **[ ] 2.3. Control Plane Go 服務完善**:
    - **任務**: 實現 Control Plane 的真實業務邏輯，取代所有模擬資料。
    - **前置條件**: Phase 2.2 資料庫架構完成
    - **當前狀態**: 7/49 個端點已實現 (14%)
    - **相關子任務**:
        - [x] 實作核心健康檢查端點 (`/healthz`, `/readyz`, `/metrics`)
        - [x] 實作資源列表查詢 (`GET /resources`)
        - [ ] **儀表板功能** (2個端點未實現)
            - [ ] `GET /api/v1/dashboard/trends` - 趨勢數據
            - [ ] `GET /api/v1/dashboard/resource-distribution` - 資源分佈統計
        - [ ] **資源管理 CRUD** (7個端點未實現)
            - [ ] `POST /api/v1/resources` - 創建資源
            - [ ] `GET /api/v1/resources/{resourceId}` - 獲取資源詳情
            - [ ] `PUT /api/v1/resources/{resourceId}` - 更新資源
            - [ ] `DELETE /api/v1/resources/{resourceId}` - 刪除資源
            - [ ] `POST /api/v1/resources/batch` - 批次操作
            - [ ] `POST /api/v1/resources/scan` - 網段掃描
            - [ ] `GET /api/v1/resources/scan/{taskId}` - 掃描結果
        - [ ] **資源群組管理** (5個端點未實現)
            - [ ] `GET /api/v1/resource-groups` - 群組列表
            - [ ] `POST /api/v1/resource-groups` - 創建群組
            - [ ] `PUT /api/v1/resource-groups/{groupId}` - 更新群組
            - [ ] `DELETE /api/v1/resource-groups/{groupId}` - 刪除群組
            - [ ] `POST /api/v1/resource-groups/{groupId}/members` - 管理成員
        - [ ] **事件與告警管理** (10個端點未實現)
            - [ ] `PUT /api/v1/incidents/{incidentId}` - 更新事件
            - [ ] `GET /api/v1/alerts` - 獲取活躍告警
            - [ ] 其他 8 個事件管理端點...
        - [ ] **告警規則管理** (8個端點未實現)
            - [ ] `GET /api/v1/alert-rules` - 規則列表
            - [ ] `POST /api/v1/alert-rules` - 創建規則
            - [ ] `GET /api/v1/alert-rules/{ruleId}` - 規則詳情
            - [ ] `PUT /api/v1/alert-rules/{ruleId}` - 更新規則
            - [ ] `DELETE /api/v1/alert-rules/{ruleId}` - 刪除規則
            - [ ] `POST /api/v1/alert-rules/{ruleId}/test` - 測試規則
            - [ ] `POST /api/v1/alert-rules/{ruleId}/enable` - 啟用規則
            - [ ] `POST /api/v1/alert-rules/{ruleId}/disable` - 停用規則
        - [ ] **自動化腳本管理** (9個端點未實現)
            - [ ] `GET /api/v1/automation/scripts` - 腳本列表
            - [ ] `POST /api/v1/automation/scripts` - 創建腳本
            - [ ] `GET /api/v1/automation/scripts/{scriptId}` - 腳本詳情
            - [ ] `PUT /api/v1/automation/scripts/{scriptId}` - 更新腳本
            - [ ] `DELETE /api/v1/automation/scripts/{scriptId}` - 刪除腳本
            - [ ] `POST /api/v1/automation/execute` - 執行腳本
            - [ ] `GET /api/v1/automation/executions` - 執行歷史
            - [ ] `GET /api/v1/automation/executions/{executionId}` - 執行詳情
            - [ ] `POST /api/v1/automation/schedules` - 創建排程
        - [ ] **用戶與團隊管理** (16個端點未實現)
            - [ ] 用戶 CRUD 操作 (5個端點)
            - [ ] 用戶個人資料管理 (5個端點)
            - [ ] 團隊 CRUD 操作 (6個端點)
        - [ ] **通知管道管理** (6個端點未實現)
            - [ ] `GET /api/v1/notification-channels` - 管道列表
            - [ ] `POST /api/v1/notification-channels` - 創建管道
            - [ ] `GET /api/v1/notification-channels/{channelId}` - 管道詳情
            - [ ] `PUT /api/v1/notification-channels/{channelId}` - 更新管道
            - [ ] `DELETE /api/v1/notification-channels/{channelId}` - 刪除管道
            - [ ] `POST /api/v1/notification-channels/{channelId}/test` - 測試管道
        - [ ] **系統設定管理** (3個端點未實現)
            - [ ] `GET /api/v1/settings` - 獲取設定
            - [ ] `PUT /api/v1/settings` - 更新設定
            - [ ] `GET /api/v1/settings/maintenance-windows` - 維護時段
        - [ ] **審計與回調** (2個端點未實現)
            - [ ] `GET /api/v1/audit-logs` - 審計日誌
            - [ ] `POST /api/v1/callbacks/diagnosis-complete` - 診斷回調
        - [ ] 實作與 SRE Assistant 的完整整合
        - [ ] 實現中間件和認證機制
    - **參考**:
        - **全端架構範本**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
        - **前端實作參考**: [`docs/references/adk-agent-samples/gemini-fullstack/frontend/`](./references/adk-agent-samples/gemini-fullstack/frontend/)
        - **後端 API 文件**: [`docs/references/adk-docs/api-reference.md`](./references/adk-docs/api-reference.md)
    - 補充參考（ADK 最佳實踐）:
        - [ADK API 參考 | ADK 文件](./references/adk-docs/api-reference.md)
        - [Gemini Fullstack 前端（串流與事件驅動）](./references/adk-agent-samples/gemini-fullstack/frontend/index.html)
        - [FastAPI 範例（事件串流與 Runner 整合）](./references/adk-agent-samples/personal-expense-assistant-adk/backend.py)

- **[ ] 2.4. 測試覆蓋率提升**:
    - **任務**: 為所有在 Phase 1 和 Phase 2 中實現的核心模組與工具增加單元測試與整合測試，目標覆蓋率 > 80%。
    - **相關子任務**:
        - [ ] **SRE Assistant Python 服務測試**: 各診斷工具的單元測試。
        - [ ] **Control Plane Go 服務測試**: Handler 層, Service 層, Client 層, 整合測試。
    - **參考**:
        - **SRE 理論 - 可靠性測試**: [`docs/references/google-sre-book/Chapter-17-Testing-for-Reliability.md`](./references/google-sre-book/Chapter-17-Testing-for-Reliability.md)
        - **ADK 官方指南**: [`docs/references/adk-docs/get-started-testing.md`](./references/adk-docs/get-started-testing.md)
        - **專案結構範本**: [`docs/references/agent-starter-pack/tests/`](./references/agent-starter-pack/tests/)
    - 補充參考（ADK 最佳實踐）:
        - [測試入門 | ADK 文件](./references/adk-docs/get-started-testing.md)
        - [HelloWorld 代理測試（程式碼）](./references/adk-agent-samples/helloworld/test_client.py)
        - [LangGraph 範例測試（程式碼）](./references/adk-agent-samples/langgraph/app/test_client.py)

- **[ ] 2.5. 建立串流式前端資料模型 (Create Streaming Frontend Data Model)**:
    - **任務**: 根據 `gemini-fullstack` 範例，為前端定義一個能夠處理來自 `sre-assistant` 串流事件的資料模型。此模型應能區分不同的事件類型 (如 `tool_call`, `thought`, `final_result`) 並在 UI 中呈現一個豐富的、即時的活動時間軸。
    - **前置條件**: Phase 2.1 診斷後端邏輯完成
    - **相關子任務**:
        - [ ] 定義前端事件資料模型 (Event Types, Streaming States)
        - [ ] 實作事件處理器 (Event Handlers for tool_call, thought, final_result)
        - [ ] 建立即時活動時間軸組件 (Real-time Activity Timeline Component)
        - [ ] 整合 WebSocket 或 SSE 連接管理
    - **參考**:
        - **核心範本**: [`docs/references/adk-agent-samples/gemini-fullstack/frontend/src/App.tsx`](./references/adk-agent-samples/gemini-fullstack/frontend/src/App.tsx)
        - **串流概念**: [`docs/references/adk-docs/get-started-streaming.md`](./references/adk-docs/get-started-streaming.md)
    - 補充參考（ADK 最佳實踐）:
        - [串流入門 | ADK 文件](./references/adk-docs/get-started-streaming.md)
        - [ADK Runner 串流事件處理（後端程式碼）](./references/adk-agent-samples/personal-expense-assistant-adk/backend.py)
        - [瀏覽器端串流管理（JS）](./references/adk-agent-samples/navigoAI_voice_agent_adk/client/stream_manager.js)

---

## Phase 3: 聯邦化與主動預防 (Federation & Proactive Prevention)

- **主題**: 將 `sre-assistant` 從單一代理演進為多代理協同的聯邦化系統，並具備預測性維護能力。
- **關鍵目標**: 實現從「被動響應」到「主動預防」的轉變。

### 主要交付物 (Key Deliverables):

- **[ ] 3.1. 實現增強型 SRE 工作流程**:
    - **任務**: 根據 `salvaged_code.md` 中的 `EnhancedSREWorkflow` 範例，重構現有的 `SREWorkflow`，引入 `SequentialAgent`, `ParallelAgent` 等 ADK 標準模式。
    - **參考**:
        - **核心架構**: [`docs/references/adk-architecture/adk-components.png`](./references/adk-architecture/adk-components.png)
        - **官方文件**: [`docs/references/adk-docs/agents-multi-agents.md`](./references/adk-docs/agents-multi-agents.md)
        - **高級模式 (對抗性)**: [`docs/references/adk-agent-samples/any_agent_adversarial_multiagent/`](./references/adk-agent-samples/any_agent_adversarial_multiagent/)
    - 補充參考（ADK 最佳實踐）:
        - [多代理架構 | ADK 文件](./references/adk-docs/agents-multi-agents.md)
        - [子代理範例（Subagent）](./references/adk-agent-samples/google-adk-workflows/subagent.py)
        - [對抗式多代理範例](./references/adk-agent-samples/any_agent_adversarial_multiagent/README.md)

- **[ ] 3.2. 第一個專業化子代理**:
    - **任務**: 將一項核心功能（如覆盤報告生成）重構為一個獨立的、可透過 A2A (Agent-to-Agent) 協議呼叫的 `PostmortemAgent`。
    - **參考**:
        - **官方介紹**: [`docs/references/adk-docs/a2a.md`](./references/adk-docs/a2a.md)
        - **底層協議**: [`docs/references/adk-docs/mcp.md`](./references/adk-docs/mcp.md)
        - **安全通訊範例**: [`docs/references/adk-examples/a2a_auth/`](./references/adk-examples/a2a_auth/)
    - 補充參考（ADK 最佳實踐）:
        - [A2A 代理到代理協議 | ADK 文件](./references/adk-docs/a2a.md)
        - [模型上下文協議（MCP） | ADK 文件](./references/adk-docs/mcp.md)
        - [A2A 基礎範例（程式碼）](./references/adk-examples/a2a_basic/agent.py)

- **[ ] 3.3. 主動預防能力**:
    - **任務**: 整合機器學習模型，用於異常檢測和趨勢預測。
    - **參考**:
        - **SRE 理論 - 自動化演進**: [`docs/references/google-sre-book/Chapter-07-The-Evolution-of-Automation-at-Google.md`](./references/google-sre-book/Chapter-07-The-Evolution-of-Automation-at-Google.md)
        - **實作範本 (機器學習)**: [`docs/references/adk-agent-samples/machine-learning-engineering/`](./references/adk-agent-samples/machine-learning-engineering/)
        - **實作範本 (綜合 SRE Bot)**: [`docs/references/adk-agent-samples/sre-bot/`](./references/adk-agent-samples/sre-bot/)
    - 補充參考（ADK 最佳實踐）:
        - [機器學習工程範例（README）](./references/adk-agent-samples/machine-learning-engineering/README.md)
        - [機器學習工程範例（Agent 程式碼）](./references/adk-agent-samples/machine-learning-engineering/machine_learning_engineering/agent.py)
        - [SRE Bot 範例（README）](./references/adk-agent-samples/sre-bot/README.md)

- **[ ] 3.4. 代理可觀測性**:
    - **任務**: 建立一個完善的 LLM 可觀測性儀表板，用於追蹤代理的決策過程、成本和性能。
    - **相關子任務**:
        - [ ] **實作 Prometheus Metrics**: API 請求次數和延遲指標, 診斷任務成功/失敗率等。
        - [ ] **實作結構化日誌**: 統一日誌格式 (JSON), 添加 TraceID 支援。
    - **參考**:
        - **SRE 理論 - 監控**: [`docs/references/google-sre-book/Chapter-06-Monitoring-Distributed-Systems.md`](./references/google-sre-book/Chapter-06-Monitoring-Distributed-Systems.md)
        - **核心模式 (回呼)**: [`docs/references/adk-docs/callbacks-design-patterns-and-best-practices.md`](./references/adk-docs/callbacks-design-patterns-and-best-practices.md)
        - **雲端整合**: [`docs/references/adk-docs/observability-cloud-trace.md`](./references/adk-docs/observability-cloud-trace.md)
    - 補充參考（ADK 最佳實踐）:
        - [Observability - 結構化日誌 | ADK 文件](./references/adk-docs/observability-logging.md)
        - [Observability - Cloud Trace | ADK 文件](./references/adk-docs/observability-cloud-trace.md)
        - [Callbacks 設計模式 | ADK 文件](./references/adk-docs/callbacks-design-patterns-and-best-practices.md)

---

## Phase 4: 架構重構與最佳實踐 (Architectural Refactoring & Best Practices)

- **主題**: 根據 ADK 官方最佳實踐，對現有程式碼庫進行重構。
- **關鍵目標**: 償還現有技術債，並將架構升級到符合 Google SRE 和 ADK 團隊推薦的標準模式。

### 主要交付物 (Key Deliverables):

- **[ ] 4.1. 性能優化與安全增強**:
    - **任務**: 實現連線池、API 限流和審計日誌。
    - **相關子任務 (性能)**:
        - [ ] **實作連線池**: HTTP 客戶端, 資料庫, Redis。
        - [ ] **實作快取策略**: 查詢結果, 元資料, 會話。
    - **相關子任務 (安全)**:
        - [ ] **實作 API 限流**: 基於 IP 和用戶。
        - [ ] **實作審計日誌**: 記錄所有 API 調用和敏感操作。
    - 補充參考（ADK 最佳實踐）:
        - [AgentOps 可觀測性 | ADK 文件](./references/adk-docs/observability-agentops.md)
        - [Observability - 結構化日誌 | ADK 文件](./references/adk-docs/observability-logging.md)
        - [工具認證與安全 | ADK 文件](./references/adk-docs/tools-authentication.md)

- **[ ] 4.2. 清理技術債 (Clean Up Technical Debt)**:
    - **任務**: 解決程式碼庫中的小問題：
    1. 刪除重複的 `tools/workflow.py` 檔案。
    2. 完整實現 `main.py` 中的健康檢查 (`check_database`, `check_redis`)。
    3. 將 `main.py` 中的認證邏輯重構到獨立的模組中。
    - **參考**:
        - **專案結構**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
        - **SRE 理論 - 消除瑣事**: [`docs/references/google-sre-book/Chapter-05-Eliminating-Toil.md`](./references/google-sre-book/Chapter-05-Eliminating-Toil.md)
    - 補充參考（ADK 最佳實踐）:
        - [Headless Agent 認證中介層（OAuth2 Middleware）](./references/adk-agent-samples/headless_agent_auth/oauth2_middleware.py)
        - [FastAPI + ADK Runner 實作（包含健康檢查與壽命）](./references/adk-agent-samples/personal-expense-assistant-adk/backend.py)
        - [ADK 入門與專案結構 | ADK 文件](./references/adk-docs/get-started-about.md)

- **[ ] 4.3. 建立 CI/CD 管道 (Establish CI/CD Pipeline)**:
    - **任務**: 建立完整的持續整合和持續部署管道，包含自動化測試、建置、部署和監控。
    - **前置條件**: Phase 2.4 測試覆蓋率提升完成
    - **相關子任務**:
        - [ ] 設定 GitHub Actions 或 GitLab CI 工作流
        - [ ] 實作自動化單元測試和整合測試
        - [ ] 設定自動建置和容器化 (Docker)
        - [ ] 實作自動部署到測試/生產環境
        - [ ] 建立部署回滾機制
        - [ ] 整合監控和告警通知
    - **參考**:
        - **SRE 理論 - 持續部署**: [`docs/references/google-sre-book/Chapter-07-The-Evolution-of-Automation-at-Google.md`](./references/google-sre-book/Chapter-07-The-Evolution-of-Automation-at-Google.md)
        - **專案範本**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
    - 補充參考（ADK 最佳實踐）:
        - [ADK 專案結構與部署 | ADK 文件](./references/adk-docs/get-started-about.md)

- **[ ] 4.4. 增強 ControlPlaneTool (Enhance ControlPlaneTool)**:
    - **任務**: 將 `ControlPlaneTool` 重構為一個功能完整的工具集。
        1.為所有輸入和輸出定義 Pydantic 模型。
        2.返回結構化的成功/錯誤回應。
        3.增加寫入/修改操作，例如 `restart_deployment`, `acknowledge_alert` 等，使其不僅僅是唯讀的。
    - **參考**:
        - **工具集結構**: [`docs/references/adk-agent-samples/github-agent/github_toolset.py`](./references/adk-agent-samples/github-agent/github_toolset.py)
        - **工具設計指南**: [`docs/references/adk-docs/tools-overview.md`](./references/adk-docs/tools-overview.md)
    - 補充參考（ADK 最佳實踐）:
        - [工具總覽與設計 | ADK 文件](./references/adk-docs/tools-overview.md)
        - [Function Tools 設計 | ADK 文件](./references/adk-docs/tools-function-tools.md)

---

## 📈 KPI 追蹤

| 指標 | 當前狀態 | 目標 | 測量方式 |
|------|---------|------|----------|
| API 合規性 | 70% | 100% | OpenAPI 契約測試 |
| 測試覆蓋率 | ~10% | 80% | Coverage 工具 |
| P99 延遲 | N/A | <500ms | APM 監控 |
| 錯誤率 | N/A | <0.1% | 錯誤監控 |
| 可用性 | N/A | 99.9% | 正常運行時間監控 |

### 業務指標
- [x] **API 完整性** (第1週) ✅
  - SRE Assistant: 10/11 個端點已實作 (91%) - 缺少 `/api/v1/metrics`
  - Control Plane: 24/49 個端點已實作 (49%) - 使用模擬數據實現
- [ ] **MVP 功能完成** (第4週)
  - 核心診斷功能可用
  - 基本 UI 可操作
  - 工具實際實作完成
- [ ] **Beta 版本發布** (第8週)
  - 性能達標
  - 基本監控完善
  - 主要 bug 修復
- [ ] **生產就緒** (第12週)
  - 安全檢查通過
  - 壓力測試通過
  - 文檔完整

---

## ⚠️ 風險管控

### 高風險項目監控
- [ ] **技術複雜度管控**
  - 每週技術債務評估
  - 代碼複雜度監控
  - 依賴關係管理
- [ ] **外部依賴風險**
  - 外部服務 SLA 監控
  - 備用方案準備
  - 降級策略測試

---

## 已完成項目歸檔

### ✅ 第一週完成項目
1. **SRE Assistant API 實作** - 91% 完成 (10/11 個端點) - 缺少 `/api/v1/metrics`
2. **資料模型定義** - 關鍵資料模型已定義並對齊 OpenAPI
3. **任務持久化** - Redis 存儲已實作，24 小時過期
4. **環境變數配置** - 基本的配置管理已完成
5. **服務間認證** - JWT 驗證邏輯已實作
6. **核心工具開發** - Prometheus, Loki, ControlPlane 工具已實作

### ⚠️ 需要修正的項目狀態
- **SRE Assistant**: 缺少 `/api/v1/metrics` 端點實現
- **Control Plane**: 25個端點使用模擬數據，需要連接真實資料庫
- **測試覆蓋率**: 約 10% (遠低於 80% 目標)
- **資料庫架構**: 需要建立完整的 PostgreSQL schema 和 migration
- **業務邏輯**: 需要將模擬實現替換為真實的業務邏輯
