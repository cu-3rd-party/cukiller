package store

import (
	"context"
	"database/sql"
	"errors"
	"time"

	"github.com/google/uuid"
)

// KillEvent represents kill event object in the database
type KillEvent struct {
	Id                uuid.UUID
	CreatedAt         time.Time
	UpdatedAt         time.Time
	KillerConfirmed   bool
	KillerConfirmedAt sql.NullTime
	VictimConfirmed   bool
	VictimConfirmedAt sql.NullTime
	Status            string
	ModeratedAt       sql.NullTime
	IsApproved        bool
	GameId            uuid.UUID
	KillerId          uuid.UUID
	ModeratorId       uuid.NullUUID
	VictimId          uuid.UUID
}

func DefaultKillEvent() KillEvent {
	return KillEvent{
		Id:                uuid.Nil,
		CreatedAt:         time.Now(),
		UpdatedAt:         time.Now(),
		KillerConfirmed:   false,
		KillerConfirmedAt: sql.NullTime{},
		VictimConfirmed:   false,
		VictimConfirmedAt: sql.NullTime{},
		Status:            "pending",
		ModeratedAt:       sql.NullTime{},
		IsApproved:        false,
		GameId:            uuid.Nil,
		KillerId:          uuid.Nil,
		ModeratorId:       uuid.NullUUID{},
		VictimId:          uuid.Nil,
	}
}

// KillEventStore provides CRUD access to database
type KillEventStore struct {
	db *sql.DB
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
	res, err := s.db.ExecContext(ctx, `DELETE FROM kill_events WHERE id = $1`, id)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}
