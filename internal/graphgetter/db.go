package graphgetter

import (
	"cukiller/internal/shared"
	"time"

	_ "github.com/lib/pq"
)

var db = conf.ConfigDatabase.MustGetDb()

// InitDb is called on startup
func InitDb() {
	go shared.MonitorDbConnection(db, time.Second*time.Duration(conf.DbPingDelay))
}
