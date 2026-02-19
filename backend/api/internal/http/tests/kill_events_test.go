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

type killEventResponse struct {
	Id              uuid.UUID `json:"id"`
	GameId          uuid.UUID `json:"game_id"`
	KillerId        uuid.UUID `json:"killer_id"`
	VictimId        uuid.UUID `json:"victim_id"`
	Status          string    `json:"status"`
	IsApproved      bool      `json:"is_approved"`
	KillerConfirmed bool      `json:"killer_confirmed"`
	VictimConfirmed bool      `json:"victim_confirmed"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

type killEventListResponse struct {
	Items  []killEventResponse `json:"items"`
	Limit  int                 `json:"limit"`
	Offset int                 `json:"offset"`
}

func setupKillEventTest(t *testing.T) (*gin.Engine, store.UserStore, store.GameStore, store.KillEventStore) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	db := SetupDb(t)

	userStore := store.NewUserStore(db)
	gameStore := store.NewGameStore(db)
	killEventStore := store.NewKillEventStore(db)

	router := api.NewRouter(api.Config{
		User:      userStore,
		Game:      gameStore,
		KillEvent: killEventStore,
		Chat:      store.NewChatStore(db),
		Player:    store.NewPlayerStore(db),
	})

	return router, userStore, gameStore, killEventStore
}

func createTestUser(t *testing.T, userStore store.UserStore, tgId int64) store.User {
	t.Helper()
	entry := store.User{
		Id:                 uuid.New(),
		TgId:               tgId,
		Status:             "active",
		AllowHuggingOnKill: false,
	}
	ok := userStore.Create(t.Context(), &entry)
	assert.True(t, ok)
	return entry
}

func createTestGame(t *testing.T, gameStore store.GameStore, name string) store.Game {
	t.Helper()
	entry := store.Game{
		Id:   uuid.New(),
		Name: name,
	}
	ok := gameStore.Create(t.Context(), &entry)
	assert.True(t, ok)
	return entry
}

func TestKillEventCreateGetUpdateListBulk(t *testing.T) {
	router, userStore, gameStore, killEventStore := setupKillEventTest(t)

	base := time.Now().UnixNano()
	killer := createTestUser(t, userStore, base+1)
	victim := createTestUser(t, userStore, base+2)
	game := createTestGame(t, gameStore, fmt.Sprintf("game-%d", base))

	createPayload := map[string]any{
		"game_id":   game.Id,
		"killer_id": killer.Id,
		"victim_id": victim.Id,
	}
	body, err := json.Marshal(createPayload)
	if err != nil {
		t.Fatalf("failed to marshal create body: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/kill-events", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusCreated, rec.Code)

	var created killEventResponse
	err = json.NewDecoder(rec.Body).Decode(&created)
	assert.NoError(t, err)
	assert.Equal(t, game.Id, created.GameId)
	assert.Equal(t, killer.Id, created.KillerId)
	assert.Equal(t, victim.Id, created.VictimId)
	assert.Equal(t, "pending", created.Status)

	getReq := httptest.NewRequest(http.MethodGet, "/kill-events/"+created.Id.String(), nil)
	getRec := httptest.NewRecorder()
	router.ServeHTTP(getRec, getReq)
	assert.Equal(t, http.StatusOK, getRec.Code)

	var fetched killEventResponse
	err = json.NewDecoder(getRec.Body).Decode(&fetched)
	assert.NoError(t, err)
	assert.Equal(t, created.Id, fetched.Id)

	updatePayload := map[string]any{
		"status":           "confirmed",
		"killer_confirmed": true,
	}
	updateBody, err := json.Marshal(updatePayload)
	if err != nil {
		t.Fatalf("failed to marshal update body: %v", err)
	}
	updateReq := httptest.NewRequest(http.MethodPatch, "/kill-events/"+created.Id.String(), bytes.NewReader(updateBody))
	updateReq.Header.Set("Content-Type", "application/json")
	updateRec := httptest.NewRecorder()
	router.ServeHTTP(updateRec, updateReq)
	assert.Equal(t, http.StatusOK, updateRec.Code)

	var updated killEventResponse
	err = json.NewDecoder(updateRec.Body).Decode(&updated)
	assert.NoError(t, err)
	assert.Equal(t, "confirmed", updated.Status)
	assert.True(t, updated.KillerConfirmed)

	listReq := httptest.NewRequest(http.MethodGet, "/kill-events?game_id="+game.Id.String(), nil)
	listRec := httptest.NewRecorder()
	router.ServeHTTP(listRec, listReq)
	assert.Equal(t, http.StatusOK, listRec.Code)

	var listResp killEventListResponse
	err = json.NewDecoder(listRec.Body).Decode(&listResp)
	assert.NoError(t, err)
	assert.GreaterOrEqual(t, len(listResp.Items), 1)

	second := store.KillEvent{
		Id:       uuid.New(),
		GameId:   game.Id,
		KillerId: killer.Id,
		VictimId: victim.Id,
		Status:   "pending",
	}
	ok := killEventStore.Create(t.Context(), &second)
	assert.True(t, ok)

	bulkPayload := map[string]any{
		"ids": []uuid.UUID{created.Id, second.Id},
		"update": map[string]any{
			"status": "rejected",
		},
	}
	bulkBody, err := json.Marshal(bulkPayload)
	if err != nil {
		t.Fatalf("failed to marshal bulk body: %v", err)
	}
	bulkReq := httptest.NewRequest(http.MethodPost, "/kill-events/bulk-update", bytes.NewReader(bulkBody))
	bulkReq.Header.Set("Content-Type", "application/json")
	bulkRec := httptest.NewRecorder()
	router.ServeHTTP(bulkRec, bulkReq)
	assert.Equal(t, http.StatusOK, bulkRec.Code)

	var bulkResp struct {
		Count int64 `json:"count"`
	}
	err = json.NewDecoder(bulkRec.Body).Decode(&bulkResp)
	assert.NoError(t, err)
	assert.Equal(t, int64(2), bulkResp.Count)

	updatedFirst, ok := killEventStore.GetById(t.Context(), created.Id)
	assert.True(t, ok)
	assert.Equal(t, "rejected", updatedFirst.Status)
}
