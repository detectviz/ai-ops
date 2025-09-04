// Package handlers 包含了所有 HTTP 請求的處理器函數。
// 它的職責是解析傳入的請求，呼叫對應的業務邏輯服務，並將結果呈現給使用者。
package handlers

import (
	"encoding/json"
	"html/template"
	"net/http"
	"strings"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/gorilla/mux"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

// Handlers 是一個容器，集中管理所有 HTTP 處理器方法。
// 這種結構有助於依賴注入，讓處理器可以存取後端服務、模板等。
type Handlers struct {
	Services    *services.Services
	Templates   *template.Template
	AuthService *auth.KeycloakService
	Logger      *otelzap.Logger
}

// NewHandlers 建立並返回一個新的 Handlers 實例。
func NewHandlers(s *services.Services, t *template.Template, as *auth.KeycloakService, l *otelzap.Logger) *Handlers {
	return &Handlers{
		Services:    s,
		Templates:   t,
		AuthService: as,
		Logger:      l,
	}
}

// --- 健康檢查處理器 ---

func (h *Handlers) HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

func (h *Handlers) ReadinessCheck(w http.ResponseWriter, r *http.Request) {
	// TODO: 在未來可以加入對資料庫等依賴的檢查
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

// --- 認證處理器 ---

func (h *Handlers) LoginPage(w http.ResponseWriter, r *http.Request) {
	// 這裡應該渲染一個包含登入按鈕的 HTML 頁面
	// 為了簡化，我們先直接重定向
	h.AuthService.HandleLogin(w, r)
}

func (h *Handlers) HandleLogin(w http.ResponseWriter, r *http.Request) {
	h.AuthService.HandleLogin(w, r)
}

func (h *Handlers) HandleLogout(w http.ResponseWriter, r *http.Request) {
	// 清除 session cookie
	http.SetCookie(w, &http.Cookie{
		Name:   "session_token",
		Value:  "",
		Path:   "/",
		MaxAge: -1,
	})
	// TODO: 理想情況下應該也要重定向到 Keycloak 的登出端點
	http.Redirect(w, r, "/auth/login", http.StatusFound)
}

func (h *Handlers) AuthCallback(w http.ResponseWriter, r *http.Request) {
	idToken, err := h.AuthService.AuthCallback(w, r)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("認證回調失敗", zap.Error(err))
		http.Error(w, "認證失敗: "+err.Error(), http.StatusInternalServerError)
		return
	}
	// 建立一個 session cookie
	http.SetCookie(w, &http.Cookie{
		Name:     "session_token",
		Value:    idToken,
		Path:     "/",
		HttpOnly: true,
		Secure:   r.TLS != nil,
		MaxAge:   3600, // 1 hour
	})
	http.Redirect(w, r, "/", http.StatusFound)
}

// --- Web UI 頁面處理器 (存根) ---
// 為了專注於核心任務，我們先為每個頁面提供一個簡單的佔位符。

func (h *Handlers) renderPlaceholder(w http.ResponseWriter, r *http.Request, title string) {
	// 為了簡化，我們重複使用 base.html。在實際應用中，每個頁面會有自己的模板。
	err := h.Templates.ExecuteTemplate(w, "base.html", map[string]string{"Title": title})
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染模板", zap.String("template", "base.html"), zap.Error(err))
		http.Error(w, "無法渲染模板", http.StatusInternalServerError)
	}
}

func (h *Handlers) Dashboard(w http.ResponseWriter, r *http.Request)      { h.renderPlaceholder(w, r, "Dashboard") }
func (h *Handlers) ResourcesPage(w http.ResponseWriter, r *http.Request)  { h.renderPlaceholder(w, r, "Resources") }
func (h *Handlers) PersonnelPage(w http.ResponseWriter, r *http.Request)  { h.renderPlaceholder(w, r, "Personnel") }
func (h *Handlers) TeamsPage(w http.ResponseWriter, r *http.Request)      { h.renderPlaceholder(w, r, "Teams") }
func (h *Handlers) AlertsPage(w http.ResponseWriter, r *http.Request)     { h.renderPlaceholder(w, r, "Alerts") }
func (h *Handlers) AutomationPage(w http.ResponseWriter, r *http.Request) { h.renderPlaceholder(w, r, "Automation") }
func (h *Handlers) CapacityPage(w http.ResponseWriter, r *http.Request)   { h.renderPlaceholder(w, r, "Capacity Planning") }
func (h *Handlers) IncidentsPage(w http.ResponseWriter, r *http.Request)  { h.renderPlaceholder(w, r, "Incidents") }
func (h *Handlers) ChannelsPage(w http.ResponseWriter, r *http.Request)   { h.renderPlaceholder(w, r, "Channels") }
func (h *Handlers) ProfilePage(w http.ResponseWriter, r *http.Request)    { h.renderPlaceholder(w, r, "Profile") }
func (h *Handlers) SettingsPage(w http.ResponseWriter, r *http.Request)   { h.renderPlaceholder(w, r, "Settings") }


// --- HTMX API 處理器 (存根) ---

func (h *Handlers) ResourcesTable(w http.ResponseWriter, r *http.Request)     {}
func (h *Handlers) CreateResource(w http.ResponseWriter, r *http.Request)     {}
func (h *Handlers) EditResource(w http.ResponseWriter, r *http.Request)       {}
func (h *Handlers) UpdateResource(w http.ResponseWriter, r *http.Request)     {}
func (h *Handlers) DeleteResource(w http.ResponseWriter, r *http.Request)     {}
func (h *Handlers) BatchDeleteResources(w http.ResponseWriter, r *http.Request) {}


// --- SRE Assistant 整合處理器 (核心任務的起點) ---

// DiagnoseDeployment 是觸發 SRE Assistant 診斷部署的核心端點。
func (h *Handlers) DiagnoseDeployment(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	vars := mux.Vars(r)
	deploymentID, ok := vars["id"]
	if !ok {
		h.Logger.Ctx(ctx).Error("缺少 deployment ID")
		http.Error(w, "缺少 deployment ID", http.StatusBadRequest)
		return
	}

	h.Logger.Ctx(ctx).Info("開始部署診斷", zap.String("deploymentID", deploymentID))

	// 從資料庫獲取部署資訊
	deployment, err := h.Services.GetDeploymentByID(deploymentID)
	if err != nil {
		h.Logger.Ctx(ctx).Error("無法從資料庫獲取部署資訊", zap.String("deploymentID", deploymentID), zap.Error(err))
		if strings.Contains(err.Error(), "找不到") {
			http.Error(w, "找不到部署資訊: "+err.Error(), http.StatusNotFound)
		} else {
			http.Error(w, "查詢部署資訊時發生錯誤", http.StatusInternalServerError)
		}
		return
	}

	h.Logger.Ctx(ctx).Info("成功獲取部署資訊",
		zap.String("serviceName", deployment.ServiceName),
		zap.String("namespace", deployment.Namespace),
	)

	resp, err := h.Services.SreAssistantClient.DiagnoseDeployment(ctx, deploymentID, deployment.ServiceName, deployment.Namespace)
	if err != nil {
		h.Logger.Ctx(ctx).Error("呼叫 SRE Assistant 失敗", zap.Error(err))
		http.Error(w, "呼叫診斷服務失敗", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusAccepted)
	json.NewEncoder(w).Encode(resp)
}

func (h *Handlers) DiagnoseAlerts(w http.ResponseWriter, r *http.Request) {
	h.Logger.Ctx(r.Context()).Info("接收到告警診斷請求 (尚未實作)")
	w.WriteHeader(http.StatusAccepted)
	w.Write([]byte("請求已接受，處理邏輯尚未實作。"))
}

func (h *Handlers) GenerateAIReport(w http.ResponseWriter, r *http.Request) {
	h.Logger.Ctx(r.Context()).Info("接收到 AI 報告生成請求 (尚未實作)")
	w.WriteHeader(http.StatusAccepted)
	w.Write([]byte("請求已接受，處理邏輯尚未實作。"))
}
