# SRE Platform - 全面審查報告與修正清單（Audit Fixes）

最後更新：2025-09-07  
作者：ADK 首席架構師（審查自動化產出）

---

## 0. 執行摘要（Executive Summary）

- 進展佳：健康/就緒/metrics 端點已在兩側服務完成並對齊 OpenAPI；Control Plane 儀表板 trends/resource-distribution 已最小實作；Cookie/Session 金鑰環境變數化完成；新增關鍵契約測試（Python/Go）。
- 主要缺口：工具層（Prometheus/Loki/ControlPlaneTool）單元測試與錯誤分類一致性；Control Plane 多數業務端點仍為骨架/模擬；尚未把契約回歸測試納入 CI。
- 建議順序：
  1) 工具層單元測試 + 統一錯誤碼分類（高優先）
  2) 將契約測試整合進 CI（高優先）
  3) 逐步替換 Control Plane 業務邏輯（中優先）

---

## 1. OpenAPI 契約一致性檢查（重點）

### 1.1 SRE Assistant（對照 pkg/api/sre-assistant-openapi.yaml）
- /api/v1/healthz：回傳 HealthStatus（status/timestamp/version?/uptime?）— 一致。
- /api/v1/readyz：回傳 ReadinessStatus（ready + checks: prometheus/loki/control_plane）— 一致（已移除 redis 暴露）。
- /api/v1/metrics：text/plain（Prometheus exposition）— 一致。
- /api/v1/diagnostics/deployment（POST, 202）、/api/v1/diagnostics/{sessionId}/status（GET, 200/404）— 流程與結構一致。
- /api/v1/diagnostics/alerts、/api/v1/execute、/api/v1/diagnostics/history、/api/v1/workflows/templates、/api/v1/tools/status — 端點存在，結構方向正確。

結論：SRE Assistant 與契約一致性達 100%。

### 1.2 Control Plane（對照 pkg/api/control-plane-openapi.yaml）
- /api/v1/healthz、/api/v1/readyz、/api/v1/metrics — 已對齊（Readiness checks：database/redis/keycloak/sre_assistant）。
- /api/v1/dashboard/summary — 存在（骨架結構）；/api/v1/dashboard/trends、/api/v1/dashboard/resource-distribution — 已最小實作並對齊 schema。
- 其餘（Resources/Incidents/Alert Rules/Automation/Notifications/Settings/Audit）— 路由齊全，多為骨架/模擬結構，需隨業務邏輯落地時同步契約檢測。

結論：Control Plane 核心健康/儀表板端點合規，其餘需在實作業務邏輯時持續對齊契約。

---

## 2. 程式碼品質觀察（Code Quality）

- 分層與結構：Monorepo 結構清晰，FastAPI/Go handlers 責任清楚；SREWorkflow/Toolset 層次分明。
- 日誌與觀測性：
  - Python：建議導入 JSON 結構化日誌（structlog/python-json-logger）、FastAPI Request/Trace ID 中介層。
  - Go：已用 otelzap，建議加 RequestID middleware，統一 JSON 欄位（time, level, msg, request_id, trace_id）。
  - Metrics：兩側 /api/v1/metrics 可被 Prometheus 抓取，Tracing 待解決依賴後恢復。
- 錯誤處理：
  - 工具層需分類 httpx 錯誤（HTTPStatusError/Timeout/ConnectError）並統一 ToolError（code/message/details），與 workflow 重試條件對齊。
- 安全：
  - Cookie 金鑰已環境變數化；請持續避免任何 secrets 硬編碼。

---

## 3. 風險與缺口（Risks & Gaps）

- Control Plane 多數業務端點尚為骨架/模擬，與資料庫/服務整合需逐步落地。
- 工具層錯誤分類與統一回傳結構尚未完成，影響 workflow 重試行為一致性。
- 未在 CI 加入契約回歸測試，後續改動有契約漂移風險。

---

## 4. 修正建議（Action Plan）

### 4.1 高優先（本週內）
- 工具層單元測試與錯誤分類一致化：
  - 覆蓋成功/超時/HTTPStatusError/ConnectError；
  - 統一 ToolError：{ code, message, details }；
  - 與 workflow 重試條件（如 Timeout/Connect 類重試）對齊。
- 將契約測試納入 CI：
  - make test 同時執行 Python/Go 契約測試；
  - 在 CI（GitHub Actions）上於 PR/主分支自動執行。
- 擴充 Control Plane 健康/儀表板契約測試：
  - 驗證 Readiness checks 鍵與型別；
  - 驗證 trends/resource-distribution 的 schema 鍵與型別。

### 4.2 中優先（2–3 週）
- 日誌與觀測性一致化：
  - Python：JSON 結構化 + Request/Trace ID；
  - Go：RequestID middleware + JSON 欄位一致；
  - 指標延伸（請求延遲直方圖、失敗率、業務 KPI）。
- Control Plane 業務端點落地：
  - Resources/Incidents/Alert Rules… 每交付一端點即補單元+契約測試。
- 覆蓋率 ≥ 60%（第一階段）：
  - 聚焦工具層、handlers、workflow 主路徑。

### 4.3 低優先（4–6 週）
- Tracing：修復 Control Plane 依賴，恢復 OTel Trace，與 SRE Assistant 串起 trace-id。
- 安全加固：敏感端點限流；SCA/SAST 納入 CI。
- SDK 生成：依 OpenAPI 生成內部 SDK，避免手寫 Client 漂移。

---

## 5. ROADMAP 對齊（已更新）
- docs/ROADMAP.md 已新增「綜合審查修正建議（Audit Fixes）」章節，並在 Phase 2.2 註記：trends/resource-distribution 最小實作完成。
- 之後所有審查建議與進度更新，以 ROADMAP 為主同步維護。

---

## 6. 驗證步驟（Verification）

- Python（SRE Assistant）
  - 契約測試：`make test-py`
  - 觀察：`/api/v1/healthz`（200, HealthStatus）、`/api/v1/readyz`（200/503, ReadinessStatus）、`/api/v1/metrics`（text/plain）

- Go（Control Plane）
  - 契約測試：`make test-go`
  - 觀察：`/api/v1/healthz`、`/api/v1/readyz`、`/api/v1/metrics`、`/api/v1/dashboard/trends`、`/api/v1/dashboard/resource-distribution`

---

## 7. 參考（本地文件）
- OpenAPI 與測試：
  - docs/references/adk-docs/tools-openapi-tools.md
  - docs/references/adk-docs/get-started-testing.md
- 認證與安全：
  - docs/references/adk-docs/tools-authentication.md
  - docs/references/adk-agent-samples/headless_agent_auth/
- 工作流：
  - docs/references/adk-docs/agents-workflow-agents-parallel-agents.md
  - docs/references/adk-agent-samples/google-adk-workflows/
- 觀測性：
  - docs/references/adk-docs/observability-logging.md
  - docs/references/adk-docs/observability-cloud-trace.md

