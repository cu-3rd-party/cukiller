package store

import (
	"context"
	"database/sql"
	"testing"
	"time"

	"cukiller/api/pkg/db"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

func seedKillEventDeps(t *testing.T) (UserStore, User, User, uuid.UUID) {
	userStore := UserStore{db: db.SetupDb(t)}

	killer := DefaultUser()
	killer.Id = uuid.New()
	killer.TgId = uint64(time.Now().UnixNano())
	assert.True(t, userStore.Create(t.Context(), &killer))

	victim := DefaultUser()
	victim.Id = uuid.New()
	victim.TgId = uint64(time.Now().UnixNano() + 1)
	assert.True(t, userStore.Create(t.Context(), &victim))

	gameId := uuid.New()
	assert.NoError(t, insertGame(t.Context(), userStore.db, gameId, "test_game"))

	return userStore, killer, victim, gameId
}

func cleanupKillEventDeps(t *testing.T, userStore UserStore, killer User, victim User, gameId uuid.UUID) {
	_, _ = userStore.db.ExecContext(t.Context(), `DELETE FROM games WHERE id = $1`, gameId)
	userStore.Delete(t.Context(), killer.Id)
	userStore.Delete(t.Context(), victim.Id)
}

func insertGame(ctx context.Context, db *sql.DB, id uuid.UUID, name string) error {
	_, err := db.ExecContext(
		ctx,
		`INSERT INTO games (id, name) VALUES ($1, $2)`,
		id,
		name,
	)
	return err
}

func TestKillEventStore_CreateGet(t *testing.T) {
	userStore, killer, victim, gameId := seedKillEventDeps(t)
	store := KillEventStore{db: userStore.db}

	entry := DefaultKillEvent()
	entry.Id = uuid.New()
	entry.GameId = gameId
	entry.KillerId = killer.Id
	entry.VictimId = victim.Id
	entry.Status = "pending"

	assert.True(t, store.Create(t.Context(), &entry))
	got, ok := store.GetById(t.Context(), entry.Id)
	assert.True(t, ok)
	if assert.NotNil(t, got) {
		assert.Equal(t, entry.Id, got.Id)
	}

	// cleanup
	store.Delete(t.Context(), entry.Id)
	_, ok = store.GetById(t.Context(), entry.Id)
	assert.False(t, ok)
	cleanupKillEventDeps(t, userStore, killer, victim, gameId)
}

func TestKillEventStore_CreateUpdateGet(t *testing.T) {
	userStore, killer, victim, gameId := seedKillEventDeps(t)
	store := KillEventStore{db: userStore.db}

	entry := DefaultKillEvent()
	entry.Id = uuid.New()
	entry.GameId = gameId
	entry.KillerId = killer.Id
	entry.VictimId = victim.Id
	entry.Status = "pending"
	assert.True(t, store.Create(t.Context(), &entry))

	now := time.Now()
	entry.KillerConfirmed = true
	entry.KillerConfirmedAt = sql.NullTime{Time: now, Valid: true}
	entry.Status = "confirmed"
	assert.True(t, store.Update(t.Context(), &entry))

	got, ok := store.GetById(t.Context(), entry.Id)
	assert.True(t, ok)
	if assert.NotNil(t, got) {
		assert.Equal(t, true, got.KillerConfirmed)
		assert.True(t, got.KillerConfirmedAt.Valid)
		assert.Equal(t, "confirmed", got.Status)
	}

	// cleanup
	store.Delete(t.Context(), entry.Id)
	_, ok = store.GetById(t.Context(), entry.Id)
	assert.False(t, ok)
	cleanupKillEventDeps(t, userStore, killer, victim, gameId)
}
