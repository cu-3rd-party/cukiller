package shared

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
)

// MustGetDb returns a database connection
func (conf *ConfigDatabase) MustGetDb() *sql.DB {
	connStr := fmt.Sprintf(
		"postgres://%s:%s@%s:%s/%s?sslmode=disable",
		conf.DbUser,
		conf.DbPassword,
		conf.DbHost,
		conf.DbPort,
		conf.DbName,
	)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		panic("Failed to connect to database")
	}
	TestDbConnection(db)
	return db
}

// MonitorDbConnection pings database every delay and fails the program when a ping fails
func MonitorDbConnection(db *sql.DB, delay time.Duration) {
	ticker := time.NewTicker(delay)
	defer ticker.Stop()

	TestDbConnection(db)
	for {
		select {
		case <-ticker.C:
			TestDbConnection(db)
		}
	}
}

func TestDbConnection(db *sql.DB) {
	if err := db.Ping(); err != nil {
		logger.Fatalf("Failed to ping database: %v", err)
	}
}

func GetActiveGame(db *sql.DB) (bool, uuid.UUID) {
	row := db.QueryRow(`
	SELECT g.id FROM games g WHERE g.end_date IS NULL LIMIT 1
	`)
	var id uuid.UUID
	err := row.Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		// Нет активной игры
		return false, id
	}

	if err != nil {
		// Ошибка SQL — безопасный return
		logger.Error("GetActiveGame SQL error: %v", err)
		return false, id
	}

	// Если нашли хотя бы одну строку — игра идет и возвращаем ее айди
	return true, id
}
