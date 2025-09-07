# SRE Platform Docker 環境

本專案提供了一個完整的 Docker 容器化環境，包含所有 SRE Platform 所需的依賴服務。

## 🚀 快速開始

### 前置要求

- Docker (20.10+)
- Docker Compose (2.0+) 或 docker-compose
- 至少 4GB RAM 和 10GB 磁碟空間

### 啟動環境

```bash
# 克隆專案並進入目錄
git clone <repository-url>
cd sre-platform

# 啟動所有服務
./docker-start.sh

# 或手動啟動
docker-compose up -d
```

### 停止環境

```bash
# 停止所有服務
docker-compose down

# 停止並刪除資料卷
docker-compose down -v
```

## 📋 服務總覽

| 服務名稱 | 端口 | 描述 | 預設帳號 |
|---------|------|------|----------|
| **PostgreSQL** | 5432 | 主要資料庫 | postgres/postgres |
| **Redis** | 6379 | 快取和會話存儲 | - |
| **Grafana** | 3000 | 儀表板和可視化 | admin/admin |
| **VictoriaMetrics** | 8480/8481 | 時序資料庫 | - |
| **Prometheus** | 8429 | 指標收集 | - |
| **SNMP Exporter** | 9116 | 網路設備監控 | - |
| **ChromaDB** | 8000 | 向量資料庫 | - |
| **Keycloak** | 8080 | 身份認證服務 | admin/admin |

## 🔧 服務配置

### 環境變數

可以在 `.env` 文件中設置以下環境變數：

```bash
# 資料庫
POSTGRES_DB=sre_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Redis
REDIS_URL=redis://redis:6379/0

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin

# Keycloak
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
```

### 持久化資料

所有服務的資料都會持久化到 Docker 卷中：

- `postgres_data`: PostgreSQL 資料庫檔案
- `redis_data`: Redis 快取資料
- `grafana_data`: Grafana 配置和儀表板
- `vmstorage_data`: VictoriaMetrics 時序資料
- `chromadb_data`: ChromaDB 向量資料

## 🔍 健康檢查

### 自動健康檢查

所有服務都配置了健康檢查，確保服務正常運行：

```bash
# 查看服務狀態
docker-compose ps

# 查看特定服務日誌
docker-compose logs -f grafana

# 查看所有服務健康狀態
./docker-start.sh  # 會自動檢查服務狀態
```

### 手動健康檢查

```bash
# PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Redis
docker-compose exec redis redis-cli ping

# VictoriaMetrics
curl http://localhost:8481/health

# Grafana
curl http://localhost:3000/api/health

# ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# Keycloak
curl http://localhost:8080/health/ready
```

## 📊 監控和日誌

### 指標收集

Prometheus 會自動收集所有服務的指標：

- SRE Assistant: `http://localhost:8001/api/v1/metrics`
- Control Plane: `http://localhost:8081/api/v1/metrics`
- VictoriaMetrics: `http://localhost:8429/metrics`
- 其他服務的標準指標端點

### 日誌查看

```bash
# 查看所有服務日誌
docker-compose logs

# 查看特定服務日誌
docker-compose logs -f postgres
docker-compose logs -f keycloak

# 查看最近的錯誤日誌
docker-compose logs --tail=100 | grep ERROR
```

## 🔒 安全注意事項

### 開發環境

此配置專為開發環境設計，包含：

- 預設密碼（請勿在生產環境使用）
- 開放的網路訪問
- 簡化的認證設定

### 生產環境建議

生產環境部署時請考慮：

1. **密碼管理**
   - 使用強密碼
   - 通過環境變數或密碼管理系統設置

2. **網路安全**
   - 使用內部網路
   - 配置防火牆規則
   - 啟用 TLS/SSL

3. **資源限制**
   - 設置 CPU 和記憶體限制
   - 配置日誌輪轉

4. **備份策略**
   - 定期備份資料卷
   - 測試恢復程序

## 🐛 故障排除

### 常見問題

#### 端口衝突

如果本地端口被佔用，可以修改 `docker-compose.yml` 中的端口映射：

```yaml
services:
  grafana:
    ports:
      - "3001:3000"  # 改為 3001
```

#### 服務啟動失敗

1. 檢查系統資源是否充足
2. 查看具體服務的日誌：

```bash
docker-compose logs <service_name>
```

3. 確保沒有其他服務佔用相同端口

#### 資料持久化問題

如果資料卷損壞，可以重置：

```bash
# 停止服務並刪除資料卷
docker-compose down -v

# 重新啟動
docker-compose up -d
```

### 獲取幫助

如果遇到問題，請檢查：

1. Docker 和 Docker Compose 版本
2. 系統資源使用情況
3. 網路連接狀態
4. 服務特定的錯誤日誌

## 📚 相關文件

- [SRE Platform 架構說明](../docs/ARCHITECTURE.md)
- [開發環境設置](../docs/DEV_GUIDE.md)
- [API 參考文檔](../docs/API_REFERENCE.md)
- [部署指南](../docs/ROADMAP.md)

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request 來改進 Docker 環境配置！
