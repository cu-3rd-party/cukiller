package handlers

import (
	"fmt"
	"net/http"
	"strconv"
	"time"

	"cukiller/api/pkg/db/store"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

type UserHandler struct {
	*store.UserStore
}

type GetOrCreateUserRequest struct {
	TgId       int64  `json:"tg_id" binding:"required"`
	TgUsername string `json:"tg_username"`
	GivenName  string `json:"given_name"`
	FamilyName string `json:"family_name"`
}

func (r *GetOrCreateUserRequest) applyToUser(u *store.User) {
	u.TgId = r.TgId
	u.TgUsername = r.TgUsername
	u.GivenName = r.GivenName
	u.FamilyName = r.FamilyName
}

func (h *UserHandler) GetOrCreate(c *gin.Context) {
	var req GetOrCreateUserRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": fmt.Sprintf("failed to parse request: %s", err),
		})
		return
	}

	user, found := h.UserStore.GetByTgId(c, req.TgId)

	if found {
		user.TgUsername = req.TgUsername
		if ok := h.UserStore.Upsert(c, user); !ok {
			c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to update user"})
			return
		}
		c.JSON(http.StatusOK, user)
		log.Debug().
			Str("username", user.TgUsername).
			Str("status", user.Status).
			Msg("new user")
		return
	}

	user = store.DefaultUser()
	req.applyToUser(user)
	if ok := h.UserStore.Create(c, user); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to create user"})
		return
	}

	c.JSON(http.StatusCreated, user)
}

type UserCreateRequest struct {
	TgId               int64      `json:"tg_id" binding:"required"`
	TgUsername         *string    `json:"tg_username"`
	GivenName          *string    `json:"given_name"`
	FamilyName         *string    `json:"family_name"`
	Type               *string    `json:"type"`
	CourseNumber       *int       `json:"course_number"`
	GroupName          *string    `json:"group_name"`
	Photo              *string    `json:"photo"`
	AboutUser          *string    `json:"about_user"`
	AllowHuggingOnKill *bool      `json:"allow_hugging_on_kill"`
	FamilyNameRequired *bool      `json:"family_name_required"`
	IsInGame           *bool      `json:"is_in_game"`
	IsAdmin            *bool      `json:"is_admin"`
	ExitCooldownUntil  *time.Time `json:"exit_cooldown_until"`
	Status             *string    `json:"status"`
}

func (r *UserCreateRequest) applyToUser(u *store.User) error {
	u.TgId = r.TgId
	if r.TgUsername != nil {
		u.TgUsername = *r.TgUsername
	}
	if r.GivenName != nil {
		u.GivenName = *r.GivenName
	}
	if r.FamilyName != nil {
		u.FamilyName = *r.FamilyName
	}
	if r.Type != nil {
		u.Type = *r.Type
	}
	if r.CourseNumber != nil {
		if *r.CourseNumber < 0 || *r.CourseNumber > 255 {
			return fmt.Errorf("course_number out of range")
		}
		u.CourseNumber = uint8(*r.CourseNumber)
	}
	if r.GroupName != nil {
		u.GroupName = *r.GroupName
	}
	if r.Photo != nil {
		u.Photo = *r.Photo
	}
	if r.AboutUser != nil {
		u.AboutUser = *r.AboutUser
	}
	if r.AllowHuggingOnKill != nil {
		u.AllowHuggingOnKill = *r.AllowHuggingOnKill
	}
	if r.FamilyNameRequired != nil {
		u.FamilyNameRequired = *r.FamilyNameRequired
	}
	if r.IsInGame != nil {
		u.IsInGame = *r.IsInGame
	}
	if r.IsAdmin != nil {
		u.IsAdmin = *r.IsAdmin
	}
	if r.ExitCooldownUntil != nil {
		u.ExitCooldownUntil = *r.ExitCooldownUntil
	}
	if r.Status != nil {
		u.Status = *r.Status
	} else if u.Status == "" {
		u.Status = "active"
	}
	return nil
}

type UserUpdateRequest struct {
	TgUsername         *string    `json:"tg_username"`
	GivenName          *string    `json:"given_name"`
	FamilyName         *string    `json:"family_name"`
	Type               *string    `json:"type"`
	CourseNumber       *int       `json:"course_number"`
	GroupName          *string    `json:"group_name"`
	Photo              *string    `json:"photo"`
	AboutUser          *string    `json:"about_user"`
	AllowHuggingOnKill *bool      `json:"allow_hugging_on_kill"`
	FamilyNameRequired *bool      `json:"family_name_required"`
	IsInGame           *bool      `json:"is_in_game"`
	IsAdmin            *bool      `json:"is_admin"`
	ExitCooldownUntil  *time.Time `json:"exit_cooldown_until"`
	Status             *string    `json:"status"`
}

func (r *UserUpdateRequest) applyToUser(u *store.User) error {
	if r.TgUsername != nil {
		u.TgUsername = *r.TgUsername
	}
	if r.GivenName != nil {
		u.GivenName = *r.GivenName
	}
	if r.FamilyName != nil {
		u.FamilyName = *r.FamilyName
	}
	if r.Type != nil {
		u.Type = *r.Type
	}
	if r.CourseNumber != nil {
		if *r.CourseNumber < 0 || *r.CourseNumber > 255 {
			return fmt.Errorf("course_number out of range")
		}
		u.CourseNumber = uint8(*r.CourseNumber)
	}
	if r.GroupName != nil {
		u.GroupName = *r.GroupName
	}
	if r.Photo != nil {
		u.Photo = *r.Photo
	}
	if r.AboutUser != nil {
		u.AboutUser = *r.AboutUser
	}
	if r.AllowHuggingOnKill != nil {
		u.AllowHuggingOnKill = *r.AllowHuggingOnKill
	}
	if r.FamilyNameRequired != nil {
		u.FamilyNameRequired = *r.FamilyNameRequired
	}
	if r.IsInGame != nil {
		u.IsInGame = *r.IsInGame
	}
	if r.IsAdmin != nil {
		u.IsAdmin = *r.IsAdmin
	}
	if r.ExitCooldownUntil != nil {
		u.ExitCooldownUntil = *r.ExitCooldownUntil
	}
	if r.Status != nil {
		u.Status = *r.Status
	}
	return nil
}

type UsersListResponse struct {
	Items  []store.User `json:"items"`
	Limit  int          `json:"limit"`
	Offset int          `json:"offset"`
}

var allowedUserStatuses = map[string]struct{}{
	"active":    {},
	"pending":   {},
	"confirmed": {},
	"rejected":  {},
	"banned":    {},
}

func parseStatus(status string) (string, bool) {
	if status == "" {
		return "", true
	}
	_, ok := allowedUserStatuses[status]
	return status, ok
}

func (h *UserHandler) List(c *gin.Context) {
	status, ok := parseStatus(c.Query("status"))
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"message": "invalid status"})
		return
	}

	var isInGame *bool
	if raw, ok := c.GetQuery("is_in_game"); ok {
		parsed, err := strconv.ParseBool(raw)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": "invalid is_in_game"})
			return
		}
		isInGame = &parsed
	}

	var isAdmin *bool
	if raw, ok := c.GetQuery("is_admin"); ok {
		parsed, err := strconv.ParseBool(raw)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": "invalid is_admin"})
			return
		}
		isAdmin = &parsed
	}

	limit, err := strconv.Atoi(c.DefaultQuery("limit", "100"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "invalid limit"})
		return
	}
	offset, err := strconv.Atoi(c.DefaultQuery("offset", "0"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "invalid offset"})
		return
	}

	users, ok := h.UserStore.List(c, store.UserListFilters{
		Status:   status,
		IsInGame: isInGame,
		IsAdmin:  isAdmin,
		Limit:    limit,
		Offset:   offset,
	})
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to list users"})
		return
	}

	c.JSON(http.StatusOK, UsersListResponse{
		Items:  users,
		Limit:  limit,
		Offset: offset,
	})
}

func (h *UserHandler) Create(c *gin.Context) {
	var req UserCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": fmt.Sprintf("failed to parse request: %s", err),
		})
		return
	}
	if req.Status != nil {
		if _, ok := parseStatus(*req.Status); !ok {
			c.JSON(http.StatusBadRequest, gin.H{"message": "invalid status"})
			return
		}
	}

	user := store.DefaultUser()
	if err := req.applyToUser(user); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": err.Error()})
		return
	}
	user.Id = uuid.New()

	if ok := h.UserStore.Create(c, user); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to create user"})
		return
	}
	c.JSON(http.StatusCreated, user)
}

func (h *UserHandler) Count(c *gin.Context) {
	status, ok := parseStatus(c.Query("status"))
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"message": "invalid status"})
		return
	}

	total, ok := h.UserStore.Count(c, status)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to count users"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"total": total})
}

type BulkIdsRequest struct {
	Ids []string `json:"ids" binding:"required"`
}

func (h *UserHandler) Bulk(c *gin.Context) {
	var req BulkIdsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": fmt.Sprintf("failed to parse request: %s", err)})
		return
	}

	ids := make([]uuid.UUID, 0, len(req.Ids))
	for _, raw := range req.Ids {
		parsed, err := uuid.Parse(raw)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"message": "invalid id"})
			return
		}
		ids = append(ids, parsed)
	}

	users, ok := h.UserStore.GetByIds(c, ids)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to fetch users"})
		return
	}

	response := make(map[string]store.User, len(users))
	for id, user := range users {
		response[id.String()] = user
	}

	c.JSON(http.StatusOK, response)
}

func (h *UserHandler) GetByTgId(c *gin.Context) {
	tgID, err := strconv.ParseInt(c.Param("tg_id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "invalid tg_id"})
		return
	}

	user, ok := h.UserStore.GetByTgId(c, tgID)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"message": "user not found"})
		return
	}

	c.JSON(http.StatusOK, user)
}

func (h *UserHandler) UpdateByTgId(c *gin.Context) {
	tgID, err := strconv.ParseInt(c.Param("tg_id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "invalid tg_id"})
		return
	}

	var req UserUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": fmt.Sprintf("failed to parse request: %s", err),
		})
		return
	}
	if req.Status != nil {
		if _, ok := parseStatus(*req.Status); !ok {
			c.JSON(http.StatusBadRequest, gin.H{"message": "invalid status"})
			return
		}
	}

	user, ok := h.UserStore.GetByTgId(c, tgID)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"message": "user not found"})
		return
	}

	if err := req.applyToUser(user); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": err.Error()})
		return
	}

	if ok := h.UserStore.Update(c, user); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to update user"})
		return
	}

	c.JSON(http.StatusOK, user)
}

func (h *UserHandler) GetById(c *gin.Context) {
	id, err := uuid.Parse(c.Param("user_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "invalid user_id"})
		return
	}

	user, ok := h.UserStore.GetById(c, id)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"message": "user not found"})
		return
	}

	c.JSON(http.StatusOK, user)
}

func (h *UserHandler) Update(c *gin.Context) {
	id, err := uuid.Parse(c.Param("user_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": "invalid user_id"})
		return
	}

	var req UserUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": fmt.Sprintf("failed to parse request: %s", err),
		})
		return
	}
	if req.Status != nil {
		if _, ok := parseStatus(*req.Status); !ok {
			c.JSON(http.StatusBadRequest, gin.H{"message": "invalid status"})
			return
		}
	}

	user, ok := h.UserStore.GetById(c, id)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"message": "user not found"})
		return
	}

	if err := req.applyToUser(user); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": err.Error()})
		return
	}

	if ok := h.UserStore.Update(c, user); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to update user"})
		return
	}

	c.JSON(http.StatusOK, user)
}
