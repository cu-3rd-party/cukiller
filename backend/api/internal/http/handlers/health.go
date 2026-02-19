package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

type Healthcheck struct {
	Method func(context.Context) bool
}

func (h *Healthcheck) Health(c *gin.Context) {
	if ok := h.Method(c); ok {
		c.JSON(http.StatusOK, gin.H{"status": "healthy", "timestamp": time.Now().Format("2025-03-13T15:41:12.111Z")})
		return
	}
	c.JSON(http.StatusInternalServerError, gin.H{"status": "unhealthy", "timestamp": time.Now().Format("2025-03-13T15:41:12.111Z")})
}
