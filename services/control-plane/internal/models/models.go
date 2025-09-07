// services/control-plane/internal/models/models.go
package models

import (
	"database/sql/driver"
	"encoding/json"
	"time"
)

// Resource 資源模型 (已對齊 OpenAPI spec)
type Resource struct {
	ID          string    `gorm:"type:uuid;primary_key;" json:"id"`
	Name        string    `gorm:"not null;uniqueIndex" json:"name"`
	Type        string    `json:"type"`                     // spec enum: [server, network, database, application, container]
	Status      string    `json:"status"`                   // spec enum: [healthy, warning, critical, unknown]
	IPAddress   string    `json:"ip_address,omitempty"`
	Location    string    `json:"location,omitempty"`
	GroupID     string    `json:"group_id,omitempty"`
	Description string    `json:"description,omitempty"`
	Tags        JSONB     `gorm:"type:jsonb" json:"tags,omitempty"` // OpenAPI shows array of strings, JSONB is flexible
	Owner       string    `json:"owner,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// Incident 告警事件 (已對齊 OpenAPI spec)
type Incident struct {
	ID                string     `gorm:"type:uuid;primary_key;" json:"id"`
	Title             string     `gorm:"not null" json:"title"`
	Description       string     `json:"description,omitempty"`
	Severity          string     `gorm:"not null" json:"severity"` // spec enum: [critical, error, warning, info]
	Status            string     `gorm:"not null" json:"status"`   // spec enum: [new, acknowledged, resolved]
	AffectedResources JSONB      `gorm:"type:jsonb" json:"affected_resources,omitempty"`
	Assignee          *string    `json:"assignee,omitempty"`
	AcknowledgedBy    *string    `json:"acknowledged_by,omitempty"`
	AcknowledgedAt    *time.Time `json:"acknowledged_at,omitempty"`
	ResolvedBy        *string    `json:"resolved_by,omitempty"`
	ResolvedAt        *time.Time `json:"resolved_at,omitempty"`
	Resolution        string     `json:"resolution,omitempty"`
	RootCause         string     `json:"root_cause,omitempty"`
	Comments          JSONB      `gorm:"type:jsonb" json:"comments,omitempty"`
	Tags              JSONB      `gorm:"type:jsonb" json:"tags,omitempty"`
	CreatedAt         time.Time  `json:"created_at"`
	UpdatedAt         time.Time  `json:"updated_at"`
}


// --- Unchanged Models Below ---

// ResourceGroup 資源群組
type ResourceGroup struct {
	ID          uint        `gorm:"primarykey" json:"id"`
	Name        string      `gorm:"not null;uniqueIndex" json:"name"`
	Description string      `json:"description"`
	Resources   []Resource  `gorm:"many2many:resource_resource_groups;" json:"resources,omitempty"`
	Teams       []Team      `gorm:"many2many:team_resource_groups;" json:"teams,omitempty"`
	AlertRules  []AlertRule `json:"alert_rules,omitempty"`
	CreatedAt   time.Time   `json:"created_at"`
	UpdatedAt   time.Time   `json:"updated_at"`
}

// Personnel 人員
type Personnel struct {
	ID                uint      `gorm:"primarykey" json:"id"`
	Username          string    `gorm:"not null;uniqueIndex" json:"username"`
	Name              string    `json:"name"`
	Email             string    `json:"email"`
	EmailVerified     bool      `json:"email_verified"`
	Phone             string    `json:"phone"`
	PhoneVerified     bool      `json:"phone_verified"`
	LineToken         string    `json:"-"`
	LineVerified      bool      `json:"line_verified"`
	Role              string    `json:"role"`
	NotificationLevel string    `json:"notification_level"`
	Teams             []Team    `gorm:"many2many:team_members;" json:"teams,omitempty"`
	CreatedAt         time.Time `json:"created_at"`
	UpdatedAt         time.Time `json:"updated_at"`
}

// Team 團隊
type Team struct {
	ID             uint            `gorm:"primarykey" json:"id"`
	Name           string          `gorm:"not null;uniqueIndex" json:"name"`
	Description    string          `json:"description"`
	Members        []Personnel     `gorm:"many2many:team_members;" json:"members,omitempty"`
	ResourceGroups []ResourceGroup `gorm:"many2many:team_resource_groups;" json:"resource_groups,omitempty"`
	Subscribers    JSONB           `gorm:"type:jsonb" json:"subscribers"`
	CreatedAt      time.Time       `json:"created_at"`
	UpdatedAt      time.Time       `json:"updated_at"`
}

// NotificationChannel 通知管道
type NotificationChannel struct {
	ID        uint      `gorm:"primarykey" json:"id"`
	Name      string    `gorm:"not null;uniqueIndex" json:"name"`
	Type      string    `json:"type"` // email, webhook, slack, line, sms
	Config    JSONB     `gorm:"type:jsonb" json:"config"`
	Enabled   bool      `json:"enabled"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// AlertRule 告警規則
type AlertRule struct {
	ID               uint          `gorm:"primarykey" json:"id"`
	Name             string        `gorm:"not null" json:"name"`
	ResourceGroupID  uint          `json:"resource_group_id"`
	ResourceGroup    ResourceGroup `json:"resource_group,omitempty"`
	Expression       string        `json:"expression"`
	Severity         string        `json:"severity"`
	Duration         string        `json:"duration"`
	CustomTitle      string        `json:"custom_title"`
	CustomContent    string        `json:"custom_content"`
	AutomationScript *Script       `gorm:"foreignKey:ScriptID" json:"automation_script,omitempty"`
	ScriptID         *uint         `json:"script_id,omitempty"`
	Enabled          bool          `json:"enabled"`
	CreatedAt        time.Time     `json:"created_at"`
	UpdatedAt        time.Time     `json:"updated_at"`
}

// Script 自動化腳本
type Script struct {
	ID          uint      `gorm:"primarykey" json:"id"`
	Name        string    `gorm:"not null;uniqueIndex" json:"name"`
	Description string    `json:"description"`
	Type        string    `json:"type"` // shell, ansible, python
	Content     string    `json:"content"`
	Parameters  JSONB     `gorm:"type:jsonb" json:"parameters"`
	RiskLevel   string    `json:"risk_level"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// ExecutionLog 執行日誌
type ExecutionLog struct {
	ID            uint      `gorm:"primarykey" json:"id"`
	ScriptID      uint      `json:"script_id"`
	Script        Script    `json:"script,omitempty"`
	IncidentID    *uint     `json:"incident_id,omitempty"`
	Incident      *Incident `json:"incident,omitempty"`
	ExecutionTime time.Time `json:"executionTime"`
	ScriptName    string    `json:"scriptName"`
	TriggerAlert  string    `json:"triggerAlert"`
	Status        string    `json:"status"` // success, failed
	Duration      string    `json:"duration"`
	Output        string    `json:"output"`
	Error         string    `json:"error,omitempty"`
	ExecutedBy    string    `json:"executed_by"`
	CreatedAt     time.Time `json:"created_at"`
}

// AuditLog 審計日誌
type AuditLog struct {
	ID          uint      `gorm:"primarykey" json:"id"`
	User        string    `json:"user"`
	Action      string    `json:"action"`
	Resource    string    `json:"resource"`
	ResourceID  string    `json:"resource_id"`
	ServiceName string    `json:"service_name"`
	Details     JSONB     `gorm:"type:jsonb" json:"details"`
	IPAddress   string    `json:"ip_address"`
	UserAgent   string    `json:"user_agent"`
	Success     bool      `json:"success"`
	Error       string    `json:"error,omitempty"`
	Timestamp   time.Time `json:"timestamp"`
	CreatedAt   time.Time `json:"created_at"`
}

// Maintenance 維護時段
type Maintenance struct {
	ID             uint            `gorm:"primarykey" json:"id"`
	Name           string          `gorm:"not null" json:"name"`
	ResourceGroups []ResourceGroup `gorm:"many2many:maintenance_resource_groups;" json:"resource_groups,omitempty"`
	StartTime      time.Time       `json:"start_time"`
	EndTime        time.Time       `json:"end_time"`
	Description    string          `json:"description"`
	CreatedBy      string          `json:"created_by"`
	Enabled        bool            `json:"enabled"`
	CreatedAt      time.Time       `json:"created_at"`
	UpdatedAt      time.Time       `json:"updated_at"`
}

// Deployment 代表一個部署實例
type Deployment struct {
	ID          string    `gorm:"primarykey" json:"id"`
	ServiceName string    `gorm:"not null" json:"service_name"`
	Namespace   string    `gorm:"not null" json:"namespace"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// JSONB 自定義 JSON 類型
type JSONB map[string]interface{}

// Scan 實現 sql.Scanner 介面
func (j *JSONB) Scan(value interface{}) error {
	if value == nil {
		*j = make(map[string]interface{})
		return nil
	}

	bytes, ok := value.([]byte)
	if !ok {
		return nil
	}

	return json.Unmarshal(bytes, j)
}

// Value 實現 driver.Valuer 介面
func (j JSONB) Value() (driver.Value, error) {
	if j == nil {
		return nil, nil
	}
	return json.Marshal(j)
}

// --- API Skeletons ---

// DashboardSummaryAlerts 代表儀表板摘要中的告警統計部分。
type DashboardSummaryAlerts struct {
	New           int `json:"new,omitempty"`
	Processing    int `json:"processing,omitempty"`
	ResolvedToday int `json:"resolved_today,omitempty"`
}

// DashboardSummaryResources 代表儀表板摘要中的資源統計部分。
type DashboardSummaryResources struct {
	Total    int `json:"total,omitempty"`
	Healthy  int `json:"healthy,omitempty"`
	Warning  int `json:"warning,omitempty"`
	Critical int `json:"critical,omitempty"`
}

// DashboardSummaryKPIs 代表儀表板摘要中的關鍵績效指標 (KPI) 部分。
type DashboardSummaryKPIs struct {
	Availability float64 `json:"availability,omitempty"` // 系統可用性百分比
	MTTR         float64 `json:"mttr,omitempty"`         // 平均修復時間（分鐘）
	IncidentRate float64 `json:"incident_rate,omitempty"`  // 事件發生率
}

// DashboardSummary 是儀表板摘要 API 的頂層回應結構。
type DashboardSummary struct {
	Alerts    *DashboardSummaryAlerts    `json:"alerts,omitempty"`
	Resources *DashboardSummaryResources `json:"resources,omitempty"`
	KPIs      *DashboardSummaryKPIs      `json:"kpis,omitempty"`
}

// Pagination 定義了 API 回應中用於分頁的標準結構。
type Pagination struct {
	Page       int `json:"page"`
	PageSize   int `json:"page_size"`
	Total      int `json:"total"`
	TotalPages int `json:"total_pages"`
}

// ResourceList 代表一個分頁的資源列表。
type ResourceList struct {
	Items      []Resource `json:"items"`
	Pagination Pagination `json:"pagination"`
}

// ResourceCreateRequest 定義了創建新資源時請求體的結構。
type ResourceCreateRequest struct {
	Name        string   `json:"name" binding:"required"`
	Type        string   `json:"type" binding:"required"`
	IPAddress   string   `json:"ip_address" binding:"required"`
	Location    string   `json:"location,omitempty"`
	GroupID     string   `json:"group_id,omitempty"`
	Tags        []string `json:"tags,omitempty"`
	Owner       string   `json:"owner,omitempty"`
	Description string   `json:"description,omitempty"`
	Metadata    JSONB    `json:"metadata,omitempty"`
}

// ResourceUpdateRequest 定義了更新已存在資源時請求體的結構。
type ResourceUpdateRequest struct {
	Name        string   `json:"name,omitempty"`
	Location    string   `json:"location,omitempty"`
	GroupID     string   `json:"group_id,omitempty"`
	Tags        []string `json:"tags,omitempty"`
	Owner       string   `json:"owner,omitempty"`
	Description string   `json:"description,omitempty"`
	Metadata    JSONB    `json:"metadata,omitempty"`
}

// BatchResourceOperation 定義了對資源進行批次操作的請求結構。
type BatchResourceOperation struct {
	Operation   string                 `json:"operation" binding:"required"`   // 例如 "delete", "add_to_group"
	ResourceIDs []string               `json:"resource_ids" binding:"required"`
	Parameters  map[string]interface{} `json:"parameters,omitempty"`         // 操作所需的額外參數，如 group_id
}

// BatchOperationResultFailure 代表批次操作中單個資源的操作失敗資訊。
type BatchOperationResultFailure struct {
	ResourceID string `json:"resource_id"`
	Error      string `json:"error"`
}

// BatchOperationResult 定義了批次資源操作的結果。
type BatchOperationResult struct {
	SuccessCount int                           `json:"success_count"`
	FailureCount int                           `json:"failure_count"`
	Failures     []BatchOperationResultFailure `json:"failures,omitempty"`
}

// NetworkScanRequest 定義了發起網路掃描的請求結構。
type NetworkScanRequest struct {
	CIDR       string   `json:"cidr" binding:"required"` // CIDR 格式的網段
	PortRanges []string `json:"port_ranges,omitempty"`
	Timeout    int      `json:"timeout,omitempty"`
}

// ScanTaskResponse 定義了異步掃描任務被接受時的回應。
type ScanTaskResponse struct {
	TaskID  string `json:"task_id"`
	Status  string `json:"status"`
	Message string `json:"message"`
}

// DiscoveredResource 代表在網路掃描中發現的單個資源。
type DiscoveredResource struct {
	IPAddress    string   `json:"ip_address"`
	Hostname     string   `json:"hostname"`
	OpenPorts    []int    `json:"open_ports"`
	OSDetection  string   `json:"os_detection"`
	Services     []string `json:"services"`
}

// ScanResult 定義了網路掃描任務完成後的詳細結果。
type ScanResult struct {
	TaskID             string               `json:"task_id"`
	Status             string               `json:"status"`
	DiscoveredResources []DiscoveredResource `json:"discovered_resources"`
	ScanTime           time.Time            `json:"scan_time"`
	Error              string               `json:"error,omitempty"`
}

// IncidentList 代表一個分頁的事件列表。
type IncidentList struct {
	Items      []Incident `json:"items"`
	Pagination Pagination `json:"pagination"`
}

// IncidentCreateRequest 定義了創建新事件時請求體的結構。
type IncidentCreateRequest struct {
	Title             string   `json:"title" binding:"required"`
	Severity          string   `json:"severity" binding:"required"`
	Description       string   `json:"description,omitempty"`
	AffectedResources []string `json:"affected_resources,omitempty"`
	Tags              []string `json:"tags,omitempty"`
}

// IncidentUpdateRequest 定義了更新已存在事件時請求體的結構。
type IncidentUpdateRequest struct {
	Title             string   `json:"title,omitempty"`
	Description       string   `json:"description,omitempty"`
	Severity          string   `json:"severity,omitempty"`
	AffectedResources []string `json:"affected_resources,omitempty"`
	Tags              []string `json:"tags,omitempty"`
}

// AcknowledgeIncidentRequest 定義了確認事件的請求體。
type AcknowledgeIncidentRequest struct {
	AcknowledgedBy string `json:"acknowledged_by"`
	Comment        string `json:"comment,omitempty"`
}

// ResolveIncidentRequest 定義了標記事件為已解決的請求體。
type ResolveIncidentRequest struct {
	ResolvedBy string `json:"resolved_by"`
	Resolution string `json:"resolution"`
	RootCause  string `json:"root_cause,omitempty"`
}

// AssignIncidentRequest 定義了指派事件的請求體。
type AssignIncidentRequest struct {
	AssigneeID string `json:"assignee_id" binding:"required"`
}

// AddIncidentCommentRequest 定義了為事件新增註記的請求體。
type AddIncidentCommentRequest struct {
	Comment string `json:"comment" binding:"required"`
}

// AIGeneratedReport 代表由 AI 生成的事件分析報告。
type AIGeneratedReport struct {
	ReportType      string    `json:"report_type"`
	Content         string    `json:"content"`
	KeyFindings     []string  `json:"key_findings"`
	Recommendations []string  `json:"recommendations"`
	ConfidenceScore float64   `json:"confidence_score"`
	GeneratedAt     time.Time `json:"generated_at"`
}
