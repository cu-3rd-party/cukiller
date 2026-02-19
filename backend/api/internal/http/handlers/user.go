package handlers

import (
	"fmt"
	"net/http"

	"cukiller/api/pkg/db/store"

	"github.com/gin-gonic/gin"
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

	if !found {
		user = &store.User{}
	}

	req.applyToUser(user)

	if found {
		if ok := h.UserStore.Upsert(c, user); !ok {
			c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to update user"})
			return
		}
		c.JSON(http.StatusOK, user)
		return
	}

	if ok := h.UserStore.Create(c, user); !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"message": "failed to create user"})
		return
	}

	c.JSON(http.StatusCreated, user)
}
