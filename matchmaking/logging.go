package main

import (
	"log"
	"os"
)

type Logger struct {
	*log.Logger
}

var logger = &Logger{
	log.New(os.Stdout, "[MATCHMAKING] ", log.LstdFlags|log.Lshortfile),
}

func (l *Logger) Info(format string, v ...interface{}) {
	l.Printf("INFO: "+format, v...)
}

func (l *Logger) Warn(format string, v ...interface{}) {
	l.Printf("WARN: "+format, v...)
}

func (l *Logger) Error(format string, v ...interface{}) {
	l.Printf("ERROR: "+format, v...)
}
