# 新一代自動化維運平台

[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![HTMX](https://img.shields.io/badge/HTMX-Driven-3498DB)](https://htmx.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

## 1. 專案簡介

一個採用 Monorepo 架構的現代化維運平台，旨在將複雜的 SRE 工作流程自動化、智能化。它整合了兩個核心服務，共同實現從被動故障應對到主動系統管理的轉型。


### 核心服務

1.  **Control Plane (指揮官)**
    - **角色**: 提供 Web UI 的指揮中心，負責應用管理、資源操作與任務發起。
    - **技術**: 後端採用 Go，前端使用 HTMX 驅動，實現輕量、高效的互動體驗。

2.  **SRE Assistant (專家代理)**
    - **角色**: 無介面的 (headless) 專家代理，負責執行複雜的診斷、分析與自動化任務。
    - **技術**: 基於 Google Agent Development Kit (ADK) 和 Python 构建。

## 2. 快速開始 (本地開發)

本專案推薦使用基於本地服務的開發模式。

1.  **環境準備**:
    - Go 1.21+, Python 3.11+ (及 Poetry), Make, `sudo` 權限。
    - 完整細節請參考 `AGENT.md`。

2.  **一鍵安裝與啟動**:
    ```bash
    # 克隆專案
    git clone https://github.com/detectviz/sre-platform
    cd sre-platform

    # 執行安裝、設定並啟動所有本地服務
    make setup-dev
    ```

3.  **驗證服務**:
    ```bash
    make verify
    ```

4.  **服務存取**:
    - **Control Plane UI**: http://localhost:8081
    - **SRE Assistant API**: http://localhost:8000
    - **Grafana**: http://localhost:3000
    - **Keycloak**: http://localhost:8080
