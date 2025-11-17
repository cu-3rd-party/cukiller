package internal

import (
	"encoding/json"
	"fmt"
	"strings"
)

// EducationType represents the type of education program
type EducationType uint8

const (
	EducationTypeUndefined EducationType = iota
	EducationTypeBachelor
	EducationTypeMaster
	EducationTypeSpecialist
	EducationTypeOther
)

// String returns the string representation of EducationType
func (e EducationType) String() string {
	switch e {
	case EducationTypeBachelor:
		return "бакалавр"
	case EducationTypeMaster:
		return "магистр"
	case EducationTypeSpecialist:
		return "специалитет"
	case EducationTypeOther:
		return "иное"
	default:
		return "не определено"
	}
}

// MarshalJSON implements json.Marshaler interface
func (e EducationType) MarshalJSON() ([]byte, error) {
	return json.Marshal(e.String())
}

// UnmarshalJSON implements json.Unmarshaler interface
func (e *EducationType) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err != nil {
		return err
	}

	*e = EducationTypeFromString(s)
	return nil
}

// EducationTypeFromString converts string to EducationType
func EducationTypeFromString(s string) EducationType {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "бакалавр", "bachelor":
		return EducationTypeBachelor
	case "магистр", "master":
		return EducationTypeMaster
	case "специалитет", "specialist":
		return EducationTypeSpecialist
	case "иное", "other":
		return EducationTypeOther
	default:
		return EducationTypeUndefined
	}
}

// GroupName represents the academic group specialization
type GroupName uint8

const (
	GroupNameUndefined GroupName = iota
	GroupNameDevelopment
	GroupNameAI
	GroupNameBusinessAnalytics
)

// String returns the string representation of GroupName
func (g GroupName) String() string {
	switch g {
	case GroupNameDevelopment:
		return "Разработка"
	case GroupNameAI:
		return "ИИ"
	case GroupNameBusinessAnalytics:
		return "бизнес-аналитика"
	default:
		return "неопределено"
	}
}

// MarshalJSON implements json.Marshaler interface
func (g GroupName) MarshalJSON() ([]byte, error) {
	return json.Marshal(g.String())
}

// UnmarshalJSON implements json.Unmarshaler interface
func (g *GroupName) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err != nil {
		return err
	}

	*g = GroupNameFromString(s)
	return nil
}

// GroupNameFromString converts string to GroupName
func GroupNameFromString(s string) GroupName {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "разработка", "development":
		return GroupNameDevelopment
	case "ии", "ai", "искусственный интеллект":
		return GroupNameAI
	case "бизнес-аналитика", "business-analytics", "business analytics":
		return GroupNameBusinessAnalytics
	default:
		return GroupNameUndefined
	}
}

// Validation constants
const (
	MinRating     = 0
	MaxRating     = 3000
	MinCourse     = 1
	MaxCourse     = 6
	DefaultRating = 1200
)

// PlayerData represents a player in the matchmaking system
type PlayerData struct {
	TgId         uint64        `json:"tg_id"`                   // telegram id of the player
	Rating       int           `json:"rating"`                  // elo rating of the player
	Type         EducationType `json:"type"`                    // education type
	CourseNumber *int          `json:"course_number,omitempty"` // course number (optional)
	GroupName    GroupName     `json:"group_name,omitempty"`    // group specialization (optional)
}

// NewPlayerData creates a new PlayerData with validation
func NewPlayerData(tgId uint64, rating int, educationType EducationType, courseNumber *int, groupName GroupName) (*PlayerData, error) {
	p := &PlayerData{
		TgId:         tgId,
		Rating:       rating,
		Type:         educationType,
		CourseNumber: courseNumber,
		GroupName:    groupName,
	}

	if err := p.Validate(); err != nil {
		return nil, err
	}

	return p, nil
}

// Validate validates player data
func (p *PlayerData) Validate() error {
	if p.TgId <= 0 {
		return fmt.Errorf("invalid telegram ID: %d", p.TgId)
	}

	if p.Rating < MinRating || p.Rating > MaxRating {
		return fmt.Errorf("rating %d out of range [%d, %d]", p.Rating, MinRating, MaxRating)
	}

	if p.Type == EducationTypeUndefined {
		return fmt.Errorf("education type is undefined")
	}

	if p.CourseNumber != nil {
		if *p.CourseNumber < MinCourse || *p.CourseNumber > MaxCourse {
			return fmt.Errorf("course number %d out of range [%d, %d]", *p.CourseNumber, MinCourse, MaxCourse)
		}
	}

	return nil
}

// WithDefaultRating sets default rating if current rating is invalid
func (p *PlayerData) WithDefaultRating() *PlayerData {
	if p.Rating < MinRating || p.Rating > MaxRating {
		p.Rating = DefaultRating
	}
	return p
}

// HasCourseNumber returns true if course number is set
func (p *PlayerData) HasCourseNumber() bool {
	return p.CourseNumber != nil
}

// GetCourseNumber returns course number or 0 if not set
func (p *PlayerData) GetCourseNumber() int {
	if p.CourseNumber != nil {
		return *p.CourseNumber
	}
	return 0
}

// SetCourseNumber safely sets course number with validation
func (p *PlayerData) SetCourseNumber(course int) error {
	if course < MinCourse || course > MaxCourse {
		return fmt.Errorf("course number %d out of range [%d, %d]", course, MinCourse, MaxCourse)
	}
	p.CourseNumber = &course
	return nil
}

// ClearCourseNumber clears the course number
func (p *PlayerData) ClearCourseNumber() {
	p.CourseNumber = nil
}

// String returns a string representation of PlayerData
func (p *PlayerData) String() string {
	courseInfo := "not set"
	if p.HasCourseNumber() {
		courseInfo = fmt.Sprintf("%d", p.GetCourseNumber())
	}

	return fmt.Sprintf(
		"Player{TgId: %d, Rating: %d, Type: %s, Course: %s, Group: %s}",
		p.TgId, p.Rating, p.Type.String(), courseInfo, p.GroupName.String(),
	)
}
