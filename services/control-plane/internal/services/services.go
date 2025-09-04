// Package services 包含了應用程式的核心業務邏輯。
// 它是處理器 (handlers) 和底層實現 (如資料庫) 之間的中介層。
// 這種分層有助於保持程式碼的整潔和可測試性。
package services

import (
	"database/sql"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/config"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
)

// Services 是一個容器，集中管理所有業務邏輯服務。
// 它會被傳遞給 HTTP 處理器 (handlers)，讓處理器可以存取後端服務。
type Services struct {
	DB                 *sql.DB
	Config             *config.Config
	Logger             *otelzap.Logger
	SreAssistantClient *SreAssistantClientImpl // SRE Assistant 服務的客戶端
}

// NewServices 建立並返回一個新的 Services 實例。
func NewServices(db *sql.DB, cfg *config.Config, logger *otelzap.Logger, authSvc *auth.KeycloakService) *Services {
	// 初始化 SRE Assistant 的客戶端。
	sreClient := NewSreAssistantClient(cfg.SREAssistant.BaseURL, authSvc, logger)

	return &Services{
		DB:                 db,
		Config:             cfg,
		Logger:             logger,
		SreAssistantClient: sreClient,
	}
}
