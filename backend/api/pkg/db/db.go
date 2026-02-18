package db

import (
	"context"
	"database/sql"
	"time"

	_ "github.com/lib/pq"
)

// Open connects to Postgres and verifies the connection with a ping.
func Open(ctx context.Context, dbURL string) (*sql.DB, error) {
	db, err := sql.Open("postgres", dbURL)
	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := db.PingContext(ctx); err != nil {
		_ = db.Close()
		return nil, err
	}

	return db, nil
}
