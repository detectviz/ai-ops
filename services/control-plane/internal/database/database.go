package database

import (
	"fmt"
	"log"

	"github.com/detectviz/control-plane/internal/models"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// DB 是一個 GORM 資料庫連線的封裝。
type DB struct {
	*gorm.DB
}

// New 建立一個新的 GORM 資料庫連線。
// 這是建立資料庫實例的唯一方式。
func New(dataSourceName string) (*DB, error) {
	// 1. 使用 GORM 開啟資料庫連線
	db, err := gorm.Open(postgres.Open(dataSourceName), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("無法使用 GORM 開啟資料庫連線: %w", err)
	}

	log.Println("資料庫連線池成功初始化 (GORM)")
	return &DB{db}, nil
}

// Close 不再需要，GORM 會自動管理連線池的關閉。

// Migrate 執行資料庫遷移，使用 GORM 自動建立所有必要的資料表。
func (d *DB) Migrate() error {
	log.Println("正在執行 GORM 資料庫自動遷移...")

	// GORM 的 AutoMigrate 會檢查並建立所有不存在的資料表和欄位。
	err := d.AutoMigrate(
		&models.Resource{},
		&models.ResourceGroup{},
		&models.Personnel{},
		&models.Team{},
		&models.NotificationChannel{},
		&models.AlertRule{},
		&models.Incident{},
		&models.Script{},
		&models.ExecutionLog{},
		&models.AuditLog{},
		&models.Maintenance{},
		&models.Deployment{},
	)
	if err != nil {
		return fmt.Errorf("GORM 自動遷移失敗: %w", err)
	}

	log.Println("GORM 資料庫遷移成功完成。")
	return nil
}

// TODO (Jules): 在後續步驟中，使用 GORM 語法重新實作所有資料庫查詢方法，
// 例如 GetDeploymentByID, ListResources 等。
