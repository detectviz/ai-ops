# SRE Platform 配置目錄

本目錄包含 SRE Platform 所有配置文件，按照功能分類組織。

## 📁 目錄結構

```
config/
├── docker/                    # Docker 容器配置
│   └── docker-compose.yml    # 服務編排配置
├── monitoring/               # 監控配置
│   ├── prometheus.yml        # Prometheus 指標收集配置
│   └── snmp.yml             # SNMP Exporter 配置
├── scripts/                  # 管理腳本
│   └── docker-start.sh      # Docker 環境啟動腳本
├── DOCKER_README.md         # Docker 環境詳細說明
├── env-example.txt          # 環境變數配置模板
└── README.md               # 本文件
```

## 🚀 快速開始

### 使用簡易啟動腳本

```bash
# 從專案根目錄啟動
./start-docker.sh

# 或使用完整路徑
./config/scripts/docker-start.sh
```

### 手動管理服務

```bash
# 啟動服務
docker-compose -f config/docker/docker-compose.yml up -d

# 查看狀態
docker-compose -f config/docker/docker-compose.yml ps

# 查看日誌
docker-compose -f config/docker/docker-compose.yml logs -f

# 停止服務
docker-compose -f config/docker/docker-compose.yml down
```

## ⚙️ 配置說明

### Docker Compose 配置 (`docker/docker-compose.yml`)

- **服務定義**: 包含 8 個核心服務
- **網路配置**: 使用 `sre-network` 自定義網路
- **數據持久化**: 所有服務數據保存到 Docker 卷
- **健康檢查**: 每個服務都有健康檢查配置
- **依賴關係**: 服務間正確的啟動順序

### 監控配置 (`monitoring/`)

#### Prometheus 配置 (`prometheus.yml`)
- **指標收集**: 配置所有服務的指標收集
- **抓取間隔**: 根據服務類型設置不同間隔
- **自定義指標**: SRE Assistant 和 Control Plane 的 `/api/v1/metrics`

#### SNMP 配置 (`snmp.yml`)
- **設備支持**: Cisco, Juniper, 通用網路設備, Linux/Windows 伺服器
- **SNMP 版本**: 支持 SNMP v2c
- **OID 映射**: 關鍵指標的 OID 配置

### 環境變數 (`env-example.txt`)

- **資料庫配置**: PostgreSQL 連接參數
- **認證服務**: Keycloak 和 Grafana 預設帳號
- **應用配置**: SRE Assistant 和 Control Plane 設定
- **安全配置**: Session 金鑰等敏感信息

## 🔧 自定義配置

### 修改端口映射

如果本地端口衝突，可以修改 `docker/docker-compose.yml`：

```yaml
services:
  grafana:
    ports:
      - "3001:3000"  # 改為 3001
```

### 添加環境變數

1. 複製 `env-example.txt` 為 `.env`
2. 修改需要的環境變數
3. Docker Compose 會自動載入 `.env` 文件

### 自定義監控配置

修改 `monitoring/prometheus.yml` 添加新的指標收集目標：

```yaml
scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['my-service:8080']
```

## 🔒 安全注意事項

### 開發環境

- 使用預設密碼（生產環境必須修改）
- 開放網路訪問（生產環境應限制）
- 日誌級別設置為 INFO（生產環境可設為 WARN）

### 生產環境建議

1. **密碼管理**
   - 修改所有預設密碼
   - 使用密碼管理系統

2. **網路安全**
   - 配置防火牆規則
   - 使用內部網路
   - 啟用 TLS/SSL

3. **資源限制**
   - 設置 CPU 和記憶體限制
   - 配置日誌輪轉

## 🐛 故障排除

### 常見問題

#### 服務啟動失敗

```bash
# 查看具體錯誤
docker-compose -f config/docker/docker-compose.yml logs <service_name>

# 檢查端口衝突
netstat -tlnp | grep :<port>
```

#### 數據持久化問題

```bash
# 重置所有數據卷
docker-compose -f config/docker/docker-compose.yml down -v
docker-compose -f config/docker/docker-compose.yml up -d
```

#### 網路連接問題

```bash
# 檢查網路
docker network ls
docker network inspect sre-network
```

## 📚 相關文檔

- [專案主要 README](../../README.md)
- [Docker 環境詳細說明](DOCKER_README.md)
- [開發指南](../../docs/DEV_GUIDE.md)
- [API 參考](../../docs/API_REFERENCE.md)

## 🤝 貢獻

歡迎提交配置改進建議！請確保：

1. 更新對應的說明文檔
2. 測試配置的向後兼容性
3. 遵循現有的命名規範
4. 添加必要的註釋
