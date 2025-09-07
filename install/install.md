# 本地環境安裝手冊

此文件說明如何使用自動化腳本設定 SRE Platform 的本地開發環境。

## 1. 自動化安裝

我們強烈建議使用 `setup_local_environment.sh` 腳本來一鍵安裝所有必要的服務。此腳本會從 `install/` 目錄中複製必要的元件，並設定相關的 systemd 服務。

**執行腳本：**

```bash
# 賦予腳本執行權限
chmod +x ./install/setup_local_environment.sh

# 執行安裝
./install/setup_local_environment.sh
```

此腳本會自動安裝並啟動以下服務：
*   Redis
*   Grafana
*   VictoriaMetrics Cluster (vmstorage, vminsert, vmselect)
*   vmagent
*   snmp_exporter

## 2. 後續手動設定

腳本執行完畢後，部分服務需要進行手動設定或啟動。

### PostgreSQL
腳本會安裝 PostgreSQL，但您需要手動建立開發用的資料庫和使用者：
```bash
sudo -u postgres psql -c "CREATE DATABASE sre_dev;"
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sre_dev TO postgres;"
```

### ChromaDB
腳本會透過 pip 安裝 ChromaDB，但不會自動啟動伺服器。您需要手動啟動：
```bash
# 在您選擇的路徑啟動 ChromaDB 伺服器
chroma run --path /path/to/your/chroma/db
```

### Keycloak
腳本會將 Keycloak 安裝至 `/opt/keycloak`，但不會建立 systemd 服務。您可以用開發模式手動啟動：
```bash
/opt/keycloak/bin/kc.sh start-dev
```

## 3. 驗證

安裝完成後，我們提供了一個驗證腳本來快速檢查所有自動啟動的服務是否正常運行。

**執行驗證腳本：**

```bash
# 賦予腳本執行權限
chmod +x ./install/verify_environment.sh

# 執行驗證
./install/verify_environment.sh
```

此腳本會檢查核心監控服務、Grafana、Redis 和 PostgreSQL 的狀態。
