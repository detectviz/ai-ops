# SRE Platform Frontend (Go/HTMX SSR)

SRE 平台的前端應用程式，採用伺服器端渲染 (Server-Side Rendering) 架構，提供現代化的用戶界面來管理資源、監控系統健康狀態和執行診斷任務。

## 🚀 技術棧

- **後端框架**: Go
- **前端互動**: HTMX
- **客戶端腳本**: Alpine.js
- **樣式**: Tailwind CSS
- **模板引擎**: Go `html/template`

## 🏗️ 專案結構

前端相關的所有檔案都位於 `services/control-plane/web/` 目錄下。

```
web/
├── static/            # 靜態資源 (CSS, JS, 圖片)
│   └── css/
│       └── app.css
├── templates/         # Go HTML 模板
│   ├── layouts/       # 頁面佈局
│   │   ├── app.html   # 主要應用程式佈局
│   │   └── auth.html  # 登入頁佈局
│   ├── pages/         # 具體頁面
│   │   ├── dashboard.html
│   │   ├── resources.html
│   │   └── incidents.html
│   ├── partials/      # 可由 HTMX 動態載入的 HTML 片段
│   │   ├── resource-table.html
│   │   └── incident-list.html
│   └── components/    # 可重用的 UI 組件模板
│       └── modal.html
└── README.md          # 本文件
```

## 🔧 開發工作流程

本專案的前端是與 Go 後端緊密整合的 SSR 應用，不作為獨立的 Node.js 專案運行。

### 環境需求

- Go 1.21+
- `make` 工具

### 快速開始

所有指令都應在 **專案根目錄** 執行。

1.  **安裝依賴與設定環境**
    ```bash
    # 此指令會安裝所有必要的 Go 和 Python 依賴
    make setup-dev
    ```

2.  **啟動依賴服務**
    ```bash
    # 啟動 PostgreSQL, Redis 等背景服務
    make start-services
    ```

3.  **運行 Control Plane 伺服器**
    ```bash
    # 進入 Control Plane 目錄
    cd services/control-plane

    # 啟動伺服器
    go run ./cmd/server/main.go
    ```
    應用程式將在 `http://localhost:8081` 啟動。

### 測試

```bash
# 在專案根目錄執行
# 此命令會執行所有 Control Plane 相關的 Go 測試
make test-go
```

## 🧩 架構說明

### 伺服器端渲染 (SSR)

所有 HTML 頁面都在 Go 後端進行渲染。前端的動態互動主要由 HTMX 驅動，它透過向伺服器請求 HTML 片段來更新頁面，而不是請求 JSON 數據。

### HTMX 互動模式

- **頁面載入**: 由 Go handler 渲染完整的頁面模板 (例如 `pages/dashboard.html`)。
- **動態內容**: 頁面中的特定區域 (例如一個表格) 使用 `hx-get` 屬性在載入時或由使用者觸發時，向後端 `/htmx/...` 端點請求內容。
- **後端回應**: `/htmx` 端點的 Go handler 只渲染對應的 HTML 片段 (partial)，例如 `partials/resource-table.html`，並將其回傳。
- **前端更新**: HTMX 接收到 HTML 片段後，根據 `hx-target` 和 `hx-swap` 屬性將其插入到頁面的正確位置。

### 狀態管理

- **伺服器狀態**: 由後端資料庫和服務層管理。
- **客戶端 UI 狀態**: 輕量級的 UI 狀態 (例如模態框的開關) 由 Alpine.js 處理。

## 🤝 貢獻指南

1.  **分支**: 從 `main` 分支創建新的功能分支 (`feature/your-feature-name`)。
2.  **開發**:
    - 在 `web/templates/` 中建立或修改 HTML 模板。
    - 在 `services/control-plane/internal/handlers/` 中新增或修改對應的 Go 處理器。
    - 在 `services/control-plane/cmd/server/main.go` 中註冊新的路由。
3.  **測試**: 確保 `make test-go` 能夠成功執行。
4.  **提交**: 使用「約定式提交」格式 (`feat(control-plane): ...`) 提交更改。
5.  **Pull Request**: 發起 PR 到 `main` 分支。

## 📝 開發備註

- **API 契約**: 所有後端 API 呼叫都應遵循 `pkg/api/control-plane-openapi.yaml` 的規範。HTMX 處理器是 UI 層的一部分，但其調用的服務應與 OpenAPI 對齊。
- **程式碼風格**: 遵循標準的 Go 程式碼風格。
- **註解**: 所有新的 Go 程式碼和 HTML 模板都應包含繁體中文註解。
