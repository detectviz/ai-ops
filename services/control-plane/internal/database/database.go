package database

import (
	"database/sql"
	"fmt"
	"log"

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

// Migrate 執行資料庫遷移。
// TODO: 在未來加入真正的遷移邏輯。
func Migrate(db *sql.DB) error {
	// 在這裡加入您的資料庫綱要 (schema) 建立邏輯
	// 例如: CREATE TABLE IF NOT EXISTS ...
	log.Println("正在執行資料庫遷移 (目前為空操作)...")
	// query := `
	// CREATE TABLE IF NOT EXISTS users (
	//  id SERIAL PRIMARY KEY,
	//  name TEXT NOT NULL
	// );
	// `
	// _, err := db.Exec(query)
	// return err
	return nil
}
