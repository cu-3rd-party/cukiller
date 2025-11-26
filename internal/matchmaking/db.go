package matchmaking

import (
	"context"
	"cukiller/internal/shared"
	"database/sql"
	"errors"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

type QueueInfo struct {
	KillersQueue []int64 `json:"killers_queue"`
	VictimsQueue []int64 `json:"victims_queue"`
}

var db = conf.ConfigDatabase.MustGetDb()

// InitDb is called on startup
func InitDb() {
	go shared.MonitorDbConnection(db, time.Second*time.Duration(conf.DbPingDelay))
	_ = populateQueues(context.Background())
}

// populateQueues finds players who are in game but don't have kill events and puts them into KillerPool and VictimPool
func populateQueues(ctx context.Context) error {
	populationTime := time.Now()
	ok, gameId := GetActiveGame()
	if !ok {
		return nil
	}

	// --- Populate KillerPool ---
	killerRows, err := db.QueryContext(ctx, `
        SELECT u.tg_id, p.rating, u.type, u.course_number, u.group_name 
        FROM users u
        LEFT JOIN players p ON u.id = p.user_id AND p.game_id = $1
        LEFT JOIN kill_events k ON u.id = k.killer_user_id AND k.game_id = $1 AND k.status != 'confirmed'
        WHERE u.is_in_game = TRUE AND k.id IS NULL
    `, gameId)
	if err != nil {
		logger.Error("Error querying potential killers: %v", err)
		return nil
	}
	defer func(killerRows *sql.Rows) {
		err := killerRows.Close()
		if err != nil {
			logger.Error("Failed to close killerRows")
		}
	}(killerRows)

	for killerRows.Next() {
		var p QueuePlayer
		var courseNumber sql.NullInt64
		var groupName sql.NullString
		var educationType string

		err = killerRows.Scan(&p.TgId, &p.Rating, &educationType, &courseNumber, &groupName)
		if err != nil {
			logger.Error("Error scanning killer row: %v", err)
			continue
		}

		p.PlayerData.TgId = p.TgId

		p.Type = EducationTypeFromString(educationType)
		if courseNumber.Valid {
			num := int(courseNumber.Int64)
			p.CourseNumber = &num
		}
		if groupName.Valid {
			p.GroupName = GroupNameFromString(groupName.String)
		}
		p.JoinedAt = populationTime

		KillerPool[p.TgId] = p
	}

	// --- Populate VictimPool ---
	victimRows, err := db.QueryContext(ctx, `
        SELECT u.tg_id, p.rating, u.type, u.course_number, u.group_name 
        FROM users u
        LEFT JOIN players p ON u.id = p.user_id AND p.game_id = $1
        LEFT JOIN kill_events k ON u.id = k.victim_user_id AND k.game_id = $1 AND k.status != 'confirmed'
        WHERE u.is_in_game = TRUE AND k.id IS NULL
    `, gameId)
	if err != nil {
		logger.Error("Error querying potential victims: %v", err)
		return nil
	}
	defer func(victimRows *sql.Rows) {
		err := victimRows.Close()
		if err != nil {
			logger.Error("Failed to close victimRows")
		}
	}(victimRows)

	for victimRows.Next() {
		var p QueuePlayer
		var courseNumber sql.NullInt64
		var groupName sql.NullString
		var educationType string

		err = victimRows.Scan(&p.TgId, &p.Rating, &educationType, &courseNumber, &groupName)
		if err != nil {
			logger.Error("Error scanning victim row: %v", err)
			continue
		}

		p.PlayerData.TgId = p.TgId
		p.Type = EducationTypeFromString(educationType)
		if courseNumber.Valid {
			num := int(courseNumber.Int64)
			p.CourseNumber = &num
		}
		if groupName.Valid {
			p.GroupName = GroupNameFromString(groupName.String)
		}
		p.JoinedAt = populationTime

		VictimPool[p.TgId] = p
	}

	logger.Info("Queue initialization complete: %d killers, %d victims", len(KillerPool), len(VictimPool))

	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
	}

	return nil
}

func getUserIdByTgId(tgId uint64) (uuid.UUID, error) {
	row := db.QueryRow(`
		SELECT u.id
		FROM users u 
		WHERE u.tg_id = $1
		LIMIT 1
	`, tgId)

	var id uuid.UUID
	err := row.Scan(&id)
	if err != nil {
		logger.Error("Error getting user uid by tg_id %d: %v", tgId, err)
		return uuid.UUID{}, err
	}

	return id, nil
}

func PlayersWerePairedRecently(gameId uuid.UUID, killerTgId, victimTgId uint64) (ok bool) {
	defer func() {
		logger.Debug("PlayersWerePairedRecently(gameId=%s, killer=%d, victim=%d) returned %t",
			gameId, killerTgId, victimTgId, ok)
	}()
	killerId, err1 := getUserIdByTgId(killerTgId)
	victimId, err2 := getUserIdByTgId(victimTgId)
	logger.Debug("PlayersWerePairedRecently: killerId: %s, victimId: %s", killerId, victimId)

	if err1 != nil || err2 != nil {
		// не нашли пользователя => считаем что нет истории игр
		return false
	}

	// Выбираем последние N confirmed kill_events
	rows, err := db.Query(`
		SELECT killer_user_id, victim_user_id
		FROM kill_events
		WHERE status != 'pending' AND game_id = $1
		ORDER BY created_at DESC
		LIMIT $2
	`, gameId, conf.MatchHistoryCheckDepth)
	if err != nil {
		logger.Error("Error querying last kill events: %v", err)
		return false // безопасная логика
	}
	defer func(rows *sql.Rows) {
		err := rows.Close()
		if err != nil {
			logger.Error("Failed to close rows")
		}
	}(rows)

	for rows.Next() {
		var kId uuid.UUID
		var vId uuid.UUID

		err := rows.Scan(&kId, &vId)
		if err != nil {
			logger.Error("Error scanning kill event row: %v", err)
			continue
		}
		logger.Debug("Success scanning kill event row: %s -> %s", kId, vId)

		// Проверяем совпадение пары
		if kId == killerId && vId == victimId {
			// Они были вместе недавно
			return true
		}
	}

	// Среди последних 3 матчей не было этой пары
	return false
}

func ArePaired(gameId uuid.UUID, killerTgId, victimTgId uint64) (ok bool) {
	defer func() {
		logger.Debug("ArePaired(killer=%d, victim=%d) returned %t",
			killerTgId, victimTgId, ok)
	}()

	killerId, err1 := getUserIdByTgId(killerTgId)
	victimId, err2 := getUserIdByTgId(victimTgId)
	if err1 != nil || err2 != nil {
		// не нашли пользователя ⇒ считаем, что они не спарены
		return false
	}

	row := db.QueryRow(`
		SELECT 1
		FROM kill_events ke
		WHERE 
			ke.killer_user_id = $1 
			AND ke.victim_user_id = $2 
			AND ke.status = 'pending'
			AND ke.game_id = $3
		LIMIT 1
	`, killerId, victimId, gameId)

	var dummy int
	err := row.Scan(&dummy)

	if errors.Is(err, sql.ErrNoRows) {
		// Нет pending event — значит не спарены
		return false
	}

	if err != nil {
		// Ошибка SQL — безопасный return
		logger.Error("ArePaired SQL error: %v", err)
		return false
	}

	// Если нашли хотя бы одну строку — они спарены
	return true
}

func GetActiveGame() (bool, uuid.UUID) {
	row := db.QueryRow(`
	SELECT g.id FROM games g WHERE g.end_date IS NULL LIMIT 1
	`)
	var id uuid.UUID
	err := row.Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		// Нет активной игры
		return false, id
	}

	if err != nil {
		// Ошибка SQL — безопасный return
		logger.Error("GetActiveGame SQL error: %v", err)
		return false, id
	}

	// Если нашли хотя бы одну строку — игра идет и возвращаем ее айди
	return true, id
}
