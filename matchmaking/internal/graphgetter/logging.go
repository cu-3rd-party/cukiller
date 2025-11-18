package graphgetter

import (
	"log"
	"matchmaking/internal/shared"
)

type Logger struct {
	shared.LogLevel
	*log.Logger
}

var logger = shared.GetLogger(conf.LogLevel)

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
