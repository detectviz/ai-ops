package database

import (
	"database/sql"
	"github.com/detectviz/control-plane/internal/models"
)

// ListResources 模擬從資料庫獲取資源列表
func ListResources(db *sql.DB) ([]models.Resource, error) {
	mockResources := []models.Resource{
		{ID: 1, Status: "normal", Name: "Edge SW13", IP: "88.201.0.13", Branch: "仁愛分行", Type: "Switch", Monitored: true},
		{ID: 2, Status: "warning", Name: "Backup Server", IP: "88.201.0.14", Branch: "仁愛分行", Type: "Server", Monitored: true},
		{ID: 3, Status: "error", Name: "DATA Router", IP: "88.255.252.101", Branch: "林口分行", Type: "Router", Monitored: false},
        {ID: 4, Status: "normal", Name: "VG Router", IP: "88.99.33.12", Branch: "林口分行", Type: "Router", Monitored: true},
        {ID: 5, Status: "error", Name: "Delta PDU", IP: "88.99.33.15", Branch: "林口分行", Type: "Server", Monitored: true},
	}
	return mockResources, nil
}
