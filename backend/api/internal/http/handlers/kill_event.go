package handlers

import (
	"fmt"
	"net/http"
	"strconv"
	"time"

	"cukiller/api/pkg/db/store"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

var killEventStatuses = map[string]struct{}{
	"pending":   {},
	"confirmed": {},
	"rejected":  {},
	"canceled":  {},
	"timeout":   {},
}

type KillEventHandler struct {
	KillEventStore *store.KillEventStore
}

type KillEventResponse struct {
	Id                uuid.UUID  `json:"id"`
	GameId            uuid.UUID  `json:"game_id"`
	KillerId          uuid.UUID  `json:"killer_id"`
	VictimId          uuid.UUID  `json:"victim_id"`
	KillerConfirmed   bool       `json:"killer_confirmed"`
	KillerConfirmedAt *time.Time `json:"killer_confirmed_at,omitempty"`
	VictimConfirmed   bool       `json:"victim_confirmed"`
	VictimConfirmedAt *time.Time `json:"victim_confirmed_at,omitempty"`
	Status            string     `json:"status"`
	ModeratorId       *uuid.UUID `json:"moderator_id,omitempty"`
	ModeratedAt       *time.Time `json:"moderated_at,omitempty"`
	IsApproved        bool       `json:"is_approved"`
	CreatedAt         time.Time  `json:"created_at"`
	UpdatedAt         time.Time  `json:"updated_at"`
}

type KillEventListResponse struct {
	Items  []KillEventResponse `json:"items"`
	Limit  int                 `json:"limit"`
	Offset int                 `json:"offset"`
}

type KillEventCreateRequest struct {
	GameId   uuid.UUID `json:"game_id" binding:"required"`
	KillerId uuid.UUID `json:"killer_id" binding:"required"`
	VictimId uuid.UUID `json:"victim_id" binding:"required"`
	Status   string    `json:"status"`
}

type KillEventUpdateRequest struct {
	KillerConfirmed   *bool      `json:"killer_confirmed"`
	KillerConfirmedAt *time.Time `json:"killer_confirmed_at"`
	VictimConfirmed   *bool      `json:"victim_confirmed"`
	VictimConfirmedAt *time.Time `json:"victim_confirmed_at"`
	Status            *string    `json:"status"`
	ModeratorId       *uuid.UUID `json:"moderator_id"`
	ModeratedAt       *time.Time `json:"moderated_at"`
	IsApproved        *bool      `json:"is_approved"`
}

type KillEventBulkUpdateRequest struct {
	Ids    []uuid.UUID            `json:"ids" binding:"required,min=1"`
	Update KillEventUpdateRequest `json:"update" binding:"required"`
}

func (h *KillEventHandler) List(c *gin.Context) {
	filters := store.KillEventFilters{
		Limit:  100,
		Offset: 0,
	}

	if gameID := c.Query("game_id"); gameID != "" {
		parsed, err := uuid.Parse(gameID)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid game_id"})
			return
		}
		filters.GameId = &parsed
	}
	if killerID := c.Query("killer_id"); killerID != "" {
		parsed, err := uuid.Parse(killerID)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid killer_id"})
			return
		}
		filters.KillerId = &parsed
	}
	if victimID := c.Query("victim_id"); victimID != "" {
		parsed, err := uuid.Parse(victimID)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid victim_id"})
			return
		}
		filters.VictimId = &parsed
	}
	if status := c.Query("status"); status != "" {
		if !isValidKillEventStatus(status) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid status"})
			return
		}
		filters.Status = &status
	}
	if updatedBefore := c.Query("updated_before"); updatedBefore != "" {
		parsed, err := time.Parse(time.RFC3339, updatedBefore)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid updated_before"})
			return
		}
		filters.UpdatedBefore = &parsed
	}
	if limit := c.Query("limit"); limit != "" {
		parsed, err := parsePositiveInt(limit)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid limit"})
			return
		}
		filters.Limit = parsed
	}
	if offset := c.Query("offset"); offset != "" {
		parsed, err := parseNonNegativeInt(offset)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid offset"})
			return
		}
		filters.Offset = parsed
	}

	entries, ok := h.KillEventStore.List(c, filters)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list kill events"})
		return
	}

	items := make([]KillEventResponse, 0, len(entries))
	for i := range entries {
		items = append(items, killEventToResponse(&entries[i]))
	}

	c.JSON(http.StatusOK, KillEventListResponse{
		Items:  items,
		Limit:  filters.Limit,
		Offset: filters.Offset,
	})
}

func (h *KillEventHandler) Create(c *gin.Context) {
	var req KillEventCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse request: %s", err)})
		return
	}

	status := "pending"
	if req.Status != "" {
		if !isValidKillEventStatus(req.Status) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid status"})
			return
		}
		status = req.Status
	}

	entry := store.KillEvent{
		Id:              uuid.New(),
		GameId:          req.GameId,
		KillerId:        req.KillerId,
		VictimId:        req.VictimId,
		Status:          status,
		KillerConfirmed: false,
		VictimConfirmed: false,
		IsApproved:      false,
	}

	if ok := h.KillEventStore.Create(c, &entry); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to create kill event"})
		return
	}

	c.JSON(http.StatusCreated, killEventToResponse(&entry))
}

func (h *KillEventHandler) GetById(c *gin.Context) {
	killEventID, err := uuid.Parse(c.Param("kill_event_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid kill_event_id"})
		return
	}

	entry, ok := h.KillEventStore.GetById(c, killEventID)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "kill event not found"})
		return
	}

	c.JSON(http.StatusOK, killEventToResponse(entry))
}

func (h *KillEventHandler) Update(c *gin.Context) {
	killEventID, err := uuid.Parse(c.Param("kill_event_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid kill_event_id"})
		return
	}

	var req KillEventUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse request: %s", err)})
		return
	}

	if req.Status != nil && !isValidKillEventStatus(*req.Status) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid status"})
		return
	}

	entry, ok := h.KillEventStore.GetById(c, killEventID)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "kill event not found"})
		return
	}

	if req.KillerConfirmed != nil {
		entry.KillerConfirmed = *req.KillerConfirmed
	}
	if req.KillerConfirmedAt != nil {
		entry.KillerConfirmedAt.Time = *req.KillerConfirmedAt
		entry.KillerConfirmedAt.Valid = true
	}
	if req.VictimConfirmed != nil {
		entry.VictimConfirmed = *req.VictimConfirmed
	}
	if req.VictimConfirmedAt != nil {
		entry.VictimConfirmedAt.Time = *req.VictimConfirmedAt
		entry.VictimConfirmedAt.Valid = true
	}
	if req.Status != nil {
		entry.Status = *req.Status
	}
	if req.ModeratorId != nil {
		entry.ModeratorId.UUID = *req.ModeratorId
		entry.ModeratorId.Valid = true
	}
	if req.ModeratedAt != nil {
		entry.ModeratedAt.Time = *req.ModeratedAt
		entry.ModeratedAt.Valid = true
	}
	if req.IsApproved != nil {
		entry.IsApproved = *req.IsApproved
	}

	if ok := h.KillEventStore.Update(c, entry); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update kill event"})
		return
	}

	entry, _ = h.KillEventStore.GetById(c, killEventID)
	c.JSON(http.StatusOK, killEventToResponse(entry))
}

func (h *KillEventHandler) BulkUpdate(c *gin.Context) {
	var req KillEventBulkUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse request: %s", err)})
		return
	}

	if req.Update.Status != nil && !isValidKillEventStatus(*req.Update.Status) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid status"})
		return
	}

	update := store.KillEventUpdateFields{
		KillerConfirmed:   req.Update.KillerConfirmed,
		KillerConfirmedAt: req.Update.KillerConfirmedAt,
		VictimConfirmed:   req.Update.VictimConfirmed,
		VictimConfirmedAt: req.Update.VictimConfirmedAt,
		Status:            req.Update.Status,
		ModeratorId:       req.Update.ModeratorId,
		ModeratedAt:       req.Update.ModeratedAt,
		IsApproved:        req.Update.IsApproved,
	}

	count, ok := h.KillEventStore.BulkUpdate(c, req.Ids, update)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "failed to bulk update kill events"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"count": count})
}

func killEventToResponse(entry *store.KillEvent) KillEventResponse {
	var killerConfirmedAt *time.Time
	if entry.KillerConfirmedAt.Valid {
		killerConfirmedAt = &entry.KillerConfirmedAt.Time
	}
	var victimConfirmedAt *time.Time
	if entry.VictimConfirmedAt.Valid {
		victimConfirmedAt = &entry.VictimConfirmedAt.Time
	}
	var moderatedAt *time.Time
	if entry.ModeratedAt.Valid {
		moderatedAt = &entry.ModeratedAt.Time
	}
	var moderatorId *uuid.UUID
	if entry.ModeratorId.Valid {
		moderatorId = &entry.ModeratorId.UUID
	}
	return KillEventResponse{
		Id:                entry.Id,
		GameId:            entry.GameId,
		KillerId:          entry.KillerId,
		VictimId:          entry.VictimId,
		KillerConfirmed:   entry.KillerConfirmed,
		KillerConfirmedAt: killerConfirmedAt,
		VictimConfirmed:   entry.VictimConfirmed,
		VictimConfirmedAt: victimConfirmedAt,
		Status:            entry.Status,
		ModeratorId:       moderatorId,
		ModeratedAt:       moderatedAt,
		IsApproved:        entry.IsApproved,
		CreatedAt:         entry.CreatedAt,
		UpdatedAt:         entry.UpdatedAt,
	}
}

func isValidKillEventStatus(status string) bool {
	_, ok := killEventStatuses[status]
	return ok
}

func parsePositiveInt(value string) (int, error) {
	parsed, err := strconv.Atoi(value)
	if err != nil || parsed <= 0 {
		return 0, fmt.Errorf("invalid")
	}
	return parsed, nil
}

func parseNonNegativeInt(value string) (int, error) {
	parsed, err := strconv.Atoi(value)
	if err != nil || parsed < 0 {
		return 0, fmt.Errorf("invalid")
	}
	return parsed, nil
}
