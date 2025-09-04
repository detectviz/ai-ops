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

- **[✅] 1.3. 核心工具開發 (`Prometheus`, `Loki`, `ControlPlane`)**:
    - **任務**: 實現 `PrometheusQueryTool`、`LokiLogQueryTool` 和 `ControlPlaneTool`，為診斷流程提供數據來源。
    - **對應 API**: 這些工具是 `/diagnostics/deployment` 端點的基礎。

- **[✅] 1.4. 端到端流程實作與測試**:
    - **任務**: 在 `SREWorkflow` 中整合所有核心工具，並建立一個完整的整合測試，以驗證 `/diagnostics/deployment` 的端到端流程。
    - **對應 API**: `/diagnostics/deployment`。

- **[✅] 1.5. 核心服務本地化與持久化**:
    - **任務**: 確保開發環境使用 PostgreSQL 作為會話後端，ChromaDB 作為記憶體後端，並能穩定啟動與互動。

---

## Phase 2: Control Plane 功能擴展與 UI 整合

- **主題**: 專注於擴充 `sre-assistant` 的後端能力，並為這些能力在 `control-plane` 上提供對應的 UI 操作介面。
- **關鍵目標**: 讓使用者能夠透過 UI 觸發 `sre-assistant` 的各項核心診斷功能。

### 主要交付物 (Key Deliverables):

- **[ ] 2.1. 實現告警診斷後端邏輯**:
    - **任務**: 完整實現 `SREWorkflow` 中的 `_diagnose_alerts` 方法，使其能夠處理來自 UI 的告警分析請求。
    - **對應 API**: `/diagnostics/alerts`

- **[ ] 2.2. 實現容量分析後端邏輯**:
    - **任務**: 為 `SREWorkflow` 新增容量分析的邏輯，使其能夠根據請求執行容量規劃計算。
    - **對應 API**: `/capacity/analyze`

- **[ ] 2.3. 實現通用查詢後端邏輯**:
    - **任務**: 整合語言模型，使 `/execute` 端點能夠理解更廣泛的自然語言查詢。
    - **對應 API**: `/execute`

- **[ ] 2.4. Control Plane UI 開發**:
    - **任務**: 在 Control Plane (Go 服務) 的前端頁面中，為上述三個端點提供對應的觸發介面（例如，按鈕、表單）。

- **[ ] 2.5. 測試覆蓋率提升**:
    - **任務**: 為所有在 Phase 1 和 Phase 2 中實現的核心模組與工具增加單元測試與整合測試，目標覆蓋率 > 80%。

---

## Phase 3: 聯邦化與主動預防 (Federation & Proactive Prevention)

- **主題**: 將 `sre-assistant` 從單一代理演進為多代理協同的聯邦化系統，並具備預測性維護能力。
- **關鍵目標**: 實現從「被動響應」到「主動預防」的轉變。

### 主要交付物 (Key Deliverables):

- **[ ] 3.1. 第一個專業化子代理**:
    - **任務**: 將一項核心功能（如覆盤報告生成）重構為一個獨立的、可透過 A2A (Agent-to-Agent) 協議呼叫的 `PostmortemAgent`。

- **[ ] 3.2. 主動預防能力**:
    - **任務**: 整合機器學習模型，用於異常檢測和趨勢預測。

- **[ ] 3.3. 代理可觀測性**:
    - **任務**: 建立一個完善的 LLM 可觀測性儀表板，用於追蹤代理的決策過程、成本和性能。
