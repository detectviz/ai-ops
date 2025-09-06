// services/control-plane/internal/handlers/handlers.go
package handlers

import (
	"database/sql"
	"encoding/json"
	"errors"
	"html/template"
	"net/http"
	"time"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/gorilla/mux"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

// Handlers 是一個容器，集中管理所有 HTTP 處理器方法。
type Handlers struct {
	Services    *services.Services
	Templates   *template.Template
	AuthService auth.KeycloakService
	Logger      *otelzap.Logger
}

// NewHandlers 建立並返回一個新的 Handlers 實例。
func NewHandlers(s *services.Services, t *template.Template, as auth.KeycloakService, l *otelzap.Logger) *Handlers {
	return &Handlers{
		Services:    s,
		Templates:   t,
		AuthService: as,
		Logger:      l,
	}
}

func (h *Handlers) writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(data); err != nil {
		h.Logger.Error("無法寫入 JSON 響應", zap.Error(err))
	}
}

// DiagnoseDeployment 是觸發 SRE Assistant 診斷部署的核心端點。
func (h *Handlers) DiagnoseDeployment(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	vars := mux.Vars(r)
	deploymentID, ok := vars["id"]
	if !ok {
		h.writeJSON(w, http.StatusBadRequest, map[string]string{"error": "缺少 deployment ID"})
		return
	}

	h.Logger.Ctx(ctx).Info("開始部署診斷", zap.String("deploymentID", deploymentID))

	// 從資料庫獲取部署資訊
	deployment, err := h.Services.GetDeploymentByID(ctx, deploymentID)
	if err != nil {
		h.Logger.Ctx(ctx).Error("無法從資料庫獲取部署資訊", zap.String("deploymentID", deploymentID), zap.Error(err))
		// 修正: 使用 errors.Is 進行更可靠的錯誤判斷
		if errors.Is(err, sql.ErrNoRows) {
			h.writeJSON(w, http.StatusNotFound, map[string]string{"error": "找不到部署資訊"})
		} else {
			h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "查詢部署資訊時發生錯誤"})
		}
		return
	}

	// 觸發非同步診斷
	resp, err := h.Services.TriggerDeploymentDiagnosis(ctx, deployment)
	if err != nil {
		h.Logger.Ctx(ctx).Error("呼叫 SRE Assistant 失敗", zap.Error(err))
		h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "呼叫診斷服務失敗"})
		return
	}

	h.writeJSON(w, http.StatusAccepted, resp)
}

// GetDiagnosisStatus 處理輪詢請求，查詢診斷任務的狀態。
func (h *Handlers) GetDiagnosisStatus(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	vars := mux.Vars(r)
	sessionID, ok := vars["session_id"]
	if !ok {
		h.writeJSON(w, http.StatusBadRequest, map[string]string{"error": "缺少 session_id"})
		return
	}

	status, err := h.Services.CheckDiagnosisStatus(ctx, sessionID)
	if err != nil {
		h.Logger.Ctx(ctx).Error("查詢狀態失敗", zap.Error(err), zap.String("sessionID", sessionID))
		// 假設 404 錯誤會被服務層正確傳遞上來
		h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "查詢狀態時發生內部錯誤"})
		return
	}

	h.writeJSON(w, http.StatusOK, status)
}

// --- 其他處理器 (存根) ---

// HealthCheck 檢查服務是否存活，並回傳符合 OpenAPI 規範的格式。
func (h *Handlers) HealthCheck(w http.ResponseWriter, r *http.Request) {
	// 建立符合 HealthStatus schema 的響應
	response := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
		"version":   "1.0.0", // 範例版本號
	}
	h.writeJSON(w, http.StatusOK, response)
}

// ReadinessCheck 檢查服務及其依賴是否就緒，並回傳符合 OpenAPI 規範的格式。
func (h *Handlers) ReadinessCheck(w http.ResponseWriter, r *http.Request) {
	// 在真實的應用中，這裡會包含對資料庫、Redis、Keycloak 等的實際檢查。
	dbReady := h.Services.DB.Ping() == nil

	// 建立符合 ReadinessStatus schema 的響應
	response := map[string]interface{}{
		"ready": dbReady,
		"checks": map[string]bool{
			"database":      dbReady,
			"redis":         true, // 假設 Redis 正常
			"keycloak":      true, // 假設 Keycloak 正常
			"sre_assistant": true, // 假設 SRE Assistant 正常
		},
	}

	if !dbReady {
		h.writeJSON(w, http.StatusServiceUnavailable, response)
		return
	}
	h.writeJSON(w, http.StatusOK, response)
}

// MetricsCheck 提供一個符合 Prometheus 格式的簡單指標端點。
func (h *Handlers) MetricsCheck(w http.ResponseWriter, r *http.Request) {
	// 為了符合 OpenAPI 規範，這裡提供一個基本的靜態回應。
	// 在一個完整的實作中，這裡應該整合一個真正的指標庫（例如 Prometheus Go client）。
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	w.WriteHeader(http.StatusOK)
	// 回應一個簡單的 'up' 指標，表示服務正在運行。
	w.Write([]byte("# HELP control_plane_up Control Plane service status\n# TYPE control_plane_up gauge\ncontrol_plane_up 1\n"))
}

func (h *Handlers) LoginPage(w http.ResponseWriter, r *http.Request) {
	// Simple render of the login page
	err := h.Templates.ExecuteTemplate(w, "login.html", nil)
	if err != nil {
		http.Error(w, "無法渲染登入頁面", http.StatusInternalServerError)
	}
}

func (h *Handlers) AuthCallback(w http.ResponseWriter, r *http.Request) {}

func (h *Handlers) HandleLogin(w http.ResponseWriter, r *http.Request) {
	if h.Services.Config.Auth.Mode == "dev" {
		// Dev mode: simple form-based login
		if err := r.ParseForm(); err != nil {
			http.Error(w, "無法解析表單", http.StatusBadRequest)
			return
		}
		username := r.PostFormValue("username")
		password := r.PostFormValue("password")

		// TODO: Use a more secure way to handle dev credentials
		if username == "admin" && password == "admin" {
			session, _ := auth.Store.Get(r, auth.SessionName)
			session.Values["authenticated"] = true
			session.Values["user"] = username
			if err := session.Save(r, w); err != nil {
				http.Error(w, "無法儲存 Session", http.StatusInternalServerError)
				return
			}
			http.Redirect(w, r, "/", http.StatusFound)
		} else {
			// TODO: Add flash messages for errors
			http.Redirect(w, r, "/auth/login?error=invalid_credentials", http.StatusFound)
		}
	} else {
		// Keycloak mode: redirect to OIDC provider
		h.AuthService.HandleLogin(w, r)
	}
}

func (h *Handlers) HandleLogout(w http.ResponseWriter, r *http.Request) {
	session, _ := auth.Store.Get(r, auth.SessionName)
	// Revoke the session
	session.Values["authenticated"] = false
	session.Options.MaxAge = -1
	if err := session.Save(r, w); err != nil {
		h.Logger.Ctx(r.Context()).Error("無法登出時儲存 session", zap.Error(err))
		http.Error(w, "登出失敗", http.StatusInternalServerError)
		return
	}

	// TODO: Add Keycloak single-sign-out
	http.Redirect(w, r, "/auth/login", http.StatusFound)
}
func (h *Handlers) Dashboard(w http.ResponseWriter, r *http.Request)      {}
func (h *Handlers) TeamsPage(w http.ResponseWriter, r *http.Request)      {}
func (h *Handlers) AlertsPage(w http.ResponseWriter, r *http.Request)     {}
func (h *Handlers) AutomationPage(w http.ResponseWriter, r *http.Request) {}
func (h *Handlers) CapacityPage(w http.ResponseWriter, r *http.Request)   {}
func (h *Handlers) IncidentsPage(w http.ResponseWriter, r *http.Request)  {}
func (h *Handlers) ChannelsPage(w http.ResponseWriter, r *http.Request)   {}
func (h *Handlers) ProfilePage(w http.ResponseWriter, r *http.Request)    {}
func (h *Handlers) SettingsPage(w http.ResponseWriter, r *http.Request)   {}
func (h *Handlers) ResourcesTable(w http.ResponseWriter, r *http.Request) {}
func (h *Handlers) ResourcesPage(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	resources, err := h.Services.ListResources(ctx)
	if err != nil {
		h.Logger.Ctx(ctx).Error("無法獲取資源列表", zap.Error(err))
		http.Error(w, "無法載入資源頁面", http.StatusInternalServerError)
		return
	}

	// Marshal resources to JSON for the script block
	resourcesJSON, err := json.Marshal(resources)
	if err != nil {
		h.Logger.Ctx(ctx).Error("無法將資源序列化為 JSON", zap.Error(err))
		http.Error(w, "無法準備頁面資料", http.StatusInternalServerError)
		return
	}

	data := map[string]interface{}{
		"Title":         "資源管理",
		"Page":          "resources",
		"Resources":     resources,
		"ResourcesJSON": string(resourcesJSON),
	}

	err = h.Templates.ExecuteTemplate(w, "resources.html", data)
	if err != nil {
		h.Logger.Ctx(ctx).Error("無法渲染資源頁面模板", zap.Error(err))
		http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}
