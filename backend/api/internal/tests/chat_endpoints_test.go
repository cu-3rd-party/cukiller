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
	"github.com/stretchr/testify/assert"
)

func TestChatCreateAndFetch(t *testing.T) {
	gin.SetMode(gin.TestMode)

	db := SetupDb(t)
	chatStore := store.NewChatStore(db)
	router := api.NewRouter(api.Config{Chat: chatStore})

	base := time.Now().UnixNano()
	chatId := base + 1
	key := fmt.Sprintf("key-%d", base)

	payload := map[string]any{
		"chat_id": chatId,
		"key":     key,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	createReq := httptest.NewRequest(http.MethodPost, "/chats", bytes.NewReader(body))
	createReq.Header.Set("Content-Type", "application/json")
	createRec := httptest.NewRecorder()
	router.ServeHTTP(createRec, createReq)
	assert.Equal(t, http.StatusCreated, createRec.Code)

	createdChat, ok := chatStore.GetByChatIdAndKey(t.Context(), chatId, key)
	assert.True(t, ok)
	assert.NotNil(t, createdChat)

	getByKeyReq := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/chats/by-key/%s", key), nil)
	getByKeyRec := httptest.NewRecorder()
	router.ServeHTTP(getByKeyRec, getByKeyReq)
	assert.Equal(t, http.StatusOK, getByKeyRec.Code)

	getByIdReq := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/chats/by-id/%d", chatId), nil)
	getByIdRec := httptest.NewRecorder()
	router.ServeHTTP(getByIdRec, getByIdReq)
	assert.Equal(t, http.StatusOK, getByIdRec.Code)
}

func TestChatGetNotFound(t *testing.T) {
	gin.SetMode(gin.TestMode)

	db := SetupDb(t)
	router := api.NewRouter(api.Config{Chat: store.NewChatStore(db)})

	getByKeyReq := httptest.NewRequest(http.MethodGet, "/chats/by-key/missing", nil)
	getByKeyRec := httptest.NewRecorder()
	router.ServeHTTP(getByKeyRec, getByKeyReq)
	assert.Equal(t, http.StatusNotFound, getByKeyRec.Code)

	getByIdReq := httptest.NewRequest(http.MethodGet, "/chats/by-id/999999", nil)
	getByIdRec := httptest.NewRecorder()
	router.ServeHTTP(getByIdRec, getByIdReq)
	assert.Equal(t, http.StatusNotFound, getByIdRec.Code)
}

func TestChatCreateBadBody(t *testing.T) {
	gin.SetMode(gin.TestMode)

	db := SetupDb(t)
	router := api.NewRouter(api.Config{Chat: store.NewChatStore(db)})

	req := httptest.NewRequest(http.MethodPost, "/chats", bytes.NewBufferString("{"))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusBadRequest, rec.Code)
}
