package store

import (
	"context"
	"database/sql"
	"errors"
	"time"

	"github.com/google/uuid"
	"github.com/rs/zerolog/log"
)

// Player represents player object in the database
type Player struct {
	Id        uuid.UUID
	CreatedAt time.Time
	UpdatedAt time.Time
	GameId    uuid.UUID
	UserId    uuid.UUID
	Rating    int
}

func DefaultPlayer() Player {
	return Player{
		Id:        uuid.New(),
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		GameId:    uuid.New(),
		UserId:    uuid.New(),
		Rating:    600,
	}
}

// PlayerStore provides CRUD access to database
type PlayerStore struct {
	db *sql.DB
}

func NewPlayerStore(db *sql.DB) PlayerStore {
	return PlayerStore{db: db}
}

func (s *PlayerStore) Create(ctx context.Context, entry *Player) bool {
	const query = `
		INSERT INTO players (
			id,
			game_id,
			user_id,
			rating
		) VALUES (
			$1, $2, $3, $4
		)
		RETURNING id, created_at, updated_at
	`

	log.Debug().
		Str("store", "player").
		Str("op", "create").
		Str("game_id", entry.GameId.String()).
		Str("user_id", entry.UserId.String()).
		Msg("db operation")

	err := s.db.QueryRowContext(
		ctx,
		query,
		entry.Id,
		entry.GameId,
		entry.UserId,
		entry.Rating,
	).Scan(&entry.Id, &entry.CreatedAt, &entry.UpdatedAt)

	return err == nil
}

const playerSelectQuery = `
	SELECT
		id,
		created_at,
		updated_at,
		game_id,
		user_id,
		rating
	FROM players
`

type playerRowScanner interface {
	Scan(dest ...any) error
}

func scanPlayer(row playerRowScanner) (Player, error) {
	var entry Player
	err := row.Scan(
		&entry.Id,
		&entry.CreatedAt,
		&entry.UpdatedAt,
		&entry.GameId,
		&entry.UserId,
		&entry.Rating,
	)
	return entry, err
}

func (s *PlayerStore) GetById(ctx context.Context, id uuid.UUID) (*Player, bool) {
	log.Debug().
		Str("store", "player").
		Str("op", "get_by_id").
		Str("id", id.String()).
		Msg("db operation")

	row := s.db.QueryRowContext(ctx, playerSelectQuery+`
	WHERE id = $1`, id)
	entry, err := scanPlayer(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *PlayerStore) GetByUserIdAndGameId(ctx context.Context, userId, gameId uuid.UUID) (*Player, bool) {
	log.Debug().
		Str("store", "player").
		Str("op", "get_by_user_id_and_game_id").
		Str("user_id", userId.String()).
		Str("game_id", gameId.String()).
		Msg("db operation")

	row := s.db.QueryRowContext(ctx, playerSelectQuery+`
	WHERE user_id = $1 AND game_id = $2`, userId, gameId)
	entry, err := scanPlayer(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *PlayerStore) Update(ctx context.Context, entry *Player) bool {
	const query = `
		UPDATE players SET
			game_id = $1,
			user_id = $2,
			rating = $3,
			updated_at = CURRENT_TIMESTAMP
		WHERE id = $4
	`

	log.Debug().
		Str("store", "player").
		Str("op", "update").
		Str("id", entry.Id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(
		ctx,
		query,
		entry.GameId,
		entry.UserId,
		entry.Rating,
		entry.Id,
	)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}

func (s *PlayerStore) Delete(ctx context.Context, id uuid.UUID) bool {
	log.Debug().
		Str("store", "player").
		Str("op", "delete").
		Str("id", id.String()).
		Msg("db operation")

	res, err := s.db.ExecContext(ctx, `DELETE FROM players WHERE id = $1`, id)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}
