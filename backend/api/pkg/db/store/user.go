package store

import (
	"context"
	"database/sql"
	"errors"
	"time"

	"github.com/google/uuid"
)

// User represents user object in the database
type User struct {
	Id                 uuid.UUID
	CreatedAt          time.Time
	UpdatedAt          time.Time
	TgId               uint64
	TgUsername         string
	Type               string
	CourseNumber       uint8
	GroupName          string
	IsInGame           bool
	IsAdmin            bool
	Photo              string
	AboutUser          string
	Status             string
	AllowHuggingOnKill bool
	ExitCooldownUntil  time.Time
	GivenName          string
	FamilyName         string
	FamilyNameRequired bool
}

func DefaultUser() User {
	return User{
		Id:                 uuid.Nil,
		CreatedAt:          time.Now(),
		UpdatedAt:          time.Now(),
		TgId:               0,
		TgUsername:         "",
		Type:               "",
		CourseNumber:       0,
		GroupName:          "",
		IsInGame:           false,
		IsAdmin:            false,
		Photo:              "",
		AboutUser:          "",
		Status:             "",
		AllowHuggingOnKill: false,
		ExitCooldownUntil:  time.Time{},
		GivenName:          "",
		FamilyName:         "",
		FamilyNameRequired: false,
	}
}

// UserStore provides CRUD access to database
type UserStore struct {
	db *sql.DB
}

func nullableString(value string) sql.NullString {
	if value == "" {
		return sql.NullString{Valid: false}
	}
	return sql.NullString{String: value, Valid: true}
}

func (s *UserStore) Create(ctx context.Context, entry *User) bool {
	const query = `
		INSERT INTO users (
		    id,
			tg_id,
			tg_username,
			type,
			course_number,
			group_name,
			is_in_game,
			is_admin,
			photo,
			about_user,
			status,
			allow_hugging_on_kill,
			exit_cooldown_until,
			given_name,
			family_name,
			family_name_required
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8,
			$9, $10, $11, $12, $13, $14, $15, $16
		)
		RETURNING id, created_at, updated_at
	`

	err := s.db.QueryRowContext(
		ctx,
		query,
		entry.Id,
		entry.TgId,
		nullableString(entry.TgUsername),
		entry.Type,
		entry.CourseNumber,
		entry.GroupName,
		entry.IsInGame,
		entry.IsAdmin,
		entry.Photo,
		entry.AboutUser,
		entry.Status,
		entry.AllowHuggingOnKill,
		entry.ExitCooldownUntil,
		entry.GivenName,
		entry.FamilyName,
		entry.FamilyNameRequired,
	).Scan(&entry.Id, &entry.CreatedAt, &entry.UpdatedAt)

	return err == nil
}

const userSelectQuery = `
	SELECT
		id,
		created_at,
		updated_at,
		tg_id,
		tg_username,
		type,
		course_number,
		group_name,
		is_in_game::text,
		is_admin,
		photo,
		about_user,
		status,
		allow_hugging_on_kill,
		exit_cooldown_until,
		given_name,
		family_name,
		family_name_required
	FROM users
`

type userRowScanner interface {
	Scan(dest ...any) error
}

func scanUser(row userRowScanner) (User, error) {
	var entry User
	var tgUsername sql.NullString
	err := row.Scan(
		&entry.Id,
		&entry.CreatedAt,
		&entry.UpdatedAt,
		&entry.TgId,
		&tgUsername,
		&entry.Type,
		&entry.CourseNumber,
		&entry.GroupName,
		&entry.IsInGame,
		&entry.IsAdmin,
		&entry.Photo,
		&entry.AboutUser,
		&entry.Status,
		&entry.AllowHuggingOnKill,
		&entry.ExitCooldownUntil,
		&entry.GivenName,
		&entry.FamilyName,
		&entry.FamilyNameRequired,
	)
	if tgUsername.Valid {
		entry.TgUsername = tgUsername.String
	} else {
		entry.TgUsername = ""
	}
	return entry, err
}

func (s *UserStore) GetById(ctx context.Context, id uuid.UUID) (*User, bool) {
	row := s.db.QueryRowContext(ctx, userSelectQuery+`
	WHERE id = $1`, id)
	entry, err := scanUser(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *UserStore) GetByTgId(ctx context.Context, tgId uint64) (*User, bool) {
	row := s.db.QueryRowContext(ctx, userSelectQuery+`
	WHERE tg_id = $1`, tgId)
	entry, err := scanUser(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *UserStore) Update(ctx context.Context, entry *User) bool {
	const query = `
		UPDATE users SET
			tg_id = $1,
			tg_username = $2,
			type = $3,
			course_number = $4,
			group_name = $5,
			is_in_game = $6,
			is_admin = $7,
			photo = $8,
			about_user = $9,
			status = $10,
			allow_hugging_on_kill = $11,
			exit_cooldown_until = $12,
			given_name = $13,
			family_name = $14,
			family_name_required = $15,
			updated_at = CURRENT_TIMESTAMP
		WHERE id = $16
	`

	res, err := s.db.ExecContext(
		ctx,
		query,
		entry.TgId,
		nullableString(entry.TgUsername),
		entry.Type,
		entry.CourseNumber,
		entry.GroupName,
		entry.IsInGame,
		entry.IsAdmin,
		entry.Photo,
		entry.AboutUser,
		entry.Status,
		entry.AllowHuggingOnKill,
		entry.ExitCooldownUntil,
		entry.GivenName,
		entry.FamilyName,
		entry.FamilyNameRequired,
		entry.Id,
	)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}

func (s *UserStore) Delete(ctx context.Context, id uuid.UUID) bool {
	res, err := s.db.ExecContext(ctx, `DELETE FROM users WHERE id = $1`, id)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}
