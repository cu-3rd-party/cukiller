package graphgetter

import (
	"cukiller/internal/shared"
	"fmt"
	"math/rand/v2"
	"sync"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

var db = conf.ConfigDatabase.MustGetDb()

// InitDb is called on startup
func InitDb() {
	go shared.MonitorDbConnection(db, time.Second*time.Duration(conf.DbPingDelay))
}

type AnonEdge struct {
	From int `json:"from"`
	To   int `json:"to"`
}

func GetKillEventConnections() ([]AnonEdge, error) {
	ok, gameId := shared.GetActiveGame(db)
	if ok {
		return nil, fmt.Errorf("there's no active game")
	}
	rows, err := db.Query(`
        SELECT killer_id, victim_id
        FROM kill_events
        WHERE status = 'pending' AND game_id = $1
    `, gameId)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Анонимизация: UUID → int
	anonMap := make(map[uuid.UUID]int)
	var mutex sync.Mutex

	getAnon := func(id uuid.UUID) int {
		mutex.Lock()
		defer mutex.Unlock()
		if v, ok := anonMap[id]; ok {
			return v
		}
		anonMap[id] = rand.Int()
		return anonMap[id]
	}

	var edges []AnonEdge

	for rows.Next() {
		var killerId uuid.UUID
		var victimId uuid.UUID

		if err := rows.Scan(&killerId, &victimId); err != nil {
			return nil, err
		}

		edges = append(edges, AnonEdge{
			From: getAnon(killerId),
			To:   getAnon(victimId),
		})
	}

	return edges, nil
}
