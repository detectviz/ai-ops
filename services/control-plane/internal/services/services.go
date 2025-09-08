// services/control-plane/internal/services/services.go
package services

import (
	"context"
	"time"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/config"
	"github.com/detectviz/control-plane/internal/database"
	"github.com/detectviz/control-plane/internal/models"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

// Services 是一個容器，集中管理所有業務邏輯服務。
type Services struct {
	DB                 *database.DB // << 修改：使用我們自訂的 DB 結構體
	Config             *config.Config
	Logger             *otelzap.Logger
	SreAssistantClient SreAssistantClient
}

// NewServices 建立並返回一個新的 Services 實例。
func NewServices(db *database.DB, cfg *config.Config, logger *otelzap.Logger, authSvc *auth.KeycloakService) *Services { // << 修改：接受 *database.DB 和 *auth.KeycloakService
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
	// TODO (Jules): 等待 database 層使用 GORM 重新實作 GetDeploymentByID 後，再恢復此處的邏輯。
	// 目前返回一個模擬的部署物件以確保編譯通過。
	return &models.Deployment{
		ID:          id,
		ServiceName: "mock-service",
		Namespace:   "default",
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}, nil
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
		},
	}

	return s.SreAssistantClient.DiagnoseDeployment(ctx, req)
}

// CheckDiagnosisStatus 檢查診斷任務的狀態
func (s *Services) CheckDiagnosisStatus(ctx context.Context, sessionID string) (*DiagnosticStatus, error) {
	return s.SreAssistantClient.GetDiagnosticStatus(ctx, sessionID)
}

// CheckReadiness 檢查所有依賴服務的就緒狀態。
func (s *Services) CheckReadiness() bool {
	// 檢查資料庫連線
	if s.DB == nil {
		return false
	}
	// Access the embedded *gorm.DB field directly, then call its DB() method.
	sqlDB, err := s.DB.DB.DB()
	if err != nil {
		s.Logger.Error("無法獲取底層 SQL DB 物件", zap.Error(err))
		return false
	}
	if err := sqlDB.Ping(); err != nil {
		s.Logger.Error("資料庫 Ping 失敗", zap.Error(err))
		return false
	}

	// TODO: 增加對 Redis, SRE Assistant 等其他服務的檢查

	return true
}

// GetConfig returns the service's configuration.
func (s *Services) GetConfig() *config.Config {
	return s.Config
}

// << 移除：ListResources 函式，因為它呼叫了一個不存在的 database.ListResources
