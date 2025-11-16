package main

import (
	"encoding/json"

	"github.com/stretchr/testify/assert"

	"testing"
)

func TestPlayerDataSimple(t *testing.T) {
	course := 1
	p, err := NewPlayerData(
		123,
		123,
		EducationTypeBachelor,
		&course,
		GroupNameDevelopment)
	assert.Nil(t, err)
	assert.NotNil(t, p)

	assert.Equal(t, p.TgId, 123)
	assert.Equal(t, p.Rating, 123)
	assert.Equal(t, p.Type, EducationTypeBachelor)
	assert.Equal(t, p.GroupName, GroupNameDevelopment)
	assert.Equal(t, p.CourseNumber, &course)
	assert.Equal(t, p.GetCourseNumber(), course)
}

func TestPlayerDataToString(t *testing.T) {
	course := 1
	p, err := NewPlayerData(
		123,
		123,
		EducationTypeBachelor,
		&course,
		GroupNameDevelopment)
	assert.Nil(t, err)
	assert.NotNil(t, p)

	assert.Equal(t, p.String(), "Player{TgId: 123, Rating: 123, Type: бакалавр, Course: 1, Group: Разработка}")
}

func TestPlayerDataJson(t *testing.T) {
	jsonStr := `{"tg_id": 987654321, "rating": 1600, "type": "магистр", "group_name": "ИИ"}`
	var player PlayerData
	err := json.Unmarshal([]byte(jsonStr), &player)
	assert.Nil(t, err)
	jsonData, err := json.MarshalIndent(player, "", "  ")
	assert.Nil(t, err)
	assert.JSONEq(t, jsonStr, string(jsonData))
}
