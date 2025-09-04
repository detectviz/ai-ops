# SRE Platform - 新一代自動化維運平台

[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![HTMX](https://img.shields.io/badge/HTMX-Driven-3498DB)](https://htmx.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

## 1. 專案簡介

SRE Platform 是一個採用 Monorepo 架構的現代化維運平台，旨在將複雜的 SRE 工作流程自動化、智能化。它整合了兩個核心服務，共同實現從被動故障應對到主動系統管理的轉型。

- **Control Plane (指揮官)**: 提供 Web UI 的指揮中心，負責應用管理、資源操作與任務發起。後端採用 Go，前端使用 HTMX 驅動，實現輕量、高效的互動體驗。
- **SRE Assistant (專家代理)**: 無介面的 (headless) 專家代理，基於 Google Agent Development Kit (ADK) 和 Python 构建，負責執行複雜的診斷、分析與自動化任務。

## 2. 核心架構

本平台的核心理念是將複雜性集中在 Go 後端的 `Control Plane`，並利用一個無介面的 `SRE Assistant` 來執行專家級的診斷任務。

```mermaid
graph TD
    subgraph "使用者層"
        User([使用者])
    end

    subgraph "指揮中心 (Control Plane)"
        ControlPlaneUI[Control Plane UI<br/>(HTMX, Go Backend)]
    end

    subgraph "專家代理 (SRE Assistant)"
        SREAssistantAPI[SRE Assistant API<br/>(Python, Google ADK)]
    end

    subgraph "外部系統"
        Observability[可觀測性平台<br/>(Prometheus, Loki)]
        AuditLogs[Control Plane Audit API]
    end

    User --> ControlPlaneUI
    ControlPlaneUI -- API 請求 (攜帶 M2M JWT) --> SREAssistantAPI
    SREAssistantAPI -- 執行工具 --> Observability
    SREAssistantAPI -- 查詢變更歷史 --> AuditLogs
```

> 欲了解更詳細的架構設計、權限模型與技術選型，請參閱 [**完整架構文件 (Full Architecture Document)**](docs/ARCHITECTURE.md)。

## 3. 快速入門 (本地開發)

本專案提供基於 `make` 的統一開發體驗，強烈建議所有開發者使用。

### 3.1. 環境需求

- 一個基於 Debian/Ubuntu 的環境
- `sudo` 權限
- Go 1.21+
- Python 3.11+ (及 Poetry)
- Make

### 3.2. 一鍵安裝與啟動

```bash
# 1. 克隆專案
git clone https://github.com/detectviz/sre-platform
cd sre-platform

# 2. 執行安裝、設定並啟動所有本地服務
#    此指令會自動安裝所有系統與語言層級的依賴
make setup-dev

# 3. (可選) 驗證所有服務是否正常運行
make verify
```

### 3.3. 服務存取點

- **Control Plane UI**: http://localhost:8081
- **SRE Assistant API**: http://localhost:8000
- **Grafana**: http://localhost:3000
- **Keycloak**: http://localhost:8080
- **VictoriaMetrics**: http://localhost:8481

### 3.4. 常用開發指令

- `make test`: 執行所有服務的測試。
- `make test-go`: 僅執行 `control-plane` 的測試。
- `make test-py`: 僅執行 `sre-assistant` 的測試。
- `make stop-services`: 停止所有背景服務。
- `make logs`: 查看 `keycloak` 和 `chromadb` 的日誌。

## 4. 互動原型 (Live Demo)

本專案提供一個基於 `demo-page.html` 的互動原型，用於快速體驗產品的核心功能與 UI/UX。

- **線上預覽**: **[點此體驗 Live Demo](https://detectviz.github.io/control-plane/demo-page.html)**
- **測試帳號**:
  - **超級管理員**: `admin` / `admin`
  - **團隊管理員**: `manager` / `manager`
  - **一般使用者**: `member` / `member`

## 5. 詳細文件

- **[使用者指南 (User Guide)](docs/USER_GUIDE.md)**: 學習如何操作 Control Plane UI 的各項功能。
- **[架構設計書 (Architecture Document)](docs/ARCHITECTURE.md)**: 深入了解系統的設計理念、權限模型與技術細節。
- **[開發路線圖 (Development Roadmap)](docs/ROADMAP.md)**: 查看專案的開發階段與未來規劃。
- **[SRE Assistant 開發指南](docs/SRE_ASSISTANT.md)**: 專為 `sre-assistant` 服務開發者提供的詳細指南。
- **[AI 代理開發指南 (For AI Agents)](AGENT.md)**: 為 AI 開發者提供的專屬操作手冊。
- **[API 契約 (API Contract)](pkg/api/openapi.yaml)**: `control-plane` 與 `sre-assistant` 之間通訊的唯一真實來源。
