package main

import (
	"fmt"
	"net/http"
	"os"
	"time"
)

func startupHttp() {
	http.HandleFunc("/ping/", ping)
	http.HandleFunc("/health/", health)

	addr := fmt.Sprintf(":%d", conf.Port)
	logger.Info("HTTP server starting on %s", addr)

	if err := http.ListenAndServe(addr, nil); err != nil {
		logger.Error("HTTP server failed: %v", err)
		os.Exit(1)
	}
}

func ping(w http.ResponseWriter, r *http.Request) {
	logger.Info("Ping endpoint called from %s", r.RemoteAddr)

	_, err := fmt.Fprintf(w, "Hello, world!\n")
	if err != nil {
		logger.Error("Failed to write ping response: %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
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

	w.WriteHeader(http.StatusOK)
}
