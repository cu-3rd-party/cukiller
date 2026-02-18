package api

import (
	"context"
	"cukiller/api/pkg/db/store"
)

// Config controls HTTP API routing behavior.
type Config struct {
	BasePath string

	HealthCheck func(context.Context) bool
	// Database stores
	User           *store.UserStore
	Chat           *store.ChatStore
	Game           *store.GameStore
	KillEvent      *store.KillEventStore
	PendingProfile *store.PendingProfileStore
	Player         *store.PlayerStore
}
