# 🤖 AGENT.md - SRE Platform AI 代理開發指南

> 本文件為 AI 代理與開發者提供操作 **SRE Platform Monorepo** 的具體指引，確保團隊在本地環境即可高效開發、測試與維護。

---

### Jules 🚫 禁止事項
- ❌ **安裝 Docker**: Sandbox 環境無法安裝 Docker，必須使用本地安裝 `install/install.md` 中的方式安裝

---

### 🛡️ AI 代理職責：專案文件守護者

本代理（Jules）被賦予**專案文件守護者**的角色，核心職責是確保**程式碼、文件與 API 契約**之間保持嚴格的一致性。

**核心任務**:
1.  **檢查文件同步性**: 每當程式碼或架構更新時，必須檢查 `docs/`、`README.md`、`AGENT.md`以及 `pkg/api/*.yaml` 是否需要同步更新。
2.  **避免過時資訊**: 若發現文件內容過時、矛盾或遺漏，將主動標記並提出更新建議。
3.  **自動提示更新**: 當 PR 或 Commit 涉及以下情境，將自動要求更新對應文件：
    - API 介面變更 → 檢查 `pkg/api/*.yaml` 與 `docs/API_REFERENCE.md`
    - 環境依賴更新 → 檢查 `AGENT.md` 與 `README.md`
    - 新增功能/模組 → 檢查 `ROADMAP.md`、架構圖

---

## 📋 專案總覽

SRE Platform 採用 **Monorepo 架構**，核心由兩大服務組成：

### 🏗️ 核心服務架構

| 服務 | 技術棧 | 主要責任 |
|------|--------|----------|
| **Control Plane** | Go + HTMX | 指揮中心，負責 UI、資源管理與指令下達 |
| **SRE Assistant** | Python/FastAPI | 後端專家代理，執行診斷、自動化與維運任務 |

### 🔄 服務互動模式
```
Control Plane ←─ OpenAPI ─→ SRE Assistant
     │                           │
     ├── UI 操作                 ├── AI 診斷
     ├── 資源管理                 ├── 自動化任務
     └── 任務協調                 └── 維運分析
```

---

## ⚙️ 開發環境設定

本專案提供統一的 `Makefile` 指令，所有操作需於 **專案根目錄** 執行。

### 🚀 快速開始

#### 1️⃣ 一鍵初始化環境
```bash
make setup-dev
```

**功能**: 安裝所有依賴項
- ✅ Go 模組與工具
- ✅ Python 套件 (Poetry)
- ✅ 開發工具與檢查器

#### 2️⃣ 啟動基礎服務
```bash
# 啟動所有依賴服務
make start-services

# 停止所有服務
make stop-services

# 驗證環境狀態
make verify
```

**啟動的服務**:
- 🔐 **Keycloak** - 身份認證與授權
- 🗄️ **PostgreSQL** - 主要資料庫
- ⚡ **Redis** - 快取與任務佇列
- 📊 **VictoriaMetrics** - 時間序列資料庫
- 🧠 **ChromaDB** - 向量資料庫

---

## 🛠️ 開發與測試流程

### 🧪 測試執行

```bash
# 執行所有測試套件
make test

# 分別執行各服務測試
make test-go    # Control Plane (Go)
make test-py    # SRE Assistant (Python)
```

### 🔧 獨立開發模式

#### Control Plane (Go)
```bash
cd services/control-plane
go run cmd/server/main.go
```

#### SRE Assistant (Python)
```bash
cd services/sre-assistant
poetry run python -m sre_assistant.main
```

### 📊 開發工作流程建議

1. **功能開發** → 2. **單元測試** → 3. **整合測試** → 4. **API 測試** → 5. **提交 PR**

---

## 📏 關鍵規範

### 📄 API 契約規範

#### 🎯 唯一真實來源 (Single Source of Truth)

| 服務 | OpenAPI 規範文件 | 用途 |
|------|------------------|------|
| **Control Plane** | `pkg/api/control-plane-openapi.yaml` | UI 與資源管理 API |
| **SRE Assistant** | `pkg/api/sre-assistant-openapi.yaml` | 診斷與自動化 API |

#### ⚠️ 修改原則
- 🔄 **API 更新** = **OpenAPI 文件修改** + **程式碼實作**
- ✅ **PR 要求**: 必須同步包含 API 文件與程式碼變更
- 🚫 **禁止**: 直接修改服務程式碼中的 API 定義
        

### 🔐 認證與授權

#### 🛡️ 安全架構
- **身份驗證**: Keycloak M2M JWT Token
- **授權模式**: 服務間認證 (Service-to-Service)

#### 🔄 認證流程
```
Control Plane → Keycloak (取得 JWT)
     ↓
Control Plane → SRE Assistant (攜帶 Bearer Token)
     ↓
SRE Assistant ← 驗證 JWT 有效性
```

**請求範例**:
```bash
curl -H "Authorization: Bearer <jwt_token>" \
     http://localhost:8000/api/v1/diagnostics/deployment
```
    

### 📝 Git 提交規範

#### 📋 規範要求
- **格式**: [Conventional Commits](https://www.conventionalcommits.org/)
- **語言**: **繁體中文** 提交訊息
- **範圍**: 可選，但建議指定服務名稱

#### 💡 提交類型
| 類型 | 說明 | 範例 |
|------|------|------|
| `feat` | 新功能 | `feat(control-plane): 新增資源管理介面` |
| `fix` | 錯誤修復 | `fix(sre-assistant): 修正診斷任務狀態追蹤` |
| `docs` | 文件更新 | `docs: 補充 API 參考文件` |
| `refactor` | 重構 | `refactor: 優化資料庫查詢效能` |
| `test` | 測試相關 | `test: 新增整合測試案例` |
| `chore` | 建置/工具 | `chore: 更新依賴套件版本` |
    

### ⚠️ 開發注意事項

#### 🚫 禁止事項
- ❌ **API 修改**: 直接修改服務程式碼中的 API 定義（必須透過 `pkg/api/*.yaml`）
- ❌ **硬編碼**: 不可將敏感資訊寫死在程式碼中
- ❌ **直接呼叫**: 禁止服務間直接呼叫，必須透過 API

#### ✅ 最佳實務
- ✅ **同步更新**: 修改 API 時必須同步更新文件與測試
- ✅ **低耦合**: 保持服務間的低耦合設計
- ✅ **環境變數**: 統一使用環境變數管理配置
- ✅ **文件優先**: OpenAPI 文件為唯一真實來源

---

## 🎯 推進原則

| 原則 | 說明 | 實作方式 |
|------|------|----------|
| **🔧 務實** | 本地環境完整運行 | Sandbox 環境支援所有功能開發 |
| **📚 可維護** | 程式碼與文件同步 | 程式碼 + API 文件 + 測試三者一致 |
| **📊 可觀測** | 完整的監控能力 | 健康檢查、日誌、指標完整輸出 |
| **🤖 自動化** | 統一工作流程 | `Makefile` + CI/CD 自動化 |

---

## 📚 相關文件

- 📖 **API 參考**: [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md)
- 🗺️ **開發路線圖**: [`docs/ROADMAP.md`](./docs/ROADMAP.md)
- 🏗️ **架構說明**: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- 📋 **開發指南**: [`docs/DEV_GUIDE.md`](./docs/DEV_GUIDE.md)