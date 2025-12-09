package matchmaking

import (
	"cukiller/internal/shared"
	"time"
)

var conf = getConfig()
var logger = shared.GetLogger(conf.LogLevel)

type Config struct {
	Port          int
	BotUrl        string
	SecretKey     string
	ReloadTimeout time.Duration
	ConfigMatchmaking
	shared.LogLevel
	shared.ConfigDatabase
}

// ConfigRatePlayerPair contains coefficients for RatePlayerPair logic
type ConfigRatePlayerPair struct {
	MaxRatingDiff     float64
	CourseCoefficient float64
	GroupCoefficient  float64
	TypeCoefficient   float64
	TimeCoefficient   float64
}

type ConfigMatchmaking struct {
	Interval int

	QualityThreshold        float64
	MatchHistoryCheckDepth  int
	MinPossibleVictimsCount int
	ConfigRatePlayerPair
}

func getConfig() Config {
	return Config{
		Port:          shared.GetEnvInt("PORT", 6543),
		BotUrl:        shared.GetEnvString("BOT_URL", "http://localhost:8000"),
		SecretKey:     shared.GetEnvString("SECRET_KEY", ""),
		LogLevel:      shared.ParseLogLevel(shared.GetEnvString("LOGLEVEL", "INFO")),
		ReloadTimeout: time.Duration(shared.GetEnvFloat64("RELOAD_TIMEOUT", 2.0)) * time.Second,
		ConfigMatchmaking: ConfigMatchmaking{
			Interval:                shared.GetEnvInt("MATCHMAKING_INTERVAL", 5),
			QualityThreshold:        shared.GetEnvFloat64("QUALITY_THRESHOLD", 0.6),
			MatchHistoryCheckDepth:  shared.GetEnvInt("MATCH_HISTORY_CHECK_DEPTH", 3),
			MinPossibleVictimsCount: shared.GetEnvInt("MIN_POSSIBLE_VICTIMS_COUNT", 3),
			ConfigRatePlayerPair: ConfigRatePlayerPair{
				MaxRatingDiff:     shared.GetEnvFloat64("MAX_RATING_DIFF", 1000),
				CourseCoefficient: shared.GetEnvFloat64("COURSE_COEFFICIENT", -0.3),
				GroupCoefficient:  shared.GetEnvFloat64("GROUP_COEFFICIENT", 0.2),
				TypeCoefficient:   shared.GetEnvFloat64("TYPE_COEFFICIENT", -0.6),
				TimeCoefficient:   shared.GetEnvFloat64("TIME_COEFFICIENT", 0.001),
			},
		},
		ConfigDatabase: shared.GetDbConfig(),
	}
}
