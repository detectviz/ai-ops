# SRE Platform API 參考文檔

**版本**: v2.0  
**最後更新**: 2025年9月5日  
**基礎 URL**: `https://sre-platform.example.com`

---

## 📋 目錄

- [1. API 概述](#1-api-概述)
- [2. 認證機制](#2-認證機制)
- [3. 健康檢查 API](#3-健康檢查-api)
- [4. SRE Assistant 診斷 API](#4-sre-assistant-診斷-api)
- [5. 資源管理 API](#5-資源管理-api)
- [6. 組織與權限管理 API](#6-組織與權限管理-api)
- [7. 告警與事件管理 API](#7-告警與事件管理-api)
- [8. 自動化腳本 API](#8-自動化腳本-api)
- [9. 通知管道 API](#9-通知管道-api)
- [10. 儀表板與統計 API](#10-儀表板與統計-api)
- [11. 個人資料與設定 API](#11-個人資料與設定-api)
- [12. 錯誤處理](#12-錯誤處理)
- [13. 速率限制](#13-速率限制)

---

## 1. API 概述

### 1.1 設計原則

SRE Platform API 遵循 RESTful 設計原則，提供統一、一致的介面規範：

- **資源導向**: 每個 URL 對應一個特定的資源
- **HTTP 動詞**: 使用標準 HTTP 方法 (GET, POST, PUT, DELETE, PATCH)
- **狀態碼**: 使用標準 HTTP 狀態碼表示操作結果
- **JSON 格式**: 統一使用 JSON 進行資料交換
- **版本控制**: 透過 URL 路徑進行版本管理

### 1.2 API 端點分類

| 分類 | 端點前綴 | 說明 |
|------|----------|------|
| 健康檢查 | `/healthz`, `/readyz` | 服務健康狀態檢查 |
| 診斷分析 | `/api/v1/diagnostics/` | SRE Assistant 智能診斷 |
| 容量分析 | `/api/v1/capacity/` | 容量規劃與預測 |
| 資源管理 | `/api/v1/resources/` | 資源 CRUD 與批次操作 |
| 組織管理 | `/api/v1/users/`, `/api/v1/teams/` | 人員與團隊管理 |
| 告警事件 | `/api/v1/alerts/`, `/api/v1/incidents/` | 告警與事件處理 |
| 自動化 | `/api/v1/automation/` | 腳本與執行管理 |
| 通知 | `/api/v1/notification-channels/` | 通知管道管理 |
| 儀表板 | `/api/v1/dashboard/` | 統計與 KPI 數據 |
| 個人設定 | `/api/v1/profile/`, `/api/v1/settings/` | 用戶設定管理 |

---

## 2. 認證機制

### 2.1 JWT Bearer Token

所有 API 請求（除健康檢查外）都需要在 Header 中攜帶有效的 JWT Token：

```http
Authorization: Bearer <JWT_TOKEN>
```

### 2.2 Token 類型

| Token 類型 | 用途 | 有效期 |
|------------|------|--------|
| **用戶 Token** | 前端 UI 操作 | 8 小時 |
| **M2M Token** | 服務間通訊 | 24 小時 |
| **Refresh Token** | Token 刷新 | 7 天 |

### 2.3 權限級別

```yaml
權限矩陣:
  SuperAdmin:    # 超級管理員
    - 所有 API 完整存取權限
  TeamManager:   # 團隊管理員  
    - 管理所屬團隊資源
    - 檢視團隊告警與事件
  TeamMember:    # 一般使用者
    - 檢視權限
    - 個人設定修改
  ReadOnly:      # 唯讀使用者
    - 僅檢視權限
```

---

## 3. 健康檢查 API

### 3.1 存活性檢查

檢查服務是否存活，用於 Kubernetes liveness probe。

**端點**: `GET /healthz`

**回應範例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-05T10:30:00Z",
  "version": "1.2.3"
}
```

### 3.2 就緒性檢查

檢查服務是否就緒，包含依賴服務檢查。

**端點**: `GET /readyz`

**回應範例**:
```json
{
  "ready": true,
  "checks": {
    "database": true,
    "redis": true,
    "keycloak": true,
    "prometheus": true
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

### 3.3 監控指標

**端點**: `GET /metrics`

**回應格式**: Prometheus 格式
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",status="200"} 1234
sre_platform_active_users 56
sre_platform_resource_count 1204
```

---

## 4. SRE Assistant 診斷 API

### 4.1 部署診斷

分析部署問題並提供診斷報告。

**端點**: `POST /api/v1/diagnostics/deployment`

**請求範例**:
```json
{
  "incident_id": "INC-2025-001",
  "severity": "P1",
  "title": "Payment API 部署失敗",
  "description": "payment-api v2.1.0 部署後出現 502 錯誤",
  "affected_services": ["payment-api", "order-service"],
  "time_range": {
    "start": "2025-09-05T09:00:00Z",
    "end": "2025-09-05T10:00:00Z"
  },
  "context": {
    "deployment_id": "deploy-12345",
    "namespace": "production"
  }
}
```

**回應範例**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "診斷任務已接受，正在背景處理中",
  "estimated_time": 120
}
```

### 4.2 告警分析

分析告警並提供根因分析。

**端點**: `POST /api/v1/diagnostics/alerts`

**請求範例**:
```json
{
  "alert_ids": ["alert-001", "alert-002", "alert-003"],
  "correlation_window": 300,
  "include_metrics": true,
  "include_logs": true
}
```

### 4.3 診斷狀態查詢

查詢非同步診斷任務的執行狀態。

**端點**: `GET /api/v1/diagnostics/{session_id}/status`

**回應範例**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "current_step": "生成診斷報告",
  "result": {
    "summary": "發現 3 個關鍵問題，建議立即處理",
    "findings": [
      {
        "source": "Prometheus",
        "severity": "critical",
        "message": "CPU 使用率持續超過 90%",
        "evidence": {},
        "timestamp": "2025-09-05T10:25:00Z"
      }
    ],
    "recommended_actions": [
      "增加 Pod 副本數至 5 個",
      "檢查記憶體洩漏問題"
    ],
    "confidence_score": 0.87,
    "tools_used": ["prometheus", "loki", "kubernetes"],
    "execution_time": 118.5
  }
}
```

### 4.4 容量分析

分析資源使用趨勢並預測容量需求。

**端點**: `POST /api/v1/capacity/analyze`

**請求範例**:
```json
{
  "resources": ["group-001", "group-002"],
  "analysis_type": "forecast",
  "forecast_days": 30,
  "optimization_target": "cost"
}
```

**回應範例**:
```json
{
  "current_usage": {
    "cpu": {
      "current": 65.2,
      "allocated": 80.0,
      "limit": 100.0,
      "utilization_percent": 81.5,
      "unit": "cores"
    },
    "memory": {
      "current": 120.5,
      "allocated": 150.0,
      "limit": 200.0,
      "utilization_percent": 80.3,
      "unit": "GB"
    }
  },
  "forecast": {
    "cpu": {
      "predicted_values": [
        {
          "timestamp": "2025-09-06T00:00:00Z",
          "value": 67.1,
          "confidence_interval": {
            "lower": 62.5,
            "upper": 71.7
          }
        }
      ],
      "trend": "increasing",
      "anomaly_detected": false
    }
  },
  "recommendations": [
    {
      "type": "scale_up",
      "resource": "cpu",
      "current_value": 80.0,
      "recommended_value": 100.0,
      "reason": "預計在 15 天後達到容量上限",
      "impact": "high",
      "estimated_savings": 0
    }
  ],
  "estimated_cost_savings": 0
}
```

---

## 5. 資源管理 API

### 5.1 資源列表

獲取所有受管理的資源。

**端點**: `GET /api/v1/resources`

**查詢參數**:
- `type`: 資源類型 (server, switch, router, firewall)
- `status`: 狀態篩選 (normal, warning, error)
- `group_id`: 資源群組 ID
- `branch`: 分行篩選
- `limit`: 每頁數量 (預設 100)
- `offset`: 頁面偏移

**回應範例**:
```json
{
  "items": [
    {
      "id": "res-001",
      "name": "Edge SW13",
      "type": "switch",
      "ip_address": "88.201.0.13",
      "status": "normal",
      "branch": "仁愛分行",
      "group_ids": ["group-001"],
      "metadata": {
        "location": "機房 A",
        "vendor": "Cisco",
        "model": "C9300-24T"
      },
      "metrics": {
        "cpu_usage": 25.5,
        "memory_usage": 45.2,
        "uptime": 2592000
      },
      "created_at": "2025-01-15T08:30:00Z",
      "updated_at": "2025-09-05T10:30:00Z"
    }
  ],
  "total": 1204,
  "page": 1,
  "page_size": 100,
  "has_more": true
}
```

### 5.2 創建資源

**端點**: `POST /api/v1/resources`

**請求範例**:
```json
{
  "name": "New Core Switch",
  "type": "switch",
  "ip_address": "192.168.1.100",
  "branch": "台中分行",
  "group_ids": ["group-001"],
  "metadata": {
    "location": "機房 B",
    "vendor": "Arista",
    "model": "7050X"
  }
}
```

### 5.3 更新資源

**端點**: `PUT /api/v1/resources/{resource_id}`

### 5.4 刪除資源

**端點**: `DELETE /api/v1/resources/{resource_id}`

### 5.5 批次操作

**端點**: `POST /api/v1/resources/batch`

**請求範例**:
```json
{
  "operation": "delete",
  "resource_ids": ["res-001", "res-002", "res-003"]
}
```

### 5.6 網段掃描

**端點**: `POST /api/v1/resources/scan`

**請求範例**:
```json
{
  "cidr": "192.168.1.0/24",
  "scan_type": "ping",
  "timeout": 30
}
```

---

## 6. 組織與權限管理 API

### 6.1 用戶管理

#### 獲取用戶列表
**端點**: `GET /api/v1/users`

**回應範例**:
```json
{
  "users": [
    {
      "id": "user-001",
      "username": "admin",
      "name": "系統管理員",
      "email": "admin@corp.com",
      "role": "SuperAdmin",
      "team_ids": ["team-001", "team-002"],
      "status": "active",
      "last_login": "2025-09-05T09:15:00Z",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 25
}
```

#### 創建用戶
**端點**: `POST /api/v1/users`

#### 更新用戶
**端點**: `PUT /api/v1/users/{user_id}`

#### 刪除用戶
**端點**: `DELETE /api/v1/users/{user_id}`

### 6.2 團隊管理

#### 獲取團隊列表
**端點**: `GET /api/v1/teams`

**回應範例**:
```json
{
  "teams": [
    {
      "id": "team-001",
      "name": "網路團隊",
      "manager_id": "user-002",
      "member_ids": ["user-001", "user-002", "user-003"],
      "accessible_group_ids": ["group-001", "group-003"],
      "subscribers": [
        {
          "type": "user",
          "id": "user-003"
        },
        {
          "type": "channel",
          "id": "channel-001"
        }
      ],
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 5
}
```

#### 創建團隊
**端點**: `POST /api/v1/teams`

#### 更新團隊
**端點**: `PUT /api/v1/teams/{team_id}`

#### 管理團隊成員
**端點**: `POST /api/v1/teams/{team_id}/members`

---

## 7. 告警與事件管理 API

### 7.1 告警列表

**端點**: `GET /api/v1/alerts`

**查詢參數**:
- `severity`: 嚴重程度 (P0, P1, P2, P3)
- `status`: 告警狀態 (firing, resolved, pending)
- `start_time`: 開始時間
- `end_time`: 結束時間

### 7.2 事件管理

#### 獲取事件列表
**端點**: `GET /api/v1/incidents`

**回應範例**:
```json
{
  "incidents": [
    {
      "id": "inc-001",
      "title": "Edge SW13 連線中斷",
      "level": "error",
      "status": "new",
      "resource_name": "Edge SW13",
      "description": "資源斷線超過15分鐘",
      "assignee": null,
      "acknowledged_by": null,
      "created_at": "2025-09-05T10:15:00Z",
      "updated_at": "2025-09-05T10:15:00Z",
      "comments": []
    }
  ],
  "total": 156,
  "new_count": 12,
  "acknowledged_count": 8,
  "resolved_count": 136
}
```

#### 確認事件
**端點**: `POST /api/v1/incidents/{incident_id}/acknowledge`

#### 解決事件
**端點**: `POST /api/v1/incidents/{incident_id}/resolve`

#### 指派處理人
**端點**: `POST /api/v1/incidents/{incident_id}/assign`

#### 新增註記
**端點**: `POST /api/v1/incidents/{incident_id}/comments`

---

## 8. 自動化腳本 API

### 8.1 腳本管理

#### 獲取腳本列表
**端點**: `GET /api/v1/automation/scripts`

**回應範例**:
```json
{
  "scripts": [
    {
      "id": "script-001",
      "name": "重啟 Web 服務",
      "type": "shell",
      "description": "自動重啟 Apache/Nginx 服務",
      "content": "#!/bin/bash\nsudo systemctl restart $SERVICE_NAME",
      "parameters": ["service_name", "host_ip"],
      "created_by": "user-001",
      "created_at": "2025-08-25T10:00:00Z",
      "updated_at": "2025-08-25T10:00:00Z"
    }
  ],
  "total": 15
}
```

#### 創建腳本
**端點**: `POST /api/v1/automation/scripts`

#### 執行腳本
**端點**: `POST /api/v1/automation/execute`

### 8.2 執行歷史

**端點**: `GET /api/v1/automation/executions`

**回應範例**:
```json
{
  "executions": [
    {
      "id": "exec-001",
      "script_id": "script-001",
      "script_name": "重啟 Web 服務",
      "trigger_alert": "Edge SW13 斷線",
      "status": "success",
      "duration": "15s",
      "output": "Service restarted successfully",
      "executed_by": "system",
      "executed_at": "2025-09-05T01:20:00Z"
    }
  ],
  "total": 1250
}
```

---

## 9. 通知管道 API

### 9.1 管道管理

#### 獲取通知管道列表
**端點**: `GET /api/v1/notification-channels`

**回應範例**:
```json
{
  "channels": [
    {
      "id": "channel-001",
      "name": "網路一部 Slack",
      "type": "slack",
      "status": "active",
      "config": {
        "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXX",
        "channel": "#network-alerts"
      },
      "last_test": "2025-09-01T10:00:00Z",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 8
}
```

#### 測試通知管道
**端點**: `POST /api/v1/notification-channels/{channel_id}/test`

---

## 10. 儀表板與統計 API

### 10.1 儀表板統計

**端點**: `GET /api/v1/dashboard/stats`

**回應範例**:
```json
{
  "alert_stats": {
    "new": 12,
    "acknowledged": 8,
    "resolved_today": 25,
    "trends": {
      "new_change": "+15%",
      "acknowledged_change": "-8%",
      "resolved_change": "+22%"
    }
  },
  "resource_stats": {
    "total": 1204,
    "healthy": 1156,
    "warning": 32,
    "error": 16,
    "availability": 99.8
  },
  "performance_stats": {
    "avg_response_time": "23ms",
    "avg_network_latency": "23ms"
  }
}
```

### 10.2 KPI 指標

**端點**: `GET /api/v1/dashboard/kpis`

### 10.3 趨勢數據

**端點**: `GET /api/v1/dashboard/trends`

---

## 11. 個人資料與設定 API

### 11.1 個人資料

#### 獲取個人資料
**端點**: `GET /api/v1/profile`

**回應範例**:
```json
{
  "user": {
    "id": "user-001",
    "username": "admin",
    "name": "系統管理員",
    "email": "admin@corp.com",
    "role": "SuperAdmin",
    "teams": ["網路團隊", "資安團隊"],
    "language": "zh-TW"
  },
  "contact_methods": {
    "email": {
      "value": "admin@corp.com",
      "verified": true
    },
    "line_token": {
      "value": "ABC123xyz",
      "verified": true
    },
    "sms": {
      "value": "+886912345678",
      "verified": false
    }
  },
  "notification_preferences": {
    "subscribed_levels": ["high", "medium", "low"]
  }
}
```

#### 更新個人資料
**端點**: `PUT /api/v1/profile`

#### 修改密碼
**端點**: `POST /api/v1/profile/change-password`

#### 驗證聯絡方式
**端點**: `POST /api/v1/profile/verify-contact`

### 11.2 系統設定

#### 獲取系統設定 (管理員)
**端點**: `GET /api/v1/settings`

#### 更新系統設定 (管理員)
**端點**: `PUT /api/v1/settings`

---

## 12. 錯誤處理

### 12.1 標準錯誤格式

```json
{
  "error": "RESOURCE_NOT_FOUND",
  "message": "指定的資源不存在",
  "details": {
    "resource_id": "res-001",
    "resource_type": "switch"
  },
  "request_id": "req-550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-09-05T10:30:00Z"
}
```

### 12.2 常見錯誤碼

| HTTP 狀態碼 | 錯誤碼 | 說明 |
|-------------|--------|------|
| 400 | INVALID_REQUEST | 請求參數錯誤 |
| 401 | UNAUTHORIZED | 未授權或 Token 無效 |
| 403 | FORBIDDEN | 權限不足 |
| 404 | RESOURCE_NOT_FOUND | 資源不存在 |
| 409 | RESOURCE_CONFLICT | 資源衝突 |
| 422 | VALIDATION_ERROR | 資料驗證失敗 |
| 429 | RATE_LIMIT_EXCEEDED | 超過速率限制 |
| 500 | INTERNAL_ERROR | 內部伺服器錯誤 |
| 503 | SERVICE_UNAVAILABLE | 服務不可用 |

---

## 13. 速率限制

### 13.1 限制規則

| API 類型 | 限制 | 時間窗口 |
|----------|------|----------|
| 一般 API | 1000 次 | 每小時 |
| 診斷 API | 10 次 | 每分鐘 |
| 批次操作 | 5 次 | 每分鐘 |
| 檔案上傳 | 20 次 | 每小時 |

### 13.2 回應 Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1725537000
```

---

## 附錄

### A. 範例集合

詳細的 API 請求與回應範例，請參考：
- [Postman Collection](./postman/SRE-Platform.postman_collection.json)
- [OpenAPI Specification](../pkg/api/openapi-v2.yaml)

### B. SDK 與工具

- **Go SDK**: `github.com/sre-platform/go-sdk`
- **Python SDK**: `pip install sre-platform-sdk`
- **CLI 工具**: `sre-cli`

### C. 版本歷史

- **v2.0** (2025-09-05): 完整功能 API 規範
- **v1.0** (2025-08-01): 初始版本，基礎診斷功能

---

*文檔生成時間: 2025-09-05T10:30:00Z*  
*如有疑問，請聯繫 SRE Platform 開發團隊*