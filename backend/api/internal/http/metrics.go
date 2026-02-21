package api

import (
	"context"
	"cukiller/api/pkg/db/store"
	"cukiller/api/pkg/middleware"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog/log"
)

const MetricsPort = 6969

type MetricsConfig struct {
	User   *store.UserStore
	Game   *store.GameStore
	Player *store.PlayerStore
}

var (
	usersTotal = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: "cukiller",
			Subsystem: "db",
			Name:      "users_total",
			Help:      "Total number of users in the database.",
		},
		[]string{"status"},
	)
	gamesTotal = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: "cukiller",
			Subsystem: "db",
			Name:      "games_total",
			Help:      "Total number of games in the database.",
		},
		[]string{"status"},
	)
	playersTotal = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Namespace: "cukiller",
			Subsystem: "db",
			Name:      "players_total",
			Help:      "Total number of players in the database.",
		},
		[]string{"scope"},
	)
)

func init() {
	prometheus.MustRegister(usersTotal, gamesTotal, playersTotal)
}

func Metrics(enable bool, cfg MetricsConfig) {
	if !enable {
		return
	}
	router := NewMetricsRouter(cfg)
	addr := ":" + strconv.Itoa(MetricsPort)
	if err := router.Run(addr); err != nil {
		log.Fatal().Err(err).Msg("metrics server error")
	}
}

func NewMetricsRouter(cfg MetricsConfig) *gin.Engine {
	router := gin.New()

	router.Use(middleware.Logging())
	router.Use(gin.Recovery())

	router.GET("/metrics", metricsHandler(cfg))

	return router
}

func metricsHandler(cfg MetricsConfig) gin.HandlerFunc {
	handler := promhttp.Handler()
	return func(c *gin.Context) {
		updateDBMetrics(c.Request.Context(), cfg)
		handler.ServeHTTP(c.Writer, c.Request)
	}
}

func updateDBMetrics(ctx context.Context, cfg MetricsConfig) {
	if cfg.User != nil {
		updateUserMetrics(ctx, cfg.User)
	}
	if cfg.Game != nil {
		updateGameMetrics(ctx, cfg.Game)
	}
	if cfg.Player != nil {
		updatePlayerMetrics(ctx, cfg.Game, cfg.Player)
	}
}

func updateUserMetrics(ctx context.Context, users *store.UserStore) {
	total, ok := users.Count(ctx, "")
	if ok {
		usersTotal.WithLabelValues("total").Set(float64(total))
	}
	statuses := []string{"active", "pending", "confirmed", "rejected", "banned"}
	for _, status := range statuses {
		count, ok := users.Count(ctx, status)
		if ok {
			usersTotal.WithLabelValues(status).Set(float64(count))
		}
	}
}

func updateGameMetrics(ctx context.Context, games *store.GameStore) {
	total, ok := games.Count(ctx, nil)
	if ok {
		gamesTotal.WithLabelValues("total").Set(float64(total))
	}
	statuses := []string{"scheduled", "active", "completed"}
	for _, status := range statuses {
		status := status
		count, ok := games.Count(ctx, &status)
		if ok {
			gamesTotal.WithLabelValues(status).Set(float64(count))
		}
	}
}

func updatePlayerMetrics(ctx context.Context, games *store.GameStore, players *store.PlayerStore) {
	total, ok := players.Count(ctx, store.PlayerFilters{})
	if ok {
		playersTotal.WithLabelValues("total").Set(float64(total))
	}
	if games == nil {
		return
	}
	active, ok := games.GetActive(ctx)
	if !ok || active == nil {
		playersTotal.WithLabelValues("active_game").Set(0)
		return
	}
	activeCount, ok := players.Count(ctx, store.PlayerFilters{GameId: &active.Id})
	if ok {
		playersTotal.WithLabelValues("active_game").Set(float64(activeCount))
	}
}
