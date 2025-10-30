package main

import "time"

type MatchedPair struct {
	Victim  int     `json:"victim"`
	Killer  int     `json:"killer"`
	Quality float64 `json:"quality"`
}

type QueuePlayer struct {
	TgId     int
	JoinedAt time.Time
	PlayerData
}

func matchmakingTicker() {
	ticker := time.NewTicker(time.Second * time.Duration(conf.MatchmakingConfig.Interval))
	defer ticker.Stop()

	logger.Info("Matchmaking ticker started with interval: %d seconds", conf.Interval)

	for {
		select {
		case <-ticker.C:
			matchmaking(&conf.MatchmakingConfig)
		}
	}
}

func matchmaking(conf *MatchmakingConfig) {
	//TODO: Implement matchmaking logic
}
