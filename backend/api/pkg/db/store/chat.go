package store

import (
	"context"
	"database/sql"
	"errors"
	"time"

	"github.com/google/uuid"
)

// Chat represents chat object in the database
type Chat struct {
	Id        uuid.UUID
	CreatedAt time.Time
	UpdatedAt time.Time
	ChatId    int64
	Key       string
}

func DefaultChat() Chat {
	return Chat{
		Id:        uuid.Nil,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		ChatId:    0,
		Key:       "",
	}
}

// ChatStore provides CRUD access to database
type ChatStore struct {
	db *sql.DB
}

func (s *ChatStore) Create(ctx context.Context, entry *Chat) bool {
	const query = `
		INSERT INTO chats (
			id,
			chat_id,
			key
		) VALUES (
			$1, $2, $3
		)
		RETURNING id, created_at, updated_at
	`

	if entry == nil {
		return false
	}

	err := s.db.QueryRowContext(
		ctx,
		query,
		entry.Id,
		entry.ChatId,
		entry.Key,
	).Scan(&entry.Id, &entry.CreatedAt, &entry.UpdatedAt)

	return err == nil
}

const chatSelectQuery = `
	SELECT
		id,
		created_at,
		updated_at,
		chat_id,
		key
	FROM chats
`

type chatRowScanner interface {
	Scan(dest ...any) error
}

func scanChat(row chatRowScanner) (Chat, error) {
	var entry Chat
	err := row.Scan(
		&entry.Id,
		&entry.CreatedAt,
		&entry.UpdatedAt,
		&entry.ChatId,
		&entry.Key,
	)
	return entry, err
}

func (s *ChatStore) GetById(ctx context.Context, id uuid.UUID) (*Chat, bool) {
	row := s.db.QueryRowContext(ctx, chatSelectQuery+`
	WHERE id = $1`, id)
	entry, err := scanChat(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *ChatStore) GetByChatIdAndKey(ctx context.Context, chatId int64, key string) (*Chat, bool) {
	row := s.db.QueryRowContext(ctx, chatSelectQuery+`
	WHERE chat_id = $1 AND key = $2`, chatId, key)
	entry, err := scanChat(row)
	if errors.Is(err, sql.ErrNoRows) || err != nil {
		return nil, false
	}
	return &entry, true
}

func (s *ChatStore) Update(ctx context.Context, entry *Chat) bool {
	const query = `
		UPDATE chats SET
			chat_id = $1,
			key = $2,
			updated_at = CURRENT_TIMESTAMP
		WHERE id = $3
	`

	if entry == nil {
		return false
	}

	res, err := s.db.ExecContext(
		ctx,
		query,
		entry.ChatId,
		entry.Key,
		entry.Id,
	)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}

func (s *ChatStore) Delete(ctx context.Context, id uuid.UUID) bool {
	res, err := s.db.ExecContext(ctx, `DELETE FROM chats WHERE id = $1`, id)
	if err != nil {
		return false
	}
	rows, err := res.RowsAffected()
	return err == nil && rows > 0
}
