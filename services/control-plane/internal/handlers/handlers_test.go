package handlers_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/detectviz/control-plane/internal/config"
	"github.com/detectviz/control-plane/internal/handlers"
	"github.com/detectviz/control-plane/internal/models"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/stretchr/testify/assert"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

// MockServices is a mock implementation of the Services interface for testing.
type MockServices struct {
	readinessResult bool
	// Add fields to control mock behavior for other methods
}

func (m *MockServices) CheckReadiness() bool {
	return m.readinessResult
}

func (m *MockServices) GetDeploymentByID(ctx context.Context, id string) (*models.Deployment, error) {
	return &models.Deployment{ID: id, ServiceName: "mock-service"}, nil
}

func (m *MockServices) TriggerDeploymentDiagnosis(ctx context.Context, deployment *models.Deployment) (*services.DiagnosticResponse, error) {
	return &services.DiagnosticResponse{SessionID: "mock-session-id"}, nil
}

func (m *MockServices) CheckDiagnosisStatus(ctx context.Context, sessionID string) (*services.DiagnosticStatus, error) {
	return &services.DiagnosticStatus{SessionID: sessionID, Status: "completed"}, nil
}

func (m *MockServices) GetConfig() *config.Config {
	return &config.Config{Auth: config.AuthConfig{Mode: "dev"}}
}

// Ensure MockServices implements the necessary interface for handlers.
var _ handlers.ServiceChecker = (*MockServices)(nil)


func TestHealthCheck(t *testing.T) {
	// Arrange
	h := &handlers.Handlers{Logger: otelzap.New(zap.NewNop())}
	req, err := http.NewRequest("GET", "/api/v1/healthz", nil)
	assert.NoError(t, err)
	rr := httptest.NewRecorder()

	// Act
	h.HealthCheck(rr, req)

	// Assert
	assert.Equal(t, http.StatusOK, rr.Code, "HealthCheck should return status 200")

	var resp map[string]interface{}
	err = json.Unmarshal(rr.Body.Bytes(), &resp)
	assert.NoError(t, err)
	assert.Equal(t, "healthy", resp["status"], "HealthCheck response should indicate a healthy status")
}

func TestReadinessCheck_Ready(t *testing.T) {
	// Arrange
	mockServices := &MockServices{readinessResult: true}
	h := handlers.NewHandlersForTest(mockServices, nil, otelzap.New(zap.NewNop()))

	req, err := http.NewRequest("GET", "/api/v1/readyz", nil)
	assert.NoError(t, err)
	rr := httptest.NewRecorder()

	// Act
	h.ReadinessCheck(rr, req)

	// Assert
	assert.Equal(t, http.StatusOK, rr.Code, "ReadinessCheck should return status 200 when services are ready")

	var resp map[string]interface{}
	err = json.Unmarshal(rr.Body.Bytes(), &resp)
	assert.NoError(t, err)
	assert.True(t, resp["ready"].(bool), "ReadinessCheck response should be true when ready")
}

func TestReadinessCheck_NotReady(t *testing.T) {
	// Arrange
	mockServices := &MockServices{readinessResult: false}
	h := handlers.NewHandlersForTest(mockServices, nil, otelzap.New(zap.NewNop()))

	req, err := http.NewRequest("GET", "/api/v1/readyz", nil)
	assert.NoError(t, err)
	rr := httptest.NewRecorder()

	// Act
	h.ReadinessCheck(rr, req)

	// Assert
	assert.Equal(t, http.StatusServiceUnavailable, rr.Code, "ReadinessCheck should return status 503 when services are not ready")

	var resp map[string]interface{}
	err = json.Unmarshal(rr.Body.Bytes(), &resp)
	assert.NoError(t, err)
	assert.False(t, resp["ready"].(bool), "ReadinessCheck response should be false when not ready")
}
