package store

import (
	"cukiller/api/pkg/db"
	"testing"

	"github.com/stretchr/testify/assert"
)

const TestChatId int64 = 456
const TestChatKey = "test_key"

func TestChatStore_CreateGet(t *testing.T) {
	store := ChatStore{db: db.SetupDb(t)}

	chat := DefaultChat()
	chat.ChatId = TestChatId
	chat.Key = TestChatKey

	assert.True(t, store.Create(t.Context(), &chat))
	got, ok := store.GetByChatIdAndKey(t.Context(), TestChatId, TestChatKey)
	assert.True(t, ok)
	assert.EqualValues(t, TestChatKey, got.Key)

	// cleanup
	store.Delete(t.Context(), got.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}

func TestChatStore_CreateUpdateGet(t *testing.T) {
	store := ChatStore{db: db.SetupDb(t)}

	chat := DefaultChat()
	chat.ChatId = TestChatId
	chat.Key = TestChatKey

	assert.True(t, store.Create(t.Context(), &chat))

	const TestOtherKey = "other_key"
	chat.Key = TestOtherKey
	assert.True(t, store.Update(t.Context(), &chat))
	got, ok := store.GetByChatIdAndKey(t.Context(), TestChatId, TestOtherKey)
	assert.True(t, ok)
	assert.Equal(t, TestOtherKey, got.Key)

	// cleanup
	store.Delete(t.Context(), got.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}
