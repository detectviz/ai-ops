package config

import (
	"github.com/caarlos0/env/v6"
)

// Config 包含了應用程式的所有配置。
// 我們使用 "env" 標籤來從環境變數中讀取配置，這是一種雲原生的最佳實踐。
type Config struct {
	Server       ServerConfig
	Database     DatabaseConfig
	Auth         AuthConfig
	SREAssistant SREAssistantConfig
}

// ServerConfig 包含了伺服器的配置。
type ServerConfig struct {
	Port        int      `env:"PORT" envDefault:"8081"`
	CORSOrigins []string `env:"CORS_ORIGINS" envDefault:"http://localhost:8081" envSeparator:","`
}

// DatabaseConfig 包含了資料庫的配置。
type DatabaseConfig struct {
	URL string `env:"DATABASE_URL" envDefault:"postgres://postgres:postgres@localhost:5432/sre_dev?sslmode=disable"`
}

// AuthConfig 包含了 Keycloak 的配置。
type AuthConfig struct {
	URL             string `env:"KEYCLOAK_URL" envDefault:"http://localhost:8080"`
	Realm           string `env:"KEYCLOAK_REALM" envDefault:"sre-platform"`
	ClientID        string `env:"KEYCLOAK_CLIENT_ID" envDefault:"control-plane-ui"`
	ClientSecret    string `env:"KEYCLOAK_CLIENT_SECRET" envDefault:"your-ui-secret"` // 注意：這應該在生產環境中透過安全的方式提供
	RedirectURL     string `env:"KEYCLOAK_REDIRECT_URL" envDefault:"http://localhost:8081/auth/callback"`
	M2MClientID     string `env:"KEYCLOAK_M2M_CLIENT_ID" envDefault:"control-plane"`
	M2MClientSecret string `env:"KEYCLOAK_M2M_CLIENT_SECRET" envDefault:"control-plane-secret"`
}

// SREAssistantConfig 包含了 SRE Assistant 服務的配置。
type SREAssistantConfig struct {
	BaseURL string `env:"SRE_ASSISTANT_URL" envDefault:"http://localhost:8000"`
}

// Load 從環境變數中載入配置。
// 如果環境變數未設定，則會使用 envDefault 中定義的預設值。
func Load() (*Config, error) {
	cfg := &Config{}
	if err := env.Parse(cfg); err != nil {
		return nil, err
	}
	return cfg, nil
}
