package stats

import "cukiller/stats/internal/shared"

var conf = getConfig()
var logger = shared.GetLogger(conf.LogLevel)

type Config struct {
	Port int
	shared.LogLevel
	shared.ConfigDatabase
}

func getConfig() Config {
	return Config{
		Port:           shared.GetEnvInt("PORT", 8000),
		LogLevel:       shared.ParseLogLevel(shared.GetEnvString("LOGLEVEL", "INFO")),
		ConfigDatabase: shared.GetDbConfig(),
	}
}
