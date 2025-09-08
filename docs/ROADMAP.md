# SRE Platform - 開發路線圖與任務清單

> **基於**: SRE Platform 專案全面審查報告 (2025-09-05)
> **當前專案成熟度**: 75/100
> **目標**: 在12週內達到生產就緒狀態
>
> **總覽**: 本文件是 SRE Platform 專案的**唯一真實來源 (Single Source of Truth)**，用於追蹤所有開發任務。它根據架構設計的階段進行組織，並整合了所有新功能、重構計畫和已知的技術債。

---

## 綜合審查修正建議（Audit Fixes）

最後更新：2025-09-07

### 本次更新摘要
- 已完成
  - SRE Assistant：/api/v1/healthz、/api/v1/readyz、/api/v1/metrics 端點對齊 OpenAPI（就緒 checks 僅含 prometheus/loki/control_plane）
  - SRE Assistant：control_plane.base_url 預設改為 /api/v1，避免下游 404
  - Control Plane：/api/v1/healthz、/api/v1/readyz、/api/v1/metrics 端點已新增（最小可用）
  - Control Plane：/api/v1/dashboard/trends 與 /api/v1/dashboard/resource-distribution 已最小實作，回覆結構對齊 OpenAPI
  - Control Plane：Cookie/Session 金鑰改為環境變數（CONTROL_PLANE_SESSION_KEY）
- 待辦
  - 工具層單元測試與錯誤分類補齊（Prometheus/Loki/ControlPlaneTool）
  - 契約回歸測試與 CI 整合（make test 聚合兩服務的契約測試）

### 1) 高優先度（本週內）
- [x] SRE Assistant：/api/v1/healthz（HealthStatus）
- [x] SRE Assistant：/api/v1/readyz（ReadinessStatus：checks=prometheus/loki/control_plane）
- [x] SRE Assistant：/api/v1/metrics（text/plain; Prometheus exposition format）
- [x] SRE Assistant：control_plane.base_url → http://localhost:8081/api/v1
- [x] 工具層錯誤處理分類與統一 ToolError（httpx HTTPStatusError/Timeout/ConnectError）
- [x] 工具層單元測試（成功/超時/例外/快取命中）
- [x] Control Plane：/api/v1/healthz、/api/v1/readyz、/api/v1/metrics
- [x] Control Plane：/api/v1/dashboard/trends、/api/v1/dashboard/resource-distribution（最小實作）
- [x] Control Plane：Cookie/Session 金鑰改為環境變數（CONTROL_PLANE_SESSION_KEY）

### 2) 中優先度（2–3 週）
- [x] 結構化日誌一致性：
  - [x] Python：structlog/python-json-logger + Request/Trace ID 中介層
  - Go：RequestID middleware + otelzap JSON 欄位一致
- [x] HTTP 逾時/重試/連線池策略統一（httpx / net/http）
- [ ] ControlPlaneTool 唯讀能力覆蓋（resources/resource-groups/audit-logs/incidents/alert-rules/automation/executions）並以 Pydantic 驗證
- [ ] 測試覆蓋 ≥ 60%（第一階段）與 E2E：部署診斷 202→輪詢→完成

### 3) 低優先度（4–6 週）
- [ ] 修復 Control Plane Tracer 依賴並恢復 OTel Trace；與 SRE Assistant 串接 trace-id
- [ ] 限流與安全加固（IP/使用者限流；SCA/SAST 納入 CI）
- [ ] 由 OpenAPI 生成內部 SDK（避免 client 漂移）

### 驗收標準（Definition of Done）
- 路徑/方法/狀態碼/Content-Type/基本鍵值 與 pkg/api/*.yaml 一致
- 新增/調整端點皆有對應測試：單元（成功/錯誤/超時）、契約（狀態碼/型別）、必要時 E2E
- 服務提供 GET /api/v1/metrics 可被 Prometheus 抓取
- 日誌具備 request_id/trace_id，為 JSON 結構化
- CI 綠燈（含契約測試）

### 參考（本地文件）
- OpenAPI 與測試：docs/references/adk-docs/tools-openapi-tools.md、docs/references/adk-docs/get-started-testing.md
- 認證與安全：docs/references/adk-docs/tools-authentication.md、docs/references/adk-agent-samples/headless_agent_auth/
- 工作流：docs/references/adk-docs/agents-workflow-agents-parallel-agents.md、docs/references/adk-agent-samples/google-adk-workflows/
- 觀測性：docs/references/adk-docs/observability-logging.md、docs/references/adk-docs/observability-cloud-trace.md

## Phase 1: 核心整合 (Core Integration)

- **主題**: 專注於完成 `sre-assistant` 與 `control-plane` 之間的所有技術對接工作，確保兩者能夠安全、可靠地協同工作。
- **關鍵目標**: 實現一個可由 `control-plane` 觸發並完成端到端診斷流程的最小可行產品 (MVP)。

### 主要交付物 (Key Deliverables):

- **[✅] 1.1. API 契約符合性 (API Contract Compliance)**:
    - **任務**: 確保所有服務嚴格遵守其 OpenAPI 規範。
    - **當前狀態**:
        - ✅ **SRE Assistant: 100% 完成** (所有端點路徑、參數、格式均符合 `sre-assistant-openapi.yaml`)
        - ✅ **Control Plane: 100% 健康檢查符合性** (3/3 個健康檢查端點的路徑與格式已修正)
    - **相關子任務**:
        - [x] **Control Plane**: 修正 `/healthz`, `/readyz` 的路徑與響應格式。
        - [x] **Control Plane**: 新增缺失的 `/api/v1/metrics` 端點。
        - [x] **SRE Assistant**: 將 `{session_id}` 路徑參數修正為 `{sessionId}`。
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
    - **當前狀態**: 工具代碼已存在且包含真實 HTTP 請求邏輯 (非模擬數據)。`ControlPlaneTool` 已引入 Pydantic 模型進行資料驗證。
    - **子任務 (PrometheusQueryTool)**:
        - [x] 實作實際的 Prometheus 查詢邏輯 (已完成)
        - [x] 移除模擬資料，使用真實 API 調用 (已完成)
        - [x] **添加查詢優化和錯誤處理**: 已重構錯誤處理，使其更穩健並返回結構化錯誤。
        - [x] **實作查詢結果快取機制**: 已驗證並啟用 Redis 快取，以減少對 Prometheus 的重複查詢。
    - **子任務 (LokiLogQueryTool)**:
        - [x] 實作動態查詢參數設定 (已完成)
        - [x] **添加完整的錯誤處理機制**: 已重構錯誤處理，使其更穩健並返回結構化錯誤。
        - [x] **實作日誌過濾和聚合功能**: 已驗證工具內建的過濾與客戶端聚合分析功能。
    - **子任務 (ControlPlaneTool)**:
        - [x] **查詢資源狀態 (`GET /api/v1/resources`)**: 已實現，並引入 Pydantic 模型進行結構化錯誤處理。
        - [x] **獲取資源詳情 (`GET /api/v1/resources/{resourceId}`)**: 已實現，並引入 Pydantic 模型進行結構化錯誤處理。
        - [x] **查詢資源群組 (`GET /api/v1/resource-groups`)**: 已實現，並引入 Pydantic 模型進行結構化錯誤處理。
        - [x] **查詢部署相關的審計日誌 (`GET /api/v1/audit-logs`)**: 已整合至 `_diagnose_deployment` 工作流程。
        - [x] **查詢相關事件 (`GET /api/v1/incidents`)**: 已整合至 `_diagnose_deployment` 工作流程。
        - [x] **獲取告警規則狀態 (`GET /api/v1/alert-rules`)**: 已實現，並引入 Pydantic 模型進行結構化錯誤處理。
        - [x] **查詢自動化腳本執行歷史 (`GET /api/v1/automation/executions`)**: 已實現，並引入 Pydantic 模型進行結構化錯誤處理。
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
        - [x] **API 整合測試**: 端到端診斷流程測試, 非同步任務狀態追蹤測試, 錯誤情境測試。 (註：`test_diagnose_deployment_success_e2e` 和 `test_async_task_status_polling` 等測試已新增並通過。)
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

- **[🚧] 2.1. 實現診斷後端邏輯**:
    - **任務**: 完整實現 `SREWorkflow` 中的 `_diagnose_alerts`, `_analyze_capacity`, `_execute_query` 方法。
    - **對應 API**: `/diagnostics/alerts`, `/diagnostics/capacity`, `/execute`
    - **相關子任務**:
        - [x] **實現告警診斷工作流程 (`_diagnose_alerts`)**: 已實現核心邏輯並添加單元測試。
        - [ ] **實現容量分析工作流程 (`_analyze_capacity`)**
        - [ ] **實現自然語言查詢工作流程 (`_execute_query`)**
    - **注意事項**:
        - `test_integration.py` 中有兩個測試 (`test_access_protected_endpoint_with_bad_token`, `test_loki_query_integration`) 因環境問題暫時跳過，待後續修復。
    - **參考**:
        - **基本工作流**: [`docs/references/adk-examples/workflow_triage/agent.py`](./references/adk-examples/workflow_triage/agent.py)
        - **高級模式 (帶自我校驗)**: [`docs/references/adk-agent-samples/google-adk-workflows/self_critic/`](./references/adk-agent-samples/google-adk-workflows/self_critic/)
        - **SRE 理論 - 事件響應**: [`docs/references/google-sre-book/Chapter-13-Emergency-Response.md`](./references/google-sre-book/Chapter-13-Emergency-Response.md)
        - **SRE 理論 - 事後剖析**: [`docs/references/google-sre-book/Chapter-15-Postmortem-CultureLearning-from-Failure.md`](./references/google-sre-book/Chapter-15-Postmortem-CultureLearning-from-Failure.md)
    - 補充參考（ADK 最佳實踐）:
        - [工作流代理總覽 | ADK 文件](./references/adk-docs/agents-workflow-agents.md)
        - [序列式工作流代理 | ADK 文件](./references/adk-docs/agents-workflow-agents-sequential-agents.md)
        - [Dispatcher 工作流範例（程式碼）](./references/adk-agent-samples/google-adk-workflows/dispatcher/agent.py)

- **[ ] 2.2. Control Plane Go 服務完善**:
    - **任務**: 實現 Control Plane 的真實業務邏輯，取代所有模擬資料。
    - **相關子任務**:
        - [ ] 實作實際的業務邏輯（非模擬資料）
        - [ ] 完成批次操作功能
        - [ ] 實作與 SRE Assistant 的完整整合
    - **進度更新（2025-09-07）**:
        - 已補齊儀表板端點：`GET /api/v1/dashboard/trends`、`GET /api/v1/dashboard/resource-distribution`（最小版，回覆結構已對齊 OpenAPI）
    - **參考**:
        - **全端架構範本**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
        - **前端實作參考**: [`docs/references/adk-agent-samples/gemini-fullstack/frontend/`](./references/adk-agent-samples/gemini-fullstack/frontend/)
        - **後端 API 文件**: [`docs/references/adk-docs/api-reference.md`](./references/adk-docs/api-reference.md)
    - 補充參考（ADK 最佳實踐）:
        - [ADK API 參考 | ADK 文件](./references/adk-docs/api-reference.md)
        - [Gemini Fullstack 前端（串流與事件驅動）](./references/adk-agent-samples/gemini-fullstack/frontend/index.html)
        - [FastAPI 範例（事件串流與 Runner 整合）](./references/adk-agent-samples/personal-expense-assistant-adk/backend.py)

- **[ ] 2.3. 測試覆蓋率提升**:
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

- **[ ] 2.4. 建立串流式前端資料模型 (Create Streaming Frontend Data Model)**:
    - **任務**: 根據 `gemini-fullstack` 範例，為前端定義一個能夠處理來自 `sre-assistant` 串流事件的資料模型。此模型應能區分不同的事件類型 (如 `tool_call`, `thought`, `final_result`) 並在 UI 中呈現一個豐富的、即時的活動時間軸。
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

- **[ ] 4.2. 從 OpenAPI 自動生成客戶端**:
    - **任務**: 從 `pkg/api/control-plane-openapi.yaml` 自動生成 Go 客戶端程式碼。
    - **參考**:
        - **ADK OpenAPI 工具**: [`docs/references/adk-docs/tools-openapi.md`](./references/adk-docs/tools-openapi.md)
        - **Go Code Gen (外部參考)**: `https://github.com/deepmap/oapi-codegen`
    - 補充參考（ADK 最佳實踐）:
        - [OpenAPI 工具指南 | ADK 文件](./references/adk-docs/tools-openapi-tools.md)
        - [OpenAPI 工具範例（程式碼片段）](./references/snippets/tools/openapi_tool.py)

- **[🚧] 4.3. 清理技術債 (Clean Up Technical Debt)**:
    - **任務**: 解決程式碼庫中的小問題：1) 刪除重複的 `tools/workflow.py` 檔案。2) 完整實現 `main.py` 中的健康檢查 (`check_database`, `check_redis`)。3) 將 `main.py` 中的認證邏輯重構到獨立的模組中。
    - **相關子任務**:
        - [ ] 刪除重複的 `tools/workflow.py`
        - [x] **健康檢查 (`/readyz`)**:
            - [x] 實現對 Redis 的即時連線檢查
            - [x] 實現對 Database 的連線檢查
        - [x] 將認證邏輯重構到獨立模組
    - **參考**:
        - **專案結構**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
        - **SRE 理論 - 消除瑣事**: [`docs/references/google-sre-book/Chapter-05-Eliminating-Toil.md`](./references/google-sre-book/Chapter-05-Eliminating-Toil.md)
    - 補充參考（ADK 最佳實踐）:
        - [Headless Agent 認證中介層（OAuth2 Middleware）](./references/adk-agent-samples/headless_agent_auth/oauth2_middleware.py)
        - [FastAPI + ADK Runner 實作（包含健康檢查與壽命）](./references/adk-agent-samples/personal-expense-assistant-adk/backend.py)
        - [ADK 入門與專案結構 | ADK 文件](./references/adk-docs/get-started-about.md)

- **[ ] 4.4. 增強 ControlPlaneTool (Enhance ControlPlaneTool)**:
    - **任務**: 將 `ControlPlaneTool` 重構為一個功能完整的工具集。1) 為所有輸入和輸出定義 Pydantic 模型。2) 返回結構化的成功/錯誤回應。3) 增加寫入/修改操作，例如 `restart_deployment`, `acknowledge_alert` 等，使其不僅僅是唯讀的。
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
| API 合規性 | 71% | 100% | OpenAPI 契約測試 & 手動審查 |
| 測試覆蓋率 | ~25% | 80% | Coverage 工具 (預估) |
| P99 延遲 | N/A | <500ms | APM 監控 |
| 錯誤率 | N/A | <0.1% | 錯誤監控 |
| 可用性 | N/A | 99.9% | 正常運行時間監控 |

### 業務指標
- [x] **API 完整性** (第1週) ✅
  - 所有 SRE Assistant 端點已實作
  - Control Plane 健康檢查端點已實作
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

## ✅ 已完成項目歸檔 (Archive of Completed Items)

### Phase 1: 核心整合
- **1.1 API 契約符合性**:
    - SRE Assistant: 所有端點 (11/11) 的路徑、參數、格式均已符合 OpenAPI 規範。
    - Control Plane: 健康檢查相關端點 (3/3) 的路徑與響應格式已修正。
- **1.2 服務對服務認證**:
    - 已完整實現基於 Keycloak 和 JWT 的 M2M 認證機制。
- **1.3 核心工具開發**:
    - `ControlPlaneTool`: 所有唯讀方法均已實現，並引入 Pydantic 模型進行結構化錯誤處理。
    - `PrometheusQueryTool`: 已重構錯誤處理，並驗證了 Redis 快取機制。
- **1.4 端到端流程實作與測試**:
    - `asyncio.gather` 錯誤處理已修復。
    - 核心 E2E 測試 (`test_diagnose_deployment_success_e2e`) 已修復並能穩定通過。
    - 已新增非同步任務狀態輪詢測試 (`test_async_task_status_polling`)。
- **1.5 核心服務本地化與持久化**:
    - 已實現基於 Redis 的任務狀態持久化。
    - 已將硬編碼的 URL 移至環境變數。
- **4.3 清理技術債**:
    - `/readyz` 健康檢查已增強，包含對 Redis 的即時連線檢查。
