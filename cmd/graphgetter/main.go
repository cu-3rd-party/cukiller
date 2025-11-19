package main

import (
	. "cukiller/internal/graphgetter"
	"cukiller/internal/shared"
)

var logger = shared.GetLogger(shared.LogLevelDebug)

func main() {
	logger.Info("Starting service...")

	InitDb()
	StartupHttp()
}
