package db

import (
	"cukiller/api/internal/config"
	"database/sql"
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
)

func SetupDb(t *testing.T) (db *sql.DB) {
	cfg, err := config.Load()
	assert.Nil(t, err)
	fmt.Println(cfg)
	db, err = Open(t.Context(), cfg.DbURL())
	assert.Nil(t, err)
	return
}
