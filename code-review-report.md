# SRE Platform 專案全面審查報告 & OpenAPI 規格書說明書

## SRE Platform 專案全面審查報告

### 一、專案現況總覽

#### 🎯 專案定位
- **架構類型**: Monorepo 架構
- **核心服務**: Control Plane (Go) + SRE Assistant (Python)
- **設計理念**: 指揮中心模式，Control Plane 作為 UI 層，SRE Assistant 提供智能診斷

#### ✅ 已完成項目
1. **基礎架構搭建** ✔️
   - Monorepo 結構建立
   - 開發環境配置 (Makefile, docker-compose)
   - 基本服務框架

2. **認證系統** ✔️
   - Keycloak 整合
   - M2M JWT Token 認證機制
   - 服務間安全通訊

3. **核心配置** ✔️
   - 環境變數管理
   - 多環境配置 (開發/生產)
   - 本地服務持久化

### 二、待完成事項分析

#### 🚧 Phase 1: 核心整合 (進行中)

**1.1 API 契約符合性** 🔴
- **狀態**: 部分完成
- **問題**: 
  - `openapi.yaml` 定義與實際實作不一致
  - 部分端點未實作 (`/diagnostics/alerts`, `/capacity/analyze`)
- **建議**: 優先對齊 API 契約，確保前後端一致性

**1.3 核心工具開發** 🟡
- **狀態**: 基礎框架已建立
- **缺失**:
  - `PrometheusQueryTool` 未完全實作
  - `LokiLogQueryTool` 缺少錯誤處理
  - `ControlPlaneTool` 需要完善回調機制

**1.4 端到端流程** 🔴
- **狀態**: 未完成
- **關鍵缺失**: 
  - 缺少整合測試
  - 診斷工作流程未驗證
  - 錯誤恢復機制不完整

### 三、技術債務清單

#### 📝 代碼層面
1. **重複代碼**
   - `tools/workflow.py` 與 `workflow.py` 內容重複
   - 建議: 刪除多餘檔案，統一管理

2. **未實作功能**
   - `main.py` 中的健康檢查 (`check_database`, `check_redis`)
   - 診斷方法 (`_diagnose_alerts`, `_analyze_capacity`)

3. **硬編碼問題**
   - 部分 URL 和配置值硬編碼
   - 建議: 全部改為環境變數

#### 🏗️ 架構層面
1. **缺少串流 API**
   - 目前只支援同步回應
   - 建議: 實作 SSE 或 WebSocket

2. **監控不足**
   - 缺少 Prometheus metrics
   - 沒有分散式追蹤

3. **測試覆蓋率低**
   - 目前測試覆蓋率約 30%
   - 目標: 至少達到 80%

### 四、優先改進建議

#### 🔥 高優先級 (立即處理)

1. **完成 API 契約對齊**
```python
# 需要實作的端點
- POST /diagnostics/alerts
- POST /capacity/analyze
- POST /execute
```

2. **修復關鍵 Bug**
```python
# workflow.py 中的問題
- 修復 _diagnose_deployment 的並行執行
- 完善錯誤處理機制
- 增加 timeout 控制
```

3. **完成核心工具整合**
```python
# 工具實作優先順序
1. PrometheusQueryTool - 完成查詢邏輯
2. LokiLogQueryTool - 增加錯誤處理
3. ControlPlaneTool - 實作寫入操作
```

#### 🟡 中優先級 (本週內)

1. **提升測試覆蓋率**
   - 為核心模組增加單元測試
   - 建立端到端整合測試
   - 實作 CI/CD pipeline

2. **優化性能**
   - 實作連線池管理
   - 增加快取機制
   - 優化資料庫查詢

3. **改善文件**
   - 更新 API 文件
   - 完善使用指南
   - 增加架構圖表

#### 🟢 低優先級 (計劃中)

1. **功能增強**
   - 實作預測性維護
   - 增加 AI 分析能力
   - 建立知識庫系統

2. **UI/UX 改進**
   - 優化前端介面
   - 增加即時通知
   - 改善響應式設計

### 五、下一步行動計畫

#### 本週目標
1. ✅ 完成所有 API 端點實作
2. ✅ 修復已知的關鍵 Bug
3. ✅ 建立基本的整合測試

#### 本月目標
1. 📈 測試覆蓋率達到 60%
2. 🚀 完成 Phase 1 所有任務
3. 📊 建立監控儀表板

#### 季度目標
1. 🎯 完成 Phase 2 功能擴展
2. 🔄 實作多代理協同架構
3. 📱 發布第一個正式版本

### 六、風險評估

#### ⚠️ 技術風險
- **API 不一致**: 可能導致前後端整合失敗
- **性能瓶頸**: 並行診斷未優化可能影響回應時間
- **安全漏洞**: Token 管理需要加強

#### 🔍 建議緩解措施
1. 建立 API 版本控制機制
2. 實作熔斷器和重試機制
3. 加強安全審計和滲透測試

### 七、總結與建議

專案基礎架構已建立完成，但核心功能實作尚未完善。建議：

1. **立即行動**: 優先完成 API 契約對齊和核心工具開發
2. **持續改進**: 逐步提升測試覆蓋率和文件品質
3. **長期規劃**: 朝向多代理協同和 AI 增強方向發展

專案具有良好的架構設計和發展潛力，按照路線圖穩步推進即可達成目標。

---

## OpenAPI 規格書說明書

### 🎯 核心設計理念

1. **雙向通訊模式**
   - **SRE Assistant 提供**: 診斷分析 API (`/diagnostics/*`, `/capacity/*`, `/execute`)
   - **Control Plane 提供**: 資源查詢 API (`/resources`, `/audit-logs`, `/alerts`)

2. **統一認證機制**
   - 所有 API 使用 JWT Bearer Token
   - 透過 Keycloak 進行 M2M 認證

3. **非同步處理模式**
   - 診斷任務返回 `202 Accepted` 和 `session_id`
   - 透過 `/diagnostics/{session_id}/status` 查詢進度

### 📊 API 端點總覽

#### 🤖 SRE Assistant 端點 (Control Plane 呼叫)

| 端點 | 方法 | 用途 | 回應模式 |
|------|------|------|----------|
| `/api/v1/diagnostics/deployment` | POST | 部署問題診斷 | 非同步 (202) |
| `/api/v1/diagnostics/alerts` | POST | 告警根因分析 | 非同步 (202) |
| `/api/v1/capacity/analyze` | POST | 容量趨勢分析 | 同步 (200) |
| `/api/v1/execute` | POST | 自然語言查詢 | 同步 (200) |
| `/api/v1/diagnostics/{id}/status` | GET | 查詢診斷狀態 | 同步 (200) |

#### 🎯 Control Plane 端點 (SRE Assistant 呼叫)

| 端點 | 方法 | 用途 | 資料類型 |
|------|------|------|----------|
| `/api/v1/resources` | GET | 獲取資源列表 | 分頁列表 |
| `/api/v1/resources/{id}` | GET | 獲取資源詳情 | 單一資源 |
| `/api/v1/audit-logs` | GET | 查詢審計日誌 | 時間序列 |
| `/api/v1/alerts` | GET | 獲取告警列表 | 即時資料 |

### 🔑 實作建議

#### 1. **優先實作順序**

```python
# Phase 1: 核心功能
1. /healthz, /readyz  # 健康檢查
2. /api/v1/diagnostics/deployment  # 部署診斷
3. /api/v1/resources  # 資源查詢

# Phase 2: 進階功能  
4. /api/v1/diagnostics/alerts  # 告警分析
5. /api/v1/capacity/analyze  # 容量分析
6. /api/v1/audit-logs  # 審計日誌

# Phase 3: 智能功能
7. /api/v1/execute  # 自然語言介面
```

#### 2. **關鍵資料模型**

```python
# 診斷請求標準格式
DiagnosticRequest:
  - incident_id: 唯一識別碼
  - severity: P0-P3 分級
  - affected_services: 受影響服務列表
  - context: 額外上下文資訊
```
#### 3. **錯誤處理標準**

```python
# 統一錯誤格式
ErrorResponse:
  - error: 錯誤代碼 (如 "INVALID_REQUEST")
  - message: 人類可讀訊息
  - details: 詳細錯誤資訊
  - request_id: 追蹤 ID
```

### 🔧 實作範例

#### SRE Assistant 端實作 (FastAPI)

```python
# services/sre-assistant/src/sre_assistant/api/diagnostics.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1", tags=["diagnostics"])

@router.post("/diagnostics/deployment", status_code=202)
async def diagnose_deployment(
    request: DiagnosticRequest,
    token: str = Depends(verify_jwt_token)
) -> DiagnosticResponse:
    """部署診斷端點實作"""
    
    # 1. 驗證請求
    if not request.affected_services:
        raise HTTPException(400, "必須指定受影響的服務")
    
    # 2. 建立診斷會話
    session_id = str(uuid.uuid4())
    
    # 3. 啟動非同步診斷任務
    await start_diagnostic_task(
        session_id=session_id,
        request=request
    )
    
    # 4. 返回接受回應
    return DiagnosticResponse(
        session_id=session_id,
        status="accepted",
        message=f"診斷任務已接受，預計 {request.severity} 級別需要 60 秒",
        estimated_time=60
    )

@router.get("/diagnostics/{session_id}/status")
async def get_diagnostic_status(
    session_id: str,
    token: str = Depends(verify_jwt_token)
) -> DiagnosticStatus:
    """查詢診斷狀態"""
    
    # 從資料庫或快取查詢狀態
    status = await get_task_status(session_id)
    
    if not status:
        raise HTTPException(404, f"找不到會話 {session_id}")
    
    return DiagnosticStatus(
        session_id=session_id,
        status=status.status,
        progress=status.progress,
        current_step=status.current_step,
        result=status.result if status.status == "completed" else None
    )
```

#### Control Plane 端實作 (Go)

```go
// services/control-plane/internal/services/sre_assistant_client.go
package services

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type SREAssistantClient struct {
    baseURL    string
    httpClient *http.Client
    token      string
}

// DiagnoseDeployment 呼叫 SRE Assistant 進行部署診斷
func (c *SREAssistantClient) DiagnoseDeployment(ctx context.Context, req DiagnosticRequest) (*DiagnosticResponse, error) {
    url := fmt.Sprintf("%s/api/v1/diagnostics/deployment", c.baseURL)
    
    // 1. 序列化請求
    body, err := json.Marshal(req)
    if err != nil {
        return nil, fmt.Errorf("序列化請求失敗: %w", err)
    }
    
    // 2. 建立 HTTP 請求
    httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(body))
    if err != nil {
        return nil, err
    }
    
    // 3. 設定認證標頭
    httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.token))
    httpReq.Header.Set("Content-Type", "application/json")
    
    // 4. 發送請求
    resp, err := c.httpClient.Do(httpReq)
    if err != nil {
        return nil, fmt.Errorf("請求失敗: %w", err)
    }
    defer resp.Body.Close()
    
    // 5. 處理回應
    if resp.StatusCode != http.StatusAccepted {
        var errResp ErrorResponse
        json.NewDecoder(resp.Body).Decode(&errResp)
        return nil, fmt.Errorf("診斷失敗: %s", errResp.Message)
    }
    
    var diagResp DiagnosticResponse
    if err := json.NewDecoder(resp.Body).Decode(&diagResp); err != nil {
        return nil, err
    }
    
    return &diagResp, nil
}

// PollDiagnosticStatus 輪詢診斷狀態直到完成
func (c *SREAssistantClient) PollDiagnosticStatus(ctx context.Context, sessionID string) (*DiagnosticResult, error) {
    ticker := time.NewTicker(5 * time.Second)
    defer ticker.Stop()
    
    timeout := time.After(5 * time.Minute)
    
    for {
        select {
        case <-ctx.Done():
            return nil, ctx.Err()
        case <-timeout:
            return nil, fmt.Errorf("診斷超時")
        case <-ticker.C:
            status, err := c.GetDiagnosticStatus(ctx, sessionID)
            if err != nil {
                return nil, err
            }
            
            switch status.Status {
            case "completed":
                return status.Result, nil
            case "failed":
                return nil, fmt.Errorf("診斷失敗: %s", status.Error)
            }
        }
    }
}
```

### 📝 實作檢查清單

請依照以下清單確保實作符合規格：

#### ✅ SRE Assistant 實作檢查

- [ ] **健康檢查端點**
  - [ ] `/healthz` 返回 200 和健康狀態
  - [ ] `/readyz` 檢查所有依賴服務
  - [ ] `/metrics` 提供 Prometheus 指標

- [ ] **認證機制**
  - [ ] 所有 API 端點驗證 JWT Token
  - [ ] Token 從 `Authorization: Bearer` 標頭取得
  - [ ] 驗證 Token 簽名和過期時間

- [ ] **診斷端點**
  - [ ] 接受標準 `DiagnosticRequest` 格式
  - [ ] 返回 202 和 `session_id`
  - [ ] 實作非同步任務處理

- [ ] **錯誤處理**
  - [ ] 統一使用 `ErrorResponse` 格式
  - [ ] 包含 `request_id` 用於追蹤
  - [ ] 適當的 HTTP 狀態碼

#### ✅ Control Plane 實作檢查

- [ ] **資源查詢 API**
  - [ ] `/api/v1/resources` 支援分頁和過濾
  - [ ] 返回標準 `Resource` 格式
  - [ ] 包含資源狀態和指標

- [ ] **審計日誌 API**
  - [ ] 支援時間範圍查詢
  - [ ] 返回結構化的變更記錄
  - [ ] 包含操作用戶和結果

- [ ] **M2M 認證**
  - [ ] 實作 Token 獲取和快取
  - [ ] Token 過期自動更新
  - [ ] 在呼叫 SRE Assistant 時提供 Token

### 🚀 下一步行動

1. **立即更新程式碼**
   - 將此 `openapi.yaml` 複製到 `pkg/api/openapi.yaml`
   - 更新 SRE Assistant 的 FastAPI 路由以符合規格
   - 更新 Control Plane 的客戶端程式碼

2. **產生程式碼框架** (可選)
   ```bash
   # 使用 OpenAPI Generator 產生程式碼
   # Python (FastAPI)
   openapi-generator generate -i pkg/api/openapi.yaml -g python-fastapi -o generated/python
   
   # Go
   openapi-generator generate -i pkg/api/openapi.yaml -g go -o generated/go
   ```

3. **建立整合測試**
   ```python
   # tests/integration/test_api_contract.py
   import pytest
   from jsonschema import validate
   import yaml
   
   def test_diagnostic_request_format():
       """測試診斷請求格式符合 OpenAPI 規格"""
       with open("pkg/api/openapi.yaml") as f:
           spec = yaml.safe_load(f)
       
       schema = spec["components"]["schemas"]["DiagnosticRequest"]
       
       # 測試有效請求
       valid_request = {
           "incident_id": "INC-001",
           "severity": "P1",
           "affected_services": ["web-app", "database"]
       }
       
       # 應該不會拋出異常
       validate(instance=valid_request, schema=schema)
   ```

4. **文件同步**
   - 更新 `docs/API_DOCS.md` 以反映新規格
   - 在 README.md 中標註 API 版本為 1.0.0
   - 建立 API 變更日誌