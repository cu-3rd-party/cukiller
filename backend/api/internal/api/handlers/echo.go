package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func Echo(c *gin.Context) {
	message := c.Query("message")
	if message == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "message query parameter is required"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": message})
}
