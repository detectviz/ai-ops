// services/control-plane/internal/handlers/handlers.go
package handlers

import (
	"database/sql"
	"encoding/json"
	"errors"
	"html/template"
	"net/http"
	"strings"
	"sync" // 引入 sync 套件

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
	mu          sync.RWMutex // 用於保護 mockResources 的讀寫鎖
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
func (h *Handlers) HealthCheck(w http.ResponseWriter, r *http.Request) {
	h.writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}
func (h *Handlers) ReadinessCheck(w http.ResponseWriter, r *http.Request) {
	h.writeJSON(w, http.StatusOK, map[string]bool{"ready": true})
}

func (h *Handlers) LoginPage(w http.ResponseWriter, r *http.Request) {
	// 註解：渲染登入頁面，現在使用新的佈局模板路徑
	err := h.Templates.ExecuteTemplate(w, "layouts/auth.html", nil)
	if err != nil {
		http.Error(w, "無法渲染登入頁面", http.StatusInternalServerError)
		h.Logger.Error("渲染 auth.html 失敗", zap.Error(err))
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
func (h *Handlers) Dashboard(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{
		"Title": "總覽儀表板",
		"Page":  "dashboard",
		// 初始頁面渲染時不需要卡片資料，因為它們將由 HTMX 載入
	}
	err := h.Templates.ExecuteTemplate(w, "pages/dashboard.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染儀表板頁面", zap.Error(err))
		http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}
func (h *Handlers) renderPlaceholder(w http.ResponseWriter, r *http.Request, title, page string) {
	data := map[string]interface{}{"Title": title, "Page": page}
	err := h.Templates.ExecuteTemplate(w, "pages/placeholder.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染佔位頁面", zap.Error(err), zap.String("page", page))
		http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) TeamsPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "團隊管理", "teams")
}
func (h *Handlers) AlertsPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "告警規則", "alerts")
}
func (h *Handlers) AutomationPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "自動化", "automation")
}
func (h *Handlers) CapacityPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "容量規劃", "capacity")
}
func (h *Handlers) IncidentsPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "事件管理", "incidents")
}
func (h *Handlers) ChannelsPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "通知管道", "channels")
}
func (h *Handlers) ProfilePage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "個人資料", "profile")
}
func (h *Handlers) SettingsPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "系統設定", "settings")
}

func (h *Handlers) DashboardCards(w http.ResponseWriter, r *http.Request) {
	// 註解：此為 HTMX 請求的處理器，負責回傳儀表板上的指標卡片。

	type cardData struct {
		Name       string
		Value      string
		Change     string
		ChangeType string // "increase" 或 "decrease"
		Icon       string
	}

	cards := []cardData{
		{Name: "新告警 (New)", Value: "7", Change: "+11%", ChangeType: "increase", Icon: "siren"},
		{Name: "處理中 (In Progress)", Value: "7", Change: "+6%", ChangeType: "increase", Icon: "loader-circle"},
		{Name: "今日已解決 (Resolved Today)", Value: "8", Change: "+0%", ChangeType: "increase", Icon: "check-circle-2"},
		{Name: "資源健康度", Value: "99.8%", Change: "", ChangeType: "", Icon: "shield-check"},
		{Name: "總資源數", Value: "1,204", Change: "", ChangeType: "", Icon: "database"},
		{Name: "平均網路延遲", Value: "23 ms", Change: "", ChangeType: "", Icon: "bar-chart-horizontal"},
	}

	data := map[string]interface{}{
		"Cards": cards,
	}

	err := h.Templates.ExecuteTemplate(w, "partials/dashboard-cards.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染儀表板卡片模板", zap.Error(err))
	}
}

func (h *Handlers) AddResourceForm(w http.ResponseWriter, r *http.Request) {
	// 註解：此處理器負責回傳用於新增資源的模態框和表單。
	// 它執行 resource-form.html 模板，該模板內部會引用 modal.html 組件。
	err := h.Templates.ExecuteTemplate(w, "partials/resource-form.html", nil)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染資源表單模板", zap.Error(err))
	}
}

// resource 用於模擬的資源資料結構
type resource struct {
	Name      string
	IPAddress string
	Type      string
	Status    string
}

// mockResources 作為一個包級變數，模擬一個記憶體中的資料庫。
var mockResources = []resource{
	{"control-plane-db", "10.0.1.5", "PostgreSQL", "healthy"},
	{"sre-assistant-api", "10.0.1.6", "Python FastAPI", "healthy"},
	{"monitoring-prometheus", "10.0.2.10", "Prometheus", "warning"},
	{"data-pipeline-kafka", "10.0.3.8", "Kafka", "critical"},
	{"legacy-app-server", "192.168.1.100", "JBoss EAP", "unknown"},
}

func (h *Handlers) CreateResource(w http.ResponseWriter, r *http.Request) {
	// 註解：此處理器處理新增資源的 POST 請求。
	if err := r.ParseForm(); err != nil {
		h.Logger.Ctx(r.Context()).Error("無法解析表單", zap.Error(err))
		return
	}

	newRes := resource{
		Name:      r.PostFormValue("name"),
		IPAddress: r.PostFormValue("ip_address"),
		Type:      r.PostFormValue("type"),
		Status:    "unknown",
	}

	h.mu.Lock() // 寫入前鎖定
	mockResources = append(mockResources, newRes)
	h.mu.Unlock() // 完成後解鎖

	h.Logger.Ctx(r.Context()).Info("成功創建新資源 (模擬)",
		zap.String("name", newRes.Name),
		zap.String("ip", newRes.IPAddress),
	)

	h.ResourcesTable(w, r)
}

func (h *Handlers) ResourcesTable(w http.ResponseWriter, r *http.Request) {
	h.mu.RLock() // 讀取前鎖定
	defer h.mu.RUnlock() // 確保函數結束時解鎖

	query := r.URL.Query().Get("q")

	var filteredResources []resource
	if query != "" {
		query = strings.ToLower(query)
		for _, res := range mockResources {
			if strings.Contains(strings.ToLower(res.Name), query) || strings.Contains(strings.ToLower(res.IPAddress), query) {
				filteredResources = append(filteredResources, res)
			}
		}
	} else {
		// 複製一份以避免在模板渲染時發生競爭條件
		filteredResources = make([]resource, len(mockResources))
		copy(filteredResources, mockResources)
	}

	data := map[string]interface{}{
		"Resources": filteredResources,
	}

	// 註解：執行 partials/resource-table.html 模板，只回傳表格的 HTML。
	err := h.Templates.ExecuteTemplate(w, "partials/resource-table.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染資源表格模板", zap.Error(err))
	}
}

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

	err := h.Templates.ExecuteTemplate(w, "pages/resources.html", data)
	if err != nil {
		h.Logger.Ctx(ctx).Error("無法渲染資源頁面模板", zap.Error(err))
		http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}
