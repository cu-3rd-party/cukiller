package graphgetter

import (
	"cukiller/internal/shared"
	"time"
)

var db = conf.ConfigDatabase.MustGetDb()

// InitDb is called on startup
func InitDb() {
	go shared.MonitorDbConnection(db, time.Second*time.Duration(conf.DbPingDelay))
}
