package tests

import (
	"bytes"
	"cukiller/api/internal/http"
	. "cukiller/api/pkg/db"
	"cukiller/api/pkg/db/store"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

type playerResponse struct {
	Id     string `json:"id"`
	UserId string `json:"user_id"`
	GameId string `json:"game_id"`
	Rating int    `json:"rating"`
}

type playerListResponse struct {
	Items  []playerResponse `json:"items"`
	Limit  int              `json:"limit"`
	Offset int              `json:"offset"`
}

func createTestGame(t *testing.T, gameStore store.GameStore) uuid.UUID {
	t.Helper()
	game := store.DefaultGame()
	game.Id = uuid.New()
	game.Name = fmt.Sprintf("test_game_%s", game.Id.String())
	assert.True(t, gameStore.Create(t.Context(), &game))
	return game.Id
}

func TestPlayersEndpoints(t *testing.T) {
	gin.SetMode(gin.TestMode)
	db := SetupDb(t)

	userStore := store.NewUserStore(db)
	gameStore := store.NewGameStore(db)
	playerStore := store.NewPlayerStore(db)
	router := api.NewRouter(api.Config{
		User:   userStore,
		Game:   gameStore,
		Player: playerStore,
	})

	gameId := createTestGame(t, gameStore)
	user := createTestUser(t, &userStore, time.Now().UnixNano(), "active", false, false)

	createPayload := map[string]any{
		"user_id": user.Id.String(),
		"game_id": gameId.String(),
		"rating":  750,
	}
	body, err := json.Marshal(createPayload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	createReq := httptest.NewRequest(http.MethodPost, "/players", bytes.NewReader(body))
	createReq.Header.Set("Content-Type", "application/json")
	createRec := httptest.NewRecorder()
	router.ServeHTTP(createRec, createReq)

	assert.Equal(t, http.StatusCreated, createRec.Code)
	var createdPlayer playerResponse
	assert.NoError(t, json.Unmarshal(createRec.Body.Bytes(), &createdPlayer))
	assert.Equal(t, user.Id.String(), createdPlayer.UserId)
	assert.Equal(t, gameId.String(), createdPlayer.GameId)
	assert.Equal(t, 750, createdPlayer.Rating)
	assert.NotEmpty(t, createdPlayer.Id)
	defer func() {
		_ = playerStore.Delete(t.Context(), uuid.MustParse(createdPlayer.Id))
		_ = gameStore.Delete(t.Context(), gameId)
		_ = userStore.Delete(t.Context(), user.Id)
	}()

	getReq := httptest.NewRequest(http.MethodGet, "/players/"+createdPlayer.Id, nil)
	getRec := httptest.NewRecorder()
	router.ServeHTTP(getRec, getReq)
	assert.Equal(t, http.StatusOK, getRec.Code)

	updatePayload := map[string]any{"rating": 880}
	updateBody, err := json.Marshal(updatePayload)
	if err != nil {
		t.Fatalf("failed to marshal update: %v", err)
	}
	updateReq := httptest.NewRequest(http.MethodPatch, "/players/"+createdPlayer.Id, bytes.NewReader(updateBody))
	updateReq.Header.Set("Content-Type", "application/json")
	updateRec := httptest.NewRecorder()
	router.ServeHTTP(updateRec, updateReq)
	assert.Equal(t, http.StatusOK, updateRec.Code)

	var updatedPlayer playerResponse
	assert.NoError(t, json.Unmarshal(updateRec.Body.Bytes(), &updatedPlayer))
	assert.Equal(t, 880, updatedPlayer.Rating)

	listReq := httptest.NewRequest(
		http.MethodGet,
		fmt.Sprintf("/players?game_id=%s&user_id=%s&limit=10&offset=0", gameId.String(), user.Id.String()),
		nil,
	)
	listRec := httptest.NewRecorder()
	router.ServeHTTP(listRec, listReq)
	assert.Equal(t, http.StatusOK, listRec.Code)

	var listResp playerListResponse
	assert.NoError(t, json.Unmarshal(listRec.Body.Bytes(), &listResp))
	assert.Len(t, listResp.Items, 1)
	assert.Equal(t, createdPlayer.Id, listResp.Items[0].Id)
	assert.Equal(t, 10, listResp.Limit)
	assert.Equal(t, 0, listResp.Offset)

	countReq := httptest.NewRequest(http.MethodGet, "/players/count?game_id="+gameId.String(), nil)
	countRec := httptest.NewRecorder()
	router.ServeHTTP(countRec, countReq)
	assert.Equal(t, http.StatusOK, countRec.Code)

	var countResp struct {
		Total int `json:"total"`
	}
	assert.NoError(t, json.Unmarshal(countRec.Body.Bytes(), &countResp))
	assert.Equal(t, 1, countResp.Total)
}
