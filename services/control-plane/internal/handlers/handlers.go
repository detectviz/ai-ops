// services/control-plane/internal/handlers/handlers.go
package handlers

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
	"sync"
	"time"
    "html/template"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/config"
	"github.com/detectviz/control-plane/internal/models"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/gorilla/mux"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

// ServiceChecker defines the interface for services that handlers depend on.
type ServiceChecker interface {
	CheckReadiness() bool
	GetDeploymentByID(ctx context.Context, id string) (*models.Deployment, error)
	TriggerDeploymentDiagnosis(ctx context.Context, deployment *models.Deployment) (*services.DiagnosticResponse, error)
	CheckDiagnosisStatus(ctx context.Context, sessionID string) (*services.DiagnosticStatus, error)
	GetConfig() *config.Config
}

// Handlers is a container for all HTTP handler methods.
type Handlers struct {
	Services    ServiceChecker
    Templates   *template.Template
	AuthService *auth.KeycloakService
	Logger      *otelzap.Logger
	mu          sync.RWMutex
}

// NewHandlers creates and returns a new Handlers instance.
func NewHandlers(s *services.Services, t *template.Template, as *auth.KeycloakService, l *otelzap.Logger) *Handlers {
	return &Handlers{
		Services:    s,
        Templates:   t,
		AuthService: as,
		Logger:      l,
	}
}

func NewHandlersForTest(s ServiceChecker, t *template.Template, l *otelzap.Logger) *Handlers {
    return &Handlers{
        Services:    s,
        Templates:   t,
        Logger:      l,
    }
}

// --- Helper ---

func (h *Handlers) writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if data != nil {
		if err := json.NewEncoder(w).Encode(data); err != nil {
			h.Logger.Error("無法寫入 JSON 響應", zap.Error(err))
		}
	}
}

// --- Core & Auth Handlers ---

func (h *Handlers) HealthCheck(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
		"version":   "1.0.0",
	}
	h.writeJSON(w, http.StatusOK, response)
}

func (h *Handlers) ReadinessCheck(w http.ResponseWriter, r *http.Request) {
	ready := h.Services.CheckReadiness()
	response := map[string]interface{}{
		"ready": ready,
		"checks": map[string]bool{
			"database":      ready,
			"redis":         true,
			"keycloak":      true,
			"sre_assistant": true,
		},
	}
	if !ready {
		h.writeJSON(w, http.StatusServiceUnavailable, response)
		return
	}
	h.writeJSON(w, http.StatusOK, response)
}

func (h *Handlers) MetricsCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("# HELP control_plane_up Control Plane service status\n# TYPE control_plane_up gauge\ncontrol_plane_up 1\n"))
}

func (h *Handlers) DevLogin(w http.ResponseWriter, r *http.Request) {
    // Dev only login, not for production
    h.writeJSON(w, http.StatusOK, map[string]string{"token": "dev-token"})
}

func (h *Handlers) DevRefreshToken(w http.ResponseWriter, r *http.Request) {
    h.writeJSON(w, http.StatusOK, map[string]string{"token": "refreshed-dev-token"})
}

func (h *Handlers) DevLogout(w http.ResponseWriter, r *http.Request) {
    h.writeJSON(w, http.StatusOK, map[string]string{"message": "dev user logged out"})
}

// --- SRE Assistant Related Handlers ---

func (h *Handlers) DiagnoseDeployment(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	vars := mux.Vars(r)
	deploymentID, ok := vars["id"]
	if !ok {
		h.writeJSON(w, http.StatusBadRequest, map[string]string{"error": "缺少 deployment ID"})
		return
	}
	h.Logger.Ctx(ctx).Info("開始部署診斷", zap.String("deploymentID", deploymentID))
	deployment, err := h.Services.GetDeploymentByID(ctx, deploymentID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			h.writeJSON(w, http.StatusNotFound, map[string]string{"error": "找不到部署資訊"})
		} else {
			h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "查詢部署資訊時發生錯誤"})
		}
		return
	}
	resp, err := h.Services.TriggerDeploymentDiagnosis(ctx, deployment)
	if err != nil {
		h.Logger.Ctx(ctx).Error("呼叫 SRE Assistant 失敗", zap.Error(err))
		h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "呼叫診斷服務失敗"})
		return
	}
	h.writeJSON(w, http.StatusAccepted, resp)
}

func (h *Handlers) GetDiagnosisStatus(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	vars := mux.Vars(r)
	sessionID, ok := vars["session_id"]
	if !ok {
		h.writeJSON(w, http.StatusBadRequest, map[string]string{"error": "缺少 session_id"})
		return
	}
	status, err := h.Services.CheckDiagnosisStatus(ctx, sessionID)
	if err != nil {
		h.Logger.Ctx(ctx).Error("查詢狀態失敗", zap.Error(err), zap.String("sessionID", sessionID))
		h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "查詢狀態時發生內部錯誤"})
		return
	}
	h.writeJSON(w, http.StatusOK, status)
}

// --- Mock API Handlers ---

func (h *Handlers) GetDashboardSummary(w http.ResponseWriter, r *http.Request) {
    summary := models.DashboardSummary{
        Alerts: &models.DashboardSummaryAlerts{
            New:           5,
            Processing:    10,
            ResolvedToday: 25,
        },
        Resources: &models.DashboardSummaryResources{
            Total:    150,
            Healthy:  140,
            Warning:  8,
            Critical: 2,
        },
        KPIs: &models.DashboardSummaryKPIs{
            Availability: 99.95,
            MTTR:         15.5,
            IncidentRate: 0.8,
        },
    }
    h.writeJSON(w, http.StatusOK, summary)
}

func (h *Handlers) ListResources(w http.ResponseWriter, r *http.Request) {
    resources := []models.Resource{
        {ID: "uuid-resource-1", Name: "prod-api-server-1", Type: "server", Status: "healthy", IPAddress: "10.0.1.10", Location: "us-central1-a"},
        {ID: "uuid-resource-2", Name: "prod-database-main", Type: "database", Status: "warning", IPAddress: "10.0.2.5", Location: "us-central1-a"},
    }
    h.writeJSON(w, http.StatusOK, resources)
}

func (h *Handlers) ListIncidents(w http.ResponseWriter, r *http.Request) {
    incidents := []models.Incident{
        {ID: "uuid-incident-1", Title: "Database CPU usage high", Severity: "warning", Status: "acknowledged"},
        {ID: "uuid-incident-2", Title: "API server latency spike", Severity: "critical", Status: "new"},
    }
    h.writeJSON(w, http.StatusOK, incidents)
}

// --- Placeholder Handlers for other API endpoints ---
func (h *Handlers) GetDashboardTrends(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, map[string]string{}) }
func (h *Handlers) GetResourceDistribution(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, map[string]string{}) }
func (h *Handlers) CreateResourceAPI(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusCreated, nil) }
func (h *Handlers) GetResource(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, map[string]string{}) }
func (h *Handlers) UpdateResource(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, nil) }
func (h *Handlers) DeleteResource(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusNoContent, nil) }
func (h *Handlers) BatchOperateResources(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, nil) }
func (h *Handlers) ScanNetwork(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusAccepted, nil) }
func (h *Handlers) GetScanResult(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, map[string]string{}) }
func (h *Handlers) GetAuditLogs(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, []string{}) }
func (h *Handlers) CreateIncident(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusCreated, nil) }
func (h *Handlers) GetIncident(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, map[string]string{}) }
func (h *Handlers) UpdateIncident(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, nil) }
func (h *Handlers) AcknowledgeIncident(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, nil) }
func (h *Handlers) ResolveIncident(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, nil) }
func (h *Handlers) AssignIncident(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, nil) }
func (h *Handlers) AddIncidentComment(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, nil) }
func (h *Handlers) GenerateIncidentReport(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, map[string]string{}) }
func (h *Handlers) ListAlerts(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, []string{}) }
func (h *Handlers) GetExecutions(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, []string{}) }
func (h *Handlers) CreateExecution(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusCreated, nil) }
func (h *Handlers) UpdateExecution(w http.ResponseWriter, r *http.Request) { h.writeJSON(w, http.StatusOK, nil) }
