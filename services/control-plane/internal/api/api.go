// Package api 包含了所有供外部服務 (如此處的 SRE Assistant) 呼叫的 API 端點處理器。
// 這些端點受到 M2M JWT 權杖的保護。
package api

import (
	"encoding/json"
	"net/http"
	"time"

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

// GetIncident 處理獲取單筆告警紀錄的請求 (存根)。
func GetIncident(svcs *services.Services) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// TODO: 解析 ID 並從資料庫中查詢
		mockIncident := map[string]interface{}{
			"id":     1001,
			"level":  "error",
			"time":   time.Now().Add(-30 * time.Minute).Format(time.RFC3339),
			"name":   "High CPU Usage",
			"desc":   "The payment-api service is experiencing high CPU usage.",
			"status": "new",
		}
		jsonResponse(w, http.StatusOK, mockIncident)
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
