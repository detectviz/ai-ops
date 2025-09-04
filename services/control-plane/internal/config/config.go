// services/control-plane/internal/config/config.go
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

// Config 主配置結構
type Config struct {
	Environment  string
	Server       ServerConfig
	Database     DatabaseConfig
	Redis        RedisConfig
	Auth         AuthConfig
	SREAssistant SREAssistantConfig
	Monitoring   MonitoringConfig
	Features     FeaturesConfig
}

// ServerConfig 伺服器配置
type ServerConfig struct {
	Port        int
	Host        string
	Debug       bool
	CORSOrigins []string
}

// DatabaseConfig 資料庫配置
type DatabaseConfig struct {
	URL            string
	MaxConnections int
	MaxIdle        int
	MaxLifetime    int
}

// RedisConfig Redis 配置
type RedisConfig struct {
	URL        string
	MaxRetries int
	PoolSize   int
	Password   string
}

// AuthConfig 認證配置
type AuthConfig struct {
	Provider         string
	KeycloakURL      string
	KeycloakRealm    string
	KeycloakClientID string
	KeycloakSecret   string
	JWTSecret        string
	SessionTimeout   int
	RedirectURL      string
}

// SREAssistantConfig SRE Assistant 整合配置
type SREAssistantConfig struct {
	BaseURL      string
	ClientID     string
	ClientSecret string
	Timeout      int
}

// MonitoringConfig 監控服務配置
type MonitoringConfig struct {
	PrometheusURL      string
	GrafanaURL         string
	GrafanaAPIKey      string
	VictoriaMetricsURL string
	LokiURL            string
}

// FeaturesConfig 功能開關
type FeaturesConfig struct {
	EnableAutoRemediation  bool
	EnableAIAnalysis       bool
	EnableCapacityPlanning bool
	EnableSREIntegration   bool
}

// Load 載入配置
func Load() (*Config, error) {
	// 載入 .env 檔案 (如果存在)
	_ = godotenv.Load()

	cfg := &Config{
		Environment: getEnv("ENVIRONMENT", "development"),

		Server: ServerConfig{
			Port:        getEnvAsInt("PORT", 8081),
			Host:        getEnv("HOST", "0.0.0.0"),
			Debug:       getEnvAsBool("DEBUG", false),
			CORSOrigins: getEnvAsSlice("CORS_ORIGINS", []string{"http://localhost:3000"}),
		},

		Database: DatabaseConfig{
			URL:            getEnv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/control_plane?sslmode=disable"),
			MaxConnections: getEnvAsInt("DB_MAX_CONNECTIONS", 25),
			MaxIdle:        getEnvAsInt("DB_MAX_IDLE", 5),
			MaxLifetime:    getEnvAsInt("DB_MAX_LIFETIME", 300),
		},

		Redis: RedisConfig{
			URL:        getEnv("REDIS_URL", "redis://localhost:6379"),
			MaxRetries: getEnvAsInt("REDIS_MAX_RETRIES", 3),
			PoolSize:   getEnvAsInt("REDIS_POOL_SIZE", 10),
			Password:   getEnv("REDIS_PASSWORD", ""),
		},

		Auth: AuthConfig{
			Provider:         getEnv("AUTH_PROVIDER", "keycloak"),
			KeycloakURL:      getEnv("KEYCLOAK_URL", "http://localhost:8080"),
			KeycloakRealm:    getEnv("KEYCLOAK_REALM", "sre-platform"),
			KeycloakClientID: getEnv("KEYCLOAK_CLIENT_ID", "control-plane"),
			KeycloakSecret:   getEnv("KEYCLOAK_CLIENT_SECRET", "control-plane-secret"),
			JWTSecret:        getEnv("JWT_SECRET", "change-me-in-production"),
			SessionTimeout:   getEnvAsInt("SESSION_TIMEOUT", 3600),
			RedirectURL:      getEnv("AUTH_REDIRECT_URL", "http://localhost:8081/auth/callback"),
		},

		SREAssistant: SREAssistantConfig{
			BaseURL:      getEnv("SRE_ASSISTANT_URL", "http://localhost:8000"),
			ClientID:     getEnv("SRE_ASSISTANT_CLIENT_ID", "control-plane"),
			ClientSecret: getEnv("SRE_ASSISTANT_CLIENT_SECRET", ""),
			Timeout:      getEnvAsInt("SRE_ASSISTANT_TIMEOUT", 30),
		},

		Monitoring: MonitoringConfig{
			PrometheusURL:      getEnv("PROMETHEUS_URL", "http://localhost:9090"),
			GrafanaURL:         getEnv("GRAFANA_URL", "http://localhost:3000"),
			GrafanaAPIKey:      getEnv("GRAFANA_API_KEY", ""),
			VictoriaMetricsURL: getEnv("VICTORIA_METRICS_URL", "http://localhost:8428"),
			LokiURL:            getEnv("LOKI_URL", "http://localhost:3100"),
		},

		Features: FeaturesConfig{
			EnableAutoRemediation:  getEnvAsBool("FEATURE_AUTO_REMEDIATION", false),
			EnableAIAnalysis:       getEnvAsBool("FEATURE_AI_ANALYSIS", true),
			EnableCapacityPlanning: getEnvAsBool("FEATURE_CAPACITY_PLANNING", true),
			EnableSREIntegration:   getEnvAsBool("FEATURE_SRE_INTEGRATION", true),
		},
	}

	return cfg, cfg.Validate()
}

// Validate 驗證配置
func (c *Config) Validate() error {
	if c.Server.Port <= 0 || c.Server.Port > 65535 {
		return fmt.Errorf("無效的埠號: %d", c.Server.Port)
	}

	if c.Database.URL == "" {
		return fmt.Errorf("資料庫 URL 不能為空")
	}

	if c.Auth.Provider == "keycloak" {
		if c.Auth.KeycloakURL == "" || c.Auth.KeycloakRealm == "" {
			return fmt.Errorf("Keycloak 配置不完整")
		}
	}

	return nil
}

// 輔助函式

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intVal, err := strconv.Atoi(value); err == nil {
			return intVal
		}
	}
	return defaultValue
}

func getEnvAsBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolVal, err := strconv.ParseBool(value); err == nil {
			return boolVal
		}
	}
	return defaultValue
}

func getEnvAsSlice(key string, defaultValue []string) []string {
	if value := os.Getenv(key); value != "" {
		return strings.Split(value, ",")
	}
	return defaultValue
}
