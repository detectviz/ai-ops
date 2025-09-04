# SRE Assistant 參考資料庫 (Reference Database)

**版本**: 2.0.0
**狀態**: 生效中 (Active)

## 1. 總覽

歡迎來到 SRE Assistant 的參考資料庫。本文件是整個專案的**知識中樞**，旨在為開發者提供一個清晰、結構化的指南，以便快速查閱專案的核心文檔、Google ADK 的官方文件與範例，以及 Google SRE 的最佳實踐。

在開始任何開發任務之前，請先熟悉本文件所指向的核心設計與架構文檔。在開發過程中，請頻繁參考此處的 ADK 範例與程式碼片段，以確保您的實現符合專案的最佳實踐。

---

## 2. 專案核心設計文檔

這些是理解 SRE Assistant **"是什麼"**、**"為什麼這樣設計"** 以及 **"要往哪裡去"** 的必讀文件。

- **[🚀 專案主頁 (README.md)](../README.md)**: 專案的總覽、快速入門指南和核心價值。
- **[🏛️ 統一架構設計 (ARCHITECTURE.md)](../ARCHITECTURE.md)**: 系統的架構藍圖、設計原則和長期願景。
- **[🗺️ 實施路線圖 (ROADMAP.md)](../ROADMAP.md)**: 專案的分階段開發計畫、里程碑和交付物。
- **[📋 功能與代理規格 (SPEC.md)](../SPEC.md)**: 所有功能、工具和專業化代理的詳細規格說明。
- **[✅ 統一任務清單 (TASKS.md)](../TASKS.md)**: 開發任務的唯一真實來源 (Single Source of Truth)。

---

## 3. SRE Assistant 定製化參考指南

為了將通用的 ADK 知識與本專案的具體需求相結合，我們編寫了以下兩份關鍵的對應文件。**在尋找程式碼範例時，請優先查閱這裡**。

- **[宏觀藍圖：從完整 ADK 範例學習 (reference-adk-agent-samples.md)](reference-adk-agent-samples.md)**
  - **內容**: 精選了十餘個**完整的、生產級的 ADK 專案級範例**，並詳細闡述了它們如何對應到 SRE Assistant 的特定架構（如聯邦化）、核心任務（如 RAG、認證）和長期目標（如混沌工程）。
  - **用途**: 當你需要為一個**宏觀的功能模組**（例如，實現 `MemoryProvider`、設計 `Grafana Plugin` 的後端通訊）尋找最佳實踐和架構參考時，請查閱此文件。

- **[微觀實踐：從關鍵 ADK 範例學習 (reference-adk-examples.md)](reference-adk-examples.md)**
  - **內容**: 精選了數十個**小型的、專注於單一功能的 ADK 程式碼範例**，並將它們直接映射到 `TASKS.md` 中的具體開發任務。
  - **用途**: 當你需要為一個**具體的、微觀的開發任務**（例如，實現一個工具、使用回呼、管理會話狀態）尋找最直接、最簡潔的程式碼實現時，請查閱此文件。

---

## 4. Google ADK 官方資源

### 4.1. ADK 官方文件 (`references/adk-docs/`)

這是 ADK 框架最權威的參考資料。我們已將其整理為符合 SRE Assistant 需求的專題類別。

- **[官方文件索引 (README.md)](references/adk-docs/README.md)**: 原始的、完整的文件列表。

#### **核心概念**
- [**代理 (Agents)**](references/adk-docs/agents.md): 了解不同類型的代理。
- [**工具 (Tools)**](references/adk-docs/tools.md): 了解如何建立和使用工具。
- [**會話、記憶體與狀態 (Sessions, Memory, State)**](references/adk-docs/sessions.md): 理解 ADK 如何管理對話的上下文。
- [**回呼 (Callbacks)**](references/adk-docs/callbacks.md): 學習如何掛鉤到代理的生命週期事件。

#### **工作流程與多代理**
- [**工作流程代理 (Workflow Agents)**](references/adk-docs/agents-workflow-agents.md): 學習如何使用 `SequentialAgent`, `ParallelAgent`, `LoopAgent`。
- [**多代理系統 (Multi-Agent Systems)**](references/adk-docs/agents-multi-agents.md): 學習如何組合多個代理。
- [**代理對代理通訊 (A2A)**](references/adk-docs/a2a.md): 學習如何建立聯邦化代理系統。

#### **開發與部署**
- [**入門指南 (Get Started)**](references/adk-docs/get-started.md): ADK 的安裝與快速入門。
- [**測試 (Testing)**](references/adk-docs/get-started-testing.md): 如何為你的代理編寫測試。
- [**部署 (Deploy)**](references/adk-docs/deploy.md): 部署到 Cloud Run, GKE, Agent Engine 的指南。
- [**安全性 (Safety)**](references/adk-docs/safety.md): 建立安全可靠代理的最佳實踐。
- [**可觀測性 (Observability)**](references/adk-docs/observability-logging.md): 如何整合日誌和追蹤。

### 4.2. ADK 官方程式碼片段 (`references/snippets/`)

這些是專注於單一、特定功能的極簡程式碼範例，非常適合複製貼上和快速學習。

- **[程式碼片段索引 (README.md)](references/snippets/README.md)**: 完整的程式碼片段列表。

---

## 5. 基礎知識與 SRE 最佳實踐

- **[Google SRE Book 精華 (`references/google-sre-book/`)](references/google-sre-book/README.md)**
  - **內容**: 提煉了 Google SRE 書籍的核心原則，如 SLO/SLI、錯誤預算、事後檢討文化等。
  - **用途**: 為 SRE Assistant 的**決策邏輯**和**核心價值**提供理論基礎。

- **[Google AI/Agent 研究論文 (`references/google-paper/`)](references/google-paper/)**
  - **內容**: 包含 Google 發布的關於大型語言模型和 AI 代理的關鍵研究論文。
    - [agents-companion-v2.md](references/google-paper/agents-companion-v2.md)
    - [whitepaper-foundational-large-language-models-and-text-generation-v2.md](references/google-paper/whitepaper-foundational-large-language-models-and-text-generation-v2.md)
  - **用途**: 為專案的**長期架構演進**和**演算法選型**提供前瞻性的學術視野。

---

## 6. 工具與啟動套件

- **[Agent Starter Pack (`references/agent-starter-pack/`)](references/agent-starter-pack/README.md)**
  - **內容**: 一個用於快速創建和部署生產級 ADK 代理的 Python 套件和模板庫。
  - **用途**: 當需要**啟動一個新的、獨立的專業化代理**（例如，在 Phase 3 中開發 `CostOptimizationAgent`）時，可使用此工具來快速生成包含 CI/CD、Terraform 部署腳本和可觀測性設定的完整專案結構。
