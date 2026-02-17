package main

import (
	"cukiller/stats/internal/shared"
	. "cukiller/stats/internal/stats"
)

var logger = shared.GetLogger(shared.LogLevelDebug)

func main() {
	logger.Info("Starting stats service...")

	InitDb()
	StartupHttp()
}
