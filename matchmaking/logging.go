package main

import (
	"log"
	"os"
)

type Logger struct {
	LogLevel
	*log.Logger
}

var logger = &Logger{
	conf.LogLevel,
	log.New(os.Stdout, "", log.LstdFlags),
}

func (l *Logger) Info(format string, v ...interface{}) {
	if l.LogLevel > LogLevelInfo {
		return
	}
	l.Printf("INFO: "+format, v...)
}

func (l *Logger) Warn(format string, v ...interface{}) {
	if l.LogLevel > LogLevelWarn {
		return
	}
	l.Printf("WARN: "+format, v...)
}

func (l *Logger) Error(format string, v ...interface{}) {
	if l.LogLevel > LogLevelError {
		return
	}
	l.Printf("ERROR: "+format, v...)
}

func (l *Logger) Debug(format string, v ...interface{}) {
	if l.LogLevel > LogLevelDebug {
		return
	}
	l.Printf("DEBUG: "+format, v...)
}
