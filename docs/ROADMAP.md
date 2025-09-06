# SRE Platform - 開發路線圖與任務清單

> **基於**: SRE Platform 專案全面審查報告 (2025-09-05)
> **當前專案成熟度**: 75/100
> **目標**: 在12週內達到生產就緒狀態
>
> **總覽**: 本文件是 SRE Platform 專案的**唯一真實來源 (Single Source of Truth)**，用於追蹤所有開發任務。它根據架構設計的階段進行組織，並整合了所有新功能、重構計畫和已知的技術債。

---

## Phase 1: 核心整合 (Core Integration)

- **主題**: 專注於完成 `sre-assistant` 與 `control-plane` 之間的所有技術對接工作，確保兩者能夠安全、可靠地協同工作。
- **關鍵目標**: 實現一個可由 `control-plane` 觸發並完成端到端診斷流程的最小可行產品 (MVP)。

### 主要交付物 (Key Deliverables):

- **[🚧] 1.1. API 契約符合性 (API Contract Compliance)**:
    - **任務**: 確保 `sre-assistant` 的 FastAPI 服務嚴格遵守 `pkg/api/sre-assistant-openapi.yaml` 中定義的所有端點、請求格式和回應格式。
    - **當前狀態**:
        - ✅ SRE Assistant: 91% 完成 (10/11 個端點)
        - ⚠️ Control Plane: 6% 完成 (4/67 個端點)
    - **相關子任務**:
        - [x] 在 `DiagnosticResult` 中添加 `execution_plan` 欄位
        - [x] 定義 `AlertAnalysisRequest` 資料模型
        - [x] 定義 `CapacityAnalysisRequest` 資料模型
        - [x] 定義 `ExecuteRequest` 資料模型

- **[✅] 1.2. 服務對服務認證 (M2M Authentication)**:
    - **任務**: 完整實現基於 Keycloak 和 Client Credentials Flow 的認證機制。
    - **相關子任務**:
        - [x] 實作 `verify_token` 函數的實際 JWT 驗證
        - [x] 與 Keycloak 進行整合測試
        - [x] 處理 token 過期和刷新邏輯
    - **參考**: `docs/reference-adk-examples.md` (oauth_calendar_agent)

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

- **[🚧] 1.4. 端到端流程實作與測試**:
    - **任務**: 在 `SREWorkflow` 中整合所有核心工具，並建立一個完整的整合測試，以驗證 `/diagnostics/deployment` 的端到端流程。
    - **對應 API**: `/diagnostics/deployment`。
    - **相關子任務**:
        - [x] **修復工作流程錯誤處理**: `asyncio.gather` 中已添加異常處理、容錯、超時和重試機制。
        - [ ] **API 整合測試**: 端到端診斷流程測試, 非同步任務狀態追蹤測試, 錯誤情境測試。
        - [ ] **外部服務整合測試**: Prometheus, Loki, Keycloak 整合測試。
    - **參考**: `docs/reference-adk-examples.md` (parallel_functions, workflow_agent_seq)

- **[✅] 1.5. 核心服務本地化與持久化**:
    - **任務**: 確保開發環境使用 PostgreSQL 作為會話後端，ChromaDB 作為記憶體後端，並能穩定啟動與互動。
    - **相關子任務**:
        - [x] **實作任務狀態持久化**: 使用 Redis 替代記憶體存儲任務狀態。
        - [x] **環境變數化配置**: 將硬編碼的 URL 移至環境變數。
    - **參考**: `docs/reference-adk-examples.md` (history_management, session_state_agent)

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

- **[ ] 2.2. Control Plane Go 服務完善**:
    - **任務**: 實現 Control Plane 的真實業務邏輯，取代所有模擬資料。
    - **相關子任務**:
        - [ ] 實作實際的業務邏輯（非模擬資料）
        - [ ] 完成批次操作功能
        - [ ] 實作與 SRE Assistant 的完整整合
    - **參考**:
        - **全端架構範本**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
        - **前端實作參考**: [`docs/references/adk-agent-samples/gemini-fullstack/frontend/`](./references/adk-agent-samples/gemini-fullstack/frontend/)
        - **後端 API 文件**: [`docs/references/adk-docs/api-reference.md`](./references/adk-docs/api-reference.md)

- **[ ] 2.3. 測試覆蓋率提升**:
    - **任務**: 為所有在 Phase 1 和 Phase 2 中實現的核心模組與工具增加單元測試與整合測試，目標覆蓋率 > 80%。
    - **相關子任務**:
        - [ ] **SRE Assistant Python 服務測試**: 各診斷工具的單元測試。
        - [ ] **Control Plane Go 服務測試**: Handler 層, Service 層, Client 層, 整合測試。
    - **參考**:
        - **SRE 理論 - 可靠性測試**: [`docs/references/google-sre-book/Chapter-17-Testing-for-Reliability.md`](./references/google-sre-book/Chapter-17-Testing-for-Reliability.md)
        - **ADK 官方指南**: [`docs/references/adk-docs/get-started-testing.md`](./references/adk-docs/get-started-testing.md)
        - **專案結構範本**: [`docs/references/agent-starter-pack/tests/`](./references/agent-starter-pack/tests/)

- **[ ] 2.4. 建立串流式前端資料模型 (Create Streaming Frontend Data Model)**:
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
    - **相關子任務**:
        - [ ] **實作 Prometheus Metrics**: API 請求次數和延遲指標, 診斷任務成功/失敗率等。
        - [ ] **實作結構化日誌**: 統一日誌格式 (JSON), 添加 TraceID 支援。
    - **參考**:
        - **SRE 理論 - 監控**: [`docs/references/google-sre-book/Chapter-06-Monitoring-Distributed-Systems.md`](./references/google-sre-book/Chapter-06-Monitoring-Distributed-Systems.md)
        - **核心模式 (回呼)**: [`docs/references/adk-docs/callbacks-design-patterns-and-best-practices.md`](./references/adk-docs/callbacks-design-patterns-and-best-practices.md)
        - **雲端整合**: [`docs/references/adk-docs/observability-cloud-trace.md`](./references/adk-docs/observability-cloud-trace.md)

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

- **[ ] 4.2. 從 OpenAPI 自動生成客戶端**:
    - **任務**: 從 `pkg/api/control-plane-openapi.yaml` 自動生成 Go 客戶端程式碼。
    - **參考**:
        - **ADK OpenAPI 工具**: [`docs/references/adk-docs/tools-openapi.md`](./references/adk-docs/tools-openapi.md)
        - **Go Code Gen (外部參考)**: `https://github.com/deepmap/oapi-codegen`

- **[ ] 4.3. 清理技術債 (Clean Up Technical Debt)**:
    - **任務**: 解決程式碼庫中的小問題：1) 刪除重複的 `tools/workflow.py` 檔案。2) 完整實現 `main.py` 中的健康檢查 (`check_database`, `check_redis`)。3) 將 `main.py` 中的認證邏輯重構到獨立的模組中。
    - **參考**:
        - **專案結構**: [`docs/references/agent-starter-pack/`](./references/agent-starter-pack/)
        - **SRE 理論 - 消除瑣事**: [`docs/references/google-sre-book/Chapter-05-Eliminating-Toil.md`](./references/google-sre-book/Chapter-05-Eliminating-Toil.md)

- **[ ] 4.4. 增強 ControlPlaneTool (Enhance ControlPlaneTool)**:
    - **任務**: 將 `ControlPlaneTool` 重構為一個功能完整的工具集。1) 為所有輸入和輸出定義 Pydantic 模型。2) 返回結構化的成功/錯誤回應。3) 增加寫入/修改操作，例如 `restart_deployment`, `acknowledge_alert` 等，使其不僅僅是唯讀的。
    - **參考**:
        - **工具集結構**: [`docs/references/adk-agent-samples/github-agent/github_toolset.py`](./references/adk-agent-samples/github-agent/github_toolset.py)
        - **工具設計指南**: [`docs/references/adk-docs/tools-overview.md`](./references/adk-docs/tools-overview.md)

---

## 📈 KPI 追蹤

| 指標 | 當前狀態 | 目標 | 測量方式 |
|------|---------|------|----------|
| API 合規性 | 48% | 100% | OpenAPI 契約測試 |
| 測試覆蓋率 | ~10% | 80% | Coverage 工具 |
| P99 延遲 | N/A | <500ms | APM 監控 |
| 錯誤率 | N/A | <0.1% | 錯誤監控 |
| 可用性 | N/A | 99.9% | 正常運行時間監控 |

### 業務指標
- [x] **API 完整性** (第1週) ✅
  - 所有 OpenAPI 定義的端點都已實作
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
1. **SRE Assistant API 實作** - 91% 完成 (10/11 個端點)
2. **資料模型定義** - 關鍵資料模型已定義並對齊 OpenAPI
3. **任務持久化** - Redis 存儲已實作，24 小時過期
4. **環境變數配置** - 基本的配置管理已完成
5. **服務間認證** - JWT 驗證邏輯已實作

### ⚠️ 需要修正的項目狀態
- Control Plane API 實現率僅 6% (遠低於預期)
- 測試覆蓋率約 10% (遠低於 30% 目標)
- 核心工具雖有實作但需要完善錯誤處理和快取機制
