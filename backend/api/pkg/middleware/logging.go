package middleware

import (
	"bytes"
	"io"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
)

// Logging logs basic request/response details with latency.
func Logging() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.FullPath()
		if path == "" {
			path = c.Request.URL.Path
		}

		var bodyPreview string
		if log.Debug().Enabled() && c.Request.Body != nil {
			bodyBytes, err := io.ReadAll(c.Request.Body)
			if err == nil {
				const maxBodySize = 4096
				if len(bodyBytes) > maxBodySize {
					bodyPreview = string(bodyBytes[:maxBodySize]) + "...(truncated)"
				} else {
					bodyPreview = string(bodyBytes)
				}
				c.Request.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
			}
		}

		c.Next()

		latency := time.Since(start)
		status := c.Writer.Status()
		clientIP := c.ClientIP()
		method := c.Request.Method

		log.Info().
			Str("method", method).
			Str("path", path).
			Int("status", status).
			Dur("latency", latency).
			Str("client_ip", clientIP).
			Msg("http request")

		if log.Debug().Enabled() {
			log.Debug().
				Str("method", method).
				Str("path", path).
				Str("body", bodyPreview).
				Int("status", status).
				Dur("latency", latency).
				Str("client_ip", clientIP).
				Msg("http request (advanced)")
		}
	}
}
