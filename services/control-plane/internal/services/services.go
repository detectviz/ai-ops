// services/control-plane/internal/services/services.go
package services

import (
	"context"
	"database/sql"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/config"
	"github.com/detectviz/control-plane/internal/database"
	"github.com/detectviz/control-plane/internal/models"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
)

// Services 是一個容器，集中管理所有業務邏輯服務。
type Services struct {
	DB                 *sql.DB
	Config             *config.Config
	Logger             *otelzap.Logger
	SreAssistantClient SreAssistantClient
}

// NewServices 建立並返回一個新的 Services 實例。
func NewServices(db *sql.DB, cfg *config.Config, logger *otelzap.Logger, authSvc auth.KeycloakService) *Services {
	sreClient := NewSreAssistantClient(cfg.SREAssistant.BaseURL, authSvc, logger)
	return &Services{
		DB:                 db,
		Config:             cfg,
		Logger:             logger,
		SreAssistantClient: sreClient,
	}
}

// GetDeploymentByID 透過呼叫資料庫層來根據 ID 檢索部署資訊。
func (s *Services) GetDeploymentByID(ctx context.Context, id string) (*models.Deployment, error) {
	// 修正：呼叫 database 層的函式時，不傳遞 context
	return database.GetDeploymentByID(s.DB, id)
}

// TriggerDeploymentDiagnosis 觸發一個部署診斷任務
func (s *Services) TriggerDeploymentDiagnosis(ctx context.Context, deployment *models.Deployment) (*DiagnosticResponse, error) {
	req := &DiagnosticRequest{
		IncidentID:       "deploy-" + deployment.ID,
		Severity:         "P2",
		AffectedServices: []string{deployment.ServiceName},
		Context: map[string]string{
			"deployment_id": deployment.ID,
			"service_name":  deployment.ServiceName,
			"namespace":     deployment.Namespace,
			// 修正：移除了不存在的 ImageTag 欄位
		},
	}

	return s.SreAssistantClient.DiagnoseDeployment(ctx, req)
}

// CheckDiagnosisStatus 檢查診斷任務的狀態
func (s *Services) CheckDiagnosisStatus(ctx context.Context, sessionID string) (*DiagnosticStatus, error) {
	return s.SreAssistantClient.GetDiagnosticStatus(ctx, sessionID)
}
