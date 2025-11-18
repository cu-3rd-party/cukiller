package shared

import (
	"database/sql"
	"fmt"
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
	return db
}
