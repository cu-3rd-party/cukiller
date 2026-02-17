package shared

import (
	"log"
	"os"
)

var logger = GetLogger(LogLevelDebug)

type LogLevel uint8

const (
	LogLevelDebug LogLevel = iota
	LogLevelInfo
	LogLevelWarn
	LogLevelError
	LogLevelNone
)

func ParseLogLevel(value string) LogLevel {
	var ret LogLevel
	switch value {
	case "DEBUG":
		ret = LogLevelDebug
	case "INFO":
		ret = LogLevelInfo
	case "WARN":
		ret = LogLevelWarn
	case "ERROR":
		ret = LogLevelError
	case "NONE":
		ret = LogLevelNone
	default:
		ret = LogLevelInfo
	}
	return ret
}

func GetLogger(level LogLevel) *Logger {
	return &Logger{
		LogLevel: level,
		Logger:   log.New(os.Stdout, "", log.LstdFlags),
	}
}

type Logger struct {
	LogLevel
	*log.Logger
}

func (l *Logger) Info(format string, v ...interface{}) {
	if l.LogLevel > LogLevelInfo {
		return
	}
	l.Printf("INFO:\t"+format, v...)
}

func (l *Logger) Warn(format string, v ...interface{}) {
	if l.LogLevel > LogLevelWarn {
		return
	}
	l.Printf("WARN:\t"+format, v...)
}

func (l *Logger) Error(format string, v ...interface{}) {
	if l.LogLevel > LogLevelError {
		return
	}
	l.Printf("ERROR:\t"+format, v...)
}

func (l *Logger) Debug(format string, v ...interface{}) {
	if l.LogLevel > LogLevelDebug {
		return
	}
	l.Printf("DEBUG:\t"+format, v...)
}
