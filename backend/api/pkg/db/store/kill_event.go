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

// KillEvent represents kill event object in the database
type KillEvent struct {
	Id                uuid.UUID     `json:"id"`
	CreatedAt         time.Time     `json:"created_at"`
	UpdatedAt         time.Time     `json:"updated_at"`
	KillerConfirmed   bool          `json:"killer_confirmed"`
	KillerConfirmedAt sql.NullTime  `json:"killer_confirmed_at"`
	VictimConfirmed   bool          `json:"victim_confirmed"`
	VictimConfirmedAt sql.NullTime  `json:"victim_confirmed_at"`
	Status            string        `json:"status"`
	ModeratedAt       sql.NullTime  `json:"moderated_at"`
	IsApproved        bool          `json:"is_approved"`
	GameId            uuid.UUID     `json:"game_id"`
	KillerId          uuid.UUID     `json:"killer_id"`
	ModeratorId       uuid.NullUUID `json:"moderator_id"`
	VictimId          uuid.UUID     `json:"victim_id"`
}

func DefaultKillEvent() KillEvent {
	return KillEvent{
		Id:                uuid.New(),
		CreatedAt:         time.Now(),
		UpdatedAt:         time.Now(),
		KillerConfirmed:   false,
		KillerConfirmedAt: sql.NullTime{},
		VictimConfirmed:   false,
		VictimConfirmedAt: sql.NullTime{},
		Status:            "pending",
		ModeratedAt:       sql.NullTime{},
		IsApproved:        false,
		GameId:            uuid.New(),
		KillerId:          uuid.New(),
		ModeratorId:       uuid.NullUUID{},
		VictimId:          uuid.New(),
	}
}

// KillEventStore provides CRUD access to database
type KillEventStore struct {
	db *sql.DB
}

func NewKillEventStore(db *sql.DB) KillEventStore {
	return KillEventStore{db: db}
}

func (s *KillEventStore) Create(ctx context.Context, entry *KillEvent) bool {
	const query = `
		INSERT INTO kill_events (
			id,
			killer_confirmed,
			killer_confirmed_at,
			victim_confirmed,
			victim_confirmed_at,
			status,
			moderated_at,
			is_approved,
			game_id,
			killer_id,
			moderator_id,
			victim_id
		) VALUES (
			$1, $2, $3, $4, $5, $6,
			$7, $8, $9, $10, $11, $12
		)
		RETURNING id, created_at, updated_at
	`

	log.Debug().
		Str("store", "kill_event").
		Str("op", "create").
		Str("game_id", entry.GameId.String()).
		Msg("db operation")

	err := s.db.QueryRowContext(
		ctx,
		query,
		entry.Id,
		entry.KillerConfirmed,
		entry.KillerConfirmedAt,
		entry.VictimConfirmed,
		entry.VictimConfirmedAt,
		entry.Status,
		entry.ModeratedAt,
		entry.IsApproved,
		entry.GameId,
		entry.KillerId,
		entry.ModeratorId,
		entry.VictimId,
	).Scan(&entry.Id, &entry.CreatedAt, &entry.UpdatedAt)

	return err == nil
}

const killEventSelectQuery = `
	SELECT
		id,
		created_at,
		updated_at,
		killer_confirmed,
		killer_confirmed_at,
		victim_confirmed,
		victim_confirmed_at,
		status,
		moderated_at,
		is_approved,
		game_id,
		killer_id,
		moderator_id,
		victim_id
	FROM kill_events
`

type killEventRowScanner interface {
	Scan(dest ...any) error
}

func scanKillEvent(row killEventRowScanner) (KillEvent, error) {
	var entry KillEvent
	err := row.Scan(
		&entry.Id,
		&entry.CreatedAt,
		&entry.UpdatedAt,
		&entry.KillerConfirmed,
		&entry.KillerConfirmedAt,
		&entry.VictimConfirmed,
		&entry.VictimConfirmedAt,
		&entry.Status,
		&entry.ModeratedAt,
		&entry.IsApproved,
		&entry.GameId,
		&entry.KillerId,
		&entry.ModeratorId,
		&entry.VictimId,
	)
	return entry, err
}

func (s *KillEventStore) GetById(ctx context.Context, id uuid.UUID) (*KillEvent, bool) {
	log.Debug().
		Str("store", "kill_event").
		Str("op", "get_by_id").
		Str("id", id.String()).
		Msg("db operation")

	row := s.db.QueryRowContext(ctx, killEventSelectQuery+`
	WHERE id = $1`, id)
	entry, err := scanKillEvent(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *KillEventStore) Update(ctx context.Context, entry *KillEvent) bool {
	const query = `
		UPDATE kill_events SET
			killer_confirmed = $1,
			killer_confirmed_at = $2,
			victim_confirmed = $3,
			victim_confirmed_at = $4,
			status = $5,
			moderated_at = $6,
			is_approved = $7,
			game_id = $8,
			killer_id = $9,
			moderator_id = $10,
			victim_id = $11,
			updated_at = CURRENT_TIMESTAMP
		WHERE id = $12
	`

	log.Debug().
		Str("store", "kill_event").
		Str("op", "update").
		Str("id", entry.Id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(
		ctx,
		query,
		entry.KillerConfirmed,
		entry.KillerConfirmedAt,
		entry.VictimConfirmed,
		entry.VictimConfirmedAt,
		entry.Status,
		entry.ModeratedAt,
		entry.IsApproved,
		entry.GameId,
		entry.KillerId,
		entry.ModeratorId,
		entry.VictimId,
		entry.Id,
	)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}

func (s *KillEventStore) Delete(ctx context.Context, id uuid.UUID) bool {
	log.Debug().
		Str("store", "kill_event").
		Str("op", "delete").
		Str("id", id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(ctx, `DELETE FROM kill_events WHERE id = $1`, id)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}

type KillEventFilters struct {
	GameId        *uuid.UUID
	KillerId      *uuid.UUID
	VictimId      *uuid.UUID
	Status        *string
	UpdatedBefore *time.Time
	Limit         int
	Offset        int
}

func (s *KillEventStore) List(ctx context.Context, filters KillEventFilters) ([]KillEvent, bool) {
	log.Debug().
		Str("store", "kill_event").
		Str("op", "list").
		Msg("db operation")

	query := killEventSelectQuery + `
	WHERE 1=1`
	args := []any{}

	if filters.GameId != nil {
		args = append(args, *filters.GameId)
		query += "\n	AND game_id = $" + strconv.Itoa(len(args))
	}
	if filters.KillerId != nil {
		args = append(args, *filters.KillerId)
		query += "\n	AND killer_id = $" + strconv.Itoa(len(args))
	}
	if filters.VictimId != nil {
		args = append(args, *filters.VictimId)
		query += "\n	AND victim_id = $" + strconv.Itoa(len(args))
	}
	if filters.Status != nil {
		args = append(args, *filters.Status)
		query += "\n	AND status = $" + strconv.Itoa(len(args))
	}
	if filters.UpdatedBefore != nil {
		args = append(args, *filters.UpdatedBefore)
		query += "\n	AND updated_at < $" + strconv.Itoa(len(args))
	}

	query += "\n	ORDER BY updated_at DESC"

	if filters.Limit <= 0 {
		filters.Limit = 100
	}
	if filters.Offset < 0 {
		filters.Offset = 0
	}
	args = append(args, filters.Limit)
	query += "\n	LIMIT $" + strconv.Itoa(len(args))
	args = append(args, filters.Offset)
	query += "\n	OFFSET $" + strconv.Itoa(len(args))

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, false
	}
	defer rows.Close()

	var entries []KillEvent
	for rows.Next() {
		entry, err := scanKillEvent(rows)
		if err != nil {
			return nil, false
		}
		entries = append(entries, entry)
	}
	if err := rows.Err(); err != nil {
		return nil, false
	}
	return entries, true
}

type KillEventUpdateFields struct {
	KillerConfirmed   *bool
	KillerConfirmedAt *time.Time
	VictimConfirmed   *bool
	VictimConfirmedAt *time.Time
	Status            *string
	ModeratorId       *uuid.UUID
	ModeratedAt       *time.Time
	IsApproved        *bool
}

func (s *KillEventStore) BulkUpdate(ctx context.Context, ids []uuid.UUID, update KillEventUpdateFields) (int64, bool) {
	log.Debug().
		Str("store", "kill_event").
		Str("op", "bulk_update").
		Int("ids", len(ids)).
		Msg("db operation")

	if len(ids) == 0 {
		return 0, false
	}

	setParts := []string{}
	args := []any{}

	if update.KillerConfirmed != nil {
		args = append(args, *update.KillerConfirmed)
		setParts = append(setParts, "killer_confirmed = $"+strconv.Itoa(len(args)))
	}
	if update.KillerConfirmedAt != nil {
		args = append(args, *update.KillerConfirmedAt)
		setParts = append(setParts, "killer_confirmed_at = $"+strconv.Itoa(len(args)))
	}
	if update.VictimConfirmed != nil {
		args = append(args, *update.VictimConfirmed)
		setParts = append(setParts, "victim_confirmed = $"+strconv.Itoa(len(args)))
	}
	if update.VictimConfirmedAt != nil {
		args = append(args, *update.VictimConfirmedAt)
		setParts = append(setParts, "victim_confirmed_at = $"+strconv.Itoa(len(args)))
	}
	if update.Status != nil {
		args = append(args, *update.Status)
		setParts = append(setParts, "status = $"+strconv.Itoa(len(args)))
	}
	if update.ModeratorId != nil {
		args = append(args, *update.ModeratorId)
		setParts = append(setParts, "moderator_id = $"+strconv.Itoa(len(args)))
	}
	if update.ModeratedAt != nil {
		args = append(args, *update.ModeratedAt)
		setParts = append(setParts, "moderated_at = $"+strconv.Itoa(len(args)))
	}
	if update.IsApproved != nil {
		args = append(args, *update.IsApproved)
		setParts = append(setParts, "is_approved = $"+strconv.Itoa(len(args)))
	}

	if len(setParts) == 0 {
		return 0, false
	}

	setParts = append(setParts, "updated_at = CURRENT_TIMESTAMP")
	query := `
		UPDATE kill_events SET
			` + strings.Join(setParts, ", ") + `
		WHERE id = ANY($` + strconv.Itoa(len(args)+1) + `)
	`
	args = append(args, ids)

	res, err := s.db.ExecContext(ctx, query, args...)
	if err != nil {
		return 0, false
	}
	rows, err := res.RowsAffected()
	return rows, err == nil
}
