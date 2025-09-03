# SRE Assistant

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

## 📋 專案概覽

SRE Assistant 是一個無介面 (headless) 的智能化站點可靠性工程代理，作為 SRE Platform Monorepo 的核心服務之一。它接收來自 Control Plane 的診斷請求，執行複雜的分析任務，並返回結構化的診斷結果。

### 核心功能

- 🔍 **部署診斷** - 分析部署失敗的根本原因
- 🚨 **告警分析** - 關聯多個告警找出共同模式  
- 📊 **指標查詢** - 查詢 Prometheus 四大黃金訊號
- 📝 **日誌分析** - 從 Loki 提取關鍵錯誤模式
- 🔄 **變更追蹤** - 查詢 Control Plane 的審計日誌
- 🤖 **AI 輔助** - 整合 LLM 進行智慧分析（開發中）

## 🚀 快速開始

### 前置需求

- Python 3.11+
- Poetry 1.8+
- Docker & Docker Compose (用於依賴服務)

### 本地開發設置

1. **安裝依賴**
```bash
cd services/sre-assistant
poetry install
```

2. **啟動依賴服務** (從專案根目錄)
```bash
cd ../..  # 回到 sre-platform 根目錄
make up   # 啟動所有服務
```

3. **執行服務**
```bash
cd services/sre-assistant
poetry run python -m src.sre_assistant.main
```

服務將在 http://localhost:8000 啟動

4. **驗證服務**
```bash
# 健康檢查
curl http://localhost:8000/health

# API 文件
open http://localhost:8000/docs
```

## 📁 專案結構

```
services/sre-assistant/
├── src/
│   └── sre_assistant/
│       ├── main.py              # FastAPI 應用入口
│       ├── workflow.py          # 工作流程協調器
│       ├── contracts.py         # 資料模型定義
│       ├── config/              # 配置管理
│       │   ├── config_manager.py
│       │   └── environments/
│       │       ├── development.yaml
│       │       └── production.yaml
│       └── tools/              # 診斷工具
│           ├── prometheus_tool.py
│           ├── loki_tool.py
│           └── control_plane_tool.py
├── tests/                       # 測試套件
│   ├── test_api.py
│   └── test_workflow.py
├── Dockerfile                   # 容器化配置
├── pyproject.toml              # Python 專案配置
└── README.md                   # 本文件
```

## 🔧 API 端點

### 健康檢查

- `GET /health` - 服務健康狀態
- `GET /ready` - 服務就緒狀態

### 診斷端點

- `POST /diagnostics/deployment` - 診斷部署問題
- `POST /diagnostics/alerts` - 分析告警事件
- `POST /execute` - 執行通用查詢

詳細 API 文件請訪問 http://localhost:8000/docs

## 🧪 測試

### 執行單元測試
```bash
poetry run pytest
```

### 執行測試覆蓋率
```bash
poetry run pytest --cov=src/sre_assistant --cov-report=html
```

### 程式碼品質檢查
```bash
# 格式化
poetry run black src/ tests/

# 排序 imports
poetry run isort src/ tests/

# Linting
poetry run flake8 src/ tests/

# 類型檢查
poetry run mypy src/
```

## 🔐 認證與安全

服務使用 Keycloak 進行 JWT 認證：

1. **M2M Token** - Control Plane 使用 Client Credentials Flow
2. **JWT 驗證** - 所有 API 請求需要有效的 Bearer Token
3. **RBAC** - 基於角色的訪問控制（開發中）

## 🛠️ 配置

### 環境變數

```bash
# 資料庫
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/sre_assistant

# Redis
REDIS_URL=redis://redis:6379

# Keycloak
KEYCLOAK_JWKS_URL=http://keycloak:8080/realms/sre-platform/protocol/openid-connect/certs
OAUTH_CLIENT_ID=sre-assistant

# 監控工具
PROMETHEUS_URL=http://prometheus:9090
LOKI_URL=http://loki:3100

# Control Plane
CONTROL_PLANE_URL=http://control-plane:8081/api
CONTROL_PLANE_CLIENT_SECRET=<secret>

# AI (可選)
GOOGLE_API_KEY=<your-api-key>
```

### 配置檔案

配置檔案位於 `config/environments/` 目錄：

- `development.yaml` - 開發環境
- `production.yaml` - 生產環境
- `test.yaml` - 測試環境

## 📊 監控與日誌

### 日誌

- 格式：JSON
- 級別：通過 `LOG_LEVEL` 環境變數控制
- 輸出：stdout (由 Docker 收集)

### 指標

- Prometheus 格式指標（開發中）
- 端點：`/metrics`

## 🐳 容器化

### 建置映像
```bash
docker build -t sre-assistant:latest .
```

### 執行容器
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=... \
  -e REDIS_URL=... \
  sre-assistant:latest
```

## 📚 相關文件

- [SPEC.md](SPEC.md) - 功能規格說明
- [ARCHITECTURE.md](../sre-assistant/ARCHITECTURE.md) - 系統架構
- [API 契約](../../pkg/api/openapi.yaml) - OpenAPI 規格
- [Control Plane](../control-plane/README.md) - 指揮中心服務

## 🤝 貢獻指南

1. 建立功能分支
2. 撰寫測試
3. 確保通過所有測試和 linting
4. 提交 Pull Request

## 📄 授權

Apache License 2.0

---

*本專案是 SRE Platform Monorepo 的一部分*