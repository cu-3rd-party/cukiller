package api

import (
	"cukiller/api/internal/http/handlers"
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

	health := handlers.Healthcheck{Method: cfg.HealthCheck}
	bootstrap := handlers.SystemHandler{
		ChatStore: &cfg.Chat,
		UserStore: &cfg.User,
	}
	games := handlers.GameHandler{
		GameStore:   &cfg.Game,
		UserStore:   &cfg.User,
		PlayerStore: &cfg.Player,
	}
	pendingProfiles := handlers.PendingProfileHandler{
		PendingProfileStore: &cfg.PendingProfile,
		UserStore:           &cfg.User,
	}
	users := handlers.UserHandler{
		UserStore: &cfg.User,
	}
	chats := handlers.ChatHandler{
		ChatStore: &cfg.Chat,
	}
	players := handlers.PlayerHandler{PlayerStore: &cfg.Player}
	killEvents := handlers.KillEventHandler{
		KillEventStore: &cfg.KillEvent,
	}

	group.GET("/ping", handlers.Ping)
	group.GET("/echo", handlers.Echo)
	group.GET("/health/", health.Health)
	group.POST("/system/bootstrap", bootstrap.Bootstrap)
	group.GET("/games", games.ListGames)
	group.POST("/games", games.CreateGame)
	group.GET("/games/count", games.CountGames)
	group.GET("/games/active", games.GetActiveGame)
	group.GET("/games/:game_id", games.GetGameById)
	group.PATCH("/games/:game_id", games.UpdateGame)
	group.GET("/games/:game_id/participants", games.ListGameParticipants)
	group.GET("/games/:game_id/participants/count", games.CountGameParticipants)
	group.GET("/pending-profiles", pendingProfiles.List)
	group.POST("/pending-profiles", pendingProfiles.Create)
	group.GET("/pending-profiles/:pending_id", pendingProfiles.GetById)
	group.PATCH("/pending-profiles/:pending_id", pendingProfiles.Update)
	group.POST("/users/get-or-create", users.GetOrCreate)
	group.GET("/users", users.List)
	group.POST("/users", users.Create)
	group.GET("/users/count", users.Count)
	group.POST("/users/bulk", users.Bulk)
	group.GET("/users/by-tg/:tg_id", users.GetByTgId)
	group.PATCH("/users/by-tg/:tg_id", users.UpdateByTgId)
	group.GET("/users/:user_id", users.GetById)
	group.PATCH("/users/:user_id", users.Update)
	group.GET("/chats/by-key/:key", chats.GetByKey)
	group.GET("/chats/by-id/:chat_id", chats.GetByChatId)
	group.POST("/chats", chats.Create)
	group.GET("/players", players.List)
	group.POST("/players", players.Create)
	group.GET("/players/count", players.Count)
	group.GET("/players/:player_id", players.GetById)
	group.PATCH("/players/:player_id", players.Update)
	group.GET("/kill-events", killEvents.List)
	group.POST("/kill-events", killEvents.Create)
	group.GET("/kill-events/:kill_event_id", killEvents.GetById)
	group.PATCH("/kill-events/:kill_event_id", killEvents.Update)
	group.POST("/kill-events/bulk-update", killEvents.BulkUpdate)
}
