package api

import (
	"cukiller/api/pkg/middleware"
	"log"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const MetricsPort = 6969

func Metrics(enable bool) {
	if !enable {
		return
	}
	router := NewMetricsRouter()
	addr := ":" + strconv.Itoa(MetricsPort)
	if err := router.Run(addr); err != nil {
		log.Fatalf("metrics server error: %v", err)
	}
}

func NewMetricsRouter() *gin.Engine {
	router := gin.New()

	router.Use(middleware.Logging())
	router.Use(gin.Recovery())

	router.GET("/metrics", gin.WrapH(promhttp.Handler()))

	return router
}
