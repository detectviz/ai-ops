# 部署帶有使用者介面的應用

本指南涵蓋將帶有 UI 的代理應用程式部署到 Google Cloud 的策略，重點關注開發、測試和示範的方法。

### 1. 部署策略

在部署同時包含後端和前端 UI 的應用程式時，存在兩種主要策略。

#### A. 統一一部署
*   **描述**：後端和前端被打包並從單一、統一的服務中提供。
*   **最適用於**：這種方法更簡單，非常適合**開發和測試目的**。
*   **技術**：Google Cloud Run 支援此模型，並可透過單一的 [Identity-Aware Proxy (IAP)](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run) 端點來保護它。

#### B. 解耦部署
*   **描述**：後端和前端作為獨立的服務運行。
*   **最適用於**：這是一種更穩健、**面向生產**的架構。
*   **使用時機**：如果您的後端技術不適合提供 Web 前端 (例如，如果您正在使用專用的 `Agent Engine`)，則有必要採用此方法。在這種情況下，前端會被單獨部署到另一個 Cloud Run 服務或 Cloud Storage。

::: tip 注意
本指南專注於使用 Google Cloud Run 的**統一一部署**策略，這對於快速開發和內部測試是理想的。
:::

### 2. 使用 IAP 部署到 Cloud Run

部署方法取決於您是使用框架內建的 UI 還是自訂的 UI。

#### A. 情境 1：內建框架 UI
許多代理框架 (如 ADK) 包含一個內建的 Web UI 或「遊樂場」([`adk-web`](https://github.com/google/adk-web))，預設情況下與後端 API 一起提供。這對於快速將服務提供給其他開發人員或測試人員非常有用。

**i. 部署服務：**
導覽至您專案的根目錄並執行預先設定的 `make` 指令：
```bash
make backend IAP=true
```
這個單一指令通常會處理建置容器、將其推送到註冊中心、部署到 Cloud Run 以及設定 IAP。

#### B. 情境 2：自訂前端
如果您有一個獨立的自訂前端 (例如，用於 `gemini_fullstack` 代理或 `live_api` 的 React 應用程式)，並希望將其與後端一起部署以進行測試，則該過程需要自訂容器設定。

**策略**：為了開發，修改 `Dockerfile` 以在單一容器內建置並執行前端的開發伺服器和後端的 API 伺服器。

> **重要提示：** 這種方法，特別是運行像 `npm run dev` 這樣的前端開發伺服器，僅適用於**開發和測試目的**。對於生產環境，您應該建置靜態前端資產並有效地提供它們。

**i. 設定 Dockerfile：**
建立或修改您的 `Dockerfile` 以安裝 Python 和 Node.js 的依賴項，並同時啟動兩個服務。

::: details 用於組合後端和前端的 Dockerfile 範例
```dockerfile
FROM python:3.11-slim

# 安裝 Node.js 和 npm
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.6.12

WORKDIR /code

# 複製後端檔案
COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./app ./app

# 複製前端檔案
COPY ./frontend ./frontend

# 安裝依賴項
RUN uv sync --frozen && npm --prefix frontend install

EXPOSE 8000 5173

# 並行啟動後端和前端
CMD ["sh", "-c", "ALLOW_ORIGINS='*' uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 & npm --prefix frontend run dev -- --host 0.0.0.0 & wait"]
```
:::


**ii. 🚀 部署組合服務：**
部署時，您必須指示 Cloud Run 將流量導向**前端的連接埠**。將 `PORT` 變數傳遞給您的 `make` 指令。如果您的前端在連接埠 `5173` 上運行，如範例所示：
```bash
make backend IAP=true PORT=5173
```
這可確保受 IAP 保護的公開 URL 提供您的使用者介面。

### 3. 管理使用者存取
部署後，您的 Cloud Run 服務受到 IAP 的保護，但尚無使用者被授權存取。您必須將「httpsResourceAccessor」角色授予適當的使用者或 Google 群組。

➡️ 遵循官方 Google Cloud 文件來管理您服務的存取權限：[管理使用者或群組存取](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run#manage_user_or_group_access)。
