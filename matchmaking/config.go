package main

import (
	"os"
	"strconv"
)

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
