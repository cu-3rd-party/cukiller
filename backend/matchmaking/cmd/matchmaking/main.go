package main

import (
	. "cukiller/matchmaking/internal/matchmaking"
	"cukiller/matchmaking/internal/shared"
)

var logger = shared.GetLogger(shared.LogLevelDebug)

func main() {
	logger.Info("Starting service...")

	InitDb()
	go TickerMatchmaking()
	StartupHttp()
}
