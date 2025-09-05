# SRE Platform - 開發路線圖

## 總覽

本文件是 SRE Platform 專案的**唯一真實來源 (Single Source of Truth)**，用於追蹤所有開發任務。它根據架構設計的階段進行組織，並整合了所有新功能、重構計畫和已知的技術債。

---

## Phase 1: 核心整合 (Core Integration)

- **主題**: 專注於完成 `sre-assistant` 與 `control-plane` 之間的所有技術對接工作，確保兩者能夠安全、可靠地協同工作。
- **關鍵目標**: 實現一個可由 `control-plane` 觸發並完成端到端診斷流程的最小可行產品 (MVP)。

### 主要交付物 (Key Deliverables):

- **[✅] 1.1. API 契約符合性 (API Contract Compliance)**:
    - **任務**: 確保 `sre-assistant` 的 FastAPI 服務嚴格遵守 `openapi.yaml` 中定義的所有端點、請求格式和回應格式。

- **[✅] 1.2. 服務對服務認證 (M2M Authentication)**:
    - **任務**: 完整實現基於 Keycloak 和 Client Credentials Flow 的認證機制。
    - **參考**: `docs/reference-adk-examples.md` (oauth_calendar_agent)

- **[✅] 1.3. 核心工具開發 (`Prometheus`, `Loki`, `ControlPlane`)**:
    - **任務**: 實現 `PrometheusQueryTool`、`LokiLogQueryTool` 和 `ControlPlaneTool`，為診斷流程提供數據來源。
    - **對應 API**: 這些工具是 `/diagnostics/deployment` 端點的基礎。
    - **參考**: `docs/reference-adk-examples.md` (jira_agent, bigquery)

- **[✅] 1.4. 端到端流程實作與測試**:
    - **任務**: 在 `SREWorkflow` 中整合所有核心工具，並建立一個完整的整合測試，以驗證 `/diagnostics/deployment` 的端到端流程。
    - **對應 API**: `/diagnostics/deployment`。
    - **參考**: `docs/reference-adk-examples.md` (parallel_functions, workflow_agent_seq)

- **[✅] 1.5. 核心服務本地化與持久化**:
    - **任務**: 確保開發環境使用 PostgreSQL 作為會話後端，ChromaDB 作為記憶體後端，並能穩定啟動與互動。
    - **參考**: `docs/reference-adk-examples.md` (history_management, session_state_agent)

---

## Phase 2: Control Plane 功能擴展與 UI 整合

- **主題**: 專注於擴充 `sre-assistant` 的後端能力，並為這些能力在 `control-plane` 上提供對應的 UI 操作介面。
- **關鍵目標**: 讓使用者能夠透過 UI 觸發 `sre-assistant` 的各項核心診斷功能。

### 主要交付物 (Key Deliverables):

- **[ ] 2.1. 實現告警診斷後端邏輯**:
    - **任務**: 完整實現 `SREWorkflow` 中的 `_diagnose_alerts` 方法，使其能夠處理來自 UI 的告警分析請求。
    - **對應 API**: `/diagnostics/alerts`
    - **參考**:
        - **基本工作流**: [`docs/references/adk-examples/workflow_triage/agent.py`](./references/adk-examples/workflow_triage/agent.py)
        - **高級模式 (帶自我校驗)**: [`docs/references/adk-agent-samples/google-adk-workflows/self_critic/`](./references/adk-agent-samples/google-adk-workflows/self_critic/)
        - **SRE 理論 - 事件響應**: [`docs/references/google-sre-book/Chapter-13-Emergency-Response.md`](./references/google-sre-book/Chapter-13-Emergency-Response.md)
        - **SRE 理論 - 事後剖析**: [`docs/references/google-sre-book/Chapter-15-Postmortem-CultureLearning-from-Failure.md`](./references/google-sre-book/Chapter-15-Postmortem-CultureLearning-from-Failure.md)

- **[ ] 2.2. 實現容量分析後端邏輯**:
    - **任務**: 為 `SREWorkflow` 新增容量分析的邏輯，使其能夠根據請求執行容量規劃計算。
    - **對應 API**: `/capacity/analyze`
    - **參考**:
        - **實作範本 (數據科學)**: [`docs/references/adk-agent-samples/data-science/`](./references/adk-agent-samples/data-science/)
        - **SRE 理論 - 容量規劃**: [`docs/references/google-sre-book/Chapter-22-Addressing-Cascading-Failures.md`](./references/google-sre-book/Chapter-22-Addressing-Cascading-Failures.md)
        - **相關程式碼片段**: [`docs/references/snippets/salvaged_code.md`](./references/snippets/salvaged_code.md) (SLO 錯誤預算計算邏輯)

- **[ ] 2.3. 實現通用查詢後端邏輯**:
    - **任務**: 整合語言模型，使 `/execute` 端點能夠理解更廣泛的自然語言查詢。
    - **對應 API**: `/execute`
    - **參考**:
        - **核心模式 (工具箱)**: [`docs/references/adk-examples/toolbox_agent/`](./references/adk-examples/toolbox_agent/)
        - **官方文件**: [`docs/references/adk-docs/tools-overview.md`](./references/adk-docs/tools-overview.md)
        - **基礎範例**: [`docs/references/adk-examples/adk_triaging_agent/agent.py`](./references/adk-examples/adk_triaging_agent/agent.py)

- **[ ] 2.4. Control Plane UI 開發**:
    - **任務**: 在 Control Plane (Go 服務) 的前端頁面中，為上述三個端點提供對應的觸發介面（例如，按鈕、表單）。
    - **參考**:
        - **全端架構範本**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
        - **前端實作參考**: [`docs/references/adk-agent-samples/gemini-fullstack/frontend/`](./references/adk-agent-samples/gemini-fullstack/frontend/)
        - **後端 API 文件**: [`docs/references/adk-docs/api-reference.md`](./references/adk-docs/api-reference.md)

- **[ ] 2.5. 測試覆蓋率提升**:
    - **任務**: 為所有在 Phase 1 和 Phase 2 中實現的核心模組與工具增加單元測試與整合測試，目標覆蓋率 > 80%。
    - **參考**:
        - **SRE 理論 - 可靠性測試**: [`docs/references/google-sre-book/Chapter-17-Testing-for-Reliability.md`](./references/google-sre-book/Chapter-17-Testing-for-Reliability.md)
        - **ADK 官方指南**: [`docs/references/adk-docs/get-started-testing.md`](./references/adk-docs/get-started-testing.md)
        - **專案結構範本**: [`docs/references/agent-starter-pack/tests/`](./references/agent-starter-pack/tests/)

- **[ ] 2.6. 建立串流式前端資料模型 (Create Streaming Frontend Data Model)**:
    - **任務**: 根據 `gemini-fullstack` 範例，為前端定義一個能夠處理來自 `sre-assistant` 串流事件的資料模型。此模型應能區分不同的事件類型 (如 `tool_call`, `thought`, `final_result`) 並在 UI 中呈現一個豐富的、即時的活動時間軸。
    - **參考**:
        - **核心範本**: [`docs/references/adk-agent-samples/gemini-fullstack/frontend/src/App.tsx`](./references/adk-agent-samples/gemini-fullstack/frontend/src/App.tsx)
        - **串流概念**: [`docs/references/adk-docs/get-started-streaming.md`](./references/adk-docs/get-started-streaming.md)

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

- **[ ] 3.2. 第一個專業化子代理**:
    - **任務**: 將一項核心功能（如覆盤報告生成）重構為一個獨立的、可透過 A2A (Agent-to-Agent) 協議呼叫的 `PostmortemAgent`。
    - **參考**:
        - **官方介紹**: [`docs/references/adk-docs/a2a.md`](./references/adk-docs/a2a.md)
        - **底層協議**: [`docs/references/adk-docs/mcp.md`](./references/adk-docs/mcp.md)
        - **安全通訊範例**: [`docs/references/adk-examples/a2a_auth/`](./references/adk-examples/a2a_auth/)

- **[ ] 3.3. 主動預防能力**:
    - **任務**: 整合機器學習模型，用於異常檢測和趨勢預測。
    - **參考**:
        - **SRE 理論 - 自動化演進**: [`docs/references/google-sre-book/Chapter-07-The-Evolution-of-Automation-at-Google.md`](./references/google-sre-book/Chapter-07-The-Evolution-of-Automation-at-Google.md)
        - **實作範本 (機器學習)**: [`docs/references/adk-agent-samples/machine-learning-engineering/`](./references/adk-agent-samples/machine-learning-engineering/)
        - **實作範本 (綜合 SRE Bot)**: [`docs/references/adk-agent-samples/sre-bot/`](./references/adk-agent-samples/sre-bot/)

- **[ ] 3.4. 代理可觀測性**:
    - **任務**: 建立一個完善的 LLM 可觀測性儀表板，用於追蹤代理的決策過程、成本和性能。
    - **參考**:
        - **SRE 理論 - 監控**: [`docs/references/google-sre-book/Chapter-06-Monitoring-Distributed-Systems.md`](./references/google-sre-book/Chapter-06-Monitoring-Distributed-Systems.md)
        - **核心模式 (回呼)**: [`docs/references/adk-docs/callbacks-design-patterns-and-best-practices.md`](./references/adk-docs/callbacks-design-patterns-and-best-practices.md)
        - **雲端整合**: [`docs/references/adk-docs/observability-cloud-trace.md`](./references/adk-docs/observability-cloud-trace.md)

---

## Phase 4: 架構重構與最佳實踐 (Architectural Refactoring & Best Practices)

- **主題**: 根據 ADK 官方最佳實踐，對現有程式碼庫進行重構，以提高系統的模組化、可擴展性和可維護性。
- **關鍵目標**: 償還現有技術債，並將架構升級到符合 Google SRE 和 ADK 團隊推薦的標準模式。

### 主要交付物 (Key Deliverables):

- **[ ] 4.1. 重構為多代理架構 (Refactor to Multi-Agent Architecture)**:
    - **任務**: 將單體的 `SREWorkflow` 分解為一個主 `RouterAgent` 和多個專業化的子代理 (如 `DeploymentDiagnosisAgent`, `AlertAnalysisAgent`)。主代理負責接收和路由請求，子代理負責執行具體的診斷任務。
    - **參考**:
        - **核心概念**: [`docs/references/adk-docs/agents-multi-agents.md`](./references/adk-docs/agents-multi-agents.md)
        - **實作範本**: [`docs/references/adk-agent-samples/google-adk-workflows/`](./references/adk-agent-samples/google-adk-workflows/)
        - **架構圖**: [`docs/references/adk-architecture/adk-components.png`](./references/adk-architecture/adk-components.png)

- **[ ] 4.2. 引入動態工具協調 (Introduce Dynamic Tool Orchestration)**:
    - **任務**: 改造子代理，使其不再硬編碼工具呼叫順序。為每個子代理提供一個 `Toolbox`，並利用 LLM 的函式呼叫 (Function Calling) 能力來動態決定執行哪些工具，以及如何分析其輸出。
    - **參考**:
        - **核心模式 (ReAct)**: [`docs/references/adk-examples/toolbox_agent/`](./references/adk-examples/toolbox_agent/)
        - **綜合範例**: [`docs/references/adk-agent-samples/sre-bot/`](./references/adk-agent-samples/sre-bot/)
        - **平行函式呼叫**: [`docs/references/adk-examples/parallel_functions/`](./references/adk-examples/parallel_functions/)

- **[ ] 4.3. 實現串流 API (Implement Streaming API)**:
    - **任務**: 為 `sre-assistant` 的 API 新增 Server-Sent Events (SSE) 或 WebSocket 支援，使其能夠在診斷過程中即時回傳進度。同時，更新 `control-plane` 中的 Go 客戶端以消費此串流。
    - **參考**:
        - **官方指南**: [`docs/references/adk-docs/get-started-streaming.md`](./references/adk-docs/get-started-streaming.md)
        - **SSE 範例**: [`docs/references/adk-examples/mcp_sse_agent/`](./references/adk-examples/mcp_sse_agent/)

- **[ ] 4.4. 從 OpenAPI 自動生成客戶端 (Generate Client from OpenAPI)**:
    - **任務**: 將 `pkg/api/openapi.yaml` 作為 API 的唯一真實來源。從中自動生成 `control-plane` 的 Go 客戶端程式碼，並移除手動編寫的客戶端和重複的資料結構。
    - **參考**:
        - **ADK OpenAPI 工具**: [`docs/references/adk-docs/tools-openapi.md`](./references/adk-docs/tools-openapi.md)
        - **Go Code Gen (外部參考)**: `https://github.com/deepmap/oapi-codegen`

- **[ ] 4.5. 清理技術債 (Clean Up Technical Debt)**:
    - **任務**: 解決程式碼庫中的小問題：1) 刪除重複的 `tools/workflow.py` 檔案。2) 完整實現 `main.py` 中的健康檢查 (`check_database`, `check_redis`)。3) 將 `main.py` 中的認證邏輯重構到獨立的模組中。
    - **參考**:
        - **專案結構**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
        - **SRE 理論 - 消除瑣事**: [`docs/references/google-sre-book/Chapter-05-Eliminating-Toil.md`](./references/google-sre-book/Chapter-05-Eliminating-Toil.md)

- **[ ] 4.6. 增強 ControlPlaneTool (Enhance ControlPlaneTool)**:
    - **任務**: 將 `ControlPlaneTool` 重構為一個功能完整的工具集。1) 為所有輸入和輸出定義 Pydantic 模型。2) 返回結構化的成功/錯誤回應。3) 增加寫入/修改操作，例如 `restart_deployment`, `acknowledge_alert` 等，使其不僅僅是唯讀的。
    - **參考**:
        - **工具集結構**: [`docs/references/adk-agent-samples/github-agent/github_toolset.py`](./references/adk-agent-samples/github-agent/github_toolset.py)
        - **工具設計指南**: [`docs/references/adk-docs/tools-overview.md`](./references/adk-docs/tools-overview.md)
