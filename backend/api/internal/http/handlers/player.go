package handlers

import (
	"fmt"
	"net/http"
	"time"

	"cukiller/api/pkg/db/store"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type PlayerHandler struct {
	*store.PlayerStore
}

type PlayerCreateRequest struct {
	UserId string `json:"user_id" binding:"required"`
	GameId string `json:"game_id" binding:"required"`
	Rating *int   `json:"rating"`
}

type PlayerUpdateRequest struct {
	Rating *int `json:"rating"`
}

type PlayerResponse struct {
	Id        uuid.UUID `json:"id"`
	UserId    uuid.UUID `json:"user_id"`
	GameId    uuid.UUID `json:"game_id"`
	Rating    int       `json:"rating"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type PlayerListResponse struct {
	Items  []PlayerResponse `json:"items"`
	Limit  int              `json:"limit"`
	Offset int              `json:"offset"`
}

func (h *PlayerHandler) List(c *gin.Context) {
	limit, offset, err := parseLimitOffset(c)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var filters store.PlayerFilters
	filters.Limit = limit
	filters.Offset = offset

	gameIdRaw := c.Query("game_id")
	if gameIdRaw != "" {
		gameId, err := uuid.Parse(gameIdRaw)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid game_id"})
			return
		}
		filters.GameId = &gameId
	}

	userIdRaw := c.Query("user_id")
	if userIdRaw != "" {
		userId, err := uuid.Parse(userIdRaw)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user_id"})
			return
		}
		filters.UserId = &userId
	}

	items, ok := h.PlayerStore.List(c, filters)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list players"})
		return
	}

	respItems := make([]PlayerResponse, 0, len(items))
	for _, item := range items {
		respItems = append(respItems, playerToResponse(item))
	}

	c.JSON(http.StatusOK, PlayerListResponse{
		Items:  respItems,
		Limit:  limit,
		Offset: offset,
	})
}

func (h *PlayerHandler) Create(c *gin.Context) {
	var req PlayerCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse/validate body: %s", err)})
		return
	}

	userId, err := uuid.Parse(req.UserId)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user_id"})
		return
	}
	gameId, err := uuid.Parse(req.GameId)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid game_id"})
		return
	}

	rating := 600
	if req.Rating != nil {
		rating = *req.Rating
	}

	entry := store.Player{
		Id:     uuid.New(),
		GameId: gameId,
		UserId: userId,
		Rating: rating,
	}
	if ok := h.PlayerStore.Create(c, &entry); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create player"})
		return
	}

	c.JSON(http.StatusCreated, playerToResponse(entry))
}

func (h *PlayerHandler) Count(c *gin.Context) {
	var filters store.PlayerFilters

	gameIdRaw := c.Query("game_id")
	if gameIdRaw != "" {
		gameId, err := uuid.Parse(gameIdRaw)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid game_id"})
			return
		}
		filters.GameId = &gameId
	}

	total, ok := h.PlayerStore.Count(c, filters)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to count players"})
		return
	}

	c.JSON(http.StatusOK, CountResponse{Total: total})
}

func (h *PlayerHandler) GetById(c *gin.Context) {
	playerId, err := parseUUIDParam(c, "player_id")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	entry, found := h.PlayerStore.GetById(c, playerId)
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "player not found"})
		return
	}

	c.JSON(http.StatusOK, playerToResponse(*entry))
}

func (h *PlayerHandler) Update(c *gin.Context) {
	playerId, err := parseUUIDParam(c, "player_id")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var req PlayerUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse/validate body: %s", err)})
		return
	}
	if req.Rating == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "rating is required"})
		return
	}

	entry, found := h.PlayerStore.GetById(c, playerId)
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "player not found"})
		return
	}

	entry.Rating = *req.Rating
	if ok := h.PlayerStore.Update(c, entry); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update player"})
		return
	}

	updated, ok := h.PlayerStore.GetById(c, playerId)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to fetch player"})
		return
	}

	c.JSON(http.StatusOK, playerToResponse(*updated))
}

func playerToResponse(entry store.Player) PlayerResponse {
	return PlayerResponse{
		Id:        entry.Id,
		UserId:    entry.UserId,
		GameId:    entry.GameId,
		Rating:    entry.Rating,
		CreatedAt: entry.CreatedAt,
		UpdatedAt: entry.UpdatedAt,
	}
}
