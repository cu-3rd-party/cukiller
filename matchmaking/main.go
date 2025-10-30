package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"
)

type Logger struct {
	*log.Logger
}

var logger = &Logger{
	log.New(os.Stdout, "[MATCHMAKING] ", log.LstdFlags|log.Lshortfile),
}

func (l *Logger) Info(format string, v ...interface{}) {
	l.Printf("INFO: "+format, v...)
}

func (l *Logger) Warn(format string, v ...interface{}) {
	l.Printf("WARN: "+format, v...)
}

func (l *Logger) Error(format string, v ...interface{}) {
	l.Printf("ERROR: "+format, v...)
}

var conf = getConfig()

type Config struct {
	Port int
	MatchmakingConfig
}

type MatchmakingConfig struct {
	Interval int
}

// getEnv returns environment variable value or default if not set or invalid
func getEnv(key string, defaultValue int) int {
	valueStr := os.Getenv(key)
	if valueStr == "" {
		logger.Warn("Environment variable %s not set, using default: %d", key, defaultValue)
		return defaultValue
	}

	value, err := strconv.Atoi(valueStr)
	if err != nil {
		logger.Warn("Failed to parse %s=%q, using default: %d", key, valueStr, defaultValue)
		return defaultValue
	}

	if value <= 0 {
		logger.Warn("Invalid value for %s=%d, must be positive, using default: %d", key, value, defaultValue)
		return defaultValue
	}

	logger.Info("Loaded %s=%d", key, value)
	return value
}

func getConfig() Config {
	return Config{
		Port: getEnv("PORT", 5432),
		MatchmakingConfig: MatchmakingConfig{
			Interval: getEnv("MATCHMAKING_INTERVAL", 5),
		},
	}
}

func main() {
	logger.Info("Starting matchmaking service...")

	go matchmakingTicker()
	startupHttp()
}

func matchmakingTicker() {
	ticker := time.NewTicker(time.Second * time.Duration(conf.MatchmakingConfig.Interval))
	defer ticker.Stop()

	logger.Info("Matchmaking ticker started with interval: %d seconds", conf.Interval)

	for {
		select {
		case <-ticker.C:
			matchmaking(&conf.MatchmakingConfig)
		}
	}
}

func matchmaking(conf *MatchmakingConfig) {
	//TODO: Implement matchmaking logic
}

func startupHttp() {
	http.HandleFunc("/ping/", ping)
	http.HandleFunc("/health/", health)

	addr := fmt.Sprintf(":%d", conf.Port)
	logger.Info("HTTP server starting on %s", addr)

	if err := http.ListenAndServe(addr, nil); err != nil {
		logger.Fatal("HTTP server failed: %v", err)
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
