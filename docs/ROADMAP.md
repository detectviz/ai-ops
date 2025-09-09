# SRE Platform - 開發路線圖與任務清單

> **基於**: SRE Platform 專案全面審查報告 (2025-09-05)
> **當前專案成熟度**: 90/100
> **目標**: 在10週內達到生產就緒狀態
>
> **總覽**: 本文件是 SRE Platform 專案的**唯一真實來源 (Single Source of Truth)**，用於追蹤所有開發任務。它根據架構設計的階段進行組織，並整合了所有新功能、重構計畫和已知的技術債。

---

## 待辦事項 (Backlog)

### 綜合審查修正建議（Audit Fixes）
- [ ] **契約回歸測試與 CI 整合**：實現 `make test` 以聚合兩服務的契約測試，並在 CI 流程中自動執行。

### 中優先度（2–3 週）
- [ ] **E2E 測試**：實現一個完整的端到端測試，模擬從 Control Plane UI 觸發部署診斷，並驗證 SRE Assistant 非同步任務的輪詢與最終結果呈現。

### Phase 1: 核心整合
- [🚧] **1.3. 核心工具開發 (`Prometheus`, `Loki`, `ControlPlane`)**:
    - **目標**: 移除所有模擬資料，實現真實的工具邏輯。
    - **現狀**: 所有工具的唯讀方法均已實現並經過驗證。
- [🚧] **1.4. 端到端流程實作與測試**:
    - **目標**: 建立完整的整合測試。
    - **相關子任務**:
        - [ ] **外部服務整合測試**: 撰寫能與真實 Prometheus, Loki, Keycloak 互動的整合測試。

### Phase 2: Control Plane 功能擴展與 UI 整合
- [🚧] **2.1. 實現診斷後端邏輯**:
    - **目標**: 完整實現 `SREWorkflow` 中的 `_diagnose_alerts`, `_analyze_capacity`, `_execute_query` 方法。
    - **注意事項**:
        - `test_integration.py` 中有兩個測試 (`test_access_protected_endpoint_with_bad_token`, `test_loki_query_integration`) 因環境問題暫時跳過，待後續修復。
- [ ] **2.2. Control Plane Go 服務完善**:
    - **任務**: 實現 Control Plane 的真實業務邏輯，取代所有模擬資料。
- [ ] **2.3. 測試覆蓋率提升**:
    - **任務**: 為所有在 Phase 1 和 Phase 2 中實現的核心模組與工具增加單元測試與整合測試，目標覆蓋率 > 80%。
- [ ] **2.4. 建立串流式前端資料模型**:
    - **任務**: 根據 `gemini-fullstack` 範例，為前端定義一個能夠處理來自 `sre-assistant` 串流事件的資料模型。

### Phase 3: 聯邦化與主動預防
- [ ] **3.1. 實現增強型 SRE 工作流程**:
- [ ] **3.2. 第一個專業化子代理**:
- [ ] **3.3. 主動預防能力**:
- [ ] **3.4. 代理可觀測性**:

---

## ✅ 已完成項目歸檔 (Archive of Completed Items)
- [x] **架構重構：Headless API**
    - **任務**: 將 `control-plane` 重構為純 API 服務，移除所有前端相關程式碼。
    - **理由**: 為了支援新的獨立前端 (`sre-platform-frontend`)，後端必須解耦。
    - **已完成**:
        - [x] 刪除 `services/control-plane/web` 目錄。
        - [x] 移除 `cmd/server/main.go` 中的 Web 伺服器路由與模板渲染邏輯。
        - [x] 更新 `sre-assistant` 的 `control_plane_contracts.py` 以符合新的 `openapi.yaml`。

### 綜合審查修正建議（Audit Fixes）
- [x] **PrometheusQueryTool**: 已重構，加入基於 Tenacity 的指數退避重試與更詳細的錯誤分類。

### 高優先度（本週內）
- [x] SRE Assistant：/api/v1/healthz（HealthStatus）
- [x] SRE Assistant：/api/v1/readyz（ReadinessStatus：checks=prometheus/loki/control_plane）
- [x] SRE Assistant：/api/v1/metrics（text/plain; Prometheus exposition format）
- [x] SRE Assistant：control_plane.base_url → http://localhost:8081/api/v1
- [x] 工具層錯誤處理分類與統一 ToolError（httpx HTTPStatusError/Timeout/ConnectError）
- [x] 工具層單元測試（成功/超時/例外/快取命中）
- [x] Control Plane：/api/v1/healthz、/api/v1/readyz、/api/v1/metrics
- [x] Control Plane：/api/v1/dashboard/trends、/api/v1/dashboard/resource-distribution（最小實作）
- [x] Control Plane：Cookie/Session 金鑰改為環境變數（CONTROL_PLANE_SESSION_KEY）

### 中優先度（2–3 週）
- [x] 結構化日誌一致性：
  - [x] Python：structlog/python-json-logger + Request/Trace ID 中介層
  - [x] Go：RequestID middleware + otelzap JSON 欄位一致
- [x] HTTP 逾時/重試/連線池策略統一（httpx / net/http）
- [x] ControlPlaneTool 唯讀能力覆蓋（resources/resource-groups/audit-logs/incidents/alert-rules/automation/executions）並以 Pydantic 驗證
- [x] 修復 Control Plane Tracer 依賴並恢復 OTel Trace；與 SRE Assistant 串接 trace-id
- [x] 測試覆蓋 ≥ 60%（第一階段）

### 償還現有技術債
- [x] **1. 性能優化與安全增強**:
    - **任務**: 實現連線池、API 限流和審計日誌。
    - **相關子任務 (性能)**:
        - [x] **實作連線池**: HTTP 客戶端, 資料庫, Redis。
        - [x] **實作快取策略**: 查詢結果, 元資料, 會話。
    - **相關子任務 (安全)**:
        - [x] **實作 API 限流**: 基於 IP 和用戶。
        - [x] **實作審計日誌**: 記錄所有 API 調用和敏感操作。
- [x] **2. 清理技術債 (Clean Up Technical Debt)**:
    - **任務**: 解決程式碼庫中的小問題：1) 完整實現 `main.py` 中的健康檢查 (`check_database`, `check_redis`)。2) 將 `main.py` 中的認證邏輯重構到獨立的模組中。
- [x] **3. 增強 ControlPlaneTool (Enhance ControlPlaneTool)**:
    - **任務**: 將 `ControlPlaneTool` 重構為一個功能完整的工具集。1) 為所有輸入和輸出定義 Pydantic 模型。2) 返回結構化的成功/錯誤回應。3) 增加寫入/修改操作，例如 `restart_deployment`, `acknowledge_alert` 等，使其不僅僅是唯讀的。

### Phase 1: 核心整合
- [x] **1.1. API 契約符合性 (API Contract Compliance)**
- [x] **1.2. 服務對服務認證 (M2M Authentication)**
- [x] **1.5. 核心服務本地化與持久化**
