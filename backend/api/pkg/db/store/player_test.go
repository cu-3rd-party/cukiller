package store

import (
	"cukiller/api/pkg/db"
	"database/sql"
	"fmt"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

func createTestGame(t *testing.T, dbConn *sql.DB) uuid.UUID {
	t.Helper()
	gameId := uuid.New()
	err := dbConn.QueryRowContext(
		t.Context(),
		`INSERT INTO games (id, name) VALUES ($1, $2) RETURNING id`,
		gameId,
		fmt.Sprintf("test_game_%s", gameId.String()),
	).Scan(&gameId)
	assert.Nil(t, err)
	return gameId
}

func createTestUser(t *testing.T, store UserStore) User {
	t.Helper()
	user := DefaultUser()
	user.Id = uuid.New()
	user.TgId = uint64(time.Now().UnixNano())
	user.TgUsername = fmt.Sprintf("test_user_%d", user.TgId)
	assert.True(t, store.Create(t.Context(), &user))
	return user
}

func deleteTestGame(t *testing.T, dbConn *sql.DB, gameId uuid.UUID) {
	t.Helper()
	_, err := dbConn.ExecContext(t.Context(), `DELETE FROM games WHERE id = $1`, gameId)
	assert.Nil(t, err)
}

func TestPlayerStore_CreateGet(t *testing.T) {
	store := PlayerStore{db: db.SetupDb(t)}
	userStore := UserStore{db: store.db}

	gameId := createTestGame(t, store.db)
	user := createTestUser(t, userStore)

	player := DefaultPlayer()
	player.Id = uuid.New()
	player.GameId = gameId
	player.UserId = user.Id
	player.Rating = 750

	assert.True(t, store.Create(t.Context(), &player))
	got, ok := store.GetByUserIdAndGameId(t.Context(), user.Id, gameId)
	assert.True(t, ok)
	assert.EqualValues(t, player.UserId, got.UserId)

	// cleanup
	store.Delete(t.Context(), got.Id)
	deleteTestGame(t, store.db, gameId)
	userStore.Delete(t.Context(), user.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}

func TestPlayerStore_CreateUpdateGet(t *testing.T) {
	store := PlayerStore{db: db.SetupDb(t)}
	userStore := UserStore{db: store.db}

	gameId := createTestGame(t, store.db)
	user := createTestUser(t, userStore)

	player := DefaultPlayer()
	player.Id = uuid.New()
	player.GameId = gameId
	player.UserId = user.Id
	player.Rating = 600

	assert.True(t, store.Create(t.Context(), &player))

	player.Rating = 820
	assert.True(t, store.Update(t.Context(), &player))
	got, ok := store.GetById(t.Context(), player.Id)
	assert.True(t, ok)
	assert.Equal(t, 820, got.Rating)

	// cleanup
	store.Delete(t.Context(), got.Id)
	deleteTestGame(t, store.db, gameId)
	userStore.Delete(t.Context(), user.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}
