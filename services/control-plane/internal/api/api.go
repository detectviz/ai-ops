// Package api 包含了所有供外部服務 (如此處的 SRE Assistant) 呼叫的 API 端點處理器。
// 這些端點受到 M2M JWT 權杖的保護。
package api

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/detectviz/control-plane/internal/models"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/google/uuid"
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
		// 修正：雖然這是 map[string]interface{}，但仍應盡力與 spec 保持一致
		mockIncidents := []map[string]interface{}{
			{
				"id":          "INC-1001",
				"severity":    "error",
				"created_at":  time.Now().Add(-30 * time.Minute).Format(time.RFC3339),
				"title":       "High CPU Usage",
				"description": "The payment-api service is experiencing high CPU usage.",
				"status":      "new",
			},
		}
		jsonResponse(w, http.StatusOK, mockIncidents)
	}
}

// GetExecutions 處理獲取自動化執行日誌的請求 (存根)。
func GetExecutions(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockExecutions := []map[string]interface{}{}
		jsonResponse(w, http.StatusOK, mockExecutions)
	}
}

// CreateExecution 處理建立新執行紀錄的請求 (存根)。
func CreateExecution(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
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
func UpdateExecution(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
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
		mockSummary := models.DashboardSummary{
			Alerts: &models.DashboardSummaryAlerts{ New: 5, Processing: 2, ResolvedToday: 15 },
			Resources: &models.DashboardSummaryResources{ Total: 150, Healthy: 145, Warning: 3, Critical: 2 },
			KPIs:      &models.DashboardSummaryKPIs{ Availability: 99.98, MTTR: 15.5, IncidentRate: 0.5 },
		}
		jsonResponse(w, http.StatusOK, mockSummary)
	}
}

// GetDashboardTrends 處理儀表板趨勢數據的請求 (骨架)。
func GetDashboardTrends(svcs *services.Services) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        period := r.URL.Query().Get("period")
        if period == "" {
            period = "24h"
        }
        mockTrends := map[string]interface{}{
            "period": period,
            "data_points": []map[string]interface{}{
                {"timestamp": time.Now().Add(-2 * time.Hour).Format(time.RFC3339), "incidents": 5, "cpu_usage": 60.5},
                {"timestamp": time.Now().Add(-1 * time.Hour).Format(time.RFC3339), "incidents": 3, "cpu_usage": 65.2},
                {"timestamp": time.Now().Format(time.RFC3339), "incidents": 2, "cpu_usage": 63.1},
            },
        }
        jsonResponse(w, http.StatusOK, mockTrends)
    }
}

// GetResourceDistribution 處理資源分佈數據的請求 (骨架)。
func GetResourceDistribution(svcs *services.Services) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        mockDistribution := map[string]interface{}{
            "by_status": map[string]int{
                "healthy":  145,
                "warning":  3,
                "critical": 2,
            },
            "by_type": map[string]int{
                "server":      100,
                "database":    20,
                "application": 30,
            },
            "by_group": []map[string]interface{}{
                {"group_name": "Core Services", "count": 50},
                {"group_name": "Data Platform", "count": 40},
                {"group_name": "Web Services", "count": 60},
            },
        }
        jsonResponse(w, http.StatusOK, mockDistribution)
    }
}

// --- Resources Handlers (Skeletons) ---

func ListResources(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockResources := models.ResourceList{
			Items:      []models.Resource{},
			Pagination: models.Pagination{Page: 1, PageSize: 20, Total: 0, TotalPages: 1},
		}
		jsonResponse(w, http.StatusOK, mockResources)
	}
}

func CreateResource(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req models.ResourceCreateRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			jsonResponse(w, http.StatusBadRequest, nil)
			return
		}
		mockResource := models.Resource{ID: uuid.NewString(), Name: req.Name, Type: req.Type, IPAddress: req.IPAddress, Status: "unknown"}
		jsonResponse(w, http.StatusCreated, mockResource)
	}
}

func GetResource(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockResource := models.Resource{ID: uuid.NewString(), Name: "mock-server-01", Type: "server", Status: "healthy"}
		jsonResponse(w, http.StatusOK, mockResource)
	}
}

func UpdateResource(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockResource := models.Resource{ID: uuid.NewString(), Name: "updated-mock-server-01", Type: "server", Status: "healthy"}
		jsonResponse(w, http.StatusOK, mockResource)
	}
}

func DeleteResource(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		jsonResponse(w, http.StatusNoContent, nil)
	}
}

func BatchOperateResources(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockResult := models.BatchOperationResult{SuccessCount: 1, FailureCount: 0}
		jsonResponse(w, http.StatusOK, mockResult)
	}
}

func ScanNetwork(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockResponse := models.ScanTaskResponse{TaskID: "scan-123", Status: "pending"}
		jsonResponse(w, http.StatusAccepted, mockResponse)
	}
}

func GetScanResult(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockResult := models.ScanResult{TaskID: "scan-123", Status: "completed"}
		jsonResponse(w, http.StatusOK, mockResult)
	}
}

// --- Incidents Handlers (Skeletons) ---

func ListIncidents(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockIncidents := models.IncidentList{
			Items:      []models.Incident{},
			Pagination: models.Pagination{Page: 1, PageSize: 20, Total: 0, TotalPages: 1},
		}
		jsonResponse(w, http.StatusOK, mockIncidents)
	}
}

func CreateIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req models.IncidentCreateRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			jsonResponse(w, http.StatusBadRequest, nil)
			return
		}
		mockIncident := models.Incident{ID: uuid.NewString(), Title: req.Title, Severity: req.Severity, Status: "new"}
		jsonResponse(w, http.StatusCreated, mockIncident)
	}
}

func GetIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockIncident := models.Incident{ID: uuid.NewString(), Title: "High CPU Usage", Severity: "critical", Status: "new"}
		jsonResponse(w, http.StatusOK, mockIncident)
	}
}

func UpdateIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockIncident := models.Incident{ID: uuid.NewString(), Title: "Updated Incident Title"}
		jsonResponse(w, http.StatusOK, mockIncident)
	}
}

func AcknowledgeIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockIncident := models.Incident{ID: uuid.NewString(), Status: "acknowledged"}
		jsonResponse(w, http.StatusOK, mockIncident)
	}
}

func ResolveIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockIncident := models.Incident{ID: uuid.NewString(), Status: "resolved"}
		jsonResponse(w, http.StatusOK, mockIncident)
	}
}

func AssignIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		jsonResponse(w, http.StatusOK, map[string]string{"message": "Incident assigned"})
	}
}

func AddIncidentComment(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		jsonResponse(w, http.StatusCreated, map[string]string{"message": "Comment added"})
	}
}

func GenerateIncidentReport(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		mockReport := models.AIGeneratedReport{ReportType: "summary", Content: "This is an AI generated report."}
		jsonResponse(w, http.StatusOK, mockReport)
	}
}

func ListAlerts(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		jsonResponse(w, http.StatusOK, map[string]interface{}{"alerts": []string{}, "total": 0})
	}
}
