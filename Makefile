# sre-platform/Makefile
#
# 統一的開發指令管理
# 使用方式: make help

.PHONY: help setup-dev setup-postgres start-services stop-services restart-services logs ps verify clean test test-go test-py

# 預設目標：顯示幫助
help:
	@echo "SRE Platform - 本地開發環境管理指令"
	@echo "=========================================="
	@echo ""
	@echo "主要指令："
	@echo "  make setup-dev       - 執行完整的一鍵安裝與設定"
	@echo "  make start-services  - 啟動所有必要的背景服務 (Keycloak, ChromaDB)"
	@echo "  make stop-services   - 停止所有背景服務"
	@echo "  make restart-services- 重啟所有背景服務"
	@echo "  make verify          - 驗證所有服務是否正常運行"
	@echo "  make ps              - 查看服務運行狀態 (類似 docker-compose ps)"
	@echo "  make logs            - 查看手動啟動服務的日誌"
	@echo "  make clean           - (危險) 停止服務並清理所有本地資料"
	@echo ""
	@echo "開發指令："
	@echo "  make test            - 執行所有測試"
	@echo "  make test-go         - 執行 Control Plane 測試"
	@echo "  make test-py         - 執行 SRE Assistant 測試"
	@echo ""
	@echo "手動步驟 (如果 'setup-dev' 失敗):"
	@echo "  make install-deps    - 僅執行 setup_local_environment.sh 腳本"
	@echo "  make setup-postgres  - 僅執行手動的 PostgreSQL 設定"

# --- 主要指令 ---

# 完整設定
setup-dev: install-deps setup-postgres start-services verify
	@echo "✅ 本地開發環境已設定完成！"

# 停止所有服務
stop-services:
	@echo "🛑 停止手動啟動的服務 (Keycloak, ChromaDB)..."
	@pkill -f "/opt/chroma_venv/bin/chroma run" || true
	@pkill -f "kc.sh start-dev" || true
	@echo "🛑 停止系統服務 (VictoriaMetrics, Grafana, etc.)..."
	@sudo systemctl stop vmstorage vminsert vmselect vmagent snmp_exporter grafana-server redis-server postgresql || true
	@echo "✅ 所有服務已停止。"

# 啟動服務
start-services:
	@echo "🚀 啟動系統服務 (VictoriaMetrics, Grafana, etc.)..."
	@sudo systemctl start postgresql redis-server grafana-server vmstorage vminsert vmselect vmagent snmp_exporter
	@echo "🚀 啟動手動服務 (ChromaDB, Keycloak)..."
	@echo "啟動 ChromaDB..."
	@nohup /opt/chroma_venv/bin/chroma run --path /tmp/chroma_db > /tmp/chroma.log 2>&1 &
	@echo "啟動 Keycloak..."
	@nohup /opt/keycloak/bin/kc.sh start-dev > /tmp/keycloak.log 2>&1 &
	@echo "⏳ 等待服務就緒 (約 20 秒)..."
	@sleep 20
	@make ps

# 重啟服務
restart-services: stop-services start-services

# 驗證環境
verify:
	@echo "🔍 驗證環境..."
	@chmod +x ./local/verify_environment.sh
	@./local/verify_environment.sh
	@make ps

# 查看日誌
logs:
	@echo "📄 查看 ChromaDB 和 Keycloak 日誌 (Ctrl+C 退出)..."
	@tail -f /tmp/chroma.log /tmp/keycloak.log

# 查看狀態
ps:
	@echo "📊 系統服務狀態 (systemd):"
	@systemctl is-active postgresql redis-server grafana-server vmstorage vminsert vmselect vmagent snmp_exporter || true
	@echo ""
	@echo "📊 背景進程狀態 (ps):"
	@ps aux | grep -E '/opt/chroma_venv/bin/chroma run|Dkc.home.dir=/opt/keycloak' | grep -v 'grep' || echo "ChromaDB 或 Keycloak 未運行"

# 執行所有測試
test: test-go test-py

# 執行 Control Plane 測試
test-go:
	@echo "🧪 執行 Control Plane 測試..."
	cd services/control-plane && go test ./... -v

# 執行 SRE Assistant 測試
test-py:
	@echo "🧪 執行 SRE Assistant 測試..."
	cd services/sre-assistant && poetry run pytest -v

# 清理環境
clean:
	@echo "🧹 清理環境..."
	@echo "⚠️  警告：這將停止服務並刪除 PostgreSQL 和 VictoriaMetrics 的資料！"
	@read -p "確定要繼續嗎？(y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	@make stop-services
	@echo "刪除資料目錄..."
	@sudo rm -rf /var/lib/victoriametrics /tmp/chroma_db
	@echo "✅ 環境已清理"

# --- 子指令 ---

# 執行安裝腳本
install-deps:
	@echo "📦 執行主安裝腳本..."
	@chmod +x ./local/setup_local_environment.sh
	@sudo ./local/setup_local_environment.sh

# 手動設定 PostgreSQL
setup-postgres:
	@echo "🐘 設定 PostgreSQL..."
	@sudo -u postgres psql -c "CREATE DATABASE sre_dev;" || true
	@sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';" || true
	@sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sre_dev TO postgres;"