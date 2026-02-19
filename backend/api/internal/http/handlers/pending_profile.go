package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"cukiller/api/pkg/db/store"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type PendingProfileHandler struct {
	PendingProfileStore *store.PendingProfileStore
	UserStore           *store.UserStore
}

type PendingProfileCreateRequest struct {
	UserId             string   `json:"user_id"`
	Status             string   `json:"status"`
	IsNewProfile       bool     `json:"is_new_profile"`
	ChangedFields      []string `json:"changed_fields"`
	SubmittedUsername  *string  `json:"submitted_username"`
	GivenName          *string  `json:"given_name"`
	FamilyName         *string  `json:"family_name"`
	Type               *string  `json:"type"`
	CourseNumber       *int     `json:"course_number"`
	GroupName          *string  `json:"group_name"`
	Photo              *string  `json:"photo"`
	AboutUser          *string  `json:"about_user"`
	AllowHuggingOnKill bool     `json:"allow_hugging_on_kill"`
	ChatId             *int64   `json:"chat_id"`
	MessageId          *int64   `json:"message_id"`
}

type PendingProfileUpdateRequest struct {
	Status            *string `json:"status"`
	ModeratorId       *string `json:"moderator_id"`
	Reason            *string `json:"reason"`
	ChatId            *int64  `json:"chat_id"`
	MessageId         *int64  `json:"message_id"`
	SubmittedUsername *string `json:"submitted_username"`
}

type PendingProfileResponse struct {
	Id                 uuid.UUID                   `json:"id"`
	UserId             uuid.UUID                   `json:"user_id"`
	Status             string                      `json:"status"`
	IsNewProfile       bool                        `json:"is_new_profile"`
	ModeratorId        *uuid.UUID                  `json:"moderator_id,omitempty"`
	Reason             *string                     `json:"reason"`
	ChangedFields      []string                    `json:"changed_fields"`
	ChatId             *int64                      `json:"chat_id"`
	MessageId          *int64                      `json:"message_id"`
	SubmittedUsername  *string                     `json:"submitted_username"`
	GivenName          *string                     `json:"given_name"`
	FamilyName         *string                     `json:"family_name"`
	Type               *string                     `json:"type"`
	CourseNumber       *int                        `json:"course_number"`
	GroupName          *string                     `json:"group_name"`
	Photo              *string                     `json:"photo"`
	AboutUser          *string                     `json:"about_user"`
	AllowHuggingOnKill bool                        `json:"allow_hugging_on_kill"`
	CreatedAt          time.Time                   `json:"created_at"`
	UpdatedAt          time.Time                   `json:"updated_at"`
	User               *PendingProfileUserResponse `json:"user,omitempty"`
}

type PendingProfileListResponse struct {
	Items  []PendingProfileResponse `json:"items"`
	Limit  int                      `json:"limit"`
	Offset int                      `json:"offset"`
}

type PendingProfileUserResponse struct {
	Id                 uuid.UUID  `json:"id"`
	CreatedAt          time.Time  `json:"created_at"`
	UpdatedAt          time.Time  `json:"updated_at"`
	TgId               int64      `json:"tg_id"`
	TgUsername         *string    `json:"tg_username"`
	Type               *string    `json:"type"`
	CourseNumber       *int       `json:"course_number"`
	GroupName          *string    `json:"group_name"`
	IsInGame           bool       `json:"is_in_game"`
	IsAdmin            bool       `json:"is_admin"`
	Photo              *string    `json:"photo"`
	AboutUser          *string    `json:"about_user"`
	Status             string     `json:"status"`
	AllowHuggingOnKill bool       `json:"allow_hugging_on_kill"`
	ExitCooldownUntil  *time.Time `json:"exit_cooldown_until"`
	GivenName          *string    `json:"given_name"`
	FamilyName         *string    `json:"family_name"`
	FamilyNameRequired bool       `json:"family_name_required"`
}

func (h *PendingProfileHandler) List(c *gin.Context) {
	status := c.Query("status")
	userIDRaw := c.Query("user_id")
	limit, err := parseQueryInt(c, "limit", 100)
	if err != nil {
		return
	}
	offset, err := parseQueryInt(c, "offset", 0)
	if err != nil {
		return
	}

	var userID *uuid.UUID
	if userIDRaw != "" {
		parsed, err := uuid.Parse(userIDRaw)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user_id"})
			return
		}
		userID = &parsed
	}

	items, err := h.PendingProfileStore.List(c, store.PendingProfileFilter{
		Status: status,
		UserId: userID,
		Limit:  limit,
		Offset: offset,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list pending profiles"})
		return
	}

	respItems := make([]PendingProfileResponse, 0, len(items))
	for _, entry := range items {
		resp, err := h.toResponse(c, &entry)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to serialize pending profile"})
			return
		}
		respItems = append(respItems, resp)
	}

	c.JSON(http.StatusOK, PendingProfileListResponse{
		Items:  respItems,
		Limit:  limit,
		Offset: offset,
	})
}

func (h *PendingProfileHandler) Create(c *gin.Context) {
	var req PendingProfileCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse request: %s", err)})
		return
	}
	if req.UserId == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "user_id is required"})
		return
	}
	userId, err := uuid.Parse(req.UserId)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user_id"})
		return
	}

	changedFields, err := json.Marshal(req.ChangedFields)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid changed_fields"})
		return
	}

	status := req.Status
	if status == "" {
		status = "pending"
	}

	entry := store.PendingProfile{
		Id:                 uuid.New(),
		GivenName:          derefString(req.GivenName),
		FamilyName:         derefString(req.FamilyName),
		Type:               derefString(req.Type),
		CourseNumber:       derefUint8(req.CourseNumber),
		GroupName:          derefString(req.GroupName),
		Photo:              derefString(req.Photo),
		AboutUser:          derefString(req.AboutUser),
		Status:             status,
		IsNewProfile:       req.IsNewProfile,
		Reason:             "",
		ChangedFields:      changedFields,
		ChatId:             derefInt64(req.ChatId),
		MessageId:          derefInt64(req.MessageId),
		SubmittedUsername:  derefString(req.SubmittedUsername),
		UserId:             userId,
		ModeratorId:        uuid.Nil,
		AllowHuggingOnKill: req.AllowHuggingOnKill,
	}

	if ok := h.PendingProfileStore.Create(c, &entry); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create pending profile"})
		return
	}

	resp, err := h.toResponse(c, &entry)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to serialize pending profile"})
		return
	}
	c.JSON(http.StatusCreated, resp)
}

func (h *PendingProfileHandler) GetById(c *gin.Context) {
	id, ok := parsePendingId(c)
	if !ok {
		return
	}
	entry, found := h.PendingProfileStore.GetById(c, id)
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "pending profile not found"})
		return
	}
	resp, err := h.toResponse(c, entry)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to serialize pending profile"})
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (h *PendingProfileHandler) Update(c *gin.Context) {
	id, ok := parsePendingId(c)
	if !ok {
		return
	}

	var req PendingProfileUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse request: %s", err)})
		return
	}

	entry, found := h.PendingProfileStore.GetById(c, id)
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "pending profile not found"})
		return
	}

	if req.Status != nil {
		entry.Status = *req.Status
	}
	if req.ModeratorId != nil {
		moderatorId, err := uuid.Parse(*req.ModeratorId)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid moderator_id"})
			return
		}
		entry.ModeratorId = moderatorId
	}
	if req.Reason != nil {
		entry.Reason = *req.Reason
	}
	if req.ChatId != nil {
		entry.ChatId = *req.ChatId
	}
	if req.MessageId != nil {
		entry.MessageId = *req.MessageId
	}
	if req.SubmittedUsername != nil {
		entry.SubmittedUsername = *req.SubmittedUsername
	}

	if ok := h.PendingProfileStore.Update(c, entry); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update pending profile"})
		return
	}

	resp, err := h.toResponse(c, entry)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to serialize pending profile"})
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (h *PendingProfileHandler) toResponse(ctx *gin.Context, entry *store.PendingProfile) (PendingProfileResponse, error) {
	changedFields := []string{}
	if len(entry.ChangedFields) > 0 {
		if err := json.Unmarshal(entry.ChangedFields, &changedFields); err != nil {
			return PendingProfileResponse{}, err
		}
	}

	var moderatorId *uuid.UUID
	if entry.ModeratorId != uuid.Nil {
		id := entry.ModeratorId
		moderatorId = &id
	}

	resp := PendingProfileResponse{
		Id:                 entry.Id,
		UserId:             entry.UserId,
		Status:             entry.Status,
		IsNewProfile:       entry.IsNewProfile,
		ModeratorId:        moderatorId,
		Reason:             nilIfEmpty(entry.Reason),
		ChangedFields:      changedFields,
		ChatId:             nilIfZeroInt64(entry.ChatId),
		MessageId:          nilIfZeroInt64(entry.MessageId),
		SubmittedUsername:  nilIfEmpty(entry.SubmittedUsername),
		GivenName:          nilIfEmpty(entry.GivenName),
		FamilyName:         nilIfEmpty(entry.FamilyName),
		Type:               nilIfEmpty(entry.Type),
		CourseNumber:       nilIfZeroInt(int(entry.CourseNumber)),
		GroupName:          nilIfEmpty(entry.GroupName),
		Photo:              nilIfEmpty(entry.Photo),
		AboutUser:          nilIfEmpty(entry.AboutUser),
		AllowHuggingOnKill: entry.AllowHuggingOnKill,
		CreatedAt:          entry.CreatedAt,
		UpdatedAt:          entry.UpdatedAt,
	}

	if h.UserStore != nil {
		if user, ok := h.UserStore.GetById(ctx, entry.UserId); ok {
			resp.User = toPendingProfileUserResponse(user)
		}
	}

	return resp, nil
}

func toPendingProfileUserResponse(user *store.User) *PendingProfileUserResponse {
	resp := &PendingProfileUserResponse{
		Id:                 user.Id,
		CreatedAt:          user.CreatedAt,
		UpdatedAt:          user.UpdatedAt,
		TgId:               user.TgId,
		TgUsername:         nilIfEmpty(user.TgUsername),
		Type:               nilIfEmpty(user.Type),
		CourseNumber:       nilIfZeroInt(int(user.CourseNumber)),
		GroupName:          nilIfEmpty(user.GroupName),
		IsInGame:           user.IsInGame,
		IsAdmin:            user.IsAdmin,
		Photo:              nilIfEmpty(user.Photo),
		AboutUser:          nilIfEmpty(user.AboutUser),
		Status:             user.Status,
		AllowHuggingOnKill: user.AllowHuggingOnKill,
		GivenName:          nilIfEmpty(user.GivenName),
		FamilyName:         nilIfEmpty(user.FamilyName),
		FamilyNameRequired: user.FamilyNameRequired,
	}
	if !user.ExitCooldownUntil.IsZero() {
		exit := user.ExitCooldownUntil
		resp.ExitCooldownUntil = &exit
	}
	return resp
}

func parsePendingId(c *gin.Context) (uuid.UUID, bool) {
	raw := c.Param("pending_id")
	id, err := uuid.Parse(raw)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid pending_id"})
		return uuid.Nil, false
	}
	return id, true
}

func parseQueryInt(c *gin.Context, key string, defaultValue int) (int, error) {
	raw := c.Query(key)
	if raw == "" {
		return defaultValue, nil
	}
	value, err := strconv.Atoi(raw)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("invalid %s", key)})
		return 0, err
	}
	return value, nil
}

func nilIfEmpty(value string) *string {
	if value == "" {
		return nil
	}
	return &value
}

func nilIfZeroInt64(value int64) *int64 {
	if value == 0 {
		return nil
	}
	return &value
}

func nilIfZeroInt(value int) *int {
	if value == 0 {
		return nil
	}
	return &value
}

func derefString(value *string) string {
	if value == nil {
		return ""
	}
	return *value
}

func derefInt64(value *int64) int64 {
	if value == nil {
		return 0
	}
	return *value
}

func derefUint8(value *int) uint8 {
	if value == nil || *value <= 0 {
		return 0
	}
	return uint8(*value)
}
