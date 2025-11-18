package graphgetter

import (
	"matchmaking/internal/shared"
)

var conf = getConfig()

type Config struct {
	Port      int
	BotUrl    string
	SecretKey string
	shared.LogLevel
	shared.ConfigDatabase
}

func getConfig() Config {
	return Config{
		Port:           shared.GetEnvInt("PORT", 6544),
		SecretKey:      shared.GetEnvString("SECRET_KEY", ""),
		LogLevel:       shared.ParseLogLevel(shared.GetEnvString("LOGLEVEL", "INFO")),
		ConfigDatabase: shared.GetDbConfig(),
	}
}
