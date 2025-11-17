package main

import (
	"log"
	. "matchmaking/internal"
	"os"
)

var logger = &Logger{
	LogLevel: LogLevelDebug,
	Logger:   log.New(os.Stdout, "", log.LstdFlags),
}
