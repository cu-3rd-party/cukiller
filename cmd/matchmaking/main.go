package main

import (
	. "cukiller/internal/matchmaking"
	"cukiller/internal/shared"
)

var logger = shared.GetLogger(shared.LogLevelDebug)

func main() {
	logger.Info("Starting service...")

	InitDb()
	go MatchmakingTicker()
	StartupHttp()
}
