package database

import (
	"database/sql"
	"github.com/detectviz/control-plane/internal/models"
	"github.com/google/uuid"
)

// ListResources 模擬從資料庫獲取資源列表
func ListResources(db *sql.DB) ([]models.Resource, error) {
	// 註解：此處的模擬資料應與 models.Resource 結構和 OpenAPI 規範保持一致
	mockResources := []models.Resource{
		{ID: uuid.NewString(), Status: "healthy", Name: "Edge SW13", IPAddress: "88.201.0.13", Type: "network"},
		{ID: uuid.NewString(), Status: "warning", Name: "Backup Server", IPAddress: "88.201.0.14", Type: "server"},
		{ID: uuid.NewString(), Status: "critical", Name: "DATA Router", IPAddress: "88.255.252.101", Type: "network"},
        {ID: uuid.NewString(), Status: "healthy", Name: "VG Router", IPAddress: "88.99.33.12", Type: "network"},
        {ID: uuid.NewString(), Status: "critical", Name: "Delta PDU", IPAddress: "88.99.33.15", Type: "server"},
	}
	return mockResources, nil
}
