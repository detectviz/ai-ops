#!/bin/bash

# ==============================================================================
# SRE Assistant 依賴項本地安裝腳本 (Best-Effort)
# ==============================================================================
#
# 警告：這是一個盡力而為的腳本，不保證在所有環境中都能成功執行或保持冪等性。
# 本腳本假設執行環境為 Debian/Ubuntu 系統，並擁有 sudo 權限。
# 執行過程中可能需要手動介入。
#
# 架構師：Jules
# ==============================================================================

set -e  # 若有任何指令失敗，立即中止腳本

# --- 0. 系統更新與基礎工具 ---
echo ">>> [步驟 0/8] 更新系統套件..."
sudo apt-get update
sudo apt-get install -y wget curl gnupg software-properties-common ca-certificates

# --- 1. PostgreSQL 資料庫 ---
echo ">>> [步驟 1/8] 安裝 PostgreSQL..."
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
echo "--- PostgreSQL 已安裝。請手動建立資料庫與使用者：---"
echo "  sudo -u postgres psql -c \"CREATE DATABASE sre_dev;\""
echo "  sudo -u postgres psql -c \"CREATE USER postgres WITH PASSWORD 'postgres';\""
echo "  sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE sre_dev TO postgres;\""

# --- 2. Redis 快取 ---
echo ">>> [步驟 2/8] 安裝 Redis..."
sudo apt-get install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
echo "--- Redis 已安裝並啟動。---"

# --- 3. Grafana 儀表板 ---
echo ">>> [步驟 3/8] 安裝 Grafana..."
sudo mkdir -p /etc/apt/keyrings/
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install -y grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
echo "--- Grafana 已安裝。請至 http://localhost:3000 訪問。---"

# --- 4. ChromaDB 向量資料庫 ---
echo ">>> [步驟 4/8] 安裝 ChromaDB..."
# 為符合 PEP 668，我們將在虛擬環境中安裝 ChromaDB
sudo apt-get install -y python3-pip python3.12-venv
sudo python3 -m venv /opt/chroma_venv
sudo /opt/chroma_venv/bin/pip install chromadb
echo "--- ChromaDB 已安裝至 /opt/chroma_venv。---"

# --- 5. VictoriaMetrics Cluster (From local files) ---
echo ">>> [步驟 5/8] 安裝 VictoriaMetrics Cluster..."
echo "正在停止可能正在運行的舊版監控服務..."
sudo systemctl stop vmstorage vminsert vmselect vmagent snmp_exporter >/dev/null 2>&1 || true

echo "正在從本地文件複製 VictoriaMetrics Cluster 元件..."
sudo cp ./local/victoria-metrics-linux-amd64-v1.125.0-cluster/vmstorage-prod /usr/local/bin/vmstorage
sudo cp ./local/victoria-metrics-linux-amd64-v1.125.0-cluster/vminsert-prod /usr/local/bin/vminsert
sudo cp ./local/victoria-metrics-linux-amd64-v1.125.0-cluster/vmselect-prod /usr/local/bin/vmselect

echo "建立 VictoriaMetrics 資料目錄..."
sudo mkdir -p /var/lib/victoriametrics
sudo chown -R $SUDO_USER:$SUDO_USER /var/lib/victoriametrics

echo "建立 vmstorage systemd 服務..."
cat <<EOF | sudo tee /etc/systemd/system/vmstorage.service
[Unit]
Description=VictoriaMetrics vmstorage
After=network.target

[Service]
ExecStart=/usr/local/bin/vmstorage \\
  -storageDataPath=/var/lib/victoriametrics \\
  -retentionPeriod=1
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "建立 vminsert systemd 服務..."
cat <<EOF | sudo tee /etc/systemd/system/vminsert.service
[Unit]
Description=VictoriaMetrics vminsert
After=network.target vmstorage.service

[Service]
ExecStart=/usr/local/bin/vminsert \\
  -storageNode=127.0.0.1:8400
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "建立 vmselect systemd 服務..."
cat <<EOF | sudo tee /etc/systemd/system/vmselect.service
[Unit]
Description=VictoriaMetrics vmselect
After=network.target vmstorage.service

[Service]
ExecStart=/usr/local/bin/vmselect \\
  -storageNode=127.0.0.1:8401
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "--- VictoriaMetrics Cluster 元件已安裝。---"

# --- 6. vmagent (From local files) ---
echo ">>> [步驟 6/8] 安裝 vmagent..."
echo "正在從本地文件複製 vmagent..."
sudo cp ./local/vmutils-linux-amd64-v1.125.0/vmagent-prod /usr/local/bin/vmagent

echo "建立 vmagent 設定檔目錄與檔案..."
sudo mkdir -p /etc/vmagent
cat <<EOF | sudo tee /etc/vmagent/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'self_vmagent'
    static_configs:
      - targets: ['localhost:8429']   # vmagent 自身 metrics
  - job_name: 'snmp'
    static_configs:
      - targets: ['localhost:9116']   # snmp_exporter metrics
EOF

echo "建立 vmagent systemd 服務..."
cat <<EOF | sudo tee /etc/systemd/system/vmagent.service
[Unit]
Description=vmagent
After=network.target

[Service]
ExecStart=/usr/local/bin/vmagent \\
  -promscrape.config=/etc/vmagent/prometheus.yml \\
  -remoteWrite.url=http://localhost:8480/insert/0/prometheus
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "--- vmagent 已安裝。---"

# --- 7. snmp_exporter (From local files) ---
echo ">>> [步驟 7/8] 安裝 snmp_exporter..."
echo "正在從本地文件複製 snmp_exporter..."
sudo cp ./local/snmp_exporter-0.29.0.linux-amd64/snmp_exporter /usr/local/bin/

echo "建立 snmp_exporter 設定檔目錄與檔案..."
sudo mkdir -p /etc/snmp_exporter
cat <<EOF | sudo tee /etc/snmp_exporter/snmp.yml
modules:
  default:
    walk: [1.3.6.1.2.1.1]
EOF

echo "建立 snmp_exporter systemd 服務..."
cat <<EOF | sudo tee /etc/systemd/system/snmp_exporter.service
[Unit]
Description=snmp_exporter
After=network.target

[Service]
ExecStart=/usr/local/bin/snmp_exporter \\
  --config.file=/etc/snmp_exporter/snmp.yml \\
  --web.listen-address=:9116
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "--- snmp_exporter 已安裝。---"

# --- 8. Keycloak 身份驗證服務 (From local files) ---
echo ">>> [步驟 8/8] 安裝 Keycloak..."
# Keycloak 需要 Java 執行環境
sudo apt-get install -y default-jdk
echo "正在從本地文件複製 Keycloak..."
sudo cp -r ./local/keycloak-26.3.3 /opt/keycloak
echo "變更 Keycloak 目錄擁有者以允許開發模式..."
sudo chown -R $SUDO_USER:$SUDO_USER /opt/keycloak
echo "--- Keycloak 已安裝至 /opt/keycloak。需要手動建立服務。---"
echo "--- 可使用 '/opt/keycloak/bin/kc.sh start-dev' 以開發模式啟動。---"

# --- 9. 啟用並啟動所有監控服務 ---
echo ">>> [步驟 9/9] 啟用並啟動所有監控服務..."
sudo systemctl daemon-reload
sudo systemctl enable --now vmstorage vminsert vmselect vmagent snmp_exporter
echo "--- 所有監控服務已啟用並啟動。---"

echo "=============================================================================="
echo "本地環境安裝腳本執行完畢。請檢查上方是否有錯誤訊息。"
echo "提醒：部分元件需要手動進行後續設定。"
echo "=============================================================================="
