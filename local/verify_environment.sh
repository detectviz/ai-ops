#!/bin/bash

# ==============================================================================
# SRE Platform 環境驗證腳本
# ==============================================================================
#
# 這個腳本用於驗證由 setup_local_environment.sh 安裝的各個服務是否正常運行。
#
# ==============================================================================

# --- Helper Functions for Colorized Output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print a check result
# $1: Service Name
# $2: Command to execute (should return 0 for success)
# $3: Success message (optional)
check_service() {
    local service_name=$1
    local command=$2
    local success_msg=$3

    printf "🔎 正在驗證 %-25s ... " "$service_name"
    if eval "$command" >/dev/null 2>&1; then
        printf "${GREEN}✅ 正常${NC}\n"
        if [ -n "$success_msg" ]; then
            printf "   └── ${YELLOW}%s${NC}\n" "$success_msg"
        fi
    else
        printf "${RED}❌ 失敗${NC}\n"
    fi
}

echo "========================================="
echo " SRE Platform 環境驗證"
echo "========================================="

# --- 監控服務 (VictoriaMetrics Stack) ---
echo -e "\n--- 核心監控服務 ---"
check_service "vmagent" "curl -s --fail http://localhost:8429/metrics | grep -q 'vmagent_remotewrite_rate_limit'"
check_service "snmp_exporter" "curl -s --fail http://localhost:9116/metrics | grep -q 'snmp_exporter_build_info'"
check_service "VictoriaMetrics (vmselect)" "curl -s --fail 'http://localhost:8481/select/0/prometheus/api/v1/label/__name__/values' | grep -q '\"status\":\"success\"'" "資料查詢 API 正常"

# --- 基礎設施服務 ---
echo -e "\n--- 基礎設施服務 ---"
check_service "Grafana" "curl -s --fail http://localhost:3000/api/health | grep -q '\"database\": \"ok\"'" "可訪問網址: http://localhost:3000"
check_service "Redis" "redis-cli ping | grep -q 'PONG'"
check_service "PostgreSQL" "pg_isready -h localhost -p 5432 -q"

# --- 手動啟動服務提醒 ---
echo -e "\n--- 手動啟動服務 (提醒) ---"
echo "以下服務需要手動啟動，本腳本僅檢查檔案是否存在："
check_service "Keycloak (files)" "test -f /opt/keycloak/bin/kc.sh" "啟動指令: /opt/keycloak/bin/kc.sh start-dev"
check_service "ChromaDB (pip package)" "command -v chroma >/dev/null" "啟動指令: chroma run --path /path/to/db"


echo -e "\n========================================="
echo "驗證完畢。"
echo "========================================="
