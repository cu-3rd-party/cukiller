package tests

import (
	"bytes"
	"cukiller/api/internal/http"
	. "cukiller/api/pkg/db"
	"cukiller/api/pkg/db/store"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestSystemBootstrapSuccess(t *testing.T) {
	gin.SetMode(gin.TestMode)
	db := SetupDb(t)

	chatStore := store.NewChatStore(db)
	userStore := store.NewUserStore(db)
	router := api.NewRouter(api.Config{
		Chat: chatStore,
		User: userStore,
	})

	base := time.Now().UnixNano()
	adminChatID := base + 1
	discussionChatID := base + 2
	adminTgIDs := []int64{base + 10, base + 11}
	payload := map[string]any{
		"admin_chat_id":      adminChatID,
		"discussion_chat_id": discussionChatID,
		"admin_tg_ids":       adminTgIDs,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/system/bootstrap", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusOK, rec.Code)

	adminChat, ok := chatStore.GetByChatIdAndKey(t.Context(), adminChatID, "logs")
	assert.True(t, ok)
	assert.NotNil(t, adminChat)

	discussionChat, ok := chatStore.GetByChatIdAndKey(t.Context(), discussionChatID, "discussion")
	assert.True(t, ok)
	assert.NotNil(t, discussionChat)

	for _, tgId := range adminTgIDs {
		user, ok := userStore.GetByTgId(t.Context(), tgId)
		assert.True(t, ok)
		assert.NotNil(t, user)
		assert.True(t, user.IsAdmin)
	}
}

func TestSystemBootstrapBadBody(t *testing.T) {
	gin.SetMode(gin.TestMode)
	db := SetupDb(t)

	router := api.NewRouter(api.Config{
		Chat: store.NewChatStore(db),
		User: store.NewUserStore(db),
	})

	req := httptest.NewRequest(http.MethodPost, "/system/bootstrap", bytes.NewBufferString("{"))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusBadRequest, rec.Code)
}
