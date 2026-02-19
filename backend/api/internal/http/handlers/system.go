package handlers

import (
	"fmt"
	"net/http"

	"cukiller/api/pkg/db/store"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type SystemHandler struct {
	ChatStore *store.ChatStore
	UserStore *store.UserStore
}

type BootstrapRequest struct {
	AdminChatId      int64   `json:"admin_chat_id" binding:"required"`
	DiscussionChatId int64   `json:"discussion_chat_id" binding:"required"`
	AdminTgIds       []int64 `json:"admin_tg_ids" binding:"required,min=1"`
}

func (h *SystemHandler) Bootstrap(c *gin.Context) {
	var req BootstrapRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": fmt.Sprintf("failed to parse/validate body: %s", err),
		})
		return
	}

	if err := h.upsertChat(c, req.AdminChatId, "logs"); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.upsertChat(c, req.DiscussionChatId, "discussion"); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	for _, tgID := range req.AdminTgIds {
		if err := h.upsertAdmin(c, tgID); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
	}

	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func (h *SystemHandler) upsertChat(c *gin.Context, chatId int64, key string) error {
	chat := store.Chat{
		ChatId: chatId,
		Key:    key,
	}
	if existing, ok := h.ChatStore.GetByChatIdAndKey(c, chatId, key); ok {
		chat.Id = existing.Id
	} else {
		chat.Id = uuid.New()
	}
	if ok := h.ChatStore.Upsert(c, &chat); !ok {
		return fmt.Errorf("failed to upsert chat key=%q chatId=%d", key, chatId)
	}
	return nil
}

func (h *SystemHandler) upsertAdmin(c *gin.Context, tgID int64) error {
	user := store.User{
		TgId:    tgID,
		IsAdmin: true,
	}
	if existing, ok := h.UserStore.GetByTgId(c, tgID); ok {
		user.Id = existing.Id
	} else {
		user.Id = uuid.New()
	}
	if ok := h.UserStore.Upsert(c, &user); !ok {
		return fmt.Errorf("failed to upsert admin tg_id=%d", tgID)
	}
	return nil
}
