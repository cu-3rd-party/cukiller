package store

import (
	"context"
	"database/sql"
	"errors"
	"strconv"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

// PendingProfile represents pending profile object in the database
type PendingProfile struct {
	Id                 uuid.UUID
	CreatedAt          time.Time
	UpdatedAt          time.Time
	GivenName          string
	FamilyName         string
	Type               string
	CourseNumber       uint8
	GroupName          string
	Photo              string
	AboutUser          string
	Status             string
	IsNewProfile       bool
	Reason             string
	ChangedFields      []byte
	ChatId             int64
	MessageId          int64
	SubmittedUsername  string
	UserId             uuid.UUID
	ModeratorId        uuid.UUID
	AllowHuggingOnKill bool
}

func DefaultPendingProfile() PendingProfile {
	return PendingProfile{
		Id:                 uuid.New(),
		CreatedAt:          time.Now(),
		UpdatedAt:          time.Now(),
		GivenName:          "",
		FamilyName:         "",
		Type:               "",
		CourseNumber:       0,
		GroupName:          "",
		Photo:              "",
		AboutUser:          "",
		Status:             "pending",
		IsNewProfile:       false,
		Reason:             "",
		ChangedFields:      []byte("[]"),
		ChatId:             0,
		MessageId:          0,
		SubmittedUsername:  "",
		UserId:             uuid.New(),
		ModeratorId:        uuid.New(),
		AllowHuggingOnKill: false,
	}
}

// PendingProfileStore provides CRUD access to database
type PendingProfileStore struct {
	db *sql.DB
}

func NewPendingProfileStore(db *sql.DB) PendingProfileStore {
	return PendingProfileStore{db: db}
}

func (s *PendingProfileStore) Create(ctx context.Context, entry *PendingProfile) bool {
	const query = `
		INSERT INTO pending_profiles (
		    id,
			given_name,
			family_name,
			type,
			course_number,
			group_name,
			photo,
			about_user,
			status,
			is_new_profile,
			reason,
			changed_fields,
			chat_id,
			message_id,
			submitted_username,
			user_id,
			moderator_id,
			allow_hugging_on_kill
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9,
			$10, $11, $12, $13, $14, $15, $16,
			NULLIF($17, '00000000-0000-0000-0000-000000000000'::uuid),
			$18
		)
		RETURNING id, created_at, updated_at
	`

	log.Debug().
		Str("store", "pending_profile").
		Str("op", "create").
		Str("user_id", entry.UserId.String()).
		Msg("db operation")

	err := s.db.QueryRowContext(
		ctx,
		query,
		entry.Id,
		entry.GivenName,
		entry.FamilyName,
		entry.Type,
		entry.CourseNumber,
		entry.GroupName,
		entry.Photo,
		entry.AboutUser,
		entry.Status,
		entry.IsNewProfile,
		entry.Reason,
		entry.ChangedFields,
		entry.ChatId,
		entry.MessageId,
		entry.SubmittedUsername,
		entry.UserId,
		entry.ModeratorId,
		entry.AllowHuggingOnKill,
	).Scan(&entry.Id, &entry.CreatedAt, &entry.UpdatedAt)

	return err == nil
}

const pendingProfileSelectQuery = `
	SELECT
		id,
		created_at,
		updated_at,
		COALESCE(given_name, ''),
		COALESCE(family_name, ''),
		COALESCE(type, ''),
		COALESCE(course_number, 0),
		COALESCE(group_name, ''),
		COALESCE(photo, ''),
		COALESCE(about_user, ''),
		status,
		is_new_profile,
		COALESCE(reason, ''),
		COALESCE(changed_fields, '[]'::jsonb),
		COALESCE(chat_id, 0),
		COALESCE(message_id, 0),
		COALESCE(submitted_username, ''),
		user_id,
		COALESCE(moderator_id, '00000000-0000-0000-0000-000000000000'::uuid),
		allow_hugging_on_kill
	FROM pending_profiles
`

type pendingProfileRowScanner interface {
	Scan(dest ...any) error
}

func scanPendingProfile(row pendingProfileRowScanner) (PendingProfile, error) {
	var entry PendingProfile
	err := row.Scan(
		&entry.Id,
		&entry.CreatedAt,
		&entry.UpdatedAt,
		&entry.GivenName,
		&entry.FamilyName,
		&entry.Type,
		&entry.CourseNumber,
		&entry.GroupName,
		&entry.Photo,
		&entry.AboutUser,
		&entry.Status,
		&entry.IsNewProfile,
		&entry.Reason,
		&entry.ChangedFields,
		&entry.ChatId,
		&entry.MessageId,
		&entry.SubmittedUsername,
		&entry.UserId,
		&entry.ModeratorId,
		&entry.AllowHuggingOnKill,
	)
	return entry, err
}

func (s *PendingProfileStore) GetById(ctx context.Context, id uuid.UUID) (*PendingProfile, bool) {
	log.Debug().
		Str("store", "pending_profile").
		Str("op", "get_by_id").
		Str("id", id.String()).
		Msg("db operation")

	row := s.db.QueryRowContext(ctx, pendingProfileSelectQuery+`
	WHERE id = $1`, id)
	entry, err := scanPendingProfile(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *PendingProfileStore) GetByUserId(ctx context.Context, userId uuid.UUID) (*PendingProfile, bool) {
	log.Debug().
		Str("store", "pending_profile").
		Str("op", "get_by_user_id").
		Str("user_id", userId.String()).
		Msg("db operation")

	row := s.db.QueryRowContext(ctx, pendingProfileSelectQuery+`
	WHERE user_id = $1
	ORDER BY created_at DESC
	LIMIT 1`, userId)
	entry, err := scanPendingProfile(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

type PendingProfileFilter struct {
	Status string
	UserId *uuid.UUID
	Limit  int
	Offset int
}

func (s *PendingProfileStore) List(ctx context.Context, filter PendingProfileFilter) ([]PendingProfile, error) {
	log.Debug().
		Str("store", "pending_profile").
		Str("op", "list").
		Msg("db operation")

	var builder strings.Builder
	builder.WriteString(pendingProfileSelectQuery)
	builder.WriteString("\nWHERE 1=1")

	args := make([]any, 0, 4)
	argPos := 1

	if filter.Status != "" {
		builder.WriteString("\nAND status = $" + strconv.Itoa(argPos))
		args = append(args, filter.Status)
		argPos++
	}
	if filter.UserId != nil {
		builder.WriteString("\nAND user_id = $" + strconv.Itoa(argPos))
		args = append(args, *filter.UserId)
		argPos++
	}

	builder.WriteString("\nORDER BY created_at DESC")
	builder.WriteString("\nLIMIT $" + strconv.Itoa(argPos))
	args = append(args, filter.Limit)
	argPos++
	builder.WriteString("\nOFFSET $" + strconv.Itoa(argPos))
	args = append(args, filter.Offset)

	rows, err := s.db.QueryContext(ctx, builder.String(), args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	items := make([]PendingProfile, 0)
	for rows.Next() {
		entry, err := scanPendingProfile(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, entry)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return items, nil
}

func (s *PendingProfileStore) Update(ctx context.Context, entry *PendingProfile) bool {
	const query = `
		UPDATE pending_profiles SET
			given_name = $1,
			family_name = $2,
			type = $3,
			course_number = $4,
			group_name = $5,
			photo = $6,
			about_user = $7,
			status = $8,
			is_new_profile = $9,
			reason = $10,
			changed_fields = $11,
			chat_id = $12,
			message_id = $13,
			submitted_username = $14,
			user_id = $15,
			moderator_id = NULLIF($16, '00000000-0000-0000-0000-000000000000'::uuid),
			allow_hugging_on_kill = $17,
			updated_at = CURRENT_TIMESTAMP
		WHERE id = $18
	`

	log.Debug().
		Str("store", "pending_profile").
		Str("op", "update").
		Str("id", entry.Id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(
		ctx,
		query,
		entry.GivenName,
		entry.FamilyName,
		entry.Type,
		entry.CourseNumber,
		entry.GroupName,
		entry.Photo,
		entry.AboutUser,
		entry.Status,
		entry.IsNewProfile,
		entry.Reason,
		entry.ChangedFields,
		entry.ChatId,
		entry.MessageId,
		entry.SubmittedUsername,
		entry.UserId,
		entry.ModeratorId,
		entry.AllowHuggingOnKill,
		entry.Id,
	)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}

func (s *PendingProfileStore) Delete(ctx context.Context, id uuid.UUID) bool {
	log.Debug().
		Str("store", "pending_profile").
		Str("op", "delete").
		Str("id", id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(ctx, `DELETE FROM pending_profiles WHERE id = $1`, id)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}
