package main

func main() {
	logger.Info("Starting matchmaking service...")

	db := MustGetDb()
	initDb(db)
	//restoreMatchmakingQueue()
	go matchmakingTicker()
	startupHttp()
}
