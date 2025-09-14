package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/config"
	"github.com/detectviz/control-plane/internal/database"
	"github.com/detectviz/control-plane/internal/handlers"
	"github.com/detectviz/control-plane/internal/middleware"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/gorilla/mux"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gorilla/mux/otelmux"
	"github.com/rs/cors"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	logger := initLogger()
	defer logger.Sync()

	cfg, err := config.Load()
	if err != nil {
		logger.Fatal("載入配置失敗", zap.Error(err))
	}

	tpShutdown := initTracerProvider(context.Background(), cfg, logger)
	defer func() {
		if err := tpShutdown(context.Background()); err != nil {
			logger.Error("關閉 Tracer Provider 失敗", zap.Error(err))
		}
	}()

	db, err := database.New(cfg.Database.URL)
	if err != nil {
		logger.Fatal("初始化資料庫連線池失敗", zap.Error(err))
	}
	if err := db.Migrate(); err != nil {
		logger.Fatal("資料庫遷移失敗", zap.Error(err))
	}

	authProvider, err := auth.NewAuthProvider(cfg.Auth)
	if err != nil {
		logger.Fatal("初始化認證提供者失敗", zap.Error(err))
	}
	logger.Info("✅ 認證服務已初始化", zap.String("provider", cfg.Auth.Mode))

	services := services.NewServices(db, cfg, logger, authProvider)
	h := handlers.NewHandlers(services, nil, authProvider, logger)
	router := setupRoutes(h, authProvider, logger, cfg)

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

func initTracerProvider(ctx context.Context, cfg *config.Config, logger *otelzap.Logger) func(context.Context) error {
	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceNameKey.String(cfg.Otel.ServiceName),
		),
	)
	if err != nil {
		logger.Warn("建立 OTel resource 失敗，將禁用 tracing", zap.Error(err))
		return func(context.Context) error { return nil }
	}

	dialCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(dialCtx, cfg.Otel.ExporterEndpoint, grpc.WithTransportCredentials(insecure.NewCredentials()), grpc.WithBlock())
	if err != nil {
		logger.Warn("無法連接到 OTLP gRPC exporter，將禁用 tracing",
			zap.String("endpoint", cfg.Otel.ExporterEndpoint),
			zap.Error(err),
		)
		return func(context.Context) error { return nil }
	}

	traceExporter, err := otlptracegrpc.New(ctx, otlptracegrpc.WithGRPCConn(conn))
	if err != nil {
		logger.Warn("建立 OTLP trace exporter 失敗，將禁用 tracing", zap.Error(err))
		return func(context.Context) error { return nil }
	}

	bsp := sdktrace.NewBatchSpanProcessor(traceExporter)
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(traceExporter),
		sdktrace.WithResource(res),
		sdktrace.WithSpanProcessor(bsp),
	)
	otel.SetTracerProvider(tracerProvider)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))

	logger.Info("✅ OTel Tracer Provider 初始化成功", zap.String("service_name", cfg.Otel.ServiceName), zap.String("endpoint", cfg.Otel.ExporterEndpoint))

	return tracerProvider.Shutdown
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

func setupRoutes(h *handlers.Handlers, authProvider auth.AuthProvider, logger *otelzap.Logger, cfg *config.Config) *mux.Router {
	r := mux.NewRouter()

	r.Use(otelmux.Middleware(cfg.Otel.ServiceName))
	r.Use(middleware.RequestID())
	r.Use(middleware.Logging(logger))
	r.Use(middleware.Recovery(logger))

	r.HandleFunc("/api/v1/healthz", h.HealthCheck).Methods("GET")
	r.HandleFunc("/api/v1/readyz", h.ReadinessCheck).Methods("GET")
	r.HandleFunc("/api/v1/metrics", h.MetricsCheck).Methods("GET")

	authRouter := r.PathPrefix("/api/v1/auth").Subrouter()
	authRouter.HandleFunc("/login", h.DevLogin).Methods("POST")
	authRouter.HandleFunc("/refresh", h.DevRefreshToken).Methods("POST")
	authRouter.HandleFunc("/logout", h.DevLogout).Methods("POST")

	apiRouter := r.PathPrefix("/api/v1").Subrouter()
	apiRouter.Use(middleware.RequireAuth(authProvider))

	// Existing API routes
	apiRouter.HandleFunc("/dashboard/summary", h.GetDashboardSummary).Methods("GET")
	apiRouter.HandleFunc("/dashboard/trends", h.GetDashboardTrends).Methods("GET")
	apiRouter.HandleFunc("/dashboard/resource-distribution", h.GetResourceDistribution).Methods("GET")
	apiRouter.HandleFunc("/resources", h.ListResources).Methods("GET")
	apiRouter.HandleFunc("/resources", h.CreateResourceAPI).Methods("POST")
	apiRouter.HandleFunc("/resources/{resourceId}", h.GetResource).Methods("GET")
	apiRouter.HandleFunc("/resources/{resourceId}", h.UpdateResource).Methods("PUT")
	apiRouter.HandleFunc("/resources/{resourceId}", h.DeleteResource).Methods("DELETE")
	apiRouter.HandleFunc("/resources/batch", h.BatchOperateResources).Methods("POST")
	apiRouter.HandleFunc("/resources/scan", h.ScanNetwork).Methods("POST")
	apiRouter.HandleFunc("/resources/scan/{taskId}", h.GetScanResult).Methods("GET")
	apiRouter.HandleFunc("/audit-logs", h.GetAuditLogs).Methods("GET")
	apiRouter.HandleFunc("/incidents", h.ListIncidents).Methods("GET")
	apiRouter.HandleFunc("/incidents", h.CreateIncident).Methods("POST")
	apiRouter.HandleFunc("/incidents/{incidentId}", h.GetIncident).Methods("GET")
	apiRouter.HandleFunc("/incidents/{incidentId}", h.UpdateIncident).Methods("PUT")
	apiRouter.HandleFunc("/incidents/{incidentId}/acknowledge", h.AcknowledgeIncident).Methods("POST")
	apiRouter.HandleFunc("/incidents/{incidentId}/resolve", h.ResolveIncident).Methods("POST")
	apiRouter.HandleFunc("/incidents/{incidentId}/assign", h.AssignIncident).Methods("POST")
	apiRouter.HandleFunc("/incidents/{incidentId}/comments", h.AddIncidentComment).Methods("POST")
	apiRouter.HandleFunc("/incidents/generate-report", h.GenerateIncidentReport).Methods("POST")
	apiRouter.HandleFunc("/alerts", h.ListAlerts).Methods("GET")
	apiRouter.HandleFunc("/executions", h.GetExecutions).Methods("GET")
	apiRouter.HandleFunc("/executions", h.CreateExecution).Methods("POST")
	apiRouter.HandleFunc("/executions/{id}", h.UpdateExecution).Methods("PATCH")

	return r
}
