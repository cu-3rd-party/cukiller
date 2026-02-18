package store

import (
	"cukiller/api/pkg/db"
	"database/sql"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

const TestGameName = "test_game"

func TestGameStore_CreateGet(t *testing.T) {
	store := GameStore{db: db.SetupDb(t)}

	game := DefaultGame()
	game.Name = TestGameName
	game.StartDate = sql.NullTime{Time: time.Now().UTC(), Valid: true}

	assert.True(t, store.Create(t.Context(), &game))
	got, ok := store.GetById(t.Context(), game.Id)
	assert.True(t, ok)
	assert.Equal(t, TestGameName, got.Name)

	// cleanup
	store.Delete(t.Context(), got.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}

func TestGameStore_CreateUpdateGet(t *testing.T) {
	store := GameStore{db: db.SetupDb(t)}

	game := DefaultGame()
	game.Name = TestGameName

	assert.True(t, store.Create(t.Context(), &game))

	const TestOtherGameName = "other_game"
	game.Name = TestOtherGameName
	game.EndDate = sql.NullTime{Time: time.Now().UTC(), Valid: true}
	assert.True(t, store.Update(t.Context(), &game))
	got, ok := store.GetById(t.Context(), game.Id)
	assert.True(t, ok)
	assert.Equal(t, TestOtherGameName, got.Name)
	assert.True(t, got.EndDate.Valid)

	// cleanup
	store.Delete(t.Context(), got.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}
