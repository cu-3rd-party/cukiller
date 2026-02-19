package tests

import (
	"bytes"
	"cukiller/api/internal/http"
	"cukiller/api/pkg/db"
	"cukiller/api/pkg/db/store"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
)

type pendingProfileResponse struct {
	Id            string   `json:"id"`
	UserId        string   `json:"user_id"`
	Status        string   `json:"status"`
	Reason        *string  `json:"reason"`
	ChangedFields []string `json:"changed_fields"`
}

type pendingProfileListResponse struct {
	Items  []pendingProfileResponse `json:"items"`
	Limit  int                      `json:"limit"`
	Offset int                      `json:"offset"`
}

func setupPendingProfilesRouter(t *testing.T) (*store.UserStore, *store.PendingProfileStore, *gin.Engine) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	dbConn := db.SetupDb(t)
	userStore := store.NewUserStore(dbConn)
	pendingStore := store.NewPendingProfileStore(dbConn)
	router := api.NewRouter(api.Config{
		User:           userStore,
		PendingProfile: pendingStore,
	})
	return &userStore, &pendingStore, router
}

func createPendingProfilesUser(t *testing.T, userStore *store.UserStore, tgId int64) *store.User {
	t.Helper()
	user := store.DefaultUser()
	user.Id = uuid.New()
	user.TgId = tgId
	user.TgUsername = "pending_test_user"
	assert.True(t, userStore.Create(t.Context(), user))
	return user
}

func TestPendingProfilesCreateAndGet(t *testing.T) {
	userStore, pendingStore, router := setupPendingProfilesRouter(t)
	user := createPendingProfilesUser(t, userStore, 991001)
	defer userStore.Delete(t.Context(), user.Id)

	payload := map[string]any{
		"user_id":               user.Id.String(),
		"is_new_profile":        true,
		"given_name":            "Test",
		"family_name":           "User",
		"changed_fields":        []string{"given_name", "family_name"},
		"allow_hugging_on_kill": true,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/pending-profiles", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusCreated, rec.Code)

	var created pendingProfileResponse
	assert.NoError(t, json.Unmarshal(rec.Body.Bytes(), &created))
	assert.NotEmpty(t, created.Id)
	assert.Equal(t, user.Id.String(), created.UserId)
	assert.Equal(t, "pending", created.Status)
	assert.ElementsMatch(t, []string{"given_name", "family_name"}, created.ChangedFields)

	createdId, err := uuid.Parse(created.Id)
	if err != nil {
		t.Fatalf("failed to parse created id: %v", err)
	}
	defer pendingStore.Delete(t.Context(), createdId)

	req = httptest.NewRequest(http.MethodGet, "/pending-profiles/"+created.Id, nil)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)

	var fetched pendingProfileResponse
	assert.NoError(t, json.Unmarshal(rec.Body.Bytes(), &fetched))
	assert.Equal(t, created.Id, fetched.Id)
	assert.Equal(t, user.Id.String(), fetched.UserId)
}

func TestPendingProfilesListFilters(t *testing.T) {
	userStore, pendingStore, router := setupPendingProfilesRouter(t)
	user := createPendingProfilesUser(t, userStore, 991002)
	defer userStore.Delete(t.Context(), user.Id)

	pending := store.DefaultPendingProfile()
	pending.UserId = user.Id
	pending.Status = "pending"
	pending.ModeratorId = uuid.Nil
	assert.True(t, pendingStore.Create(t.Context(), &pending))
	defer pendingStore.Delete(t.Context(), pending.Id)

	approved := store.DefaultPendingProfile()
	approved.UserId = user.Id
	approved.Status = "approved"
	approved.ModeratorId = uuid.Nil
	assert.True(t, pendingStore.Create(t.Context(), &approved))
	defer pendingStore.Delete(t.Context(), approved.Id)

	req := httptest.NewRequest(http.MethodGet, "/pending-profiles?status=pending&user_id="+user.Id.String()+"&limit=10&offset=0", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)

	var list pendingProfileListResponse
	assert.NoError(t, json.Unmarshal(rec.Body.Bytes(), &list))
	assert.Equal(t, 10, list.Limit)
	assert.Equal(t, 0, list.Offset)
	assert.Len(t, list.Items, 1)
	assert.Equal(t, "pending", list.Items[0].Status)
}

func TestPendingProfilesUpdate(t *testing.T) {
	userStore, pendingStore, router := setupPendingProfilesRouter(t)
	user := createPendingProfilesUser(t, userStore, 991003)
	defer userStore.Delete(t.Context(), user.Id)

	pending := store.DefaultPendingProfile()
	pending.UserId = user.Id
	pending.Status = "pending"
	pending.ModeratorId = uuid.Nil
	assert.True(t, pendingStore.Create(t.Context(), &pending))
	defer pendingStore.Delete(t.Context(), pending.Id)

	payload := map[string]any{
		"status":       "approved",
		"reason":       "ok",
		"moderator_id": user.Id.String(),
	}
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	req := httptest.NewRequest(http.MethodPatch, "/pending-profiles/"+pending.Id.String(), bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)

	var updated pendingProfileResponse
	assert.NoError(t, json.Unmarshal(rec.Body.Bytes(), &updated))
	assert.Equal(t, "approved", updated.Status)
	assert.NotNil(t, updated.Reason)
	assert.Equal(t, "ok", *updated.Reason)

	stored, ok := pendingStore.GetById(t.Context(), pending.Id)
	assert.True(t, ok)
	assert.Equal(t, "approved", stored.Status)
	assert.Equal(t, "ok", stored.Reason)
	assert.Equal(t, user.Id, stored.ModeratorId)
}
