package db

import (
	"context"
	"database/sql"
)

func GetHealthcheck(db *sql.DB) func(ctx context.Context) bool {
	return func(ctx context.Context) bool {
		return db.PingContext(ctx) == nil
	}
}
