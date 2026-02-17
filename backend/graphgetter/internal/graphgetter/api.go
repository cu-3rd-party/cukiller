package graphgetter

import (
	"encoding/csv"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"

	"golang.org/x/time/rate"
)

func StartupHttp() {
	http.HandleFunc("/health/", health)
	http.HandleFunc("/connections.csv", connectionsCSV)

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

var connectionsLimiter = rate.NewLimiter(rate.Every(time.Second/2), 4)

func connectionsCSV(w http.ResponseWriter, r *http.Request) {
	logger.Info("CSV request from %s", r.RemoteAddr)

	// Respect request context to avoid nil panics in limiter and honor cancellations.
	err := connectionsLimiter.Wait(r.Context())
	if err != nil {
		logger.Warn("Failed to wait for limiter for request from %s", r.RemoteAddr)
		return
	}

	w.Header().Set("Content-Type", "text/csv")
	w.Header().Set("Content-Disposition", "attachment; filename=connections.csv")

	edges, err := GetKillEventConnections()
	if err != nil {
		logger.Error("Failed to get connections: %v", err)
		http.Error(w, "failed to fetch data", http.StatusInternalServerError)
		return
	}

	// CSV writer
	csvWriter := csv.NewWriter(w)
	defer csvWriter.Flush()

	// Header row
	err = csvWriter.Write([]string{"from", "to"})
	if err != nil {
		logger.Error("CSV header write failed: %v", err)
		return
	}

	// Data rows
	for _, e := range edges {
		record := []string{
			strconv.Itoa(e.From),
			strconv.Itoa(e.To),
		}
		err := csvWriter.Write(record)
		if err != nil {
			logger.Error("CSV write failed: %v", err)
			return
		}
	}

	logger.Info("CSV successfully returned (%d rows)", len(edges))
}
