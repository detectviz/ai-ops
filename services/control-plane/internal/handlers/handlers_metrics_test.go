package handlers_test

import (
    "net/http/httptest"
    "testing"

    "github.com/detectviz/control-plane/internal/handlers"
    "github.com/uptrace/opentelemetry-go-extra/otelzap"
    "go.uber.org/zap"
)

func TestMetricsCheckContentType(t *testing.T) {
    h := &handlers.Handlers{Logger: otelzap.New(zap.NewNop())}
    rr := httptest.NewRecorder()
    req := httptest.NewRequest("GET", "/api/v1/metrics", nil)

    h.MetricsCheck(rr, req)

    if rr.Code != 200 {
        t.Fatalf("expected 200, got %d", rr.Code)
    }
    ct := rr.Header().Get("Content-Type")
    if ct == "" || ct[:10] != "text/plain" {
        t.Fatalf("unexpected content-type: %s", ct)
    }
}
