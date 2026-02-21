package tests

import (
	"bytes"
	api "cukiller/api/internal/http"
	. "cukiller/api/pkg/db"
	"cukiller/api/pkg/db/store"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

func setupUserRouter(t *testing.T) (*store.UserStore, *gin.Engine) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	db := SetupDb(t)
	userStore := store.NewUserStore(db)
	router := api.NewRouter(api.Config{
		User: userStore,
	})
	return &userStore, router
}

func createTestUser(t *testing.T, userStore *store.UserStore, tgID int64, status string, isAdmin bool, isInGame bool) *store.User {
	t.Helper()
	user := store.DefaultUser()
	user.Id = uuid.New()
	user.TgId = tgID
	user.Status = status
	user.IsAdmin = isAdmin
	user.IsInGame = isInGame
	ok := userStore.Create(t.Context(), user)
	if !ok {
		t.Fatalf("failed to create test user")
	}
	return user
}

func TestUserCreateAndGetById(t *testing.T) {
	userStore, router := setupUserRouter(t)

	payload := map[string]any{
		"tg_id":  time.Now().UnixNano(),
		"status": "active",
	}
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/users", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusCreated, rec.Code)

	var created store.User
	assert.NoError(t, json.NewDecoder(rec.Body).Decode(&created))
	assert.NotEqual(t, uuid.Nil, created.Id)

	getReq := httptest.NewRequest(http.MethodGet, "/users/"+created.Id.String(), nil)
	getRec := httptest.NewRecorder()
	router.ServeHTTP(getRec, getReq)

	assert.Equal(t, http.StatusOK, getRec.Code)

	var fetched store.User
	assert.NoError(t, json.NewDecoder(getRec.Body).Decode(&fetched))
	assert.Equal(t, created.Id, fetched.Id)

	_, ok := userStore.GetById(t.Context(), created.Id)
	assert.True(t, ok)
}

func TestUserListFilters(t *testing.T) {
	userStore, router := setupUserRouter(t)
	base := time.Now().UnixNano()

	matching := createTestUser(t, userStore, base+1, "active", true, true)
	createTestUser(t, userStore, base+2, "pending", false, false)

	req := httptest.NewRequest(http.MethodGet, "/users?status=active&is_admin=true&is_in_game=true&limit=50&offset=0", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)

	var response struct {
		Items  []store.User `json:"items"`
		Limit  int          `json:"limit"`
		Offset int          `json:"offset"`
	}
	assert.NoError(t, json.NewDecoder(rec.Body).Decode(&response))
	assert.Equal(t, 50, response.Limit)
	assert.Equal(t, 0, response.Offset)

	found := false
	for _, item := range response.Items {
		if item.Id == matching.Id {
			found = true
			break
		}
	}
	assert.True(t, found)
}

func TestUserCount(t *testing.T) {
	userStore, router := setupUserRouter(t)

	countReq := httptest.NewRequest(http.MethodGet, "/users/count?status=pending", nil)
	countRec := httptest.NewRecorder()
	router.ServeHTTP(countRec, countReq)
	assert.Equal(t, http.StatusOK, countRec.Code)

	var before struct {
		Total int `json:"total"`
	}
	assert.NoError(t, json.NewDecoder(countRec.Body).Decode(&before))

	createTestUser(t, userStore, time.Now().UnixNano(), "pending", false, false)

	countReq = httptest.NewRequest(http.MethodGet, "/users/count?status=pending", nil)
	countRec = httptest.NewRecorder()
	router.ServeHTTP(countRec, countReq)
	assert.Equal(t, http.StatusOK, countRec.Code)

	var after struct {
		Total int `json:"total"`
	}
	assert.NoError(t, json.NewDecoder(countRec.Body).Decode(&after))
	assert.Equal(t, before.Total+1, after.Total)
}

func TestUserBulk(t *testing.T) {
	userStore, router := setupUserRouter(t)
	base := time.Now().UnixNano()

	userA := createTestUser(t, userStore, base+1, "active", false, false)
	userB := createTestUser(t, userStore, base+2, "active", false, false)

	payload := map[string]any{
		"ids": []string{userA.Id.String(), userB.Id.String()},
	}
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/users/bulk", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)

	var response map[string]store.User
	assert.NoError(t, json.NewDecoder(rec.Body).Decode(&response))
	assert.Contains(t, response, userA.Id.String())
	assert.Contains(t, response, userB.Id.String())
}

func TestUserGetAndUpdateByTgId(t *testing.T) {
	userStore, router := setupUserRouter(t)
	tgID := time.Now().UnixNano()

	user := createTestUser(t, userStore, tgID, "active", false, false)

	getReq := httptest.NewRequest(http.MethodGet, "/users/by-tg/"+strconv.FormatInt(tgID, 10), nil)
	getRec := httptest.NewRecorder()
	router.ServeHTTP(getRec, getReq)
	assert.Equal(t, http.StatusOK, getRec.Code)

	var fetched store.User
	assert.NoError(t, json.NewDecoder(getRec.Body).Decode(&fetched))
	assert.Equal(t, user.Id, fetched.Id)

	updatePayload := map[string]any{
		"is_admin": true,
		"status":   "confirmed",
	}
	body, err := json.Marshal(updatePayload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}
	patchReq := httptest.NewRequest(http.MethodPatch, "/users/by-tg/"+strconv.FormatInt(tgID, 10), bytes.NewReader(body))
	patchReq.Header.Set("Content-Type", "application/json")
	patchRec := httptest.NewRecorder()
	router.ServeHTTP(patchRec, patchReq)

	assert.Equal(t, http.StatusOK, patchRec.Code)

	var updated store.User
	assert.NoError(t, json.NewDecoder(patchRec.Body).Decode(&updated))
	assert.True(t, updated.IsAdmin)
	assert.Equal(t, "confirmed", updated.Status)
}

func TestUserUpdateById(t *testing.T) {
	userStore, router := setupUserRouter(t)
	user := createTestUser(t, userStore, time.Now().UnixNano(), "active", false, false)

	updatePayload := map[string]any{
		"family_name": "Doe",
	}
	body, err := json.Marshal(updatePayload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	patchReq := httptest.NewRequest(http.MethodPatch, "/users/"+user.Id.String(), bytes.NewReader(body))
	patchReq.Header.Set("Content-Type", "application/json")
	patchRec := httptest.NewRecorder()
	router.ServeHTTP(patchRec, patchReq)

	assert.Equal(t, http.StatusOK, patchRec.Code)

	var updated store.User
	assert.NoError(t, json.NewDecoder(patchRec.Body).Decode(&updated))
	assert.Equal(t, "Doe", updated.FamilyName)
}

func TestUserGetOrCreateSetsUUID(t *testing.T) {
	_, router := setupUserRouter(t)
	tgID := time.Now().UnixNano()

	payload := map[string]any{
		"tg_id":       tgID,
		"tg_username": "new-user",
	}
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/users/get-or-create", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusCreated, rec.Code)

	var created store.User
	assert.NoError(t, json.NewDecoder(rec.Body).Decode(&created))
	assert.NotEqual(t, uuid.Nil, created.Id)

	req = httptest.NewRequest(http.MethodPost, "/users/get-or-create", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)

	var fetched store.User
	assert.NoError(t, json.NewDecoder(rec.Body).Decode(&fetched))
	assert.Equal(t, created.Id, fetched.Id)
}
