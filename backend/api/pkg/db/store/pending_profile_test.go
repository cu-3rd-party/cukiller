package store

import (
	"cukiller/api/pkg/db"
	"testing"

	"github.com/stretchr/testify/assert"
)

const TestPendingTgId = 456
const TestPendingUsername = "pending_user"

func TestPendingProfileStore_CreateGet(t *testing.T) {
	userStore := UserStore{db: db.SetupDb(t)}
	store := PendingProfileStore{db: userStore.db}

	user := DefaultUser()
	user.TgId = TestPendingTgId
	user.TgUsername = TestPendingUsername
	assert.True(t, userStore.Create(t.Context(), &user))

	profile := DefaultPendingProfile()
	profile.GivenName = "Test"
	profile.FamilyName = "User"
	profile.Type = "student"
	profile.CourseNumber = 2
	profile.GroupName = "CS-02"
	profile.Photo = "photo"
	profile.AboutUser = "about"
	profile.Status = "pending"
	profile.IsNewProfile = true
	profile.Reason = "reason"
	profile.ChangedFields = []byte(`["given_name","family_name"]`)
	profile.ChatId = 100
	profile.MessageId = 200
	profile.SubmittedUsername = "submitter"
	profile.UserId = user.Id
	profile.ModeratorId = user.Id
	profile.AllowHuggingOnKill = true

	assert.True(t, store.Create(t.Context(), &profile))
	got, ok := store.GetById(t.Context(), profile.Id)
	assert.True(t, ok)
	assert.EqualValues(t, "Test", got.GivenName)

	// cleanup
	store.Delete(t.Context(), got.Id)
	userStore.Delete(t.Context(), user.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}

func TestPendingProfileStore_CreateUpdateGet(t *testing.T) {
	userStore := UserStore{db: db.SetupDb(t)}
	store := PendingProfileStore{db: userStore.db}

	user := DefaultUser()
	user.TgId = TestPendingTgId + 1
	user.TgUsername = TestPendingUsername + "_2"
	assert.True(t, userStore.Create(t.Context(), &user))

	profile := DefaultPendingProfile()
	profile.GivenName = "Test"
	profile.FamilyName = "User"
	profile.Type = "student"
	profile.CourseNumber = 3
	profile.GroupName = "CS-03"
	profile.Photo = "photo"
	profile.AboutUser = "about"
	profile.Status = "pending"
	profile.IsNewProfile = false
	profile.Reason = "reason"
	profile.ChangedFields = []byte(`["type"]`)
	profile.ChatId = 101
	profile.MessageId = 201
	profile.SubmittedUsername = "submitter"
	profile.UserId = user.Id
	profile.ModeratorId = user.Id
	profile.AllowHuggingOnKill = false

	assert.True(t, store.Create(t.Context(), &profile))

	profile.Status = "approved"
	profile.Reason = "approved"
	assert.True(t, store.Update(t.Context(), &profile))
	got, ok := store.GetById(t.Context(), profile.Id)
	assert.True(t, ok)
	assert.Equal(t, "approved", got.Status)
	assert.Equal(t, "approved", got.Reason)

	// cleanup
	store.Delete(t.Context(), got.Id)
	userStore.Delete(t.Context(), user.Id)
	_, ok = store.GetById(t.Context(), got.Id)
	assert.False(t, ok)
}
