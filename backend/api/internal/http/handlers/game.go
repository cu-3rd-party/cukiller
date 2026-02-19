package handlers

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"cukiller/api/pkg/db/store"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type GameHandler struct {
	GameStore   *store.GameStore
	UserStore   *store.UserStore
	PlayerStore *store.PlayerStore
}

type GameResponse struct {
	Id        uuid.UUID  `json:"id"`
	Name      string     `json:"name"`
	StartDate *time.Time `json:"start_date,omitempty"`
	EndDate   *time.Time `json:"end_date,omitempty"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
}

type GameListResponse struct {
	Items  []GameResponse `json:"items"`
	Limit  int            `json:"limit"`
	Offset int            `json:"offset"`
}

type CountResponse struct {
	Total int `json:"total"`
}

type GameCreateRequest struct {
	Name      string     `json:"name" binding:"required"`
	StartDate *time.Time `json:"start_date"`
	EndDate   *time.Time `json:"end_date"`
}

type OptionalTime struct {
	Time *time.Time
	Set  bool
}

func (ot *OptionalTime) UnmarshalJSON(b []byte) error {
	ot.Set = true
	if string(b) == "null" {
		ot.Time = nil
		return nil
	}
	var parsed time.Time
	if err := json.Unmarshal(b, &parsed); err != nil {
		return err
	}
	ot.Time = &parsed
	return nil
}

func (ot OptionalTime) ToNullTime() sql.NullTime {
	if ot.Time == nil {
		return sql.NullTime{Valid: false}
	}
	return sql.NullTime{Time: *ot.Time, Valid: true}
}

type GameUpdateRequest struct {
	Name      *string      `json:"name"`
	StartDate OptionalTime `json:"start_date"`
	EndDate   OptionalTime `json:"end_date"`
}

type GameUserListResponse struct {
	Items  []GameUserResponse `json:"items"`
	Limit  int                `json:"limit"`
	Offset int                `json:"offset"`
}

func (h *GameHandler) ListGames(c *gin.Context) {
	status, err := parseGameStatus(c.Query("status"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	limit, offset, err := parseLimitOffset(c)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	games, ok := h.GameStore.List(c, status, limit, offset)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list games"})
		return
	}
	items := make([]GameResponse, 0, len(games))
	for _, game := range games {
		items = append(items, toGameResponse(game))
	}
	c.JSON(http.StatusOK, GameListResponse{
		Items:  items,
		Limit:  limit,
		Offset: offset,
	})
}

func (h *GameHandler) CreateGame(c *gin.Context) {
	var req GameCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse request: %s", err)})
		return
	}
	game := store.Game{
		Id:   uuid.New(),
		Name: req.Name,
	}
	if req.StartDate != nil {
		game.StartDate = sql.NullTime{Time: *req.StartDate, Valid: true}
	}
	if req.EndDate != nil {
		game.EndDate = sql.NullTime{Time: *req.EndDate, Valid: true}
	}
	if ok := h.GameStore.Create(c, &game); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create game"})
		return
	}
	c.JSON(http.StatusCreated, toGameResponse(game))
}

func (h *GameHandler) CountGames(c *gin.Context) {
	status, err := parseGameStatus(c.Query("status"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	total, ok := h.GameStore.Count(c, status)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to count games"})
		return
	}
	c.JSON(http.StatusOK, CountResponse{Total: total})
}

func (h *GameHandler) GetActiveGame(c *gin.Context) {
	game, ok := h.GameStore.GetActive(c)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "no active game"})
		return
	}
	c.JSON(http.StatusOK, toGameResponse(*game))
}

func (h *GameHandler) GetGameById(c *gin.Context) {
	gameID, err := parseUUIDParam(c, "game_id")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	game, ok := h.GameStore.GetById(c, gameID)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "game not found"})
		return
	}
	c.JSON(http.StatusOK, toGameResponse(*game))
}

func (h *GameHandler) UpdateGame(c *gin.Context) {
	gameID, err := parseUUIDParam(c, "game_id")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	game, ok := h.GameStore.GetById(c, gameID)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "game not found"})
		return
	}
	var req GameUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse request: %s", err)})
		return
	}
	if req.Name != nil {
		game.Name = *req.Name
	}
	if req.StartDate.Set {
		game.StartDate = req.StartDate.ToNullTime()
	}
	if req.EndDate.Set {
		game.EndDate = req.EndDate.ToNullTime()
	}
	if ok := h.GameStore.Update(c, game); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update game"})
		return
	}
	c.JSON(http.StatusOK, toGameResponse(*game))
}

func (h *GameHandler) ListGameParticipants(c *gin.Context) {
	gameID, err := parseUUIDParam(c, "game_id")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if _, ok := h.GameStore.GetById(c, gameID); !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "game not found"})
		return
	}
	users, ok := h.UserStore.ListByGameID(c, gameID)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list participants"})
		return
	}
	items := make([]GameUserResponse, 0, len(users))
	for _, user := range users {
		items = append(items, toGameUserResponse(user))
	}
	c.JSON(http.StatusOK, GameUserListResponse{
		Items:  items,
		Limit:  len(items),
		Offset: 0,
	})
}

func (h *GameHandler) CountGameParticipants(c *gin.Context) {
	gameID, err := parseUUIDParam(c, "game_id")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if _, ok := h.GameStore.GetById(c, gameID); !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "game not found"})
		return
	}
	total, ok := h.PlayerStore.CountByGameID(c, gameID)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to count participants"})
		return
	}
	c.JSON(http.StatusOK, CountResponse{Total: total})
}

func parseGameStatus(raw string) (*string, error) {
	if raw == "" {
		return nil, nil
	}
	switch raw {
	case "scheduled", "active", "completed":
		return &raw, nil
	default:
		return nil, fmt.Errorf("invalid status")
	}
}

func toGameResponse(game store.Game) GameResponse {
	resp := GameResponse{
		Id:        game.Id,
		Name:      game.Name,
		CreatedAt: game.CreatedAt,
		UpdatedAt: game.UpdatedAt,
	}
	if game.StartDate.Valid {
		resp.StartDate = &game.StartDate.Time
	}
	if game.EndDate.Valid {
		resp.EndDate = &game.EndDate.Time
	}
	return resp
}

type GameUserResponse struct {
	Id                 uuid.UUID  `json:"id"`
	CreatedAt          time.Time  `json:"created_at"`
	UpdatedAt          time.Time  `json:"updated_at"`
	TgId               int64      `json:"tg_id"`
	TgUsername         string     `json:"tg_username,omitempty"`
	Type               string     `json:"type,omitempty"`
	CourseNumber       uint8      `json:"course_number,omitempty"`
	GroupName          string     `json:"group_name,omitempty"`
	IsInGame           bool       `json:"is_in_game"`
	IsAdmin            bool       `json:"is_admin"`
	Photo              string     `json:"photo,omitempty"`
	AboutUser          string     `json:"about_user,omitempty"`
	Status             string     `json:"status,omitempty"`
	AllowHuggingOnKill bool       `json:"allow_hugging_on_kill"`
	ExitCooldownUntil  *time.Time `json:"exit_cooldown_until,omitempty"`
	GivenName          string     `json:"given_name,omitempty"`
	FamilyName         string     `json:"family_name,omitempty"`
	FamilyNameRequired bool       `json:"family_name_required"`
}

func toGameUserResponse(user store.User) GameUserResponse {
	resp := GameUserResponse{
		Id:                 user.Id,
		CreatedAt:          user.CreatedAt,
		UpdatedAt:          user.UpdatedAt,
		TgId:               user.TgId,
		TgUsername:         user.TgUsername,
		Type:               user.Type,
		CourseNumber:       user.CourseNumber,
		GroupName:          user.GroupName,
		IsInGame:           user.IsInGame,
		IsAdmin:            user.IsAdmin,
		Photo:              user.Photo,
		AboutUser:          user.AboutUser,
		Status:             user.Status,
		AllowHuggingOnKill: user.AllowHuggingOnKill,
		GivenName:          user.GivenName,
		FamilyName:         user.FamilyName,
		FamilyNameRequired: user.FamilyNameRequired,
	}
	if !user.ExitCooldownUntil.IsZero() {
		resp.ExitCooldownUntil = &user.ExitCooldownUntil
	}
	return resp
}
