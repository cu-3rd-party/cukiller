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
	Id        uuid.UUID    `json:"id"`
	CreatedAt time.Time    `json:"created_at"`
	UpdatedAt time.Time    `json:"updated_at"`
	Name      string       `json:"name"`
	StartDate sql.NullTime `json:"start_date"`
	EndDate   sql.NullTime `json:"end_date"`
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

func (s *GameStore) List(ctx context.Context, status *string, limit, offset int) ([]Game, bool) {
	query := gameSelectQuery
	args := []any{}
	if status != nil {
		filter, ok := gameStatusFilter(*status)
		if !ok {
			return nil, false
		}
		query += " WHERE " + filter
	}
	query += " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
	args = append(args, limit, offset)

	log.Debug().
		Str("store", "game").
		Str("op", "list").
		Int("limit", limit).
		Int("offset", offset).
		Msg("db operation")

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, false
	}
	defer rows.Close()

	games := []Game{}
	for rows.Next() {
		entry, err := scanGame(rows)
		if err != nil {
			return nil, false
		}
		games = append(games, entry)
	}
	if err := rows.Err(); err != nil {
		return nil, false
	}
	return games, true
}

func (s *GameStore) Count(ctx context.Context, status *string) (int, bool) {
	query := "SELECT COUNT(*) FROM games"
	if status != nil {
		filter, ok := gameStatusFilter(*status)
		if !ok {
			return 0, false
		}
		query += " WHERE " + filter
	}

	log.Debug().
		Str("store", "game").
		Str("op", "count").
		Msg("db operation")

	var total int
	if err := s.db.QueryRowContext(ctx, query).Scan(&total); err != nil {
		return 0, false
	}
	return total, true
}

func (s *GameStore) GetActive(ctx context.Context) (*Game, bool) {
	log.Debug().
		Str("store", "game").
		Str("op", "get_active").
		Msg("db operation")

	row := s.db.QueryRowContext(ctx, gameSelectQuery+`
	WHERE start_date IS NOT NULL AND end_date IS NULL
	ORDER BY start_date DESC
	LIMIT 1`)
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

func gameStatusFilter(status string) (string, bool) {
	switch status {
	case "scheduled":
		return "start_date IS NULL", true
	case "active":
		return "start_date IS NOT NULL AND end_date IS NULL", true
	case "completed":
		return "end_date IS NOT NULL", true
	default:
		return "", false
	}
}
