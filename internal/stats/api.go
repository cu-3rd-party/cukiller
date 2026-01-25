package stats

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"
)

type ListResponse struct {
	Limit  int           `json:"limit"`
	Offset int           `json:"offset"`
	Items  []PlayerEntry `json:"items"`
}

type TotalResponse struct {
	Status string `json:"status"`
	Total  int    `json:"total"`
}

func StartupHttp() {
	http.HandleFunc("/health/", health)
	http.HandleFunc("/api/stats/kills", statsKills)
	http.HandleFunc("/api/stats/rating", statsRating)
	http.HandleFunc("/api/stats/total", statsTotal)
	http.HandleFunc("/api/stats", statsUser)

	addr := fmt.Sprintf(":%d", conf.Port)
	logger.Info("HTTP server starting on %s", addr)

	if err := http.ListenAndServe(addr, nil); err != nil {
		logger.Error("HTTP server failed: %v", err)
		os.Exit(1)
	}
}

func health(w http.ResponseWriter, r *http.Request) {
	logger.Info("Health check from %s", r.RemoteAddr)

	w.Header().Set("Content-Type", "application/json")
	_, err := fmt.Fprintf(w, `{"status": "healthy", "timestamp": "%s"}`, time.Now().Format(time.RFC3339))
	if err != nil {
		logger.Error("Failed to write health response: %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		return
	}
}

func statsKills(w http.ResponseWriter, r *http.Request) {
	limit, offset, ok := parseLimitOffset(w, r)
	if !ok {
		return
	}

	entries, err := GetKillsTop(limit, offset)
	if err != nil {
		handleStatsError(w, err)
		return
	}

	writeJSON(w, ListResponse{
		Limit:  limit,
		Offset: offset,
		Items:  entries,
	})
}

func statsRating(w http.ResponseWriter, r *http.Request) {
	limit, offset, ok := parseLimitOffset(w, r)
	if !ok {
		return
	}

	entries, err := GetRatingTop(limit, offset)
	if err != nil {
		handleStatsError(w, err)
		return
	}

	writeJSON(w, ListResponse{
		Limit:  limit,
		Offset: offset,
		Items:  entries,
	})
}

func statsTotal(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")
	if status == "" {
		http.Error(w, "status is required", http.StatusBadRequest)
		return
	}

	total, err := GetKillEventsTotal(status)
	if err != nil {
		handleStatsError(w, err)
		return
	}

	writeJSON(w, TotalResponse{
		Status: status,
		Total:  total,
	})
}

func statsUser(w http.ResponseWriter, r *http.Request) {
	username := r.URL.Query().Get("user")
	if username == "" {
		http.Error(w, "user is required", http.StatusBadRequest)
		return
	}

	stats, err := GetUserStats(username)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "user not found", http.StatusNotFound)
			return
		}
		handleStatsError(w, err)
		return
	}

	writeJSON(w, stats)
}

func parseLimitOffset(w http.ResponseWriter, r *http.Request) (int, int, bool) {
	limit := 10
	offset := 0

	if raw := r.URL.Query().Get("limit"); raw != "" {
		parsed, err := strconv.Atoi(raw)
		if err != nil || parsed <= 0 {
			http.Error(w, "invalid limit", http.StatusBadRequest)
			return 0, 0, false
		}
		limit = parsed
	}

	if raw := r.URL.Query().Get("offset"); raw != "" {
		parsed, err := strconv.Atoi(raw)
		if err != nil || parsed < 0 {
			http.Error(w, "invalid offset", http.StatusBadRequest)
			return 0, 0, false
		}
		offset = parsed
	}

	if limit > 100 {
		limit = 100
	}

	return limit, offset, true
}

func handleStatsError(w http.ResponseWriter, err error) {
	if errors.Is(err, errNoActiveGame) {
		http.Error(w, "no active game", http.StatusNotFound)
		return
	}
	if errors.Is(err, errInvalidStatus) {
		http.Error(w, "invalid status", http.StatusBadRequest)
		return
	}

	logger.Error("stats error: %v", err)
	http.Error(w, "failed to fetch stats", http.StatusInternalServerError)
}

func writeJSON(w http.ResponseWriter, payload any) {
	w.Header().Set("Content-Type", "application/json")
	encoder := json.NewEncoder(w)
	encoder.SetEscapeHTML(false)
	_ = encoder.Encode(payload)
}
