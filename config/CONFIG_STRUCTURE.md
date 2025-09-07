# SRE Platform 配置檔案結構總覽

## 📁 專案結構

```
sre-platform/
├── config/                           # 📂 統一配置目錄
│   ├── docker/
│   │   └── docker-compose.yml       # 🐳 服務編排配置
│   ├── monitoring/
│   │   ├── prometheus.yml           # 📊 Prometheus 指標收集
│   │   └── snmp.yml                 # 📡 SNMP 網路監控
│   ├── scripts/
│   │   └── docker-start.sh          # 🚀 Docker 啟動腳本
│   ├── DOCKER_README.md             # 📖 Docker 環境說明
│   ├── env-example.txt              # 🔧 環境變數模板
│   └── README.md                    # 📋 配置目錄說明
├── start-docker.sh                  # 🚀 根目錄啟動腳本
├── services/                        # 🏗️ 應用服務代碼
│   ├── control-plane/               # 🎯 Go 控制平台
│   └── sre-assistant/               # 🧠 Python AI 助理
├── pkg/                            # 📦 共享包
│   ├── api/                        # 🔌 OpenAPI 規範
│   └── auth/                       # 🔐 認證配置
├── docs/                           # 📚 文件
├── install/                        # 🛠️ 安裝腳本
├── tmp/                           # 🗂️ 臨時文件
└── README.md                      # 📖 專案說明
```

## 🎯 配置目錄設計原則

### 📂 功能分組
- **docker/**: 容器編排和運行時配置
- **monitoring/**: 可觀測性配置 (指標收集、網路監控)
- **scripts/**: 自動化腳本和管理工具

### 🔧 配置層次
1. **環境變數** (.env): 運行時參數
2. **Docker Compose**: 服務定義和網路配置
3. **監控配置**: 指標收集和告警規則
4. **腳本**: 部署和維護自動化

### 🛡️ 安全考量
- 敏感配置通過環境變數注入
- 預設值適合開發環境
- 生產環境需要自定義配置

## 🚀 使用流程

### 快速啟動
```bash
# 從專案根目錄
./start-docker.sh

# 或指定配置路徑
./config/scripts/docker-start.sh
```

### 自定義配置
1. 複製環境變數模板: `cp config/env-example.txt .env`
2. 修改環境變數: `vim .env`
3. 自定義服務配置: `vim config/docker/docker-compose.yml`
4. 調整監控規則: `vim config/monitoring/prometheus.yml`

### 管理命令
```bash
# 查看服務狀態
docker-compose -f config/docker/docker-compose.yml ps

# 查看日誌
docker-compose -f config/docker/docker-compose.yml logs -f

# 停止服務
docker-compose -f config/docker/docker-compose.yml down

# 清理數據
docker-compose -f config/docker/docker-compose.yml down -v
```

## 📊 服務架構

```
┌─────────────────────────────────────────────────────────────┐
│                    SRE Platform 服務網路                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    sre-network                          │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ PostgreSQL  │ │   Redis     │ │   Grafana           │ │ │
│  │  │   :5432     │ │   :6379     │ │     :3000           │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  │                                                         │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ Keycloak    │ │ ChromaDB    │ │ VictoriaMetrics     │ │ │
│  │  │   :8080     │ │   :8000     │ │   :8480/8481        │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  │                                                         │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ Prometheus  │ │ SNMP Exp.  │ │   Control Plane     │ │ │
│  │  │   :8429     │ │   :9116     │ │     :8081           │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  │                                                         │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │                 SRE Assistant                       │ │ │
│  │  │                   :8001                             │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔗 相關文件

- [專案主要 README](README.md)
- [配置目錄詳細說明](config/README.md)
- [Docker 環境指南](config/DOCKER_README.md)
- [開發指南](docs/DEV_GUIDE.md)
- [部署說明](docs/ROADMAP.md)

---

*最後更新: 2024年9月*
