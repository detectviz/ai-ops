// Package api 包含了所有供外部服務 (如此處的 SRE Assistant) 呼叫的 API 端點處理器。
// 這些端點受到 M2M JWT 權杖的保護。
package api

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/detectviz/control-plane/internal/models"
	"github.com/detectviz/control-plane/internal/services"
)

// jsonResponse 是一個輔助函數，用於將資料結構序列化為 JSON 並寫入 HTTP 回應。
func jsonResponse(w http.ResponseWriter, statusCode int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	if data != nil {
		json.NewEncoder(w).Encode(data)
	}
}

// GetAuditLogs 處理獲取審計日誌的請求 (存根)。
func GetAuditLogs(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 從資料庫中查詢真實的審計日誌
		mockLogs := []map[string]interface{}{
			{
				"timestamp":   time.Now().Add(-1 * time.Hour).Format(time.RFC3339),
				"event_type":  "DEPLOYMENT",
				"author":      "jules@example.com",
				"summary":     "Deployed version v1.2.3 of payment-api",
			},
		}
		jsonResponse(w, http.StatusOK, mockLogs)
	}
}

// GetIncidents 處理獲取告警紀錄的請求 (存根)。
func GetIncidents(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 從資料庫中查詢真實的告警紀錄
		mockIncidents := []map[string]interface{}{
			{
				"id":     1001,
				"level":  "error",
				"time":   time.Now().Add(-30 * time.Minute).Format(time.RFC3339),
				"name":   "High CPU Usage",
				"desc":   "The payment-api service is experiencing high CPU usage.",
				"status": "new",
			},
		}
		jsonResponse(w, http.StatusOK, mockIncidents)
	}
}

// GetExecutions 處理獲取自動化執行日誌的請求 (存根)。
func GetExecutions(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 從資料庫中查詢
		mockExecutions := []map[string]interface{}{}
		jsonResponse(w, http.StatusOK, mockExecutions)
	}
}

// CreateExecution 處理建立新執行紀錄的請求 (存根)。
// 這是 SRE Assistant 在開始一個非同步任務時呼叫的回呼端點。
func CreateExecution(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 解析請求體並在資料庫中建立紀錄
		mockExecution := map[string]interface{}{
			"id":            123,
			"executionTime": time.Now().Format(time.RFC3339),
			"scriptName":    "Deployment Diagnosis",
			"status":        "running",
		}
		jsonResponse(w, http.StatusCreated, mockExecution)
	}
}

// UpdateExecution 處理更新執行紀錄狀態的請求 (存根)。
// 這是 SRE Assistant 在任務完成或失敗時呼叫的回呼端點。
func UpdateExecution(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 解析 ID 和請求體並更新資料庫紀錄
		mockExecution := map[string]interface{}{
			"id":            123,
			"executionTime": time.Now().Add(-5 * time.Minute).Format(time.RFC3339),
			"scriptName":    "Deployment Diagnosis",
			"status":        "completed",
			"duration":      "35s",
			"output":        "Diagnosis complete. No critical issues found.",
		}
		jsonResponse(w, http.StatusOK, mockExecution)
	}
}

// GetDashboardSummary 處理儀表板摘要數據的請求 (骨架)。
func GetDashboardSummary(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 從服務層獲取真實數據
		mockSummary := models.DashboardSummary{
			Alerts: &models.DashboardSummaryAlerts{
				New:           5,
				Processing:    2,
				ResolvedToday: 15,
			},
			Resources: &models.DashboardSummaryResources{
				Total:    150,
				Healthy:  145,
				Warning:  3,
				Critical: 2,
			},
			KPIs: &models.DashboardSummaryKPIs{
				Availability: 99.98,
				MTTR:         15.5,
				IncidentRate: 0.5,
			},
		}
		jsonResponse(w, http.StatusOK, mockSummary)
	}
}

// --- Resources Handlers (Skeletons) ---

// ListResources 處理獲取資源列表的請求。
func ListResources(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現包含過濾和分頁的真實查詢邏輯。
		mockResources := models.ResourceList{
			Items:      []models.Resource{},
			Pagination: models.Pagination{Page: 1, PageSize: 20, Total: 0, TotalPages: 1},
		}
		jsonResponse(w, http.StatusOK, mockResources)
	}
}

// CreateResource 處理創建新資源的請求。
func CreateResource(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現真實的資源創建邏輯。
		var req models.ResourceCreateRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			jsonResponse(w, http.StatusBadRequest, nil)
			return
		}
		mockResource := models.Resource{ID: 99, Name: req.Name, Type: req.Type, IP: req.IPAddress}
		jsonResponse(w, http.StatusCreated, mockResource)
	}
}

// GetResource 處理獲取單一資源詳情的請求。
func GetResource(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 從 URL 解析 resourceId 並查詢資料庫。
		mockResource := models.Resource{ID: 99, Name: "mock-server-01"}
		jsonResponse(w, http.StatusOK, mockResource)
	}
}

// UpdateResource 處理更新已存在資源的請求。
func UpdateResource(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現真實的資源更新邏輯。
		mockResource := models.Resource{ID: 99, Name: "updated-mock-server-01"}
		jsonResponse(w, http.StatusOK, mockResource)
	}
}

// DeleteResource 處理刪除資源的請求。
func DeleteResource(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現真實的資源刪除邏輯。
		jsonResponse(w, http.StatusNoContent, nil)
	}
}

// BatchOperateResources 處理對資源的批次操作請求。
func BatchOperateResources(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現真實的批次操作邏輯。
		mockResult := models.BatchOperationResult{SuccessCount: 1, FailureCount: 0}
		jsonResponse(w, http.StatusOK, mockResult)
	}
}

// ScanNetwork 處理發起網路掃描的請求。
func ScanNetwork(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現觸發異步掃描任務的邏輯。
		mockResponse := models.ScanTaskResponse{TaskID: "scan-123", Status: "pending"}
		jsonResponse(w, http.StatusAccepted, mockResponse)
	}
}

// GetScanResult 處理查詢網路掃描結果的請求。
func GetScanResult(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現查詢掃描任務狀態和結果的邏輯。
		mockResult := models.ScanResult{TaskID: "scan-123", Status: "completed"}
		jsonResponse(w, http.StatusOK, mockResult)
	}
}

// --- Incidents Handlers (Skeletons) ---

// ListIncidents 處理獲取事件列表的請求。
func ListIncidents(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現包含過濾和分頁的真實查詢邏輯。
		mockIncidents := models.IncidentList{
			Items:      []models.Incident{},
			Pagination: models.Pagination{Page: 1, PageSize: 20, Total: 0, TotalPages: 1},
		}
		jsonResponse(w, http.StatusOK, mockIncidents)
	}
}

// CreateIncident 處理創建新事件的請求。
func CreateIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現真實的事件創建邏輯。
		var req models.IncidentCreateRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			jsonResponse(w, http.StatusBadRequest, nil)
			return
		}
		mockIncident := models.Incident{ID: 101, Name: req.Title, Level: req.Severity, Status: "new"}
		jsonResponse(w, http.StatusCreated, mockIncident)
	}
}

// GetIncident 處理獲取單一事件詳情的請求。
func GetIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 從 URL 解析 incidentId 並查詢資料庫。
		mockIncident := models.Incident{ID: 101, Name: "High CPU Usage", Level: "critical", Status: "new"}
		jsonResponse(w, http.StatusOK, mockIncident)
	}
}

// UpdateIncident 處理更新事件的請求。
func UpdateIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現真實的事件更新邏輯。
		mockIncident := models.Incident{ID: 101, Name: "Updated Incident Title"}
		jsonResponse(w, http.StatusOK, mockIncident)
	}
}

// AcknowledgeIncident 處理確認事件的請求。
func AcknowledgeIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現事件確認邏輯。
		mockIncident := models.Incident{ID: 101, Status: "acknowledged"}
		jsonResponse(w, http.StatusOK, mockIncident)
	}
}

// ResolveIncident 處理解決事件的請求。
func ResolveIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現事件解決邏輯。
		mockIncident := models.Incident{ID: 101, Status: "resolved"}
		jsonResponse(w, http.StatusOK, mockIncident)
	}
}

// AssignIncident 處理指派事件的請求。
func AssignIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現事件指派邏輯。
		jsonResponse(w, http.StatusOK, map[string]string{"message": "Incident assigned"})
	}
}

// AddIncidentComment 處理為事件新增註記的請求。
func AddIncidentComment(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現新增註記邏輯。
		jsonResponse(w, http.StatusCreated, map[string]string{"message": "Comment added"})
	}
}

// GenerateIncidentReport 處理生成 AI 事件報告的請求。
func GenerateIncidentReport(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 呼叫 SRE Assistant 服務來生成報告。
		mockReport := models.AIGeneratedReport{ReportType: "summary", Content: "This is an AI generated report."}
		jsonResponse(w, http.StatusOK, mockReport)
	}
}

// ListAlerts 處理獲取當前活躍告警列表的請求。
func ListAlerts(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 實現從監控系統查詢告警的邏輯。
		jsonResponse(w, http.StatusOK, map[string]interface{}{"alerts": []string{}, "total": 0})
	}
}
