// services/control-plane/internal/handlers/handlers.go
package handlers

import (
	"database/sql"
	"encoding/json"
	"errors"
	"html/template"
	"net/http"
	"strings"
	"sync"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/google/uuid" // 引入 UUID 套件
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

// --- Mock Data (Aligned with OpenAPI Spec) ---

// resourceMock 用於模擬的資源資料結構
type resourceMock struct {
	ID        string
	Name      string
	Type      string
	Status    string
	IPAddress string
}

// mockResources 作為一個包級變數，模擬一個記憶體中的資料庫。
var mockResources = []resourceMock{
	{ID: uuid.NewString(), Name: "control-plane-db", Type: "database", Status: "healthy", IPAddress: "10.0.1.5"},
	{ID: uuid.NewString(), Name: "sre-assistant-api", Type: "application", Status: "healthy", IPAddress: "10.0.1.6"},
	{ID: uuid.NewString(), Name: "monitoring-prometheus", Type: "server", Status: "warning", IPAddress: "10.0.2.10"},
	{ID: uuid.NewString(), Name: "data-pipeline-kafka", Type: "server", Status: "critical", IPAddress: "10.0.3.8"},
	{ID: uuid.NewString(), Name: "legacy-app-server", Type: "application", Status: "unknown", IPAddress: "192.168.1.100"},
}

// incidentMock 用於模擬的事件資料結構
type incidentMock struct {
	ID        string
	Title     string
	Severity  string
	Status    string
	Assignee  string
	CreatedAt string
}

// mockIncidents 作為一個包級變數，模擬事件資料庫
var mockIncidents = []incidentMock{
	{ID: "INC-001", Title: "Edge SW13 - 資源斷線超過15分鐘", Status: "new", Severity: "critical", CreatedAt: "2025-08-29 01:15", Assignee: "未指派"},
	{ID: "INC-002", Title: "CPU 使用率超過 90%", Status: "acknowledged", Severity: "error", CreatedAt: "2025-08-28 10:45", Assignee: "王工程師"},
	{ID: "INC-003", Title: "網路延遲超過 200ms", Status: "resolved", Severity: "warning", CreatedAt: "2025-08-27 23:55", Assignee: "陳經理"},
}

// --- Core & Auth Handlers ---

func (h *Handlers) writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(data); err != nil {
		h.Logger.Error("無法寫入 JSON 響應", zap.Error(err))
	}
}

func (h *Handlers) HealthCheck(w http.ResponseWriter, r *http.Request) {
	h.writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *Handlers) ReadinessCheck(w http.ResponseWriter, r *http.Request) {
	h.writeJSON(w, http.StatusOK, map[string]bool{"ready": true})
}

func (h *Handlers) LoginPage(w http.ResponseWriter, r *http.Request) {
	err := h.Templates.ExecuteTemplate(w, "layouts/auth.html", nil)
	if err != nil {
		http.Error(w, "無法渲染登入頁面", http.StatusInternalServerError)
		h.Logger.Error("渲染 auth.html 失敗", zap.Error(err))
	}
}

func (h *Handlers) HandleLogin(w http.ResponseWriter, r *http.Request) {
    if h.Services.Config.Auth.Mode == "dev" {
		if err := r.ParseForm(); err != nil { http.Error(w, "無法解析表單", http.StatusBadRequest); return }
		username := r.PostFormValue("username")
		password := r.PostFormValue("password")
		if username == "admin" && password == "admin" {
			session, _ := auth.Store.Get(r, auth.SessionName)
			session.Values["authenticated"] = true
			session.Values["user"] = username
			if err := session.Save(r, w); err != nil { http.Error(w, "無法儲存 Session", http.StatusInternalServerError); return }
			http.Redirect(w, r, "/", http.StatusFound)
		} else {
			http.Redirect(w, r, "/auth/login?error=invalid_credentials", http.StatusFound)
		}
	} else {
		h.AuthService.HandleLogin(w, r)
	}
}

func (h *Handlers) HandleLogout(w http.ResponseWriter, r *http.Request) {
	session, _ := auth.Store.Get(r, auth.SessionName)
	session.Values["authenticated"] = false
	session.Options.MaxAge = -1
	if err := session.Save(r, w); err != nil {
		h.Logger.Ctx(r.Context()).Error("無法登出時儲存 session", zap.Error(err))
		http.Error(w, "登出失敗", http.StatusInternalServerError)
		return
	}
	http.Redirect(w, r, "/auth/login", http.StatusFound)
}

func (h *Handlers) AuthCallback(w http.ResponseWriter, r *http.Request) {}

// --- Page Handlers ---

func (h *Handlers) Dashboard(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{ "Title": "總覽儀表板", "Page": "dashboard" }
	err := h.Templates.ExecuteTemplate(w, "pages/dashboard.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染儀表板頁面", zap.Error(err)); http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) ResourcesPage(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{ "Title": "資源管理", "Page": "resources" }
	err := h.Templates.ExecuteTemplate(w, "pages/resources.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染資源頁面模板", zap.Error(err)); http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) IncidentsPage(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{ "Title": "告警紀錄", "Page": "incidents" }
	err := h.Templates.ExecuteTemplate(w, "pages/incidents.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染事件頁面", zap.Error(err)); http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) renderPlaceholder(w http.ResponseWriter, r *http.Request, title, page string) {
	data := map[string]interface{}{"Title": title, "Page": page}
	err := h.Templates.ExecuteTemplate(w, "pages/placeholder.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染佔位頁面", zap.Error(err), zap.String("page", page)); http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) TeamsPage(w http.ResponseWriter, r *http.Request) { h.renderPlaceholder(w, r, "團隊管理", "teams") }
func (h *Handlers) AlertsPage(w http.ResponseWriter, r *http.Request) { h.renderPlaceholder(w, r, "告警規則", "alerts") }
func (h *Handlers) AutomationPage(w http.ResponseWriter, r *http.Request) { h.renderPlaceholder(w, r, "自動化", "automation") }
func (h *Handlers) CapacityPage(w http.ResponseWriter, r *http.Request) { h.renderPlaceholder(w, r, "容量規劃", "capacity") }
func (h *Handlers) ChannelsPage(w http.ResponseWriter, r *http.Request) { h.renderPlaceholder(w, r, "通知管道", "channels") }
func (h *Handlers) ProfilePage(w http.ResponseWriter, r *http.Request) { h.renderPlaceholder(w, r, "個人資料", "profile") }
func (h *Handlers) SettingsPage(w http.ResponseWriter, r *http.Request) { h.renderPlaceholder(w, r, "系統設定", "settings") }

// --- HTMX Handlers ---

func (h *Handlers) DashboardCards(w http.ResponseWriter, r *http.Request) {
	type cardData struct { Name, Value, Change, ChangeType, Icon string }
	cards := []cardData{
		{Name: "新告警 (New)", Value: "7", Change: "+11%", ChangeType: "increase", Icon: "siren"},
		{Name: "處理中 (In Progress)", Value: "7", Change: "+6%", ChangeType: "increase", Icon: "loader-circle"},
		{Name: "今日已解決 (Resolved Today)", Value: "8", Change: "+0%", ChangeType: "increase", Icon: "check-circle-2"},
		{Name: "資源健康度", Value: "99.8%", Icon: "shield-check"},
		{Name: "總資源數", Value: "1,204", Icon: "database"},
		{Name: "平均網路延遲", Value: "23 ms", Icon: "bar-chart-horizontal"},
	}
	err := h.Templates.ExecuteTemplate(w, "partials/dashboard-cards.html", map[string]interface{}{"Cards": cards})
	if err != nil { h.Logger.Ctx(r.Context()).Error("無法渲染儀表板卡片模板", zap.Error(err)) }
}

func (h *Handlers) AddResourceForm(w http.ResponseWriter, r *http.Request) {
	err := h.Templates.ExecuteTemplate(w, "partials/resource-form.html", nil)
	if err != nil { h.Logger.Ctx(r.Context()).Error("無法渲染資源表單模板", zap.Error(err)) }
}

func (h *Handlers) CreateResource(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil { h.Logger.Ctx(r.Context()).Error("無法解析表單", zap.Error(err)); return }
	newRes := resourceMock{
		ID:        uuid.NewString(),
		Name:      r.PostFormValue("name"),
		IPAddress: r.PostFormValue("ip_address"),
		Type:      r.PostFormValue("type"),
		Status:    "unknown",
	}
	h.mu.Lock()
	mockResources = append(mockResources, newRes)
	h.mu.Unlock()
	h.Logger.Ctx(r.Context()).Info("成功創建新資源 (模擬)", zap.String("name", newRes.Name), zap.String("ip", newRes.IPAddress))
	h.ResourcesTable(w, r)
}

func (h *Handlers) ResourcesTable(w http.ResponseWriter, r *http.Request) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	query := r.URL.Query().Get("q")
	var filteredResources []resourceMock
	if query != "" {
		query = strings.ToLower(query)
		for _, res := range mockResources {
			if strings.Contains(strings.ToLower(res.Name), query) || strings.Contains(strings.ToLower(res.IPAddress), query) {
				filteredResources = append(filteredResources, res)
			}
		}
	} else {
		filteredResources = make([]resourceMock, len(mockResources))
		copy(filteredResources, mockResources)
	}
	err := h.Templates.ExecuteTemplate(w, "partials/resource-table.html", map[string]interface{}{"Resources": filteredResources})
	if err != nil { h.Logger.Ctx(r.Context()).Error("無法渲染資源表格模板", zap.Error(err)) }
}

func (h *Handlers) IncidentList(w http.ResponseWriter, r *http.Request) {
	err := h.Templates.ExecuteTemplate(w, "partials/incident-list.html", map[string]interface{}{"Incidents": mockIncidents})
	if err != nil { h.Logger.Ctx(r.Context()).Error("無法渲染事件列表模板", zap.Error(err)) }
}

func (h *Handlers) IncidentDetails(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	incidentID := vars["id"]
	var foundIncident incidentMock
	for _, inc := range mockIncidents {
		if inc.ID == incidentID {
			foundIncident = inc
			break
		}
	}
	if foundIncident.ID == "" { http.NotFound(w, r); return }
	err := h.Templates.ExecuteTemplate(w, "partials/incident-details-modal.html", map[string]interface{}{"Incident": foundIncident})
	if err != nil { h.Logger.Ctx(r.Context()).Error("無法渲染事件詳情模態框", zap.Error(err)) }
}

// --- SRE Assistant Related Handlers ---

func (h *Handlers) DiagnoseDeployment(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	vars := mux.Vars(r)
	deploymentID, ok := vars["id"]
	if !ok { h.writeJSON(w, http.StatusBadRequest, map[string]string{"error": "缺少 deployment ID"}); return }
	h.Logger.Ctx(ctx).Info("開始部署診斷", zap.String("deploymentID", deploymentID))
	deployment, err := h.Services.GetDeploymentByID(ctx, deploymentID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			h.writeJSON(w, http.StatusNotFound, map[string]string{"error": "找不到部署資訊"})
		} else {
			h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "查詢部署資訊時發生錯誤"})
		}
		return
	}
	resp, err := h.Services.TriggerDeploymentDiagnosis(ctx, deployment)
	if err != nil {
		h.Logger.Ctx(ctx).Error("呼叫 SRE Assistant 失敗", zap.Error(err))
		h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "呼叫診斷服務失敗"})
		return
	}
	h.writeJSON(w, http.StatusAccepted, resp)
}

func (h *Handlers) GetDiagnosisStatus(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	vars := mux.Vars(r)
	sessionID, ok := vars["session_id"]
	if !ok { h.writeJSON(w, http.StatusBadRequest, map[string]string{"error": "缺少 session_id"}); return }
	status, err := h.Services.CheckDiagnosisStatus(ctx, sessionID)
	if err != nil {
		h.Logger.Ctx(ctx).Error("查詢狀態失敗", zap.Error(err), zap.String("sessionID", sessionID))
		h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "查詢狀態時發生內部錯誤"})
		return
	}
	h.writeJSON(w, http.StatusOK, status)
}
