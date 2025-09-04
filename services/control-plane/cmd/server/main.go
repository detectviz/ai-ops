// services/control-plane/cmd/server/main.go
package main

import (
	"context"
	"embed"
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
	"go.uber.org/zap"
)

//go:embed templates/*
var templatesFS embed.FS

//go:embed static/*
var staticFS embed.FS

func main() {
	// 初始化日誌
	logger, err := zap.NewProduction()
	if err != nil {
		log.Fatalf("無法初始化日誌: %v", err)
	}
	defer logger.Sync()
	sugar := logger.Sugar()

	// 載入配置
	cfg, err := config.Load()
	if err != nil {
		sugar.Fatalf("載入配置失敗: %v", err)
	}

	// 連接資料庫
	db, err := database.Connect(cfg.Database.URL)
	if err != nil {
		sugar.Fatalf("連接資料庫失敗: %v", err)
	}
	defer db.Close()

	// 執行資料庫遷移
	if err := database.Migrate(db); err != nil {
		sugar.Fatalf("資料庫遷移失敗: %v", err)
	}

	// 初始化認證服務
	authService, err := auth.NewKeycloakService(cfg.Auth)
	if err != nil {
		sugar.Fatalf("初始化認證服務失敗: %v", err)
	}

	// 初始化服務層
	services := services.NewServices(db, cfg, logger)

	// 載入 HTML 模板
	templates, err := loadTemplates()
	if err != nil {
		sugar.Fatalf("載入模板失敗: %v", err)
	}

	// 初始化處理器
	h := handlers.NewHandlers(services, templates, authService, logger)

	// 設置路由
	router := setupRoutes(h, authService, logger)

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
		sugar.Infof("🚀 Control Plane 啟動於 http://localhost:%d", cfg.Server.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			sugar.Fatalf("啟動伺服器失敗: %v", err)
		}
	}()

	// 等待中斷信號
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	sugar.Info("正在關閉伺服器...")

	// 優雅關閉
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		sugar.Fatalf("伺服器強制關閉: %v", err)
	}

	sugar.Info("伺服器已關閉")
}

func loadTemplates() (*template.Template, error) {
	return template.ParseFS(templatesFS, "templates/*.html")
}

func setupRoutes(h *handlers.Handlers, auth *auth.KeycloakService, logger *zap.Logger) *mux.Router {
	r := mux.NewRouter()

	// 中介軟體
	r.Use(middleware.Logging(logger))
	r.Use(middleware.Recovery(logger))
	r.Use(middleware.RequestID())

	// 靜態檔案
	r.PathPrefix("/static/").Handler(http.FileServer(http.FS(staticFS)))

	// 健康檢查 (無需認證)
	r.HandleFunc("/health", h.HealthCheck).Methods("GET")
	r.HandleFunc("/ready", h.ReadinessCheck).Methods("GET")

	// 認證路由
	authRouter := r.PathPrefix("/auth").Subrouter()
	authRouter.HandleFunc("/login", h.LoginPage).Methods("GET")
	authRouter.HandleFunc("/login", h.HandleLogin).Methods("POST")
	authRouter.HandleFunc("/logout", h.HandleLogout).Methods("POST")
	authRouter.HandleFunc("/callback", h.AuthCallback).Methods("GET")

	// API 路由 (需要認證)
	apiRouter := r.PathPrefix("/api/v1").Subrouter()
	apiRouter.Use(middleware.RequireAuth(auth))

	// 審計日誌 (供 SRE Assistant 查詢)
	apiRouter.HandleFunc("/audit-logs", api.GetAuditLogs(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/incidents", api.GetIncidents(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/incidents/{id}", api.GetIncident(h.Services)).Methods("GET")
	apiRouter.HandleFunc("/executions", api.GetExecutions(h.Services)).Methods("GET")

	// Web UI 路由 (需要認證)
	webRouter := r.PathPrefix("/").Subrouter()
	webRouter.Use(middleware.RequireSession(auth))

	// 頁面路由
	webRouter.HandleFunc("/", h.Dashboard).Methods("GET")
	webRouter.HandleFunc("/resources", h.ResourcesPage).Methods("GET")
	webRouter.HandleFunc("/personnel", h.PersonnelPage).Methods("GET")
	webRouter.HandleFunc("/teams", h.TeamsPage).Methods("GET")
	webRouter.HandleFunc("/alerts", h.AlertsPage).Methods("GET")
	webRouter.HandleFunc("/automation", h.AutomationPage).Methods("GET")
	webRouter.HandleFunc("/capacity", h.CapacityPage).Methods("GET")
	webRouter.HandleFunc("/incidents", h.IncidentsPage).Methods("GET")
	webRouter.HandleFunc("/channels", h.ChannelsPage).Methods("GET")
	webRouter.HandleFunc("/profile", h.ProfilePage).Methods("GET")
	webRouter.HandleFunc("/settings", h.SettingsPage).Methods("GET")

	// HTMX API 端點 (局部更新)
	htmxRouter := webRouter.PathPrefix("/htmx").Subrouter()
	htmxRouter.HandleFunc("/resources/table", h.ResourcesTable).Methods("GET")
	htmxRouter.HandleFunc("/resources/create", h.CreateResource).Methods("POST")
	htmxRouter.HandleFunc("/resources/{id}/edit", h.EditResource).Methods("GET")
	htmxRouter.HandleFunc("/resources/{id}", h.UpdateResource).Methods("PUT")
	htmxRouter.HandleFunc("/resources/{id}", h.DeleteResource).Methods("DELETE")
	htmxRouter.HandleFunc("/resources/batch-delete", h.BatchDeleteResources).Methods("POST")

	// SRE Assistant 整合端點
	htmxRouter.HandleFunc("/diagnose/deployment/{id}", h.DiagnoseDeployment).Methods("POST")
	htmxRouter.HandleFunc("/diagnose/alerts", h.DiagnoseAlerts).Methods("POST")
	htmxRouter.HandleFunc("/ai/generate-report", h.GenerateAIReport).Methods("POST")

	return r
}
