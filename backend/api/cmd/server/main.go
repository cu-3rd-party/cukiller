package main

import (
	"context"
	"log"

	"cukiller/api/internal/api"
	"cukiller/api/internal/config"
	"cukiller/api/pkg/db"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	dbConn, err := db.Open(context.Background(), cfg.DbURL())
	if err != nil {
		log.Fatalf("failed to connect to database: %v", err)
	}
	defer func() {
		if err := dbConn.Close(); err != nil {
			log.Printf("failed to close database: %v", err)
		}
	}()

	go api.Metrics(cfg.EnableMetrics)

	router := api.NewRouter(api.Config{
		BasePath:    cfg.APIBasePath,
		HealthCheck: db.GetHealthcheck(dbConn),
	})

	addr := ":" + cfg.Port
	log.Printf("calendar api listening on %s", addr)
	if err := router.Run(addr); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
