package api

import (
	"cukiller/api/internal/api/handlers"
	"cukiller/api/pkg/middleware"

	"github.com/gin-gonic/gin"
)

// NewRouter builds and configures the HTTP router.
func NewRouter(cfg Config) *gin.Engine {
	if cfg.BasePath == "" {
		cfg.BasePath = "/"
	}

	router := gin.New()
	router.Use(middleware.Logging())
	router.Use(middleware.Metrics())
	router.Use(gin.Recovery())

	registerRoutes(router, cfg)
	return router
}

func registerRoutes(router *gin.Engine, cfg Config) {
	group := router.Group(cfg.BasePath)

	group.GET("/ping", handlers.Ping)
	group.GET("/echo", handlers.Echo)
}
