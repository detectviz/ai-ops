# AGENT.md - SRE Platform AI 代理開發指南

本文件為 AI 代理提供操作此 Monorepo 的具體、可執行的指南。

## 1. 專案概覽

SRE Platform 是一個採用 Monorepo 架構的現代化維運平台，整合了兩個核心服務：

- **Control Plane (Go)**: 指揮中心，提供 UI 介面與應用管理。
- **SRE Assistant (Python)**: 無介面的專家代理，執行診斷與自動化任務。

**核心互動模式**: `Control Plane` 作為指揮官，透過呼叫 `SRE Assistant` 的 API 來執行複雜任務。

## 2. 環境設定與執行

本專案使用 `make` 提供統一的開發體驗。**所有操作都應從專案根目錄執行。**

### 2.1. 一鍵設定

若要設定完整的本地開發環境，包含所有系統依賴、Go 模組和 Python 套件，請執行：
```bash
make setup-dev
```

### 2.2. 啟動與停止服務

- **啟動所有背景服務** (Keycloak, PostgreSQL, VictoriaMetrics, etc.):
  ```bash
  make start-services
  ```
- **停止所有背景服務**:
  ```bash
  make stop-services
  ```
- **驗證環境**:
  ```bash
  make verify
  ```

## 3. 開發與測試

### 3.1. 執行測試

- **執行所有測試** (Go & Python):
  ```bash
  make test
  ```
- **僅執行 Control Plane (Go) 測試**:
  ```bash
  make test-go
  ```
- **僅執行 SRE Assistant (Python) 測試**:
  ```bash
  make test-py
  ```

### 3.2. 獨立開發

- **Control Plane**:
  ```bash
  # 進入服務目錄
  cd services/control-plane
  # 執行 (需先啟動依賴服務)
  go run cmd/server/main.go
  ```

- **SRE Assistant**:
  ```bash
  # 進入服務目錄
  cd services/sre-assistant
  # 執行 (需先啟動依賴服務)
  poetry run python -m sre_assistant.main
  ```

## 4. 關鍵原則與規範

### 4.1. API 契約

- **唯一真實來源**: `pkg/api/openapi.yaml`。
- **修改流程**: 任何 API 變更必須先更新此 `openapi.yaml` 文件。

### 4.2. 認證

- **機制**: Keycloak M2M JWT Token。
- **流程**: `Control Plane` 獲取 Token，並在呼叫 `SRE Assistant` 時於 `Authorization` 標頭中提供。

### 4.3. Git Commit

- **規範**: 使用 Conventional Commits，訊息使用繁體中文。
- **範例**:
  ```
  feat: 新增部署診斷功能
  fix: 修復 JWT 驗證錯誤
  docs: 更新 API 文件
  ```

### 4.4. 重要注意事項

- **不要直接修改** `pkg/api/openapi.yaml` 以外的 API 定義。
- **不要硬編碼**敏感資訊，使用環境變數。
- **務必更新**相關文件當修改架構或 API。
- **保持服務**之間的低耦合，透過 API 通訊。
