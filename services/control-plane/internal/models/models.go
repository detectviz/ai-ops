// services/control-plane/internal/models/models.go
package models

import (
	"database/sql/driver"
	"encoding/json"
	"time"
)

// Resource 資源模型
type Resource struct {
	ID             uint            `gorm:"primarykey" json:"id"`
	Name           string          `gorm:"not null;uniqueIndex" json:"name"`
	Type           string          `json:"type"`
	IP             string          `json:"ip"`
	Branch         string          `json:"branch"`
	Description    string          `json:"description"`
	Status         string          `json:"status"`
	Monitored      bool            `json:"monitored"`
	ResourceGroups []ResourceGroup `gorm:"many2many:resource_resource_groups;" json:"resource_groups,omitempty"`
	CreatedAt      time.Time       `json:"created_at"`
	UpdatedAt      time.Time       `json:"updated_at"`
}

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
	AutomationScript *Script       `json:"automation_script,omitempty"`
	ScriptID         *uint         `json:"script_id,omitempty"`
	Enabled          bool          `json:"enabled"`
	CreatedAt        time.Time     `json:"created_at"`
	UpdatedAt        time.Time     `json:"updated_at"`
}

// Incident 告警事件
type Incident struct {
	ID             uint       `gorm:"primarykey" json:"id"`
	AlertRuleID    uint       `json:"alert_rule_id"`
	AlertRule      AlertRule  `json:"alert_rule,omitempty"`
	Level          string     `json:"level"`
	Time           time.Time  `json:"time"`
	Branch         string     `json:"branch"`
	IP             string     `json:"ip"`
	Name           string     `json:"name"`
	Description    string     `json:"desc"`
	Status         string     `json:"status"` // new, ack, resolved
	Assignee       *string    `json:"assignee"`
	AcknowledgedBy *string    `json:"acknowledgedBy"`
	AcknowledgedAt *time.Time `json:"acknowledged_at,omitempty"`
	ResolvedAt     *time.Time `json:"resolved_at,omitempty"`
	Comments       JSONB      `gorm:"type:jsonb" json:"comments"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at"`
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
