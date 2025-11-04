package main

import (
	"os"
	"strconv"
)

var conf = getConfig()

type Config struct {
	Port int
	MatchmakingConfig
	DatabaseConfig
}

type DatabaseConfig struct {
	DbUser     string
	DbPassword string
	DbHost     string
	DbPort     string
	DbName     string
}

type MatchmakingConfig struct {
	Interval int

	QualityThreshold float64
	// coefficients for RatePlayerPair logic
	MaxRatingDiff     float64
	CourseCoefficient float64
	GroupCoefficient  float64
	TypeCoefficient   float64
	TimeCoefficient   float64
}

// getEnvInt returns environment variable value or default if not set or invalid
func getEnvInt(key string, defaultValue int) int {
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

// getEnvString returns environment variable value or default if not set or invalid
func getEnvString(key string, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		logger.Warn("Environment variable %s not set, using default: %d", key, defaultValue)
		return defaultValue
	}

	logger.Info("Loaded %s=%d", key, value)
	return value
}

// getEnvFloat64 returns environment variable value or default if not set or invalid
func getEnvFloat64(key string, defaultValue float64) float64 {
	valueStr := os.Getenv(key)
	if valueStr == "" {
		logger.Warn("Environment variable %s not set, using default: %d", key, defaultValue)
		return defaultValue
	}

	value, err := strconv.ParseFloat(valueStr, 64)
	if err != nil {
		logger.Warn("Failed to parse %s=%q, using default: %d", key, valueStr, defaultValue)
		return defaultValue
	}

	logger.Info("Loaded %s=%d", key, value)
	return value
}

func getConfig() Config {
	return Config{
		Port: getEnvInt("PORT", 6543),
		MatchmakingConfig: MatchmakingConfig{
			Interval:          getEnvInt("MATCHMAKING_INTERVAL", 5),
			QualityThreshold:  getEnvFloat64("QUALITY_THRESHOLD", 0.6),
			MaxRatingDiff:     getEnvFloat64("MAX_RATING_DIFF", 1000),
			CourseCoefficient: getEnvFloat64("COURSE_COEFFICIENT", 0.3),
			GroupCoefficient:  getEnvFloat64("GROUP_COEFFICIENT", -0.2),
			TypeCoefficient:   getEnvFloat64("TYPE_COEFFICIENT", -0.6),
			TimeCoefficient:   getEnvFloat64("TIME_COEFFICIENT", 0.001),
		},
		DatabaseConfig: DatabaseConfig{
			DbUser:     getEnvString("DB_USER", "admin"),
			DbPassword: getEnvString("DB_PASSWORD", "admin"),
			DbHost:     getEnvString("DB_HOST", "localhost"),
			DbPort:     getEnvString("DB_PORT", "5432"),
			DbName:     getEnvString("DB_NAME", "db"),
		},
	}
}
