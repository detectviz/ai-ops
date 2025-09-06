package main

import (
	"context"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"os/signal"
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

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/stdout/stdouttrace"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

func main() {
	// 初始化 OpenTelemetry 和日誌系統
	ctx := context.Background()
	tp, err := initTracerProvider()
	if err != nil {
		log.Fatalf("無法初始化 Tracer Provider: %v", err)
	}
	defer func() {
		if err := tp.Shutdown(ctx); err != nil {
			log.Printf("關閉 Tracer Provider 時發生錯誤: %v", err)
		}
	}()

	logger := initLogger()
	defer logger.Sync()

	// 載入配置
	cfg, err := config.Load()
	if err != nil {
		logger.Fatal("載入配置失敗", zap.Error(err))
	}

	// 連接資料庫
	db, err := database.Connect(cfg.Database.URL)
	if err != nil {
		logger.Fatal("連接資料庫失敗", zap.Error(err))
	}
	defer db.Close()

	// 執行資料庫遷移
	if err := database.Migrate(db); err != nil {
		logger.Fatal("資料庫遷移失敗", zap.Error(err))
	}

	// 初始化認證服務
	authService, err := auth.NewKeycloakService(cfg.Auth)
	if err != nil {
		logger.Fatal("初始化認證服務失敗", zap.Error(err))
	}

	// 初始化服務層
	services := services.NewServices(db, cfg, logger, *authService)

	// 載入 HTML 模板
	templates, err := loadTemplates()
	if err != nil {
		logger.Fatal("載入模板失敗", zap.Error(err))
	}

	// 初始化處理器
	h := handlers.NewHandlers(services, templates, *authService, logger)

	// 設置路由
	router := setupRoutes(h, authService, logger, cfg)

	// 設置 CORS
	corsHandler := cors.New(cors.Options{
		AllowedOrigins:   cfg.Server.CORSOrigins,
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token"},
		ExposedHeaders:   []string{"Link"},
		AllowCredentials: true,
		MaxAge:           300,
	}).Handler(router)

	// 建立 HTTP 伺服器
	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
		Handler:      corsHandler,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// 啟動伺服器
	go func() {
		logger.Info("🚀 Control Plane 啟動", zap.Int("port", cfg.Server.Port))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("啟動伺服器失敗", zap.Error(err))
		}
	}()

	// 等待中斷信號
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logger.Info("正在關閉伺服器...")

	// 優雅關閉
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Fatal("伺服器強制關閉", zap.Error(err))
	}

	logger.Info("伺服器已關閉")
}

// initLogger 初始化 otelzap 日誌系統
func initLogger() *otelzap.Logger {
	config := zap.NewProductionConfig()
	config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	zapLogger, err := config.Build()
	if err != nil {
		log.Fatalf("無法初始化 zap 日誌: %v", err)
	}
	return otelzap.New(zapLogger)
}

// initTracerProvider 初始化 OpenTelemetry Tracer Provider
func initTracerProvider() (*sdktrace.TracerProvider, error) {
	// 為了演示，我們將追蹤資訊匯出到標準輸出。
	// 在生產環境中，您會使用 OTLP exporter 將其發送到如 Jaeger, Datadog, Uptrace 等後端。
	exporter, err := stdouttrace.New(stdouttrace.WithPrettyPrint())
	if err != nil {
		return nil, err
	}

	res, err := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceName("control-plane"),
			semconv.ServiceVersion("v1.2.0"),
		),
	)
	if err != nil {
		return nil, err
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))
	return tp, nil
}

func loadTemplates() (*template.Template, error) {
	return template.ParseGlob("templates/*.html")
}

func setupRoutes(h *handlers.Handlers, auth *auth.KeycloakService, logger *otelzap.Logger, cfg *config.Config) *mux.Router {
	r := mux.NewRouter()

	// 中介軟體
	r.Use(middleware.RequestID())
	r.Use(middleware.Logging(logger)) // Logging 中介軟體也需要更新以使用 otelzap.Logger
	r.Use(middleware.Recovery(logger))

	// 靜態檔案
	r.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./static/"))))

	// 健康檢查
	r.HandleFunc("/health", h.HealthCheck).Methods("GET")
	r.HandleFunc("/ready", h.ReadinessCheck).Methods("GET")

	// 認證路由
	authRouter := r.PathPrefix("/auth").Subrouter()
	authRouter.HandleFunc("/login", h.LoginPage).Methods("GET")
	authRouter.HandleFunc("/login", h.HandleLogin).Methods("POST")
	authRouter.HandleFunc("/logout", h.HandleLogout).Methods("POST")
	authRouter.HandleFunc("/callback", h.AuthCallback).Methods("GET")

	// API 路由
	apiRouter := r.PathPrefix("/api/v1").Subrouter()
	apiRouter.Use(middleware.RequireAuth(auth)) // 保護 API
	apiRouter.HandleFunc("/dashboard/summary", api.GetDashboardSummary(h.Services)).Methods("GET") // 新增的路由

	// Resource Routes
	apiRouter.HandleFunc("/resources", api.ListResources(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/resources", api.CreateResource(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/resources/{resourceId}", api.GetResource(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/resources/{resourceId}", api.UpdateResource(h.Services)).Methods("PUT")
	apiRouter.HandleFunc("/resources/{resourceId}", api.DeleteResource(h.Services)).Methods("DELETE")
	apiRouter.HandleFunc("/resources/batch", api.BatchOperateResources(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/resources/scan", api.ScanNetwork(h.Services)).Methods("POST")
	apiRouter.HandleFunc("/resources/scan/{taskId}", api.GetScanResult(h.Services)).Methods("GET")

	apiRouter.HandleFunc("/audit-logs", api.GetAuditLogs(h.Services)).Methods("GET")

	// Incident Routes
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

	// Web UI 路由
	webRouter := r.PathPrefix("/").Subrouter()
	webRouter.Use(middleware.RequireSession(auth, cfg)) // 保護 UI
	webRouter.HandleFunc("/", h.Dashboard).Methods("GET")
	// ... 其他頁面路由
	webRouter.HandleFunc("/resources", h.ResourcesPage).Methods("GET")
	// webRouter.HandleFunc("/personnel", h.PersonnelPage).Methods("GET")
	webRouter.HandleFunc("/teams", h.TeamsPage).Methods("GET")
	webRouter.HandleFunc("/alerts", h.AlertsPage).Methods("GET")
	webRouter.HandleFunc("/automation", h.AutomationPage).Methods("GET")
	webRouter.HandleFunc("/capacity", h.CapacityPage).Methods("GET")
	webRouter.HandleFunc("/incidents", h.IncidentsPage).Methods("GET")
	webRouter.HandleFunc("/channels", h.ChannelsPage).Methods("GET")
	webRouter.HandleFunc("/profile", h.ProfilePage).Methods("GET")
	webRouter.HandleFunc("/settings", h.SettingsPage).Methods("GET")

	// HTMX API 端點
	htmxRouter := webRouter.PathPrefix("/htmx").Subrouter()
	htmxRouter.HandleFunc("/resources/table", h.ResourcesTable).Methods("GET")
	// ... 其他 HTMX 端點

	// SRE Assistant 整合端點
	htmxRouter.HandleFunc("/diagnose/deployment/{id}", h.DiagnoseDeployment).Methods("POST")
	htmxRouter.HandleFunc("/diagnose/alerts", h.DiagnoseAlerts).Methods("POST")
	htmxRouter.HandleFunc("/ai/generate-report", h.GenerateAIReport).Methods("POST")

	return r
}
