package main

import (
	"context"
	"cukiller/api/pkg/db/store"
	"os"
	"strings"

	"cukiller/api/internal/config"
	"cukiller/api/internal/http"
	"cukiller/api/pkg/db"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatal().Err(err).Msg("failed to load config")
	}

	level, err := zerolog.ParseLevel(strings.ToLower(cfg.LogLevel))
	if err != nil {
		level = zerolog.InfoLevel
	}
	zerolog.SetGlobalLevel(level)
	log.Logger = zerolog.New(zerolog.ConsoleWriter{Out: os.Stdout}).With().Timestamp().Logger()

	dbConn, err := db.Open(context.Background(), cfg.DbURL())
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to database")
	}
	defer func() {
		if err := dbConn.Close(); err != nil {
			log.Error().Err(err).Msg("failed to close database")
		}
	}()

	userStore := store.NewUserStore(dbConn)
	chatStore := store.NewChatStore(dbConn)
	gameStore := store.NewGameStore(dbConn)
	killEventStore := store.NewKillEventStore(dbConn)
	pendingProfileStore := store.NewPendingProfileStore(dbConn)
	playerStore := store.NewPlayerStore(dbConn)

	go api.Metrics(cfg.EnableMetrics, api.MetricsConfig{
		User:   &userStore,
		Game:   &gameStore,
		Player: &playerStore,
	})

	router := api.NewRouter(api.Config{
		BasePath:       cfg.APIBasePath,
		HealthCheck:    db.GetHealthcheck(dbConn),
		User:           userStore,
		Chat:           chatStore,
		Game:           gameStore,
		KillEvent:      killEventStore,
		PendingProfile: pendingProfileStore,
		Player:         playerStore,
	})

	addr := ":" + cfg.Port
	log.Info().Str("addr", addr).Msg("http listening")
	if err := router.Run(addr); err != nil {
		log.Fatal().Err(err).Msg("server error")
	}
}
