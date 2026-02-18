package db

import (
	"cukiller/api/internal/config"
	"database/sql"
	"testing"

	"github.com/stretchr/testify/assert"
)

func SetupDb(t *testing.T) (db *sql.DB) {
	t.Helper()
	cfg, err := config.Load()
	assert.Nil(t, err)
	db, err = Open(t.Context(), cfg.DbURL())
	if err != nil {
		t.Skipf("skipping db tests: db open failed: %v", err)
	}
	return
}
