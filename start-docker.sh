#!/bin/bash

# SRE Platform Docker 環境啟動腳本
# 從專案根目錄啟動所有服務

echo "🚀 啟動 SRE Platform Docker 環境..."
echo "📁 配置目錄: config/"

# 執行實際的啟動腳本
exec ./config/scripts/docker-start.sh "$@"
