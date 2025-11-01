package main

func main() {
	logger.Info("Starting matchmaking service...")

	//restoreMatchmakingQueue()
	go matchmakingTicker()
	startupHttp()
}
