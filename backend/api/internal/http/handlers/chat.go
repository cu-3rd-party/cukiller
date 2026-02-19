package handlers

import (
	"fmt"
	"net/http"
	"strconv"

	"cukiller/api/pkg/db/store"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type ChatHandler struct {
	*store.ChatStore
}

type ChatCreateRequest struct {
	ChatId int64  `json:"chat_id" binding:"required"`
	Key    string `json:"key" binding:"required"`
}

func (h *ChatHandler) GetByKey(c *gin.Context) {
	key := c.Param("key")
	if key == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "key is required"})
		return
	}

	chat, ok := h.ChatStore.GetByKey(c, key)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"message": "chat not found"})
		return
	}

	c.JSON(http.StatusOK, chat)
}

func (h *ChatHandler) GetByChatId(c *gin.Context) {
	raw := c.Param("chat_id")
	chatId, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"message": fmt.Sprintf("invalid chat_id: %s", err)})
		return
	}

	chat, ok := h.ChatStore.GetByChatId(c, chatId)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"message": "chat not found"})
		return
	}

	c.JSON(http.StatusOK, chat)
}

func (h *ChatHandler) Create(c *gin.Context) {
	var req ChatCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": fmt.Sprintf("failed to parse request: %s", err),
		})
		return
	}

	chat := &store.Chat{
		Id:     uuid.New(),
		ChatId: req.ChatId,
		Key:    req.Key,
	}

	if ok := h.ChatStore.Create(c, chat); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to create chat"})
		return
	}

	c.JSON(http.StatusCreated, chat)
}
