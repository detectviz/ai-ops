package handlers_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/detectviz/control-plane/internal/handlers"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

func TestHealthzContract(t *testing.T) {
	// 建立一個假的 HTTP 請求
	req := httptest.NewRequest(http.MethodGet, "/api/v1/healthz", nil)
	// 建立一個 ResponseRecorder 來捕獲回應
	rr := httptest.NewRecorder()

	// 建立一個 handlers 的實例來進行測試
	// 注意：HealthCheck 不需要任何依賴，所以傳入 nil 是安全的
	h := handlers.NewHandlers(nil, nil, nil, nil)
	h.HealthCheck(rr, req)

	// 驗證狀態碼
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v",
			status, http.StatusOK)
	}

	// 驗證回應內容
	var payload map[string]interface{}
	if err := json.Unmarshal(rr.Body.Bytes(), &payload); err != nil {
		t.Fatalf("Failed to unmarshal response body: %v", err)
	}

	// 驗證必要欄位是否存在且型別正確
	if _, ok := payload["status"].(string); !ok {
		t.Errorf("response missing or has wrong type for 'status' field")
	}
	if _, ok := payload["timestamp"].(string); !ok {
		t.Errorf("response missing or has wrong type for 'timestamp' field")
	}
}

func TestReadyzContract(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/api/v1/readyz", nil)
	rr := httptest.NewRecorder()

	// 提供模擬的依賴以避免 nil pointer panic
	mockLogger := otelzap.New(zap.NewNop()) // 測試時使用無操作的 logger
	mockServices := &services.Services{}   // 一個空的 services 物件即可

	h := handlers.NewHandlers(mockServices, nil, nil, mockLogger)
	h.ReadinessCheck(rr, req)

	// 在成功的契約測試中，我們預期服務是就緒的 (200)
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(rr.Body.Bytes(), &payload); err != nil {
		t.Fatalf("Failed to unmarshal response body: %v", err)
	}

	// 驗證 'ready' 欄位
	if ready, ok := payload["ready"].(bool); !ok || !ready {
		t.Errorf("response 'ready' field is missing, not a boolean, or false")
	}

	// 驗證 'checks' 物件及其中的鍵
	checks, ok := payload["checks"].(map[string]interface{})
	if !ok {
		t.Fatalf("response missing or has wrong type for 'checks' field")
	}

	expectedChecks := []string{"database", "redis", "keycloak", "sre_assistant"}
	for _, checkName := range expectedChecks {
		if _, ok := checks[checkName].(bool); !ok {
			t.Errorf("checks object missing or has wrong type for '%s' field", checkName)
		}
	}
}
