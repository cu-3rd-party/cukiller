package store

import (
	"cukiller/api/pkg/db"
	"testing"

	"github.com/stretchr/testify/assert"
)

const TestId = 123
const TestUsername = "test_user"

func TestUserStore_CreateGet(t *testing.T) {
	store := UserStore{db: db.SetupDb(t)}

	user := DefaultUser()
	user.TgId = TestId
	user.TgUsername = TestUsername

	assert.True(t, store.Create(t.Context(), &user))
	got, ok := store.GetByTgId(t.Context(), TestId)
	assert.True(t, ok)
	assert.EqualValues(t, TestId, got.TgId)

	// cleanup
	store.Delete(t.Context(), got.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}

func TestUserStore_CreateUpdateGet(t *testing.T) {
	store := UserStore{db: db.SetupDb(t)}

	user := DefaultUser()
	user.TgId = TestId
	user.TgUsername = TestUsername

	assert.True(t, store.Create(t.Context(), &user))

	const TestOtherUsername = "other_username"
	user.TgUsername = TestOtherUsername
	assert.True(t, store.Update(t.Context(), &user))
	got, ok := store.GetByTgId(t.Context(), TestId)
	assert.True(t, ok)
	assert.Equal(t, TestOtherUsername, got.TgUsername)

	// cleanup
	store.Delete(t.Context(), got.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}
