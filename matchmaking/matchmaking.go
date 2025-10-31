package main

import (
	"math"
	"time"
)

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
			matchmaking()
		}
	}
}

var KillerPool = make(map[int]QueuePlayer)
var VictimPool = make(map[int]QueuePlayer)

// matchmaking basically does all the heavy lifting needed for this microservice
func matchmaking() {
	// because this function does a lot of heavy lifting we should have the same time for all rates
	curTime := time.Now()
	if len(KillerPool)+len(VictimPool) < 2 {
		logger.Info("Not enough players in queues to process matchmaking")
		return
	}

	processedKillers := make(map[int]struct{})
	processedVictims := make(map[int]struct{})

	// we skip sorting killers by joinedAt but maybe add in the future

	for _, killer := range KillerPool {
		if _, processed := processedKillers[killer.TgId]; processed {
			continue
		}

		var bestRating float64 = 0
		var bestVictim *QueuePlayer
		for _, victim := range VictimPool {
			if _, processed := processedVictims[victim.TgId]; processed {
				continue
			}
			rating := RatePlayerPair(&killer, &victim, curTime)
			if rating < conf.QualityThreshold {
				continue
			}
			if rating > bestRating {
				bestRating = rating
				bestVictim = &victim
			}
		}

		if bestVictim == nil {
			continue
		}

		processedKillers[killer.TgId] = struct{}{}
		processedVictims[bestVictim.TgId] = struct{}{}
		logger.Info("Matched killer %d with victim %d", killer.TgId, bestVictim.TgId)
		notifyMainProcess(MatchedPair{
			Killer:  killer.TgId,
			Victim:  bestVictim.TgId,
			Quality: bestRating,
		})
	}
}

func notifyMainProcess(pair MatchedPair) {
	// TODO
}

func RatePlayerPair(
	killer *QueuePlayer,
	victim *QueuePlayer,
	curTime time.Time) float64 {
	ratingDiff := float64(AbsDiffInt(killer.Rating, victim.Rating))
	if ratingDiff > conf.MaxRatingDiff {
		return 0
	}

	ratingSimilarity := 1 - math.Min(ratingDiff/conf.MaxRatingDiff, 1)
	courseBonus := conf.CourseCoefficient * EqualityCoefficientFloat64(killer.CourseNumber, victim.CourseNumber)
	groupBonus := conf.GroupCoefficient * EqualityCoefficientFloat64(killer.GroupName, victim.GroupName)
	typeBonus := conf.TypeCoefficient * EqualityCoefficientFloat64(killer.Type, victim.Type)
	timeBonus := conf.TimeCoefficient * (curTime.Sub(killer.JoinedAt) + curTime.Sub(victim.JoinedAt)).Seconds()

	matchQuality := ratingSimilarity +
		courseBonus +
		groupBonus +
		typeBonus +
		timeBonus

	return math.Max(0, math.Min(1, matchQuality))
}
