# SRE Assistant - 開發指南

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

## 1. 專案概覽

SRE Assistant 是一個無介面 (headless) 的智能化站點可靠性工程代理，作為 SRE Platform Monorepo 的核心服務之一。它接收來自 Control Plane 的診斷請求，執行複雜的分析任務，並返回結構化的診斷結果。

### 核心功能

- 🔍 **部署診斷**: 分析部署失敗的根本原因
- 🚨 **告警分析**: 關聯多個告警找出共同模式
- 📊 **指標查詢**: 查詢 Prometheus 四大黃金訊號
- 📝 **日誌分析**: 從 Loki 提取關鍵錯誤模式
- 🔄 **變更追蹤**: 查詢 Control Plane 的審計日誌
- 🤖 **AI 輔助**: 整合 LLM 進行智慧分析（開發中）

## 2. 本地開發

本服務的開發流程已整合至 Monorepo 的 `Makefile` 中，以提供統一的開發體驗。

### 2.1. 環境設定

請直接使用根目錄的 `make` 指令來設定完整的開發環境，它會處理所有依賴服務與 Python 套件的安裝。

```bash
# 從專案根目錄執行
make setup-dev
```

### 2.2. 獨立執行服務

如果您需要在修改後獨立啟動 `sre-assistant` 服務進行調試：

```bash
# 確保所有依賴服務正在運行
# (如果尚未啟動，請從根目錄執行 make start-services)

# 進入服務目錄
cd services/sre-assistant

# 使用 poetry 啟動服務
poetry run python -m sre_assistant.main
```

服務將在 http://localhost:8000 啟動。

### 2.3. 驗證服務

```bash
# 檢查健康狀態
curl http://localhost:8000/health

# 查看 API 文件
# 在瀏覽器中打開 http://localhost:8000/docs
```

## 3. 專案結構

```
services/sre-assistant/
├── src/
│   └── sre_assistant/
│       ├── main.py              # FastAPI 應用入口
│       ├── workflow.py          # 工作流程協調器
│       ├── contracts.py         # 資料模型定義
│       ├── config/              # 配置管理
│       └── tools/               # 診斷工具
├── tests/                       # 測試套件
├── Dockerfile                   # 容器化配置
├── pyproject.toml               # Python 專案配置
└── README.md                    # 本文件
```

## 4. API 端點

本服務採用「兩層式 API」設計，以兼顧彈性與穩定性。

### 4.1. 第一層：通用入口 (Generic Agent API)

此端點為探索性、Ad-hoc 或尚未產品化的查詢提供高度彈性。

- **`POST /execute`**
  - **用途**: 處理自然語言查詢或動態生成的診斷任務。
  - **Payload**: 包含 `user_query` 和 `context`。
    ```json
    {
      "user_query": "Why did p99 latency spike in the last 30 minutes?",
      "context": {
        "trigger_source": "ControlPlane::DashboardUI",
        "service_name": "user-profile-svc",
        "time_range": { "start": "...", "end": "..." }
      }
    }
    ```

### 4.2. 第二層：語義化端點 (Productized Endpoints)

為固定的、高頻的使用場景提供結構清晰、語義明確的 API。

- **`POST /diagnostics/deployment`**
  - **用途**: 專門用於診斷部署失敗或部署後健康狀況不佳的場景。
  - **核心工作流程 (非同步)**:
    1. **接收請求**: API 端點接收到請求後，立即建立一個唯一的 `session_id`。
    2. **啟動背景任務**: 將 `session_id` 和請求內容傳遞給一個背景任務 (background task) 進行處理。
    3. **立即回應**: API 端點立即向客戶端返回 `202 Accepted` 和 `session_id`，不等待診斷完成。
    4. **背景執行**: 背景任務中的 `SREWorkflow` 開始執行，並行呼叫 `PrometheusQueryTool`, `LokiLogQueryTool` 等工具。
    5. **狀態更新**: 工作流程在執行過程中，會將進度 (如 "processing", "completed") 和最終結果更新到一個共享的任務儲存中（以 `session_id` 為鍵）。
    6. **輪詢查詢**: 客戶端 (Control Plane) 使用 `session_id` 定期輪詢 `/diagnostics/{session_id}/status` 端點來獲取最新狀態和最終的診斷報告。
  - **Payload**:
    ```json
    {
      "context": {
        "trigger_source": "ControlPlane::DeploymentMonitor",
        "service_name": "payment-api",
        "namespace": "production",
        "deployment_id": "deploy-xyz-12345"
      }
    }
    ```

- **`POST /diagnostics/alerts`**
  - **用途**: 專門用於處理由 Alertmanager 等系統觸發的告警事件。
  - **核心工作流程**: 接收一或多個告警事件，關聯其上下文，並找出共同模式。
  - **Payload**:
    ```json
    {
      "context": {
        "trigger_source": "PrometheusAlertmanager",
        "alert_name": "HighErrorRate",
        "service_name": "checkout-svc"
      }
    }
    ```

### 4.3. 健康檢查

- `GET /health`
- `GET /ready`

> **唯一真實來源**: 所有 API 的最終規格以專案根目錄下的 `pkg/api/sre-assistant-openapi.yaml` 為準。在服務執行時，也可訪問 http://localhost:8000/docs 查看互動式 API 文件。

## 5. 內部設計模式

### 5.1. 標準化工具介面

為了確保系統的穩定性和可預測性，所有由 SRE Assistant 使用的工具 (`Tool`)，其 `execute` 方法都必須返回一個標準化的 `ToolResult` 物件。

```python
class ToolError(BaseModel):
    code: str  # e.g., "API_AUTH_ERROR", "NOT_FOUND"
    message: str

class ToolResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ToolError] = None
```
此設計確保了工作流程中的代理能夠以統一的方式處理工具的成功與失敗，並根據 `error.code` 執行相應的錯誤處理邏輯。

## 6. 測試與品質

所有測試與程式碼品質檢查都應從 **專案根目錄** 透過 `make` 指令執行。

### 5.1. 執行測試

```bash
# 執行 sre-assistant 的所有測試
make test-py
```

### 5.2. 程式碼品質

`sre-assistant` 遵循 `black` 格式化、`isort` 導入排序與 `flake8`/`mypy` 靜態分析。建議在您的 IDE 中設定這些工具，以便在存檔時自動格式化。

## 6. 配置管理

### 6.1. 環境變數

服務啟動時會讀取 `.env` 檔案。您可以複製 `services/sre-assistant/.env.example` 來建立本地的開發配置。

### 6.2. 配置檔案

詳細的服務配置（如工具參數、工作流程設定）位於 `services/sre-assistant/config/environments/` 目錄中。

## 7. 容器化

### 建置映像

```bash
# 進入服務目錄
cd services/sre-assistant

# 建置
docker build -t sre-assistant:latest .
```

---
*本文件是 SRE Platform Monorepo 的一部分。返回 [**主 README](../README.md)**。*
