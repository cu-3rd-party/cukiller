package stats

import (
	"cukiller/internal/shared"
	"database/sql"
	"errors"
	"strings"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

var db = conf.ConfigDatabase.MustGetDb()

var (
	errNoActiveGame  = errors.New("no active game")
	errInvalidStatus = errors.New("invalid status")
)

// InitDb is called on startup
func InitDb() {
	go shared.MonitorDbConnection(db, time.Second*time.Duration(conf.DbPingDelay))
}

type PlayerEntry struct {
	TgID       int64  `json:"tg_id"`
	Username   string `json:"username"`
	GivenName  string `json:"given_name"`
	FamilyName string `json:"family_name"`
	Rating     int    `json:"rating"`
	Kills      int    `json:"kills,omitempty"`
}

type UserStats struct {
	TgID       int64  `json:"tg_id"`
	Username   string `json:"username"`
	GivenName  string `json:"given_name"`
	FamilyName string `json:"family_name"`
	Rating     int    `json:"rating"`
	Kills      int    `json:"kills"`
	Deaths     int    `json:"deaths"`
}

func GetKillsTop(limit, offset int) ([]PlayerEntry, error) {
	ok, gameID := shared.GetActiveGame(db)
	if !ok {
		return nil, errNoActiveGame
	}

	rows, err := db.Query(`
		SELECT
			u.tg_id,
			COALESCE(u.tg_username, '') AS username,
			COALESCE(u.given_name, '') AS given_name,
			COALESCE(u.family_name, '') AS family_name,
			p.rating,
			COALESCE(k.kills, 0) AS kills
		FROM players p
		JOIN users u ON u.id = p.user_id
		LEFT JOIN (
			SELECT killer_id, COUNT(*) AS kills
			FROM kill_events
			WHERE game_id = $1 AND status = 'confirmed'
			GROUP BY killer_id
		) k ON k.killer_id = u.id
		WHERE p.game_id = $1
		ORDER BY COALESCE(k.kills, 0) DESC, p.rating DESC, u.tg_id ASC
		LIMIT $2 OFFSET $3
	`, gameID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var entries []PlayerEntry
	for rows.Next() {
		var entry PlayerEntry
		if err := rows.Scan(
			&entry.TgID,
			&entry.Username,
			&entry.GivenName,
			&entry.FamilyName,
			&entry.Rating,
			&entry.Kills,
		); err != nil {
			return nil, err
		}
		entries = append(entries, entry)
	}

	return entries, rows.Err()
}

func GetRatingTop(limit, offset int) ([]PlayerEntry, error) {
	ok, gameID := shared.GetActiveGame(db)
	if !ok {
		return nil, errNoActiveGame
	}

	rows, err := db.Query(`
		SELECT
			u.tg_id,
			COALESCE(u.tg_username, '') AS username,
			COALESCE(u.given_name, '') AS given_name,
			COALESCE(u.family_name, '') AS family_name,
			p.rating
		FROM players p
		JOIN users u ON u.id = p.user_id
		WHERE p.game_id = $1
		ORDER BY p.rating DESC, u.tg_id ASC
		LIMIT $2 OFFSET $3
	`, gameID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var entries []PlayerEntry
	for rows.Next() {
		var entry PlayerEntry
		if err := rows.Scan(
			&entry.TgID,
			&entry.Username,
			&entry.GivenName,
			&entry.FamilyName,
			&entry.Rating,
		); err != nil {
			return nil, err
		}
		entries = append(entries, entry)
	}

	return entries, rows.Err()
}

func GetKillEventsTotal(status string) (int, error) {
	ok, gameID := shared.GetActiveGame(db)
	if !ok {
		return 0, errNoActiveGame
	}

	status = strings.ToLower(status)
	if !isValidKillStatus(status) {
		return 0, errInvalidStatus
	}

	row := db.QueryRow(`
		SELECT COUNT(*)
		FROM kill_events
		WHERE game_id = $1 AND status = $2
	`, gameID, status)

	var total int
	if err := row.Scan(&total); err != nil {
		return 0, err
	}

	return total, nil
}

func GetUserStats(username string) (UserStats, error) {
	ok, gameID := shared.GetActiveGame(db)
	if !ok {
		return UserStats{}, errNoActiveGame
	}

	row := db.QueryRow(`
		SELECT
			u.id,
			u.tg_id,
			COALESCE(u.tg_username, '') AS username,
			COALESCE(u.given_name, '') AS given_name,
			COALESCE(u.family_name, '') AS family_name,
			p.rating
		FROM users u
		JOIN players p ON p.user_id = u.id AND p.game_id = $1
		WHERE LOWER(u.tg_username) = LOWER($2)
		LIMIT 1
	`, gameID, username)

	var userID uuid.UUID
	var stats UserStats
	if err := row.Scan(
		&userID,
		&stats.TgID,
		&stats.Username,
		&stats.GivenName,
		&stats.FamilyName,
		&stats.Rating,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return UserStats{}, sql.ErrNoRows
		}
		return UserStats{}, err
	}

	countRow := db.QueryRow(`
		SELECT
			COALESCE(SUM(CASE WHEN killer_id = $1 THEN 1 ELSE 0 END), 0) AS kills,
			COALESCE(SUM(CASE WHEN victim_id = $1 THEN 1 ELSE 0 END), 0) AS deaths
		FROM kill_events
		WHERE game_id = $2 AND status = 'confirmed'
	`, userID, gameID)

	if err := countRow.Scan(&stats.Kills, &stats.Deaths); err != nil {
		return UserStats{}, err
	}

	return stats, nil
}

func isValidKillStatus(status string) bool {
	switch status {
	case "pending", "confirmed", "rejected", "canceled", "timeout":
		return true
	default:
		return false
	}
}
