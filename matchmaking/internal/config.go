package internal

import (
	"log"
	"os"
	"strconv"
)

var conf = getConfig()

type Config struct {
	Port      int
	BotUrl    string
	SecretKey string
	LogLevel
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

var confLogger = &Logger{
	LogLevelDebug,
	log.New(os.Stdout, "", log.LstdFlags),
}

// getEnvInt returns environment variable value or default if not set or invalid
func getEnvInt(key string, defaultValue int) int {
	valueStr := os.Getenv(key)
	if valueStr == "" {
		confLogger.Warn("Environment variable %s not set, using default: %d", key, defaultValue)
		return defaultValue
	}

	value, err := strconv.Atoi(valueStr)
	if err != nil {
		confLogger.Warn("Failed to parse %s=%q, using default: %d", key, valueStr, defaultValue)
		return defaultValue
	}

	confLogger.Info("Loaded %s=%d", key, value)
	return value
}

// getEnvString returns environment variable value or default if not set or invalid
func getEnvString(key string, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		confLogger.Warn("Environment variable %s not set, using default: %d", key, defaultValue)
		return defaultValue
	}

	confLogger.Info("Loaded %s=%d", key, value)
	return value
}

// getEnvFloat64 returns environment variable value or default if not set or invalid
func getEnvFloat64(key string, defaultValue float64) float64 {
	valueStr := os.Getenv(key)
	if valueStr == "" {
		confLogger.Warn("Environment variable %s not set, using default: %d", key, defaultValue)
		return defaultValue
	}

	value, err := strconv.ParseFloat(valueStr, 64)
	if err != nil {
		confLogger.Warn("Failed to parse %s=%q, using default: %d", key, valueStr, defaultValue)
		return defaultValue
	}

	confLogger.Info("Loaded %s=%d", key, value)
	return value
}

type LogLevel uint8

const (
	LogLevelDebug LogLevel = iota
	LogLevelInfo
	LogLevelWarn
	LogLevelError
	LogLevelNone
)

func parseLogLevel(key string, defaultValue string) LogLevel {
	var ret LogLevel
	switch getEnvString(key, defaultValue) {
	case "DEBUG":
		ret = LogLevelDebug
	case "INFO":
		ret = LogLevelInfo
	case "WARN":
		ret = LogLevelWarn
	case "ERROR":
		ret = LogLevelError
	case "NONE":
		ret = LogLevelNone
	default:
		ret = LogLevelInfo
	}
	return ret
}

func getConfig() Config {
	return Config{
		Port:      getEnvInt("PORT", 6543),
		BotUrl:    getEnvString("BOT_URL", "http://localhost:8000"),
		SecretKey: getEnvString("SECRET_KEY", ""),
		LogLevel:  parseLogLevel("LOGLEVEL", "INFO"),
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
			DbUser:     getEnvString("POSTGRES_USER", "admin"),
			DbPassword: getEnvString("POSTGRES_PASSWORD", "admin"),
			DbHost:     getEnvString("POSTGRES_HOST", "localhost"),
			DbPort:     getEnvString("POSTGRES_PORT", "5432"),
			DbName:     getEnvString("POSTGRES_DB", "db"),
		},
	}
}
