package tests

import (
	"context"
	"cukiller/api/internal/api"
	. "cukiller/api/pkg/db"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestHealthy(t *testing.T) {
	gin.SetMode(gin.TestMode)

	router := api.NewRouter(api.Config{HealthCheck: func(ctx context.Context) bool {
		return true
	}})

	req := httptest.NewRequest(http.MethodGet, "/health/", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusOK, rec.Code)
}

func TestUnhealthy(t *testing.T) {
	gin.SetMode(gin.TestMode)

	router := api.NewRouter(api.Config{HealthCheck: func(ctx context.Context) bool {
		return false
	}})

	req := httptest.NewRequest(http.MethodGet, "/health/", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusInternalServerError, rec.Code)
}

func TestHealthyReal(t *testing.T) {
	gin.SetMode(gin.TestMode)
	db := SetupDb(t)

	router := api.NewRouter(api.Config{HealthCheck: GetHealthcheck(db)})

	req := httptest.NewRequest(http.MethodGet, "/health/", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusOK, rec.Code)
}
