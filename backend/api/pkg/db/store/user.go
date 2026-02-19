package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/lib/pq"
	"github.com/rs/zerolog/log"
)

// User represents user object in the database
type User struct {
	Id                 uuid.UUID
	CreatedAt          time.Time
	UpdatedAt          time.Time
	TgId               int64
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

func DefaultUser() *User {
	return &User{
		Id:                 uuid.New(),
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

func NewUserStore(db *sql.DB) UserStore {
	return UserStore{db: db}
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

	log.Debug().
		Str("store", "user").
		Str("op", "create").
		Int64("tg_id", entry.TgId).
		Msg("db operation")

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
	log.Debug().
		Str("store", "user").
		Str("op", "get_by_id").
		Str("id", id.String()).
		Msg("db operation")

	row := s.db.QueryRowContext(ctx, userSelectQuery+`
	WHERE id = $1`, id)
	entry, err := scanUser(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *UserStore) GetByTgId(ctx context.Context, tgId int64) (*User, bool) {
	log.Debug().
		Str("store", "user").
		Str("op", "get_by_tg_id").
		Int64("tg_id", tgId).
		Msg("db operation")

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

	log.Debug().
		Str("store", "user").
		Str("op", "update").
		Str("id", entry.Id.String()).
		Msg("db operation")

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
	log.Debug().
		Str("store", "user").
		Str("op", "delete").
		Str("id", id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(ctx, `DELETE FROM users WHERE id = $1`, id)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}

func (s *UserStore) ListByGameID(ctx context.Context, gameID uuid.UUID) ([]User, bool) {
	log.Debug().
		Str("store", "user").
		Str("op", "list_by_game_id").
		Str("game_id", gameID.String()).
		Msg("db operation")

	rows, err := s.db.QueryContext(ctx, userSelectQuery+`
	JOIN players p ON p.user_id = users.id
	WHERE p.game_id = $1
	ORDER BY users.created_at`, gameID)
	if err != nil {
		return nil, false
	}
	defer rows.Close()

	users := []User{}
	for rows.Next() {
		entry, err := scanUser(rows)
		if err != nil {
			return nil, false
		}
		users = append(users, entry)
	}
	if err := rows.Err(); err != nil {
		return nil, false
	}
	return users, true
}

func (s *UserStore) Upsert(ctx context.Context, entry *User) bool {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return false
	}

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
		ON CONFLICT (tg_id) DO UPDATE SET
			tg_username = EXCLUDED.tg_username,
			type = EXCLUDED.type,
			course_number = EXCLUDED.course_number,
			group_name = EXCLUDED.group_name,
			is_in_game = EXCLUDED.is_in_game,
			is_admin = EXCLUDED.is_admin,
			photo = EXCLUDED.photo,
			about_user = EXCLUDED.about_user,
			status = EXCLUDED.status,
			allow_hugging_on_kill = EXCLUDED.allow_hugging_on_kill,
			exit_cooldown_until = EXCLUDED.exit_cooldown_until,
			given_name = EXCLUDED.given_name,
			family_name = EXCLUDED.family_name,
			family_name_required = EXCLUDED.family_name_required,
			updated_at = CURRENT_TIMESTAMP
		RETURNING id, created_at, updated_at
	`

	log.Debug().
		Str("store", "user").
		Str("op", "upsert").
		Int64("tg_id", entry.TgId).
		Msg("db operation")

	err = tx.QueryRowContext(
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
	if err != nil {
		_ = tx.Rollback()
		return false
	}

	if err = tx.Commit(); err != nil {
		return false
	}

	return true
}

type UserListFilters struct {
	Status   string
	IsInGame *bool
	IsAdmin  *bool
	Limit    int
	Offset   int
}

func (s *UserStore) List(ctx context.Context, filters UserListFilters) ([]User, bool) {
	log.Debug().
		Str("store", "user").
		Str("op", "list").
		Msg("db operation")

	query := strings.Builder{}
	query.WriteString(userSelectQuery)
	args := make([]any, 0, 4)
	clauses := make([]string, 0, 3)

	if filters.Status != "" {
		clauses = append(clauses, fmt.Sprintf("status = $%d", len(args)+1))
		args = append(args, filters.Status)
	}
	if filters.IsInGame != nil {
		clauses = append(clauses, fmt.Sprintf("is_in_game = $%d", len(args)+1))
		args = append(args, *filters.IsInGame)
	}
	if filters.IsAdmin != nil {
		clauses = append(clauses, fmt.Sprintf("is_admin = $%d", len(args)+1))
		args = append(args, *filters.IsAdmin)
	}

	if len(clauses) > 0 {
		query.WriteString("\nWHERE ")
		query.WriteString(strings.Join(clauses, " AND "))
	}

	if filters.Limit <= 0 {
		filters.Limit = 100
	}
	if filters.Offset < 0 {
		filters.Offset = 0
	}
	args = append(args, filters.Limit, filters.Offset)
	query.WriteString(fmt.Sprintf("\nORDER BY created_at DESC LIMIT $%d OFFSET $%d", len(args)-1, len(args)))

	rows, err := s.db.QueryContext(ctx, query.String(), args...)
	if err != nil {
		return nil, false
	}
	defer rows.Close()

	users := make([]User, 0)
	for rows.Next() {
		entry, err := scanUser(rows)
		if err != nil {
			return nil, false
		}
		users = append(users, entry)
	}
	if err := rows.Err(); err != nil {
		return nil, false
	}
	return users, true
}

func (s *UserStore) Count(ctx context.Context, status string) (int, bool) {
	log.Debug().
		Str("store", "user").
		Str("op", "count").
		Str("status", status).
		Msg("db operation")

	query := "SELECT COUNT(*) FROM users"
	args := make([]any, 0, 1)
	if status != "" {
		query += " WHERE status = $1"
		args = append(args, status)
	}

	var total int
	err := s.db.QueryRowContext(ctx, query, args...).Scan(&total)
	if err != nil {
		return 0, false
	}
	return total, true
}

func (s *UserStore) GetByIds(ctx context.Context, ids []uuid.UUID) (map[uuid.UUID]User, bool) {
	log.Debug().
		Str("store", "user").
		Str("op", "get_by_ids").
		Int("count", len(ids)).
		Msg("db operation")

	users := make(map[uuid.UUID]User)
	if len(ids) == 0 {
		return users, true
	}

	rows, err := s.db.QueryContext(ctx, userSelectQuery+`
	WHERE id = ANY($1)`, pq.Array(ids))
	if err != nil {
		return nil, false
	}
	defer rows.Close()

	for rows.Next() {
		entry, err := scanUser(rows)
		if err != nil {
			return nil, false
		}
		users[entry.Id] = entry
	}
	if err := rows.Err(); err != nil {
		return nil, false
	}
	return users, true
}
