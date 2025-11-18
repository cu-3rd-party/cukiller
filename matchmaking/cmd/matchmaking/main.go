package main

import (
	"log"
	. "matchmaking/internal/matchmaking"
	"matchmaking/internal/shared"
	"os"
)

var logger = &shared.Logger{
	LogLevel: shared.LogLevelDebug,
	Logger:   log.New(os.Stdout, "", log.LstdFlags),
}

func main() {
	logger.Info("Starting matchmaking service...")

	InitDb()
	go MatchmakingTicker()
	StartupHttp()
}
