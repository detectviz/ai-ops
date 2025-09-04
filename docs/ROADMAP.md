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

- **[ ] 1.3. 開發 `ControlPlaneTool`**:
    - **任務**: 開發一個新的工具，專門用於回頭呼叫 `control-plane` 的 API，以獲取必要的上下文資訊 (如審計日誌)。

- **[ ] 1.4. 端到端流程測試**:
    - **任務**: 建立一個整合測試，模擬從 `control-plane` 觸發一個部署診斷，到 `sre-assistant` 執行、回調 `control-plane` API，並最終返回結果的完整流程。

- **[✅] 1.5. 核心服務本地化與持久化**:
    - **任務**: 確保開發環境使用 PostgreSQL 作為會話後端，ChromaDB 作為記憶體後端，並能穩定啟動與互動。

- **[ ] 1.6. 核心工具開發**:
    - **任務**: 實現 `PrometheusQueryTool` 和 `LokiLogQueryTool`，用於查詢監控與日誌數據。

---

## Phase 2: 功能擴展與遷移 (Feature Expansion & Migration)

- **主題**: 在完成核心整合的基礎上，將有價值的核心功能遷移並適應到新的 `control-plane` 指揮模式下。
- **關鍵目標**: 豐富 `sre-assistant` 的診斷與分析能力，使其能夠處理更多元的任務。

### 主要交付物 (Key Deliverables):

- **[ ] 2.1. 增強診斷能力**:
    - **任務**: 完善 `deployment` 和 `alert` 診斷流程的內部邏輯，確保其能夠利用 `ControlPlaneTool` 獲取上下文。

- **[ ] 2.2. 結構化報告生成**:
    - **任務**: 重構覆盤報告 (Postmortem) 的生成功能，使其能夠根據 `control-plane` 傳遞的事件 ID，自動生成結構化的分析報告。

- **[ ] 2.3. 人類介入流程 (Human-in-the-Loop)**:
    - **任務**: 改造 `HumanApprovalTool`，將審批請求導向 `control-plane` 的 UI 介面。

- **[ ] 2.4. 測試覆蓋率提升**:
    - **任務**: 為所有核心模組與工具增加單元測試與整合測試，目標覆蓋率 > 80%。

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
