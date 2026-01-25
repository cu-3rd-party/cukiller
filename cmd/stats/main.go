package main

import (
	"cukiller/internal/shared"
	. "cukiller/internal/stats"
)

var logger = shared.GetLogger(shared.LogLevelDebug)

func main() {
	logger.Info("Starting stats service...")

	InitDb()
	StartupHttp()
}
