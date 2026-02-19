package handlers

import (
	"cukiller/api/pkg/db/store"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

type SystemHandler struct {
	*store.ChatStore
	*store.UserStore
}

type BootstrapRequest struct {
	AdminChatId      int64   `json:"admin_chat_id"`
	DiscussionChatId int64   `json:"discussion_chat_id"`
	AdminTgIds       []int64 `json:"admin_tg_ids"`
}

func (h *SystemHandler) Bootstrap(c *gin.Context) {
	var request BootstrapRequest

	if err := c.ShouldBindBodyWithJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("failed to parse body: %s", err)})
		return
	}

	if ok := h.ChatStore.Upsert(c, store.DefaultChat().WithId(request.AdminChatId).WithKey("logs")); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upsert admin chat with id %d", request.AdminChatId)})
		return
	}
	if ok := h.ChatStore.Upsert(c, store.DefaultChat().WithId(request.DiscussionChatId).WithKey("discussion")); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upsert discussion chat with id %d", request.DiscussionChatId)})
		return
	}

	for _, tgId := range request.AdminTgIds {
		if ok := h.UserStore.Upsert(c, store.DefaultUser().WithTgId(tgId).WithAdmin(true)); !ok {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upsert admin with id %d", tgId)})
			return
		}
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}
