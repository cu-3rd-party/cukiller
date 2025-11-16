package main

import (
	"log"
	"os"
)

type Logger struct {
	*log.Logger
}

var logger = &Logger{
	log.New(os.Stdout, "", log.LstdFlags),
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

func (l *Logger) Debug(format string, v ...interface{}) {
	l.Printf("DEBUG: "+format, v...)
}
