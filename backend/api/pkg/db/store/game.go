package store

import (
	"context"
	"database/sql"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

// Game represents game object in the database
type Game struct {
	Id        uuid.UUID
	CreatedAt time.Time
	UpdatedAt time.Time
	Name      string
	StartDate sql.NullTime
	EndDate   sql.NullTime
}

func DefaultGame() Game {
	return Game{
		Id:        uuid.New(),
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		Name:      "",
		StartDate: sql.NullTime{},
		EndDate:   sql.NullTime{},
	}
}

// GameStore provides CRUD access to database
type GameStore struct {
	db *sql.DB
}

func NewGameStore(db *sql.DB) GameStore {
	return GameStore{db: db}
}

func (s *GameStore) Create(ctx context.Context, entry *Game) bool {
	const query = `
		INSERT INTO games (
			id,
			name,
			start_date,
			end_date
		) VALUES (
			$1, $2, $3, $4
		)
		RETURNING id, created_at, updated_at
	`

	log.Debug().
		Str("store", "game").
		Str("op", "create").
		Str("name", entry.Name).
		Msg("db operation")

	err := s.db.QueryRowContext(
		ctx,
		query,
		entry.Id,
		entry.Name,
		entry.StartDate,
		entry.EndDate,
	).Scan(&entry.Id, &entry.CreatedAt, &entry.UpdatedAt)

	return err == nil
}

const gameSelectQuery = `
	SELECT
		id,
		created_at,
		updated_at,
		name,
		start_date,
		end_date
	FROM games
`

type gameRowScanner interface {
	Scan(dest ...any) error
}

func scanGame(row gameRowScanner) (Game, error) {
	var entry Game
	err := row.Scan(
		&entry.Id,
		&entry.CreatedAt,
		&entry.UpdatedAt,
		&entry.Name,
		&entry.StartDate,
		&entry.EndDate,
	)
	return entry, err
}

func (s *GameStore) GetById(ctx context.Context, id uuid.UUID) (*Game, bool) {
	log.Debug().
		Str("store", "game").
		Str("op", "get_by_id").
		Str("id", id.String()).
		Msg("db operation")

	row := s.db.QueryRowContext(ctx, gameSelectQuery+`
	WHERE id = $1`, id)
	entry, err := scanGame(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *GameStore) Update(ctx context.Context, entry *Game) bool {
	const query = `
		UPDATE games SET
			name = $1,
			start_date = $2,
			end_date = $3,
			updated_at = CURRENT_TIMESTAMP
		WHERE id = $4
	`

	log.Debug().
		Str("store", "game").
		Str("op", "update").
		Str("id", entry.Id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(
		ctx,
		query,
		entry.Name,
		entry.StartDate,
		entry.EndDate,
		entry.Id,
	)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}

func (s *GameStore) Delete(ctx context.Context, id uuid.UUID) bool {
	log.Debug().
		Str("store", "game").
		Str("op", "delete").
		Str("id", id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(ctx, `DELETE FROM games WHERE id = $1`, id)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}
