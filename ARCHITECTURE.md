# 規格暨技術架構書

**文件版本：** 17.0 (Monorepo 統一版)
**最後更新日期：** 2025年9月03日

## **1. 核心理念與總體架構**

本專案旨在打造一個名為 **SRE Platform** 的現代化維運平台。核心理念是將複雜性集中在 Go 後端 (`Control Plane`)，並使用 HTMX 保持前端的輕量與簡潔，同時利用一個無介面的專家代理 (`SRE Assistant`) 來執行複雜的診斷與自動化任務。

### **1.1 總體架構圖 (Overall Architecture)**

此架構定義了 `Control Plane` 與 `SRE Assistant` 之間的整合模式。在此模式下，`Control Plane` 作為使用者介面和核心指揮官，負責接收使用者指令，並將其轉化為對 `SRE Assistant` 的 API 呼叫。`SRE Assistant` 則作為一個無介面的專家代理，專注於執行複雜的診斷、分析與修復任務。

```mermaid
graph TD
    subgraph "使用者層"
        User([使用者])
    end

    subgraph "指揮中心 (Control Plane)"
        ControlPlaneUI[Control Plane UI<br/>(HTMX, Go Backend)]
    end

    subgraph "專家代理 (SRE Assistant)"
        SREAssistantAPI[SRE Assistant API<br/>(Python, Google ADK)]
    end

    subgraph "外部系統"
        Observability[可觀測性平台<br/>(Prometheus, Loki)]
        AuditLogs[Control Plane Audit API]
    end

    %% Connections
    User --> ControlPlaneUI
    ControlPlaneUI -- API 請求 (攜帶 M2M JWT) --> SREAssistantAPI

    SREAssistantAPI -- 執行工具 --> Observability
    SREAssistantAPI -- 查詢變更歷史 --> AuditLogs
```

### **1.2 組件職責 (Component Roles)**

#### **Control Plane**
- **角色**: **指揮官 (Commander) / 協調器 (Orchestrator)**
- **職責**:
    - 提供統一的使用者操作介面。
    - 管理應用程式生命週期（部署、設定等）。
    - 將使用者的操作（如「診斷部署失敗」）轉換為對 `sre-assistant` 的標準化 API 請求。
    - 透過自身的 `/api/v1/audit-logs` 端點，為 `sre-assistant` 提供必要的上下文資訊（如變更歷史）。
    - 處理使用者身份驗證，並負責獲取服務間通訊所需的 M2M Token。

#### **SRE Assistant**
- **角色**: **專家代理 (Specialist Agent)**
- **職責**:
    - 作為一個無介面的後端服務運行。
    - 接收來自 `control-plane` 的 API 請求。
    - 執行核心的診斷與分析邏輯，利用其工具集（如查詢指標、日誌）與外部系統互動。
    - 在需要時，回頭呼叫 `control-plane` 的 API 以獲取更多上下文。
    - 驗證傳入的 M2M JWT，以確保請求來自合法的 `control-plane` 服務。

### **1.3 技術棧**

* **後端 (Backend):**  
  * **Control Plane**: Go (net/http), PostgreSQL
  * **SRE Assistant**: Python, FastAPI, Google ADK
* **前端 (Frontend):**  
  * 核心： HTMX  
  * 樣式： Tailwind CSS  
  * 輔助腳本： Alpine.js, Tom Select
  * 圖表： Chart.js
* **核心服務 (Core Services):**  
  * **監控 (Monitoring):** VictoriaMetrics, vmagent, snmp_exporter
  * **視覺化與告警 (Visualization & Alerting):** Grafana
  * **身份驗證 (Authentication):** Keycloak (SSO & M2M)
  * **AI 輔助 (AI Assistance):** Google Gemini API

### **1.4 非功能性需求 (Non-Functional Requirements)**

* **響應式設計 (RWD):** 平台介面必須完全響應式。
* **使用者體驗 (UX):** 整體需遵循 web.html 原型所定義的現代化 UI 風格，包含專業的配色、清晰的字體、流暢的過渡動畫等。

## **2. 系統架構與權限模型**

### **2.1 核心實體與資料關聯**

本平台圍繞以下核心實體建構：

* **資源 (Resource):** 最小的監控單元。
* **資源群組 (Resource Group):** 資源的邏輯集合。
* **人員 (Personnel):** 系統的使用者。
* **通知管道 (Notification Channel):** 如 Slack Webhook 或 Email 群組。
* **團隊 (Team):** 人員的集合，用於權限賦予和通知訂閱。
* **告警規則 (Alert Rule):** 監控條件設定。
* **告警事件 (Alert Event / Incident):** 告警規則觸發的事件。
* **維護時段 (Maintenance):** 抑制告警的排程。
* **腳本庫 (Script Repository):** 自動化腳本的儲存庫。
* **執行日誌 (Execution Log):** 自動化腳本的執行紀錄。

**核心權限邏輯：** 一位 **人員** 屬於某個 **團隊**，該 **團隊** 被授予查看特定 **資源群組** 的權限。因此，該人員登入後，只能看到其被授權的資源群組及其中的 **資源** 所產生的相關告警。

### **2.2 認證與授權 (Authentication & Authorization)**

#### **使用者認證 (User Authentication)**
採用標準的 OIDC (OpenID Connect) Authorization Code Flow，以 Keycloak 作為身份提供者。
1.  使用者訪問平台，被重導向至 Keycloak 登入。
2.  登入成功後，Go 後端用授權碼交換 JWT。
3.  Go 後端驗證 JWT，並為使用者建立一個伺服器端 Session。

#### **服務間認證 (M2M Authentication)**
為了確保服務間通訊的安全性，採用基於 Keycloak 的 **Client Credentials Flow**。
1. `Control Plane` 使用其 Client ID 和 Secret，向 Keycloak 請求一個 Access Token。
2. 在呼叫 `SRE Assistant` 的 API 時，`Control Plane` 會在 HTTP `Authorization` 標頭中以 `Bearer` 形式附上此 Token。
3. `SRE Assistant` 的 API 入口處會有一個中介軟體，負責攔截並驗證此 JWT 的有效性。

## **3. API 契約 (API Contract)**

`Control Plane` 與 `SRE Assistant` 之間的互動，嚴格遵循 `pkg/api/openapi.yaml` 文件。該文件是兩個服務之間 API 的「唯一真實來源」。

## **4. UI/UX 結構與功能規格**

(此處省略與 `services/control-plane/ARCHITECTURE.md` 相同的詳細 UI/UX 規格，以保持簡潔。實際內容應包含對儀表板、資源管理、團隊管理等所有頁面的詳細描述。)

## **5. 整合流程範例：部署失敗診斷**

1. **觸發**: 使用者在 `Control Plane` 的 UI 上點擊一個部署失敗的服務，並選擇「開始診斷」。
2. **指揮**: `Control Plane` 的後端服務，向 `SRE Assistant` 的 `POST /diagnostics/deployment` 端點發起 API 請求。請求的 Body 中包含必要的上下文，如 `{ "deployment_id": "deploy-xyz-12345", "service_name": "payment-api" }`。此請求的 Header 中攜帶著 M2M Access Token。
3. **執行**: `SRE Assistant` 驗證 Token，接收請求，並啟動其內部的診斷工作流 (Workflow)。
4. **分析**: `SRE Assistant` 的代理開始執行其工具：
    - 呼叫 VictoriaMetrics API 查詢該服務的指標。
    - 呼叫 Loki API 查詢相關的日誌。
    - **回頭呼叫** `Control Plane` 的 `GET /api/v1/audit-logs` API，查詢在問題發生時間點前後的部署或設定變更。
5. **回覆**: `SRE Assistant` 綜合所有資訊，生成一份診斷報告，並將結果回傳給 `Control Plane`。
6. **呈現**: `Control Plane` 在 UI 上向使用者展示這份診斷報告。
