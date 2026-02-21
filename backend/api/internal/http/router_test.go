package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestPing(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := NewRouter(Config{})

	req := httptest.NewRequest(http.MethodGet, "/ping", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	var payload map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}

	if payload["message"] != "pong" {
		t.Fatalf("expected message pong, got %q", payload["message"])
	}
}

func TestEcho(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := NewRouter(Config{})

	req := httptest.NewRequest(http.MethodGet, "/echo?message=hello", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	var payload map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}

	if payload["message"] != "hello" {
		t.Fatalf("expected message hello, got %q", payload["message"])
	}
}

func TestEchoMissingMessage(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := NewRouter(Config{})

	req := httptest.NewRequest(http.MethodGet, "/echo", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected status 400, got %d", rec.Code)
	}

	var payload map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}

	if payload["error"] == "" {
		t.Fatalf("expected error message, got empty string")
	}
}

func TestMetricsRouteToggle(t *testing.T) {
	gin.SetMode(gin.TestMode)

	router := NewMetricsRouter(MetricsConfig{})
	req := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200 for metrics enabled, got %d", rec.Code)
	}

	router = NewRouter(Config{})
	req = httptest.NewRequest(http.MethodGet, "/metrics", nil)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected status 404 for metrics disabled, got %d", rec.Code)
	}
}
