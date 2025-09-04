# AGENT.md - SRE Platform AI 代理開發指南

本文件為 AI 代理提供操作此 Monorepo 的具體、可執行的指南。人類使用者請參閱 `README.md`。

## 📁 專案概覽

SRE Platform 是一個採用 **Monorepo** 架構的現代化維運平台，整合了兩個核心服務：

- **Control Plane** (Go): 指揮中心，提供 UI 介面與應用管理
- **SRE Assistant** (Python): 無介面的專家代理，執行診斷與自動化任務

### 架構定位

```
使用者 → Control Plane (指揮官) → SRE Assistant (專家代理) → 外部系統
              ↑                            ↓
              └──── M2M 認證回調 ← ─────────┘
```

## 🚀 快速開始

### 環境需求

- Go 1.21+ (開發 Control Plane)
- Python 3.11+ 與 Poetry (開發 SRE Assistant)
- Make (執行自動化指令)
- 一個基於 Debian/Ubuntu 的環境，並擁有 `sudo` 權限。

### 一鍵啟動開發環境

```bash
# 克隆專案
git clone https://github.com/detectviz/sre-platform
cd sre-platform

# 按照 local/install.md 說明，把開發環境搭建起來，驗證腳本無誤、服務運行正常
```

啟動後可訪問：
- Control Plane: http://localhost:8081
- SRE Assistant API: http://localhost:8000
- Grafana: http://localhost:3000
- Keycloak: http://localhost:8080
- VictoriaMetrics (vmselect): http://localhost:8481

## 📂 Monorepo 結構

```bash
sre-platform/
├── services/                  # 應用服務
│   ├── control-plane/         # Go 後端服務
│   └── sre-assistant/         # Python AI 代理
├── pkg/                       # 共享套件
│   ├── api/                   # API 契約定義
│   │   └── openapi.yaml       # 統一的 API 規格
│   └── auth/                  # 認證配置
│       └── keycloak/          # Keycloak realm 設定
├── local/                     # 本地環境安裝資源
│   ├── setup_local_environment.sh
│   └── verify_environment.sh
├── Makefile                   # 自動化指令
├── TODO.md                    # 專案待辦事項
└── AGENT.md                   # 本文件
```

## 🔧 開發指引

### 服務間通訊規範

1. **API 契約優先**
   - 所有 API 變更必須先更新 `pkg/api/openapi.yaml`
   - Control Plane 與 SRE Assistant 都必須遵循此契約

2. **認證機制**
   - 使用 Keycloak 的 M2M (Machine-to-Machine) JWT Token
   - Control Plane 呼叫 SRE Assistant 時需攜帶有效 Token
   - SRE Assistant 回調 Control Plane 時同樣需要認證

3. **標準化回應格式**
   ```python
   # SRE Assistant 的標準回應
   {
       "status": "COMPLETED",
       "summary": "診斷摘要",
       "findings": [...],
       "recommended_action": "建議動作"
   }
   ```

### Control Plane 開發 (Go)

```bash
# 進入服務目錄
cd services/control-plane

# 安裝依賴
go mod download

# 執行測試
go test ./...

# 本地執行 (需先透過 'make start-services' 啟動依賴)
go run cmd/server/main.go
```

### SRE Assistant 開發 (Python)

```bash
# 進入服務目錄
cd services/sre-assistant

# 安裝 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安裝依賴
poetry install

# 執行測試
poetry run pytest

# 本地執行 (需先透過 'make start-services' 啟動依賴)
poetry run python -m src.sre_assistant.main
```

## 🧪 測試策略

### 單元測試

```bash
# 測試所有服務
make test

# 只測試 Control Plane
make test-go

# 只測試 SRE Assistant  
make test-py
```

### 整合測試

```bash
# 啟動服務 (如果尚未啟動)
make start-services

# 執行端到端測試
# 1. 測試認證流程
# (需先從 Keycloak UI 或 API 獲取 Token)
# 2. 測試診斷 API
curl -X POST http://localhost:8000/diagnostics/deployment \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "test-deploy-001",
    "service_name": "payment-api",
    "namespace": "production"
  }'
```

## 📋 常見開發任務

### 新增 API 端點

1.  **更新 API 契約**: `pkg/api/openapi.yaml`
2.  **實作 Control Plane 處理器**
3.  **實作 SRE Assistant 端點**

### 新增診斷工具

```python
# services/sre-assistant/src/sre_assistant/tools/new_tool.py
# (實作細節請參考檔案內模板)
```

### 更新 Keycloak 配置

```bash
# 1. 修改 realm 配置
vi pkg/auth/keycloak/realm-export.json

# 2. 重啟 Keycloak 服務
make restart-services
```

## 🐛 疑難排解

### 服務無法啟動

```bash
# 檢查服務狀態
make ps

# 查看服務日誌 (Keycloak, ChromaDB)
make logs

# 查看系統服務日誌 (以 Grafana 為例)
sudo journalctl -u grafana-server -f
```

### 認證問題

```bash
# 檢查 Keycloak 是否正常
curl http://localhost:8080/health/ready
```

### 資料庫連線問題

```bash
# 進入資料庫 shell
sudo -u postgres psql -d sre_dev

# 列出所有資料庫
\l
```

## 📝 程式碼規範

### Go (Control Plane)

- 遵循 [Effective Go](https://golang.org/doc/effective_go.html)
- 使用 `gofmt` 格式化程式碼
- 錯誤處理明確，避免 panic
- 測試覆蓋率 > 70%

### 日誌記錄規範

所有後端服務的日誌記錄都應使用 `otelzap.Logger`。關鍵原則如下：

- **結構化日誌**: 使用 `zap.String()`, `zap.Error()` 等欄位來記錄，而非簡單的字串拼接。
- **關聯追蹤**: 在處理 HTTP 請求的程式碼中，務必使用 `logger.Ctx(r.Context())` 來記錄，以確保日誌能與 OpenTelemetry 的追蹤 (Trace) 資訊自動關聯。 』

### Python (SRE Assistant)

- 遵循 PEP 8 規範
- 使用 Black 格式化程式碼
- 使用 Type Hints
- 所有公開函式需有 docstring
- 使用 Pydantic 進行資料驗證

### Git Commit 規範

使用 Conventional Commits，訊息使用繁體中文：

```
feat: 新增部署診斷功能
fix: 修復 JWT 驗證錯誤
docs: 更新 API 文件
test: 新增整合測試
refactor: 重構工作流程引擎
```

## 🚢 部署注意事項 (生產環境)

**注意**: 以下指令適用於將服務打包成 Docker 映像以進行生產環境部署，不適用於本地開發。

### 環境變數管理

```bash
# 開發環境
cp .env.example .env.development

# 生產環境 (使用 Secret Manager)
kubectl create secret generic sre-platform-secrets \
  --from-env-file=.env.production
```

### 容器映像建置

```bash
# 建置所有服務
make build

# 標記版本
docker tag control-plane:latest detectviz/control-plane:v1.0.0
docker tag sre-assistant:latest detectviz/sre-assistant:v1.0.0

# 推送到 Registry
docker push detectviz/control-plane:v1.0.0
docker push detectviz/sre-assistant:v1.0.0
```

## 📚 重要參考文件

### 必讀文件
1. `services/control-plane/ARCHITECTURE.md` - Control Plane 完整架構
2. `services/sre-assistant/SPEC.md` - SRE Assistant API 規格
3. `pkg/api/openapi.yaml` - API 契約定義
4. `TODO.md` - 專案待辦與規劃

### 外部資源
- [Google ADK 文件](https://github.com/google/genkit)
- [HTMX 文件](https://htmx.org/)
- [Keycloak 文件](https://www.keycloak.org/documentation)

## ⚠️ 注意事項

1. **不要直接修改** `pkg/api/openapi.yaml` 以外的 API 定義
2. **不要硬編碼**敏感資訊，使用環境變數
3. **不要跳過**測試直接提交程式碼
4. **務必更新**相關文件當修改架構或 API
5. **保持服務**之間的低耦合，透過 API 通訊

## 🤝 協作原則

1. **API 契約優先**: 任何功能開發前先定義 API
2. **文件驅動開發**: 更新文件 → 寫測試 → 實作功能
3. **漸進式提交**: 小步快跑，頻繁提交
4. **程式碼審查**: 所有 PR 需要至少一位審查者
5. **持續整合**: 確保 CI 通過才能合併

---

*本文件由 AI 代理維護，最後更新時間：2025-09-02*