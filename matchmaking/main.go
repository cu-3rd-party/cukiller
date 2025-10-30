package main

func main() {
	logger.Info("Starting matchmaking service...")

	go matchmakingTicker()
	startupHttp()
}
