package middleware

import (
	"log"
	"time"

	"github.com/gin-gonic/gin"
)

// Logging logs basic request/response details with latency.
func Logging() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.FullPath()
		if path == "" {
			path = c.Request.URL.Path
		}

		c.Next()

		latency := time.Since(start)
		status := c.Writer.Status()
		clientIP := c.ClientIP()
		method := c.Request.Method

		log.Printf("%s %s %d %s %s", method, path, status, latency, clientIP)
	}
}
