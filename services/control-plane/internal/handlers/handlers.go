// services/control-plane/internal/handlers/handlers.go
package handlers

import (
	"database/sql"
	"encoding/json"
	"errors"
	"html/template"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/detectviz/control-plane/internal/auth"
	"github.com/detectviz/control-plane/internal/services"
	"github.com/google/uuid"
	"github.com/gorilla/mux"
	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap"
)

// Handlers 是一個容器，集中管理所有 HTTP 處理器方法。
type Handlers struct {
	Services    *services.Services
	Templates   *template.Template
	AuthService *auth.KeycloakService
	Logger      *otelzap.Logger
	mu          sync.RWMutex // 用於保護 mockResources 的讀寫鎖
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

// teamMemberMock 用於模擬團隊成員
type teamMemberMock struct {
	ID   string
	Name string
	Role string
}

// notificationSettingsMock 用於模擬團隊的通知設定
type notificationSettingsMock struct {
	PrimaryContact    string
	EscalationContact string
}

// teamMock 用於模擬團隊資料結構，嚴格遵循 OpenAPI 規範
type teamMock struct {
	ID                   string
	Name                 string
	Description          string
	ManagerID            string
	ManagerName          string
	MemberCount          int
	Members              []teamMemberMock
	NotificationSettings notificationSettingsMock
}

// userMock 用於模擬使用者/人員資料
type userMock struct {
	ID   string
	Name string
	Role string
}

// channelMock 用於模擬通知管道資料
type channelMock struct {
	ID   string
	Name string
}

// 模擬使用者和管道數據，供團隊數據引用
var mockUsers = []userMock{
	{ID: "user-1", Name: "陳經理", Role: "Team Manager"},
	{ID: "user-2", Name: "林組長", Role: "Team Manager"},
	{ID: "user-3", Name: "王工程師", Role: "Team Member"},
	{ID: "user-4", Name: "Admin", Role: "Super Admin"},
}

var mockChannels = []channelMock{
	{ID: "channel-1", Name: "網路一部 Slack"},
	{ID: "channel-2", Name: "On-Call 值班簡訊"},
	{ID: "channel-3", Name: "預設 Email (SMTP)"},
	{ID: "channel-4", Name: "資安團隊 Email 群組"},
}

// mockTeams 作為一個包級變數，模擬團隊資料庫
var mockTeams = []teamMock{
	{
		ID:          "team-1",
		Name:        "網路團隊",
		Description: "負責公司整體網路基礎設施的維運與管理。",
		ManagerID:   "user-2",
		ManagerName: "林組長",
		MemberCount: 3,
		Members: []teamMemberMock{
			{ID: "user-1", Name: "陳經理", Role: "Team Manager"},
			{ID: "user-2", Name: "林組長", Role: "Team Manager"},
			{ID: "user-3", Name: "王工程師", Role: "Team Member"},
		},
		NotificationSettings: notificationSettingsMock{
			PrimaryContact:    "王工程師",
			EscalationContact: "網路一部 Slack",
		},
	},
	{
		ID:          "team-2",
		Name:        "伺服器團隊",
		Description: "管理所有實體與虛擬伺服器。",
		ManagerID:   "",
		ManagerName: "未指派",
		MemberCount: 1,
		Members: []teamMemberMock{
			{ID: "user-3", Name: "王工程師", Role: "Team Member"},
		},
		NotificationSettings: notificationSettingsMock{
			PrimaryContact:    "王工程師",
			EscalationContact: "",
		},
	},
	{
		ID:          "team-3",
		Name:        "資安團隊",
		Description: "負責資訊安全、防火牆規則與威脅防禦。",
		ManagerID:   "user-1",
		ManagerName: "陳經理",
		MemberCount: 1,
		Members: []teamMemberMock{
			{ID: "user-1", Name: "陳經理", Role: "Team Manager"},
		},
		NotificationSettings: notificationSettingsMock{
			PrimaryContact:    "陳經理",
			EscalationContact: "資安團隊 Email 群組",
		},
	},
}

// alertRuleConditionMock 用於模擬告警規則的觸發條件
type alertRuleConditionMock struct {
	Metric    string
	Operator  string
	Threshold float64
	Duration  int // in seconds
}

// alertRuleResourceFilterMock 用於模擬告警規則的資源過濾器
type alertRuleResourceFilterMock struct {
	Groups []string
	Types  []string
	Tags   []string
}

// alertRuleMock 用於模擬告警規則資料結構
type alertRuleMock struct {
	ID                   string
	Name                 string
	Description          string
	Enabled              bool
	Severity             string
	Condition            alertRuleConditionMock
	ResourceFilter       alertRuleResourceFilterMock
	NotificationChannels []string
	// TODO: Add fields for automation script integration
}

// mockResourceGroups and mockScripts are needed for creating mockAlertRules
var mockResourceGroups = []struct {
	ID   string
	Name string
}{
	{"group-1", "核心交換器"},
	{"group-2", "總公司防火牆"},
	{"group-3", "所有路由器"},
}

var mockScripts = []struct {
	ID   string
	Name string
}{
	{"script-1", "重啟 Web 服務"},
	{"script-2", "清除快取"},
}

// mockAlertRules 作為一個包級變數，模擬告警規則資料庫
var mockAlertRules = []alertRuleMock{
	{
		ID:          "rule-1",
		Name:        "核心交換器 CPU 過高",
		Description: "當核心交換器群組的 CPU 使用率持續過高時觸發。",
		Enabled:     true,
		Severity:    "critical",
		Condition: alertRuleConditionMock{
			Metric:    "cpu_usage",
			Operator:  "gt",
			Threshold: 90,
			Duration:  300,
		},
		ResourceFilter: alertRuleResourceFilterMock{
			Groups: []string{"group-1"},
		},
		NotificationChannels: []string{"channel-1", "channel-2"},
	},
	{
		ID:          "rule-2",
		Name:        "防火牆網路流量異常",
		Description: "當總公司防火牆的輸出流量異常時觸發。",
		Enabled:     true,
		Severity:    "warning",
		Condition: alertRuleConditionMock{
			Metric:    "network_out_bytes",
			Operator:  "gt",
			Threshold: 1000000000, // 1GB
			Duration:  60,
		},
		ResourceFilter: alertRuleResourceFilterMock{
			Groups: []string{"group-2"},
		},
		NotificationChannels: []string{"channel-4"},
	},
	{
		ID:          "rule-3",
		Name:        "路由器 Ping 延遲",
		Description: "所有路由器的網路延遲過高。",
		Enabled:     false,
		Severity:    "info",
		Condition: alertRuleConditionMock{
			Metric:    "ping_latency_ms",
			Operator:  "gt",
			Threshold: 200,
			Duration:  120,
		},
		ResourceFilter: alertRuleResourceFilterMock{
			Groups: []string{"group-3"},
		},
		NotificationChannels: []string{},
	},
}

// --- Core & Auth Handlers ---

func (h *Handlers) writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if data != nil {
		if err := json.NewEncoder(w).Encode(data); err != nil {
			h.Logger.Error("無法寫入 JSON 響應", zap.Error(err))
		}
	}
}

// HealthCheck 檢查服務是否存活，並回傳符合 OpenAPI 規範的格式。
func (h *Handlers) HealthCheck(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
		"version":   "1.0.0",
	}
	h.writeJSON(w, http.StatusOK, response)
}

// ReadinessCheck 檢查服務及其依賴是否就緒，並回傳符合 OpenAPI 規範的格式。
func (h *Handlers) ReadinessCheck(w http.ResponseWriter, r *http.Request) {
	// 這裡的 DB Ping 是一個簡化的例子。在真實應用中，可能需要更複雜的檢查邏輯。
	dbReady := true // 假設 DB 正常
	if h.Services.DB != nil {
		// dbReady = h.Services.DB.Ping() == nil // 假設有 Ping 方法
	}
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
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("# HELP control_plane_up Control Plane service status\n# TYPE control_plane_up gauge\ncontrol_plane_up 1\n"))
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
		if err := r.ParseForm(); err != nil {
			http.Error(w, "無法解析表單", http.StatusBadRequest)
			return
		}
		username := r.PostFormValue("username")
		password := r.PostFormValue("password")
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
	h.Logger.Ctx(r.Context()).Info("--- EXECUTING Dashboard HANDLER ---") // DEBUG
	data := map[string]interface{}{"Title": "總覽儀表板", "Page": "dashboard"}
	err := h.Templates.ExecuteTemplate(w, "pages/dashboard.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染儀表板頁面", zap.Error(err))
		http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) ResourcesPage(w http.ResponseWriter, r *http.Request) {
	h.Logger.Ctx(r.Context()).Info("--- EXECUTING ResourcesPage HANDLER ---") // DEBUG
	data := map[string]interface{}{"Title": "資源管理", "Page": "resources"}
	err := h.Templates.ExecuteTemplate(w, "pages/resources.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染資源頁面模板", zap.Error(err))
		http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) IncidentsPage(w http.ResponseWriter, r *http.Request) {
	h.Logger.Ctx(r.Context()).Info("--- EXECUTING IncidentsPage HANDLER ---") // DEBUG
	data := map[string]interface{}{"Title": "告警紀錄", "Page": "incidents"}
	err := h.Templates.ExecuteTemplate(w, "pages/incidents.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染事件頁面", zap.Error(err))
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
	h.Logger.Ctx(r.Context()).Info("--- EXECUTING TeamsPage HANDLER ---") // DEBUG
	data := map[string]interface{}{"Title": "團隊管理", "Page": "teams"}
	err := h.Templates.ExecuteTemplate(w, "pages/teams.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染團隊管理頁面", zap.Error(err))
		http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) AlertsPage(w http.ResponseWriter, r *http.Request) {
	h.Logger.Ctx(r.Context()).Info("--- EXECUTING AlertsPage HANDLER ---") // DEBUG
	data := map[string]interface{}{"Title": "告警規則", "Page": "alerts"}
	err := h.Templates.ExecuteTemplate(w, "pages/alerts.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染告警規則頁面", zap.Error(err))
		http.Error(w, "頁面渲染錯誤", http.StatusInternalServerError)
	}
}

func (h *Handlers) AutomationPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "自動化", "automation")
}
func (h *Handlers) CapacityPage(w http.ResponseWriter, r *http.Request) {
	h.renderPlaceholder(w, r, "容量規劃", "capacity")
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

// --- HTMX Handlers ---

func (h *Handlers) DashboardCards(w http.ResponseWriter, r *http.Request) {
	type cardData struct{ Name, Value, Change, ChangeType, Icon string }
	cards := []cardData{
		{Name: "新告警 (New)", Value: "7", Change: "+11%", ChangeType: "increase", Icon: "siren"},
		{Name: "處理中 (In Progress)", Value: "7", Change: "+6%", ChangeType: "increase", Icon: "loader-circle"},
		{Name: "今日已解決 (Resolved Today)", Value: "8", Change: "+0%", ChangeType: "increase", Icon: "check-circle-2"},
		{Name: "資源健康度", Value: "99.8%", Icon: "shield-check"},
		{Name: "總資源數", Value: "1,204", Icon: "database"},
		{Name: "平均網路延遲", Value: "23 ms", Icon: "bar-chart-horizontal"},
	}
	err := h.Templates.ExecuteTemplate(w, "partials/dashboard-cards.html", map[string]interface{}{"Cards": cards})
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染儀表板卡片模板", zap.Error(err))
	}
}

func (h *Handlers) AddResourceForm(w http.ResponseWriter, r *http.Request) {
	err := h.Templates.ExecuteTemplate(w, "partials/resource-form.html", nil)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染資源表單模板", zap.Error(err))
	}
}

func (h *Handlers) CreateResource(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		h.Logger.Ctx(r.Context()).Error("無法解析表單", zap.Error(err))
		return
	}
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
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染資源表格模板", zap.Error(err))
	}
}

// TeamList 處理獲取團隊列表的 HTMX 請求
func (h *Handlers) TeamList(w http.ResponseWriter, r *http.Request) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	query := r.URL.Query().Get("q")
	var filteredTeams []teamMock
	if query != "" {
		query = strings.ToLower(query)
		for _, team := range mockTeams {
			if strings.Contains(strings.ToLower(team.Name), query) || strings.Contains(strings.ToLower(team.Description), query) {
				filteredTeams = append(filteredTeams, team)
			}
		}
	} else {
		filteredTeams = make([]teamMock, len(mockTeams))
		copy(filteredTeams, mockTeams)
	}

	err := h.Templates.ExecuteTemplate(w, "partials/team-list.html", map[string]interface{}{"Teams": filteredTeams})
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染團隊列表模板", zap.Error(err))
	}
}

// AddTeamForm 處理顯示新增團隊表單的 HTMX 請求
func (h *Handlers) AddTeamForm(w http.ResponseWriter, r *http.Request) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	data := map[string]interface{}{
		"Users":    mockUsers,
		"Channels": mockChannels,
	}
	err := h.Templates.ExecuteTemplate(w, "partials/team-form.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染團隊表單模板", zap.Error(err))
	}
}

// CreateTeam 處理創建新團隊的 HTMX 請求
func (h *Handlers) CreateTeam(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		h.Logger.Ctx(r.Context()).Error("無法解析團隊表單", zap.Error(err))
		http.Error(w, "無效的請求", http.StatusBadRequest)
		return
	}

	managerID := r.PostFormValue("manager_id")
	var managerName string
	for _, user := range mockUsers {
		if user.ID == managerID {
			managerName = user.Name
			break
		}
	}
	if managerName == "" {
		managerName = "未指派"
	}

	newTeam := teamMock{
		ID:          uuid.NewString(),
		Name:        r.PostFormValue("name"),
		Description: r.PostFormValue("description"),
		ManagerID:   managerID,
		ManagerName: managerName,
		MemberCount: 0, // 新團隊預設沒有成員
		Members:     []teamMemberMock{},
		NotificationSettings: notificationSettingsMock{
			PrimaryContact:    r.PostFormValue("primary_contact"),
			EscalationContact: r.PostFormValue("escalation_contact"),
		},
	}

	h.mu.Lock()
	mockTeams = append(mockTeams, newTeam)
	h.mu.Unlock()

	h.Logger.Ctx(r.Context()).Info("成功創建新團隊 (模擬)", zap.String("name", newTeam.Name))

	w.Header().Set("HX-Refresh", "true")
	w.WriteHeader(http.StatusOK)
}

func (h *Handlers) ConfirmDeleteTeam(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]
	var teamName string
	for _, t := range mockTeams {
		if t.ID == id {
			teamName = t.Name
			break
		}
	}
	if teamName == "" {
		http.NotFound(w, r)
		return
	}

	data := map[string]string{
		"ItemType":  "團隊",
		"ItemName":  teamName,
		"DeleteURL": "/htmx/teams/" + id,
	}
	err := h.Templates.ExecuteTemplate(w, "partials/confirm-delete-modal.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染刪除確認模板", zap.Error(err))
	}
}

func (h *Handlers) DeleteTeam(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	h.mu.Lock()
	var found bool
	for i, t := range mockTeams {
		if t.ID == id {
			mockTeams = append(mockTeams[:i], mockTeams[i+1:]...)
			found = true
			break
		}
	}
	h.mu.Unlock()

	if !found {
		http.NotFound(w, r)
		return
	}

	h.Logger.Ctx(r.Context()).Info("成功刪除團隊 (模擬)", zap.String("id", id))

	w.Header().Set("HX-Refresh", "true")
	w.WriteHeader(http.StatusOK)
}

func (h *Handlers) EditTeamForm(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]
	var teamToEdit teamMock
	var found bool
	for _, t := range mockTeams {
		if t.ID == id {
			teamToEdit = t
			found = true
			break
		}
	}

	if !found {
		http.NotFound(w, r)
		return
	}

	h.mu.RLock()
	defer h.mu.RUnlock()
	data := map[string]interface{}{
		"Team":     teamToEdit,
		"Users":    mockUsers,
		"Channels": mockChannels,
	}
	err := h.Templates.ExecuteTemplate(w, "partials/team-form.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染團隊編輯表單模板", zap.Error(err))
	}
}

func (h *Handlers) UpdateTeam(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	if err := r.ParseForm(); err != nil {
		h.Logger.Ctx(r.Context()).Error("無法解析團隊更新表單", zap.Error(err))
		http.Error(w, "無效的請求", http.StatusBadRequest)
		return
	}

	h.mu.Lock()
	var found bool
	for i, t := range mockTeams {
		if t.ID == id {
			mockTeams[i].Name = r.PostFormValue("name")
			mockTeams[i].Description = r.PostFormValue("description")
			mockTeams[i].ManagerID = r.PostFormValue("manager_id")
			for _, u := range mockUsers {
				if u.ID == mockTeams[i].ManagerID {
					mockTeams[i].ManagerName = u.Name
					break
				}
			}
			mockTeams[i].NotificationSettings.PrimaryContact = r.PostFormValue("primary_contact")
			mockTeams[i].NotificationSettings.EscalationContact = r.PostFormValue("escalation_contact")
			found = true
			break
		}
	}
	h.mu.Unlock()

	if !found {
		http.NotFound(w, r)
		return
	}

	h.Logger.Ctx(r.Context()).Info("成功更新團隊 (模擬)", zap.String("id", id))

	w.Header().Set("HX-Refresh", "true")
	w.WriteHeader(http.StatusOK)
}

func (h *Handlers) AlertRuleList(w http.ResponseWriter, r *http.Request) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	query := r.URL.Query().Get("q")
	var filteredRules []alertRuleMock
	if query != "" {
		query = strings.ToLower(query)
		for _, rule := range mockAlertRules {
			if strings.Contains(strings.ToLower(rule.Name), query) {
				filteredRules = append(filteredRules, rule)
			}
		}
	} else {
		filteredRules = make([]alertRuleMock, len(mockAlertRules))
		copy(filteredRules, mockAlertRules)
	}

	err := h.Templates.ExecuteTemplate(w, "partials/rule-list.html", map[string]interface{}{"Rules": filteredRules})
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染告警規則列表模板", zap.Error(err))
	}
}

func (h *Handlers) AddAlertRuleForm(w http.ResponseWriter, r *http.Request) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	data := map[string]interface{}{
		"ResourceGroups": mockResourceGroups,
		"Scripts":        mockScripts,
		"Channels":       mockChannels,
	}
	err := h.Templates.ExecuteTemplate(w, "partials/rule-form.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染告警規則表單模板", zap.Error(err))
	}
}

func (h *Handlers) CreateAlertRule(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		h.Logger.Ctx(r.Context()).Error("無法解析告警規則表單", zap.Error(err))
		http.Error(w, "無效的請求", http.StatusBadRequest)
		return
	}

	threshold, _ := strconv.ParseFloat(r.PostFormValue("threshold"), 64)
	duration, _ := strconv.Atoi(r.PostFormValue("duration"))

	newRule := alertRuleMock{
		ID:          uuid.NewString(),
		Name:        r.PostFormValue("name"),
		Description: r.PostFormValue("description"),
		Enabled:     true,
		Severity:    "critical", // Simplified for now
		Condition: alertRuleConditionMock{
			Metric:    r.PostFormValue("metric"),
			Operator:  r.PostFormValue("operator"),
			Threshold: threshold,
			Duration:  duration,
		},
		ResourceFilter: alertRuleResourceFilterMock{
			Groups: []string{r.PostFormValue("group_id")},
		},
		NotificationChannels: r.Form["notification_channels"],
	}

	h.mu.Lock()
	mockAlertRules = append(mockAlertRules, newRule)
	h.mu.Unlock()

	h.Logger.Ctx(r.Context()).Info("成功創建新告警規則 (模擬)", zap.String("name", newRule.Name))
	w.Header().Set("HX-Refresh", "true")
	w.WriteHeader(http.StatusOK)
}

func (h *Handlers) EditAlertRuleForm(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]
	var ruleToEdit alertRuleMock
	var found bool
	for _, rule := range mockAlertRules {
		if rule.ID == id {
			ruleToEdit = rule
			found = true
			break
		}
	}

	if !found {
		http.NotFound(w, r)
		return
	}

	h.mu.RLock()
	defer h.mu.RUnlock()
	data := map[string]interface{}{
		"Rule":           ruleToEdit,
		"ResourceGroups": mockResourceGroups,
		"Scripts":        mockScripts,
		"Channels":       mockChannels,
	}
	err := h.Templates.ExecuteTemplate(w, "partials/rule-form.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染告警規則編輯表單模板", zap.Error(err))
	}
}

func (h *Handlers) UpdateAlertRule(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	if err := r.ParseForm(); err != nil {
		http.Error(w, "無效的請求", http.StatusBadRequest)
		return
	}

	h.mu.Lock()
	var found bool
	for i, rule := range mockAlertRules {
		if rule.ID == id {
			threshold, _ := strconv.ParseFloat(r.PostFormValue("threshold"), 64)
			duration, _ := strconv.Atoi(r.PostFormValue("duration"))

			mockAlertRules[i].Name = r.PostFormValue("name")
			mockAlertRules[i].Description = r.PostFormValue("description")
			mockAlertRules[i].Condition.Metric = r.PostFormValue("metric")
			mockAlertRules[i].Condition.Operator = r.PostFormValue("operator")
			mockAlertRules[i].Condition.Threshold = threshold
			mockAlertRules[i].Condition.Duration = duration
			mockAlertRules[i].ResourceFilter.Groups = []string{r.PostFormValue("group_id")}
			mockAlertRules[i].NotificationChannels = r.Form["notification_channels"]
			found = true
			break
		}
	}
	h.mu.Unlock()

	if !found {
		http.NotFound(w, r)
		return
	}

	h.Logger.Ctx(r.Context()).Info("成功更新告警規則 (模擬)", zap.String("id", id))
	w.Header().Set("HX-Refresh", "true")
	w.WriteHeader(http.StatusOK)
}

func (h *Handlers) ConfirmDeleteAlertRule(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]
	var ruleName string
	for _, rule := range mockAlertRules {
		if rule.ID == id {
			ruleName = rule.Name
			break
		}
	}
	if ruleName == "" {
		http.NotFound(w, r)
		return
	}

	data := map[string]string{
		"ItemType":  "告警規則",
		"ItemName":  ruleName,
		"DeleteURL": "/htmx/alerts/" + id,
	}
	err := h.Templates.ExecuteTemplate(w, "partials/confirm-delete-modal.html", data)
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染刪除確認模板", zap.Error(err))
	}
}

func (h *Handlers) DeleteAlertRule(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	h.mu.Lock()
	var found bool
	for i, rule := range mockAlertRules {
		if rule.ID == id {
			mockAlertRules = append(mockAlertRules[:i], mockAlertRules[i+1:]...)
			found = true
			break
		}
	}
	h.mu.Unlock()

	if !found {
		http.NotFound(w, r)
		return
	}

	h.Logger.Ctx(r.Context()).Info("成功刪除告警規則 (模擬)", zap.String("id", id))
	w.Header().Set("HX-Refresh", "true")
	w.WriteHeader(http.StatusOK)
}

func (h *Handlers) IncidentList(w http.ResponseWriter, r *http.Request) {
	err := h.Templates.ExecuteTemplate(w, "partials/incident-list.html", map[string]interface{}{"Incidents": mockIncidents})
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染事件列表模板", zap.Error(err))
	}
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
	if foundIncident.ID == "" {
		http.NotFound(w, r)
		return
	}
	err := h.Templates.ExecuteTemplate(w, "partials/incident-details-modal.html", map[string]interface{}{"Incident": foundIncident})
	if err != nil {
		h.Logger.Ctx(r.Context()).Error("無法渲染事件詳情模態框", zap.Error(err))
	}
}

// --- SRE Assistant Related Handlers ---

func (h *Handlers) DiagnoseDeployment(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	vars := mux.Vars(r)
	deploymentID, ok := vars["id"]
	if !ok {
		h.writeJSON(w, http.StatusBadRequest, map[string]string{"error": "缺少 deployment ID"})
		return
	}
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
	if !ok {
		h.writeJSON(w, http.StatusBadRequest, map[string]string{"error": "缺少 session_id"})
		return
	}
	status, err := h.Services.CheckDiagnosisStatus(ctx, sessionID)
	if err != nil {
		h.Logger.Ctx(ctx).Error("查詢狀態失敗", zap.Error(err), zap.String("sessionID", sessionID))
		h.writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "查詢狀態時發生內部錯誤"})
		return
	}
	h.writeJSON(w, http.StatusOK, status)
}
