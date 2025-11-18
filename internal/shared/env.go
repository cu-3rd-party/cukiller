package shared

import (
	"os"
	"strconv"
)

// GetEnvInt returns environment variable value or default if not set or invalid
func GetEnvInt(key string, defaultValue int) int {
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

	logger.Info("Loaded %s=%d", key, value)
	return value
}

// GetEnvString returns environment variable value or default if not set or invalid
func GetEnvString(key string, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		logger.Warn("Environment variable %s not set, using default: %s", key, defaultValue)
		return defaultValue
	}

	logger.Info("Loaded %s=%s", key, value)
	return value
}

// GetEnvFloat64 returns environment variable value or default if not set or invalid
func GetEnvFloat64(key string, defaultValue float64) float64 {
	valueStr := os.Getenv(key)
	if valueStr == "" {
		logger.Warn("Environment variable %s not set, using default: %f", key, defaultValue)
		return defaultValue
	}

	value, err := strconv.ParseFloat(valueStr, 64)
	if err != nil {
		logger.Warn("Failed to parse %s=%q, using default: %f", key, valueStr, defaultValue)
		return defaultValue
	}

	logger.Info("Loaded %s=%f", key, value)
	return value
}
