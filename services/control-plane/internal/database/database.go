package database

import (
	"database/sql"
	"fmt"
	"log"

	"github.com/detectviz/control-plane/internal/models"
	_ "github.com/lib/pq" // PostgreSQL driver
)

// Connect 建立並返回一個到 PostgreSQL 資料庫的連線。
func Connect(dataSourceName string) (*sql.DB, error) {
	db, err := sql.Open("postgres", dataSourceName)
	if err != nil {
		return nil, fmt.Errorf("無法開啟資料庫連線: %w", err)
	}

	if err = db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("無法連線到資料庫: %w", err)
	}

	log.Println("資料庫連線成功")
	return db, nil
}

// Migrate 執行資料庫遷移，建立必要的資料表並填入初始資料。
func Migrate(db *sql.DB) error {
	log.Println("正在執行資料庫遷移...")

	// 建立 deployments 資料表
	createTableQuery := `
	CREATE TABLE IF NOT EXISTS deployments (
		id TEXT PRIMARY KEY,
		service_name TEXT NOT NULL,
		namespace TEXT NOT NULL,
		created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
		updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
	);`

	if _, err := db.Exec(createTableQuery); err != nil {
		return fmt.Errorf("無法建立 deployments 資料表: %w", err)
	}

	log.Println("`deployments` 資料表已成功建立或已存在。")

	// 填入初始種子資料
	seedDataQuery := `
	INSERT INTO deployments (id, service_name, namespace, created_at, updated_at) VALUES
	('dep-test-123', 'payment-api', 'production', NOW(), NOW()),
	('dep-test-456', 'frontend-webapp', 'staging', NOW(), NOW())
	ON CONFLICT (id) DO NOTHING;
	`
	if _, err := db.Exec(seedDataQuery); err != nil {
		return fmt.Errorf("無法填入種子資料到 deployments 資料表: %w", err)
	}

	log.Println("資料庫遷移成功完成。")
	return nil
}

// GetDeploymentByID 根據 ID 從資料庫中檢索部署資訊。
func GetDeploymentByID(db *sql.DB, id string) (*models.Deployment, error) {
	query := `SELECT id, service_name, namespace, created_at, updated_at FROM deployments WHERE id = $1`

	deployment := &models.Deployment{}
	err := db.QueryRow(query, id).Scan(
		&deployment.ID,
		&deployment.ServiceName,
		&deployment.Namespace,
		&deployment.CreatedAt,
		&deployment.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("找不到 ID 為 %s 的部署", id)
		}
		return nil, fmt.Errorf("查詢部署時發生錯誤: %w", err)
	}

	return deployment, nil
}
