package main

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "github.com/lib/pq"
)

type QueueInfo struct {
	KillersQueue []int64 `json:"killers_queue"`
	VictimsQueue []int64 `json:"victims_queue"`
}

// MustGetDb returns a database connection
func MustGetDb() *sql.DB {
	connStr := fmt.Sprintf(
		"postgres://%s:%s@%s:%s/%s?sslmode=disable",
		conf.DbUser,
		conf.DbPassword,
		conf.DbHost,
		conf.DbPort,
		conf.DbName,
	)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		panic("Failed to connect to database")
	}
	return db
}

// initDb is called on startup
func initDb(db *sql.DB) {
	populateQueues(db)
}

// populateQueues finds players who are in game but don't have kill events and puts them into KillerPool and VictimPool
func populateQueues(db *sql.DB) {
	populationTime := time.Now()
	var gameId []uint8
	err := db.QueryRow(`SELECT id FROM games WHERE end_date ISNULL`).Scan(&gameId)
	if err != nil {
		if !errors.Is(err, sql.ErrNoRows) {
			logger.Error("Error querying active game: %v", err)
		}
		return
	}

	// --- Populate KillerPool ---
	killerRows, err := db.Query(`
        SELECT u.tg_id, u.rating, u.type, u.course_number, u.group_name 
        FROM users u
        LEFT JOIN kill_events k ON u.id = k.killer_user_id AND k.game_id = $1
        WHERE u.is_in_game = TRUE AND k.id IS NULL
    `, gameId)
	if err != nil {
		logger.Error("Error querying potential killers: %v", err)
		return
	}
	defer killerRows.Close()

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
	victimRows, err := db.Query(`
        SELECT u.tg_id, u.rating, u.type, u.course_number, u.group_name 
        FROM users u
        LEFT JOIN kill_events k ON u.id = k.victim_user_id AND k.game_id = $1
        WHERE u.is_in_game = TRUE AND k.id IS NULL
    `, gameId)
	if err != nil {
		logger.Error("Error querying potential victims: %v", err)
		return
	}
	defer victimRows.Close()

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
}
