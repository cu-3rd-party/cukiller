package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"
)

func startupHttp() {
	http.HandleFunc("/ping/", ping)
	http.HandleFunc("/health/", health)
	http.HandleFunc("/add/killer/", addKiller)
	http.HandleFunc("/add/victim/", addVictim)

	addr := fmt.Sprintf(":%d", conf.Port)
	logger.Info("HTTP server starting on %s", addr)

	if err := http.ListenAndServe(addr, nil); err != nil {
		logger.Error("HTTP server failed: %v", err)
		os.Exit(1)
	}
}

func ping(w http.ResponseWriter, r *http.Request) {
	logger.Info("Ping endpoint called from %s", r.RemoteAddr)

	_, err := fmt.Fprintf(w, "ok\n")
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

var KillerPool = make(map[int]QueuePlayer)
var VictimPool = make(map[int]QueuePlayer)

func addKiller(w http.ResponseWriter, r *http.Request) {
	// 	1. parse PlayerData from request
	var data PlayerData
	err := json.NewDecoder(r.Body).Decode(&data)
	if err != nil {
		_, _ = w.Write([]byte("failed to parse PlayerData from json request"))
		w.WriteHeader(400)
	}
	// 2. put player into killer queue
	addPlayerToPool(KillerPool, data)
	w.WriteHeader(201)
}

func addVictim(w http.ResponseWriter, r *http.Request) {
	// 	1. parse PlayerData from request
	var data PlayerData
	err := json.NewDecoder(r.Body).Decode(&data)
	if err != nil {
		_, _ = w.Write([]byte("failed to parse PlayerData from json request"))
		w.WriteHeader(400)
	}
	// 2. put player into killer queue
	addPlayerToPool(VictimPool, data)
	w.WriteHeader(201)
}

func addPlayerToPool(pool map[int]QueuePlayer, data PlayerData) {
	pool[data.TgId] = QueuePlayer{
		TgId:       data.TgId,
		JoinedAt:   time.Now(),
		PlayerData: data,
	}
}
