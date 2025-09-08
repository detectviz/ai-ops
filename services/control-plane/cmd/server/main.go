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

	// 初始化 Tracer Provider
	// 在本地開發環境中，如果 OTLP exporter 無法連線，我們不希望服務啟動失敗。
	// 因此，initTracerProvider 會處理錯誤並返回一個 no-op shutdown 函式。
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

	var authService *auth.KeycloakService
	if cfg.Auth.Mode == "keycloak" {
		var err error
		authService, err = auth.NewKeycloakService(cfg.Auth)
		if err != nil {
			logger.Fatal("初始化 Keycloak 認證服務失敗", zap.Error(err))
		}
		logger.Info("✅ Keycloak 認證服務已初始化")
	} else {
		// 在 DEV 模式下創建一個空的 KeycloakService 以避免 nil 指針
		authService = &auth.KeycloakService{}
		logger.Info("🔍 在 DEV 模式下運行，使用空的認證服務")
	}

	services := services.NewServices(db, cfg, logger, authService)

	templates, err := loadTemplates("web/templates")
	if err != nil {
		logger.Fatal("載入模板失敗", zap.Error(err))
	}

	h := handlers.NewHandlers(services, templates, authService, logger)
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

// initTracerProvider 初始化 OpenTelemetry Tracer Provider。
// 如果初始化失敗（例如，無法連接到 OTLP exporter），它會記錄一個警告並返回一個無操作的 shutdown 函式，
// 這樣應用程式就可以在沒有分散式追蹤的情況下繼續運行。
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

	// 使用 OTLP gRPC exporter
	// 增加一個短暫的超時，以避免在 collector 無法立即連線時長時間阻塞
	dialCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	// 使用 grpc.DialContext 替代已棄用的 grpc.NewClient
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

	// otelmux middleware should be first to wrap all other handlers
	r.Use(otelmux.Middleware(cfg.Otel.ServiceName))
	r.Use(middleware.RequestID())
	r.Use(middleware.Logging(logger))
	r.Use(middleware.Recovery(logger))

	r.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./web/static/"))))

	// 健康檢查路由移到 /api/v1 下，與其他 API 一致
	r.HandleFunc("/api/v1/healthz", h.HealthCheck).Methods("GET")
	r.HandleFunc("/api/v1/readyz", h.ReadinessCheck).Methods("GET")
	r.HandleFunc("/api/v1/metrics", h.MetricsCheck).Methods("GET")

	authRouter := r.PathPrefix("/auth").Subrouter()
	authRouter.HandleFunc("/login", h.LoginPage).Methods("GET")
	authRouter.HandleFunc("/login", h.HandleLogin).Methods("POST")
	authRouter.HandleFunc("/logout", h.HandleLogout).Methods("POST")
	authRouter.HandleFunc("/callback", h.AuthCallback).Methods("GET")

	apiRouter := r.PathPrefix("/api/v1").Subrouter()
	apiRouter.Use(middleware.RequireAuth(auth))
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
	htmxRouter.HandleFunc("/teams/list", h.TeamList).Methods("GET")                               // 團隊列表
	htmxRouter.HandleFunc("/teams/new", h.AddTeamForm).Methods("GET")                             // 新增團隊表單
	htmxRouter.HandleFunc("/teams/create", h.CreateTeam).Methods("POST")                          // 創建團隊
	htmxRouter.HandleFunc("/teams/{id}/confirm-delete", h.ConfirmDeleteTeam).Methods("GET")       // 顯示刪除確認
	htmxRouter.HandleFunc("/teams/{id}", h.DeleteTeam).Methods("DELETE")                          // 刪除團隊
	htmxRouter.HandleFunc("/teams/{id}/edit", h.EditTeamForm).Methods("GET")                      // 顯示編輯表單
	htmxRouter.HandleFunc("/teams/{id}", h.UpdateTeam).Methods("PUT")                             // 更新團隊
	htmxRouter.HandleFunc("/alerts/list", h.AlertRuleList).Methods("GET")                         // 告警規則列表
	htmxRouter.HandleFunc("/alerts/new", h.AddAlertRuleForm).Methods("GET")                       // 新增告警規則表單
	htmxRouter.HandleFunc("/alerts/create", h.CreateAlertRule).Methods("POST")                    // 創建告警規則
	htmxRouter.HandleFunc("/alerts/{id}/edit", h.EditAlertRuleForm).Methods("GET")                // 編輯告警規則表單
	htmxRouter.HandleFunc("/alerts/{id}", h.UpdateAlertRule).Methods("PUT")                       // 更新告警規則
	htmxRouter.HandleFunc("/alerts/{id}/confirm-delete", h.ConfirmDeleteAlertRule).Methods("GET") // 顯示刪除確認
	htmxRouter.HandleFunc("/alerts/{id}", h.DeleteAlertRule).Methods("DELETE")                    // 刪除告警規則
	htmxRouter.HandleFunc("/incidents/list", h.IncidentList).Methods("GET")                       // 事件列表
	htmxRouter.HandleFunc("/incidents/{id}/details", h.IncidentDetails).Methods("GET")            // 事件詳情模態框
	htmxRouter.HandleFunc("/diagnose/deployment/{id}", h.DiagnoseDeployment).Methods("POST")
	htmxRouter.HandleFunc("/close", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(""))
	}).Methods("GET")

	return r
}
