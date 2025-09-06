package main

import (
	"context"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/detectviz/control-plane/internal/api"
	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/config"
	"github.com/detectviz/control-plane/internal/database"
	"github.com/detectviz/control-plane/internal/handlers"
	"github.com/detectviz/control-plane/internal/middleware"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/gorilla/mux"
	"github.com/rs/cors"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

func main() {
	logger := initLogger()
	defer logger.Sync()

	cfg, err := config.Load()
	if err != nil {
		logger.Fatal("載入配置失敗", zap.Error(err))
	}


	db, err := database.New(cfg.Database.URL)

	// 連接資料庫
	db, err := database.Connect(cfg.Database.URL)

	if err != nil {
		logger.Fatal("連接資料庫失敗", zap.Error(err))
	}

	if err := db.Migrate(); err != nil {

	defer db.Close()

	// 執行資料庫遷移
	if err := database.Migrate(db); err != nil {

		logger.Fatal("資料庫遷移失敗", zap.Error(err))
	}

	var authService *auth.KeycloakService
	if cfg.Auth.Mode == "keycloak" {
		var err error
		authService, err = auth.NewKeycloakService(cfg.Auth)
		if err != nil {
			logger.Fatal("初始化 Keycloak 認證服務失敗", zap.Error(err))
		}
		logger.Info("✅ Keycloak 認證服務已初始化")
	} else {
		logger.Info("🔍 在 DEV 模式下運行，跳過 Keycloak 初始化")
	}


	// 初始化服務層
	services := services.NewServices(db, cfg, logger, *authService)

	templates, err := loadTemplates("web/templates")
	if err != nil {
		logger.Fatal("載入模板失敗", zap.Error(err))
	}

	h := handlers.NewHandlers(services, templates, *authService, logger)
	router := setupRoutes(h, authService, logger, cfg)

	corsHandler := cors.New(cors.Options{
		AllowedOrigins:   cfg.Server.CORSOrigins,
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token"},
		ExposedHeaders:   []string{"Link"},
		AllowCredentials: true,
		MaxAge:           300,
	}).Handler(router)

	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
		Handler:      corsHandler,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		logger.Info("🚀 Control Plane 啟動", zap.Int("port", cfg.Server.Port))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("啟動伺服器失敗", zap.Error(err))
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logger.Info("正在關閉伺服器...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Fatal("伺服器強制關閉", zap.Error(err))
	}

	logger.Info("伺服器已關閉")
}

func initLogger() *otelzap.Logger {
	config := zap.NewProductionConfig()
	config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	zapLogger, err := config.Build()
	if err != nil {
		log.Fatalf("無法初始化 zap 日誌: %v", err)
	}
	return otelzap.New(zapLogger)
}

func loadTemplates(dir string) (*template.Template, error) {
	tmpl := template.New("")
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasSuffix(path, ".html") {
			relPath, err := filepath.Rel(dir, path)
			if err != nil {
				return err
			}
			templateName := filepath.ToSlash(relPath)
			// 讀取檔案內容並解析
			content, err := os.ReadFile(path)
			if err != nil {
				return err
			}
			_, err = tmpl.New(templateName).Parse(string(content))
			if err != nil {
				return err
			}
		}
		return nil
	})
	if err != nil {
		return nil, fmt.Errorf("遍歷模板目錄時出錯: %w", err)
	}
	return tmpl, nil
}

func setupRoutes(h *handlers.Handlers, auth *auth.KeycloakService, logger *otelzap.Logger, cfg *config.Config) *mux.Router {
	r := mux.NewRouter()

	r.Use(middleware.RequestID())
	r.Use(middleware.Logging(logger))
	r.Use(middleware.Recovery(logger))

	r.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./web/static/"))))

	r.HandleFunc("/health", h.HealthCheck).Methods("GET")
	r.HandleFunc("/ready", h.ReadinessCheck).Methods("GET")

	authRouter := r.PathPrefix("/auth").Subrouter()
	authRouter.HandleFunc("/login", h.LoginPage).Methods("GET")
	authRouter.HandleFunc("/login", h.HandleLogin).Methods("POST")
	authRouter.HandleFunc("/logout", h.HandleLogout).Methods("POST")
	authRouter.HandleFunc("/callback", h.AuthCallback).Methods("GET")

	apiRouter := r.PathPrefix("/api/v1").Subrouter()
	apiRouter.Use(middleware.RequireAuth(auth))
	apiRouter.HandleFunc("/dashboard/summary", api.GetDashboardSummary(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/resources", api.ListResources(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/resources", api.CreateResource(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/resources/{resourceId}", api.GetResource(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/resources/{resourceId}", api.UpdateResource(h.Services)).Methods("PUT")
	apiRouter.HandleFunc("/resources/{resourceId}", api.DeleteResource(h.Services)).Methods("DELETE")
	apiRouter.HandleFunc("/resources/batch", api.BatchOperateResources(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/resources/scan", api.ScanNetwork(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/resources/scan/{taskId}", api.GetScanResult(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/audit-logs", api.GetAuditLogs(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/incidents", api.ListIncidents(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/incidents", api.CreateIncident(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/incidents/{incidentId}", api.GetIncident(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/incidents/{incidentId}", api.UpdateIncident(h.Services)).Methods("PUT")
	apiRouter.HandleFunc("/incidents/{incidentId}/acknowledge", api.AcknowledgeIncident(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/incidents/{incidentId}/resolve", api.ResolveIncident(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/incidents/{incidentId}/assign", api.AssignIncident(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/incidents/{incidentId}/comments", api.AddIncidentComment(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/incidents/generate-report", api.GenerateIncidentReport(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/alerts", api.ListAlerts(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/executions", api.GetExecutions(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/executions", api.CreateExecution(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/executions/{id}", api.UpdateExecution(h.Services)).Methods("PATCH")

	webRouter := r.PathPrefix("/").Subrouter()
	webRouter.Use(middleware.RequireSession(auth, cfg))
	webRouter.HandleFunc("/", h.Dashboard).Methods("GET")
	webRouter.HandleFunc("/resources", h.ResourcesPage).Methods("GET")
	webRouter.HandleFunc("/teams", h.TeamsPage).Methods("GET")
	webRouter.HandleFunc("/alerts", h.AlertsPage).Methods("GET")
	webRouter.HandleFunc("/automation", h.AutomationPage).Methods("GET")
	webRouter.HandleFunc("/capacity", h.CapacityPage).Methods("GET")
	webRouter.HandleFunc("/incidents", h.IncidentsPage).Methods("GET")
	webRouter.HandleFunc("/channels", h.ChannelsPage).Methods("GET")
	webRouter.HandleFunc("/profile", h.ProfilePage).Methods("GET")
	webRouter.HandleFunc("/settings", h.SettingsPage).Methods("GET")

	htmxRouter := webRouter.PathPrefix("/htmx").Subrouter()
	htmxRouter.HandleFunc("/dashboard/cards", h.DashboardCards).Methods("GET") // 儀表板指標卡
	htmxRouter.HandleFunc("/resources/table", h.ResourcesTable).Methods("GET")
	htmxRouter.HandleFunc("/resources/new", h.AddResourceForm).Methods("GET")
	htmxRouter.HandleFunc("/resources/create", h.CreateResource).Methods("POST")
	htmxRouter.HandleFunc("/diagnose/deployment/{id}", h.DiagnoseDeployment).Methods("POST")

	return r
}
