package tests

import (
	"bytes"
	"cukiller/api/internal/http"
	"cukiller/api/pkg/db"
	"cukiller/api/pkg/db/store"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

type gameResponse struct {
	Id        uuid.UUID  `json:"id"`
	Name      string     `json:"name"`
	StartDate *time.Time `json:"start_date"`
	EndDate   *time.Time `json:"end_date"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
}

type gameListResponse struct {
	Items  []gameResponse `json:"items"`
	Limit  int            `json:"limit"`
	Offset int            `json:"offset"`
}

type countResponse struct {
	Total int `json:"total"`
}

type userResponse struct {
	Id uuid.UUID `json:"id"`
}

type userListResponse struct {
	Items  []userResponse `json:"items"`
	Limit  int            `json:"limit"`
	Offset int            `json:"offset"`
}

func TestGamesCreateGetUpdate(t *testing.T) {
	gin.SetMode(gin.TestMode)
	dbConn := db.SetupDb(t)

	gameStore := store.NewGameStore(dbConn)
	router := api.NewRouter(api.Config{
		Game:   gameStore,
		User:   store.NewUserStore(dbConn),
		Player: store.NewPlayerStore(dbConn),
	})

	startDate := time.Now().UTC().Truncate(time.Second)
	payload := map[string]any{
		"name":       "integration-game",
		"start_date": startDate,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/games", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusCreated, rec.Code)

	var created gameResponse
	assert.NoError(t, json.Unmarshal(rec.Body.Bytes(), &created))
	assert.Equal(t, payload["name"], created.Name)
	assert.NotEqual(t, uuid.Nil, created.Id)

	defer gameStore.Delete(t.Context(), created.Id)

	getReq := httptest.NewRequest(http.MethodGet, "/games/"+created.Id.String(), nil)
	getRec := httptest.NewRecorder()
	router.ServeHTTP(getRec, getReq)
	assert.Equal(t, http.StatusOK, getRec.Code)

	var fetched gameResponse
	assert.NoError(t, json.Unmarshal(getRec.Body.Bytes(), &fetched))
	assert.Equal(t, created.Id, fetched.Id)

	endDate := time.Now().UTC().Add(2 * time.Hour).Truncate(time.Second)
	updatePayload := map[string]any{
		"name":     "integration-game-updated",
		"end_date": endDate,
	}
	updateBody, err := json.Marshal(updatePayload)
	if err != nil {
		t.Fatalf("failed to marshal update request: %v", err)
	}

	updateReq := httptest.NewRequest(http.MethodPatch, "/games/"+created.Id.String(), bytes.NewReader(updateBody))
	updateReq.Header.Set("Content-Type", "application/json")
	updateRec := httptest.NewRecorder()
	router.ServeHTTP(updateRec, updateReq)
	assert.Equal(t, http.StatusOK, updateRec.Code)

	var updated gameResponse
	assert.NoError(t, json.Unmarshal(updateRec.Body.Bytes(), &updated))
	assert.Equal(t, updatePayload["name"], updated.Name)
	if assert.NotNil(t, updated.EndDate) {
		assert.True(t, updated.EndDate.Equal(endDate))
	}
}

func TestGamesListCountAndActive(t *testing.T) {
	gin.SetMode(gin.TestMode)
	dbConn := db.SetupDb(t)

	gameStore := store.NewGameStore(dbConn)
	router := api.NewRouter(api.Config{
		Game:   gameStore,
		User:   store.NewUserStore(dbConn),
		Player: store.NewPlayerStore(dbConn),
	})

	scheduled := store.DefaultGame()
	scheduled.Name = "scheduled"
	assert.True(t, gameStore.Create(t.Context(), &scheduled))
	defer gameStore.Delete(t.Context(), scheduled.Id)

	active := store.DefaultGame()
	active.Name = "active"
	active.StartDate = sqlNullTime(time.Now().UTC().Add(48 * time.Hour))
	assert.True(t, gameStore.Create(t.Context(), &active))
	defer gameStore.Delete(t.Context(), active.Id)

	countBeforeReq := httptest.NewRequest(http.MethodGet, "/games/count?status=completed", nil)
	countBeforeRec := httptest.NewRecorder()
	router.ServeHTTP(countBeforeRec, countBeforeReq)
	assert.Equal(t, http.StatusOK, countBeforeRec.Code)

	var countBefore countResponse
	assert.NoError(t, json.Unmarshal(countBeforeRec.Body.Bytes(), &countBefore))

	completed := store.DefaultGame()
	completed.Name = "completed"
	completed.StartDate = sqlNullTime(time.Now().UTC().Add(-2 * time.Hour))
	completed.EndDate = sqlNullTime(time.Now().UTC().Add(-1 * time.Hour))
	assert.True(t, gameStore.Create(t.Context(), &completed))
	defer gameStore.Delete(t.Context(), completed.Id)

	req := httptest.NewRequest(http.MethodGet, "/games?status=scheduled", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusOK, rec.Code)

	var listResp gameListResponse
	assert.NoError(t, json.Unmarshal(rec.Body.Bytes(), &listResp))
	foundScheduled := false
	for _, item := range listResp.Items {
		if item.Id == scheduled.Id {
			foundScheduled = true
			break
		}
	}
	assert.True(t, foundScheduled)

	countReq := httptest.NewRequest(http.MethodGet, "/games/count?status=completed", nil)
	countRec := httptest.NewRecorder()
	router.ServeHTTP(countRec, countReq)
	assert.Equal(t, http.StatusOK, countRec.Code)

	var countResp countResponse
	assert.NoError(t, json.Unmarshal(countRec.Body.Bytes(), &countResp))
	assert.Equal(t, countBefore.Total+1, countResp.Total)

	activeReq := httptest.NewRequest(http.MethodGet, "/games/active", nil)
	activeRec := httptest.NewRecorder()
	router.ServeHTTP(activeRec, activeReq)
	assert.Equal(t, http.StatusOK, activeRec.Code)

	var activeResp gameResponse
	assert.NoError(t, json.Unmarshal(activeRec.Body.Bytes(), &activeResp))
	assert.Equal(t, active.Id, activeResp.Id)
}

func TestGamesActiveNotFound(t *testing.T) {
	gin.SetMode(gin.TestMode)
	dbConn := db.SetupDb(t)

	router := api.NewRouter(api.Config{
		Game:   store.NewGameStore(dbConn),
		User:   store.NewUserStore(dbConn),
		Player: store.NewPlayerStore(dbConn),
	})

	req := httptest.NewRequest(http.MethodGet, "/games/active", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusNotFound, rec.Code)
}

func TestGameParticipants(t *testing.T) {
	gin.SetMode(gin.TestMode)
	dbConn := db.SetupDb(t)

	gameStore := store.NewGameStore(dbConn)
	userStore := store.NewUserStore(dbConn)
	playerStore := store.NewPlayerStore(dbConn)
	router := api.NewRouter(api.Config{
		Game:   gameStore,
		User:   userStore,
		Player: playerStore,
	})

	game := store.DefaultGame()
	game.Name = "participants-game"
	assert.True(t, gameStore.Create(t.Context(), &game))
	defer gameStore.Delete(t.Context(), game.Id)

	userA := store.DefaultUser()
	userA.TgId = time.Now().UnixNano()
	assert.True(t, userStore.Create(t.Context(), userA))
	defer userStore.Delete(t.Context(), userA.Id)

	userB := store.DefaultUser()
	userB.TgId = time.Now().UnixNano() + 1
	assert.True(t, userStore.Create(t.Context(), userB))
	defer userStore.Delete(t.Context(), userB.Id)

	playerA := store.DefaultPlayer()
	playerA.GameId = game.Id
	playerA.UserId = userA.Id
	assert.True(t, playerStore.Create(t.Context(), &playerA))
	defer playerStore.Delete(t.Context(), playerA.Id)

	playerB := store.DefaultPlayer()
	playerB.GameId = game.Id
	playerB.UserId = userB.Id
	assert.True(t, playerStore.Create(t.Context(), &playerB))
	defer playerStore.Delete(t.Context(), playerB.Id)

	req := httptest.NewRequest(http.MethodGet, "/games/"+game.Id.String()+"/participants", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusOK, rec.Code)

	var listResp userListResponse
	assert.NoError(t, json.Unmarshal(rec.Body.Bytes(), &listResp))
	assert.Len(t, listResp.Items, 2)

	countReq := httptest.NewRequest(http.MethodGet, "/games/"+game.Id.String()+"/participants/count", nil)
	countRec := httptest.NewRecorder()
	router.ServeHTTP(countRec, countReq)
	assert.Equal(t, http.StatusOK, countRec.Code)

	var countResp countResponse
	assert.NoError(t, json.Unmarshal(countRec.Body.Bytes(), &countResp))
	assert.Equal(t, 2, countResp.Total)
}

func sqlNullTime(value time.Time) sql.NullTime {
	return sql.NullTime{Time: value, Valid: true}
}
