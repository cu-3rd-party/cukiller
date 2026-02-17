package main

import (
	. "cukiller/graphgetter/internal/graphgetter"
	"cukiller/graphgetter/internal/shared"
)

var logger = shared.GetLogger(shared.LogLevelDebug)

func main() {
	logger.Info("Starting service...")

	InitDb()
	StartupHttp()
}
