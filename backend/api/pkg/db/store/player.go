package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
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

type PlayerFilters struct {
	GameId *uuid.UUID
	UserId *uuid.UUID
	Limit  int
	Offset int
}

func (s *PlayerStore) List(ctx context.Context, filters PlayerFilters) ([]Player, bool) {
	log.Debug().
		Str("store", "player").
		Str("op", "list").
		Msg("db operation")

	limit := filters.Limit
	if limit <= 0 {
		limit = 100
	}
	offset := filters.Offset
	if offset < 0 {
		offset = 0
	}

	whereClause, args := buildPlayerWhereClause(filters)
	limitIndex := len(args) + 1
	offsetIndex := len(args) + 2
	query := fmt.Sprintf(
		"%s%s ORDER BY created_at DESC LIMIT $%d OFFSET $%d",
		playerSelectQuery,
		whereClause,
		limitIndex,
		offsetIndex,
	)
	args = append(args, limit, offset)

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, false
	}
	defer rows.Close()

	items := make([]Player, 0)
	for rows.Next() {
		entry, err := scanPlayer(rows)
		if err != nil {
			return nil, false
		}
		items = append(items, entry)
	}
	if err := rows.Err(); err != nil {
		return nil, false
	}
	return items, true
}

func (s *PlayerStore) Count(ctx context.Context, filters PlayerFilters) (int, bool) {
	log.Debug().
		Str("store", "player").
		Str("op", "count").
		Msg("db operation")

	whereClause, args := buildPlayerWhereClause(filters)
	query := "SELECT COUNT(*) FROM players" + whereClause

	var total int
	err := s.db.QueryRowContext(ctx, query, args...).Scan(&total)
	if err != nil {
		return 0, false
	}
	return total, true
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

func (s *PlayerStore) CountByGameID(ctx context.Context, gameID uuid.UUID) (int, bool) {
	log.Debug().
		Str("store", "player").
		Str("op", "count_by_game_id").
		Str("game_id", gameID.String()).
		Msg("db operation")

	var total int
	if err := s.db.QueryRowContext(ctx, `SELECT COUNT(*) FROM players WHERE game_id = $1`, gameID).Scan(&total); err != nil {
		return 0, false
	}
	return total, true
}

func buildPlayerWhereClause(filters PlayerFilters) (string, []any) {
	clauses := make([]string, 0, 2)
	args := make([]any, 0, 2)

	if filters.GameId != nil {
		args = append(args, *filters.GameId)
		clauses = append(clauses, fmt.Sprintf("game_id = $%d", len(args)))
	}
	if filters.UserId != nil {
		args = append(args, *filters.UserId)
		clauses = append(clauses, fmt.Sprintf("user_id = $%d", len(args)))
	}

	if len(clauses) == 0 {
		return "", args
	}
	return " WHERE " + strings.Join(clauses, " AND "), args
}
