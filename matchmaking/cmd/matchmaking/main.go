package main

import (
	. "matchmaking/internal"
)

func main() {
	logger.Info("Starting matchmaking service...")

	db := MustGetDb()
	InitDb(db)
	go MatchmakingTicker()
	StartupHttp()
}
