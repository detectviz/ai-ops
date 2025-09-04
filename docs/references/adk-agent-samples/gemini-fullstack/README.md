# Gemini 全端代理開發套件 (ADK) 快速入門

**Gemini 全端代理開發套件 (ADK) 快速入門** 是一個可用於生產的藍圖，旨在協助您使用 Gemini 建構一個複雜的全端研究代理。它的目的是展示 ADK 如何幫助您建構複雜的代理工作流程、打造模組化代理，並整合關鍵的「人在環節」(Human-in-the-Loop, HITL) 步驟。

<table>
  <thead>
    <tr>
      <th colspan="2">主要功能</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>🏗️</td>
      <td><strong>全端且可用於生產：</strong> 一個完整的 React 前端和由 ADK 驅動的 FastAPI 後端，並提供 <a href="https://cloud.google.com/run">Google Cloud Run</a> 和 <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview">Vertex AI Agent Engine</a> 的部署選項。</td>
    </tr>
    <tr>
      <td>🧠</td>
      <td><strong>進階代理工作流程：</strong> 該代理使用 Gemini 來<strong>制定</strong>多步驟計畫、<strong>反思</strong>研究結果以找出差距，並<strong>綜合</strong>成一份最終的全面報告。</td>
    </tr>
    <tr>
      <td>🔄</td>
      <td><strong>迭代式與人在環節中的研究：</strong> 讓使用者參與計畫審批，然後透過 Gemini 函式呼叫自主循環搜尋並優化其結果，直到收集到足夠的資訊為止。</td>
    </tr>
  </tbody>
</table>

以下是此代理的實際操作示範：

<img src="https://github.com/GoogleCloudPlatform/agent-starter-pack/blob/main/docs/images/adk_gemini_fullstack.gif?raw=true" width="80%" alt="Gemini 全端 ADK 預覽">

此專案的前端應用程式改編自 [Gemini 全端 LangGraph 快速入門](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart) 的概念。

## 🚀 快速入門：1 分鐘內從零到啟動代理
**先決條件：** **[Python 3.10+](https://www.python.org/downloads/)**、**[Node.js](https://nodejs.org/)**、**[uv](https://github.com/astral-sh/uv)**

您有兩種入門方式。請選擇最適合您設定的選項：

*   A. **[Google AI Studio](#a-google-ai-studio)**：如果您想使用 **Google AI Studio API 金鑰**，請選擇此路徑。此方法需要複製範例儲存庫。
*   B. **[Google Cloud Vertex AI](#b-google-cloud-vertex-ai)**：如果您想使用現有的 **Google Cloud 專案**進行身份驗證，請選擇此路徑。此方法會使用 [agent-starter-pack](https://goo.gle/agent-starter-pack) 產生一個新的、可用於生產的專案，其中包含所有必需的部署腳本。

---

### A. Google AI Studio

您需要一個 **[Google AI Studio API 金鑰](https://aistudio.google.com/app/apikey)**。

#### 步驟 1：複製儲存庫
複製儲存庫並使用 `cd` 進入專案目錄。

```bash
git clone https://github.com/google/adk-samples.git
cd adk-samples/python/agents/gemini-fullstack
```

#### 步驟 2：設定環境變數
在 `app` 資料夾中建立一個 `.env` 檔案，請執行以下指令（將 YOUR_AI_STUDIO_API_KEY 替換為您實際的 API 金鑰）：

```bash
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> app/.env
echo "GOOGLE_API_KEY=YOUR_AI_STUDIO_API_KEY" >> app/.env
```

#### 步驟 3：安裝並執行
從 `gemini-fullstack` 目錄中，安裝相依套件並啟動伺服器。

```bash
make install && make dev
```
您的代理現在正在 `http://localhost:5173` 上執行。

---

### B. Google Cloud Vertex AI

您還需要：**[Google Cloud SDK](https://cloud.google.com/sdk/docs/install)** 和一個已啟用 **Vertex AI API** 的 **Google Cloud 專案**。

#### 步驟 1：從範本建立專案
此指令使用 [Agent Starter Pack](https://goo.gle/agent-starter-pack) 建立一個名為 `my-fullstack-agent` 的新目錄，其中包含所有必要的程式碼。
```bash
# 建立並啟用虛擬環境
python -m venv .venv && source .venv/bin/activate # 在 Windows 上：.venv\Scripts\activate

# 安裝入門套件並建立您的專案
pip install --upgrade agent-starter-pack
agent-starter-pack create my-fullstack-agent -a adk@gemini-fullstack
```
<details>
<summary>⚡️ 替代方案：使用 uv</summary>

如果您已安裝 [`uv`](https://github.com/astral-sh/uv)，您可以使用單一指令來建立和設定您的專案：
```bash
uvx agent-starter-pack create my-fullstack-agent -a adk@gemini-fullstack
```
此指令會處理專案的建立，無需預先在虛擬環境中安裝套件。
</details>

系統會提示您選擇部署選項（Agent Engine 或 Cloud Run）並驗證您的 Google Cloud 憑證。

#### 步驟 2：安裝並執行
導覽至您**新建立的專案資料夾**，然後安裝相依套件並啟動伺服器。
```bash
cd my-fullstack-agent && make install && make dev
```
您的代理現在正在 `http://localhost:5173` 上執行。

## ☁️ 雲端部署
> **注意：** 以下雲端部署說明僅適用於您選擇 **Google Cloud Vertex AI** 選項的情況。

您可以快速將您的代理部署到 Google Cloud 上的**開發環境**。您可以隨時使用以下指令部署最新的程式碼：

```bash
# 將 YOUR_DEV_PROJECT_ID 替換為您實際的 Google Cloud 專案 ID
gcloud config set project YOUR_DEV_PROJECT_ID
make backend
```

若需穩健、**可用於生產的部署**並具備自動化 CI/CD，請遵循 **[Agent Starter Pack 開發指南](https://googlecloudplatform.github.io/agent-starter-pack/guide/development-guide.html#b-production-ready-deployment-with-ci-cd)** 中的詳細說明。
## 代理詳細資訊

| 屬性 | 描述 |
| :--- | :--- |
| **互動類型** | 工作流程 |
| **複雜度** | 進階 |
| **代理類型** | 多代理 (Multi Agent) |
| **元件** | 多代理、函式呼叫、網頁搜尋、React 前端、人在環節 |
| **垂直領域** | 水平 |

## 代理的思維模式：一個兩階段工作流程

後端代理定義於 `app/agent.py` 中，它遵循一個精密的工作流程，從一個簡單的主題發展成一份經過充分研究的報告。

下圖說明了代理的架構與工作流程：

![ADK Gemini 全端架構](https://github.com/GoogleCloudPlatform/agent-starter-pack/blob/main/docs/images/adk_gemini_fullstack_architecture.png?raw=true)

此過程分為兩個主要階段：

### 階段 1：規劃與優化 (人在環節)

這是協作式的腦力激盪階段。

1.  **您提供一個研究主題。**
2.  代理會產生一個高層次的研究計畫，包含數個關鍵目標（例如，「分析市場影響」、「識別主要競爭對手」）。
3.  該計畫會呈現給**您**。您可以批准它，或與代理聊天以新增、移除或修改目標，直到您滿意為止。未經您的明確批准，不會進行任何後續操作。

計畫將包含以下標籤，作為給下游代理的信號：
  - 研究計畫標籤

    - [RESEARCH]：引導透過搜尋收集資訊。
    - [DELIVERABLE]：引導最終產出的建立（例如，表格、報告）。
  
  - 計畫優化標籤

    - [MODIFIED]：目標已更新。
    - [NEW]：根據使用者要求新增的目標。
    - [IMPLIED]：由 AI 主動新增的交付項目。

### 階段 2：執行自主研究

一旦您批准計畫，代理的 `research_pipeline` 將接管並自主運作。

1.  **大綱擬定：** 它首先將批准的計畫轉換為結構化的報告大綱（類似目錄）。
2.  **迭代式研究與批判循環：** 對於大綱的每個部分，它會重複一個循環：
    *   **搜尋：** 執行網頁搜尋以收集資訊。
    *   **批判：** 一個「評論家」模型會評估研究結果中的差距或弱點。
    *   **優化：** 如果評論發現弱點，代理會產生更具體的後續問題並再次搜尋。此循環將持續進行，直到研究達到高品質標準。
3.  **撰寫最終報告：** 研究循環完成後，一個最終的代理會將所有已驗證的發現撰寫成一份精煉的報告，並自動添加內聯引用，連結回原始來源。

您可以在 `app/config.py` 中的 `ResearchConfiguration` 資料類別中編輯關鍵參數（Gemini 模型、研究循環迭代次數）。

## 客製化

您可以透過編輯後端程式碼來修改和擴展此代理的行為。

*   **修改代理邏輯：** 所有子代理（規劃器、研究員、評論家、撰寫器）的核心邏輯都定義在 `app/agent.py` 中。您可以透過修改此處的代理定義來更改提示、工具或推理步驟。
*   **調整研究參數：** 關鍵參數，例如使用的 Gemini 模型或研究循環的迭代次數，可以在 `app/config.py` 的 `ResearchConfiguration` 資料類別中進行調整。
*   **與前端同步：** 前端 UI 透過特定的代理名稱與後端整合，這些代理名稱會以不同方式處理輸出（例如，研究結果 vs. 最終報告）、使用適當的標題/圖示更新活動時間軸，並追蹤網站計數等研究指標。
    重要的代理名稱包括：
    * `section_researcher` 和 `enhanced_search_executor` - 追蹤參考的網站
    * `report_composer_with_citations` - 處理最終報告
    * `interactive_planner_agent` - 在規劃期間更新 AI 訊息
    * `plan_generator` 和 `section_planner` - 用於時間軸標籤
    
    如果您在 `app/agent.py` 中重新命名代理，您必須在前端程式碼 (`/ui`) 中更新它們的名稱以維持功能。


### 互動範例

> **使用者：** 一份關於上次 Google I/O 的報告
>
> **代理：** 這是關於上次 Google I/O 的報告的研究計畫：
>
> *   分析在 Google I/O 2025 上發布的關鍵公告和產品更新。
> *   識別 Google 在活動期間強調的核心主題和戰略方向，特別是關於 AI、Android 以及像 Android XR 等新興技術。
> *   調查主要產品發布和功能增強的市場反應和行業影響。
> *   檢視會議上呈現的 Google 開發者策略中的任何重大轉變或延續性。
> *   評估所宣布的技術和倡議對開發者、消費者和更廣泛的科技領域的影響。
>
> 這個計畫看起來可以嗎，或者您想進一步優化它？一旦批准，我就可以開始研究。
>
> **使用者：** 看起來不錯！
> *（代理接著自主執行研究，並在時間軸上顯示其進度。）*
>
> **代理：**
> 
> Google I/O 2025：關鍵公告與亮點
> ....

## 疑難排解

如果您在設定或執行此代理時遇到問題，這裡有一些資源可以幫助您進行疑難排解：
- [ADK 文件](https://google.github.io/adk-docs/)：代理開發套件的綜合文件
- [Vertex AI 身份驗證指南](https://cloud.google.com/vertex-ai/docs/authentication)：設定身份驗證的詳細說明
- [Agent Starter Pack 疑難排解](https://googlecloudplatform.github.io/agent-starter-pack/guide/troubleshooting.html)：常見問題


## 🛠️ 使用的技術

### 後端
*   [**代理開發套件 (ADK)**](https://github.com/google/adk-python)：用於建構有狀態、多輪對話代理的核心框架。
*   [**FastAPI**](https://fastapi.tiangolo.com/)：用於後端 API 的高效能網頁框架。
*   [**Google Gemini**](https://cloud.google.com/vertex-ai/generative-ai/docs)：用於規劃、推理、搜尋查詢生成和最終綜合。

### 前端
*   [**React**](https://reactjs.org/) (搭配 [Vite](https://vitejs.dev/))：用於建構互動式使用者介面。
*   [**Tailwind CSS**](https://tailwindcss.com/)：用於工具優先的樣式設計。
*   [**Shadcn UI**](https://ui.shadcn.com/)：一套設計精美、易於使用的元件。

## 免責聲明

此代理範例僅供說明之用。它作為一個代理的基本範例和一個基礎起點，供個人或團隊開發自己的代理。

使用者對基於此範例的代理的任何進一步開發、測試、安全強化和部署負全部責任。我們建議在使用任何衍生的代理於即時或關鍵系統之前，進行徹底的審查、測試和實施適當的保護措施。
