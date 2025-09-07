package api_test

import (
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"

    api "github.com/detectviz/control-plane/internal/api"
)

func TestGetDashboardTrendsContract(t *testing.T) {
    rr := httptest.NewRecorder()
    req := httptest.NewRequest(http.MethodGet, "/api/v1/dashboard/trends?period=24h", nil)

    handler := api.GetDashboardTrends(nil)
    handler.ServeHTTP(rr, req)

    if rr.Code != http.StatusOK {
        t.Fatalf("expected 200, got %d", rr.Code)
    }

    var payload map[string]interface{}
    if err := json.Unmarshal(rr.Body.Bytes(), &payload); err != nil {
        t.Fatalf("invalid json: %v", err)
    }
    if _, ok := payload["period"].(string); !ok {
        t.Fatalf("missing or invalid 'period'")
    }
    dps, ok := payload["data_points"].([]interface{})
    if !ok {
        t.Fatalf("missing or invalid 'data_points'")
    }
    if len(dps) == 0 {
        t.Fatalf("expected at least one data point")
    }
}

func TestGetResourceDistributionContract(t *testing.T) {
    rr := httptest.NewRecorder()
    req := httptest.NewRequest(http.MethodGet, "/api/v1/dashboard/resource-distribution", nil)

    handler := api.GetResourceDistribution(nil)
    handler.ServeHTTP(rr, req)

    if rr.Code != http.StatusOK {
        t.Fatalf("expected 200, got %d", rr.Code)
    }

    var payload map[string]interface{}
    if err := json.Unmarshal(rr.Body.Bytes(), &payload); err != nil {
        t.Fatalf("invalid json: %v", err)
    }
    if _, ok := payload["by_status"].(map[string]interface{}); !ok {
        t.Fatalf("missing or invalid 'by_status'")
    }
    if _, ok := payload["by_type"].(map[string]interface{}); !ok {
        t.Fatalf("missing or invalid 'by_type'")
    }
    if _, ok := payload["by_group"].([]interface{}); !ok {
        t.Fatalf("missing or invalid 'by_group'")
    }
}
