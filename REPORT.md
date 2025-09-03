### 主旨：Control-Plane 與 SRE Assistant 技術對接審查報告

### 1. 總覽

SRE Assistant 的核心是一個「診斷大腦」，它透過 API 接收自然語言查詢，並利用其工具集（存取指標、日誌、追蹤等）來找出問題根因。

我們的 Control-Plane 負責管理應用程式的生命週期（部署、設定、監控），是「行動的指揮官」。

整合的總體策略是：**讓 Control-Plane 指揮 SRE Assistant 這個大腦去解決問題**，從而將我們平台的服務管理能力從「報告狀態」提升到「提供洞見並解決問題」。

以下是四個最關鍵、最高價值的技術對接場景：

---

### 2. 對接場景分析

#### 場景一：整合部署與健康檢查流程

*   **業務場景 (What):** 當用戶透過我們的 Control-Plane 部署一個新版本後，如果該版本出現健康檢查失敗、CrashLoopBackOff 或上線後關鍵指標異常，系統不僅僅是顯示「部署失敗」，而是能立刻提供一份初步的診斷報告。
*   **用戶價值 (Why):** 將開發者從「看到失敗 -> 手動查日誌/指標 -> 猜測原因」的繁瑣流程中解放出來。極大縮短從部署失敗到定位問題的時間（MTTR）。
*   **技術實現 (How):**
    1.  **觸發器:** Control-Plane 的後端服務在偵測到部署狀態異常（例如，`Deployment` 的 `status.conditions` 長時間非 `True`，或觸發了回滾邏輯）時，自動觸發一個內部事件。
    2.  **API 對接:** 該事件的處理器會向 SRE Assistant 的 `/execute` API 端點發起一個 POST 請求。
    3.  **傳遞上下文:** 請求的 payload 必須包含足夠的上下文，例如：
        ```json
        {
          "user_query": "The deployment for service 'payment-api' in namespace 'production' failed to become healthy. Please investigate.",
          "context": {
            "service_name": "payment-api",
            "namespace": "production",
            "deployment_id": "deploy-xyz-12345",
            "trigger_event": "HealthCheckFailed"
          }
        }
        ```
    4.  **結果呈現:** Control-Plane 的部署歷史或服務狀態頁面，會顯示一個「正在診斷中...」的狀態，並在 SRE Assistant 完成後，提供一個連結指向其生成的報告，或直接在我們的 UI 中渲染出診斷摘要。

#### 場景二：強化服務可觀測性儀表板

*   **業務場景 (What):** 在 Control-Plane 為每個服務提供的監控儀表板（通常包含 CPU、記憶體、延遲等圖表）旁，增加一個「智能診斷 (Smart Diagnostics)」或「詢問 SRE 助理 (Ask SRE Assistant)」的互動式組件。
*   **用戶價值 (Why):** 讓開發者能用自然語言查詢問題，例如「過去一小時的錯誤率為什麼飆高了？」，而不是被動地查看一堆圖表並自行關聯。實現真正的可觀測性，而不僅僅是監控。
*   **技術實現 (How):**
    1.  **前端整合:** 在我們的服務監控頁面（React/Vue/etc.）中開發一個新的 UI 組件。這個組件可以是一個聊天框。
    2.  **API 對接:** 該組件會將用戶輸入的自然語言，連同當前頁面的上下文（服務名、時間範圍等），發送到 SRE Assistant 的 `/execute` API。這需要一個從我們前端到後端的 BFF (Backend for Frontend) 來代理請求，以處理認證和憑證管理。
    3.  **串流響應:** 為了獲得類似 ChatGPT 的體驗，前端與 SRE Assistant 之間的通訊最好使用 WebSocket（如架構圖所示）或 HTTP Streaming。SRE Assistant 會逐步將其分析過程和結果流式傳回，前端組件實時渲染這些更新。

#### 場景三：自動化告警與事件響應

*   **業務場景 (What):** 當我們平台內建的監控系統或與之整合的第三方監控（如 Prometheus Alertmanager）觸發一個嚴重告警時，自動啟動一次 SRE Assistant 診斷。
*   **用戶價值 (Why):** 實現 SRE Assistant 的核心價值主張：「從警報到根因分析只需 10-15 秒」。在 SRE 收到告警通知時，診斷報告已經在生成中，甚至已經附在通知裡。
*   **技術實現 (How):**
    1.  **Webhook 集成:** 這是最典型和解耦的實現方式。在我們的告警配置中，允許用戶添加一個指向 SRE Assistant API 的 Webhook `receiver`。
    2.  **告警範本:** Alertmanager 的 Webhook `template` 需要被配置成 SRE Assistant API 所需的格式。告警中的 `labels` 和 `annotations` 會被用來填充 `user_query` 和 `context`。
        ```json
        // Alertmanager Webhook a SRE Assistant 的 payload 範例
        {
          "user_query": "Alert 'HighErrorRate' is firing for service {{ .CommonLabels.service }}. Please investigate.",
          "context": {
            "alert_name": "{{ .CommonLabels.alertname }}",
            "service": "{{ .CommonLabels.service }}",
            "summary": "{{ .CommonAnnotations.summary }}",
            "source": "PrometheusAlertmanager"
          }
        }
        ```
    3.  **閉環通知:** SRE Assistant 在完成診斷後，可以透過其自身的工具（例如 Slack Tool, PagerDuty Tool）將結果推送到預設的通知渠道，完成從「告警 -> 分析 -> 通知」的閉環。

#### 場景四：關聯變更事件與系統異常

*   **業務場景 (What):** SRE Assistant 在診斷問題時，能夠知道「在問題發生前後，這個服務在我們的 Control-Plane 上發生了哪些變更？」
*   **用戶價值 (Why):** 「什麼變了？」是 SRE 排查問題時的第一個問題。將我們的 Control-Plane（變更的來源）與 SRE Assistant（診斷引擎）打通，能提供最關鍵的因果分析線索。
*   **技術實現 (How):**
    1.  **提供審計日誌 API:** 我們的 Control-Plane 需要暴露一個標準化的、可供查詢的審計日誌 API，例如 `GET /api/v1/audit-logs?service=payment-api&start_time=...&end_time=...`。該 API 返回指定時間內該服務的變更事件（如：部署、設定變更、特性標誌切換）。
    2.  **為 SRE Assistant 開發新工具:** 我們需要為 SRE Assistant 開發一個新的「Tool」，可以命名為 `ControlPlaneAuditLogTool`。這個 Tool 本質上是一個 Python 函數，它知道如何呼叫我們第一步提供的 API。
    3.  **註冊工具:** 將這個新工具註冊到 SRE Assistant 的 `ToolRegistry` 中。
    4.  **修改 Prompt/Workflow:** 在 SRE Assistant 的核心 `Workflow` 或 `Prompt` 中，加入一個步驟：「檢查最近的部署和配置變更」。這會引導 LLM 在分析時去調用我們提供的 `ControlPlaneAuditLogTool`，從而將我們的平台變更事件納入其分析範圍。

---

### 3. 結論

與 SRE Assistant 的整合，對我們的 Control-Plane 而言是一個戰略性的舉措。它能讓我們的平台變得更「聰明」，將我們的核心能力從「資源管理」延伸到「智能運維」。

建議的實施順序為：**場景一 (部署失敗診斷) -> 場景三 (告警自動診斷) -> 場景二 (儀表板整合) -> 場景四 (變更關聯)**。這個路徑能以最高的 ROI（投資回報率）逐步提升我們平台的競爭力。
