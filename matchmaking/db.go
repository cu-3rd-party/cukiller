package main

import (
	"database/sql"
	"errors"
	"fmt"
	"log"

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
	var gameId int
	err := db.QueryRow(`SELECT id, start_date, end_date FROM games WHERE end_date ISNULL`).Scan(&gameId)
	if err != nil {
		if !errors.Is(err, sql.ErrNoRows) {
			log.Printf("Error querying active game: %v", err)
		}
		return
	}
	killerRows, err := db.Query(`
        SELECT u.tg_id, u.global_rating, u.type, u.course_number, u.group_name 
        FROM users u
        LEFT JOIN kill_events k ON u.id = k.killer_user_id AND k.game_id = ?
        WHERE u.is_in_game = TRUE AND k.id IS NULL
    `, gameId)
	if err != nil {
		log.Printf("Error querying potential killers: %v", err)
		return
	}
	defer killerRows.Close()

	for killerRows.Next() {
		var playerId int
		if err = killerRows.Scan(&playerId); err != nil {
			continue
		}
		KillerPool[playerId] = QueuePlayer{TgId: playerId}
	}

	victimRows, err := db.Query(`
        SELECT u.id 
        FROM users u
        LEFT JOIN kill_events k ON u.id = k.victim_user_id AND k.game_id = ?
        WHERE u.is_in_game = TRUE AND k.id IS NULL
    `, gameId)
	if err != nil {
		log.Printf("Error querying potential victims: %v", err)
		return
	}
	defer victimRows.Close()

	for victimRows.Next() {
		var playerId int
		if err = victimRows.Scan(&playerId); err != nil {
			continue
		}
		VictimPool.Add(playerId)
	}
}
