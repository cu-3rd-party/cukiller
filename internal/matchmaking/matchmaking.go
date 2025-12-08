package matchmaking

import (
	"bytes"
	"encoding/json"
	"math"
	"net/http"
	"sync"
	"time"
)

type MatchedPair struct {
	Victim  uint64  `json:"victim"`
	Killer  uint64  `json:"killer"`
	Quality float64 `json:"quality"`
}

type QueuePlayer struct {
	TgId     uint64
	JoinedAt time.Time
	PlayerData
}

func TickerMatchmaking() {
	ticker := time.NewTicker(time.Second * time.Duration(conf.ConfigMatchmaking.Interval))
	defer ticker.Stop()

	logger.Info("Matchmaking ticker started with interval: %d seconds", conf.Interval)

	for range ticker.C {
		go matchmaking()
	}
}

var KillerPool = make(map[uint64]QueuePlayer)
var KillerPoolMutex = sync.Mutex{}
var VictimPool = make(map[uint64]QueuePlayer)
var VictimPoolMutex = sync.Mutex{}

// matchmaking basically does all the heavy lifting needed for this microservice
func matchmaking() {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()

	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	gameActive, gameId := GetActiveGame()
	if !gameActive {
		return
	}

	curTime := time.Now()
	logger.Debug("Running matchmaking cycle at %s", curTime)

	if len(KillerPool)+len(VictimPool) < 2 {
		return
	}

	processedKillers := make(map[uint64]struct{})
	processedVictims := make(map[uint64]struct{})

	for killerId, killer := range KillerPool {
		// killer уже обработан?
		if _, skip := processedKillers[killerId]; skip {
			continue
		}
		// в один цикл нам запрещено выдавать одному человеку и убийцу и жертву
		if _, skip := processedVictims[killerId]; skip {
			continue
		}

		bestRating := 0.0
		var bestVictimId uint64 = 0

		// ищем лучшую жертву
		for victimId, victim := range VictimPool {
			// killer не может быть жертвой себе
			if killerId == victimId {
				continue
			}

			// victim уже обработан?
			if _, skip := processedVictims[victimId]; skip {
				continue
			}

			// обрабатываем чтоб не было одиночных циклов
			if ArePaired(gameId, victimId, killerId) {
				continue
			}

			if PlayersWerePairedRecently(gameId, killerId, victimId) {
				continue
			}

			// считаем рейтинг пары
			rating := RatePlayerPair(&killer, &victim, curTime)
			logger.Debug("RatePlayerPair(%d, %d) got rating %f", killerId, victimId, rating)
			if rating < conf.QualityThreshold {
				continue
			}

			if rating > bestRating {
				bestRating = rating
				bestVictimId = victimId
			}
		}

		// не нашли подходящую жертву
		if bestVictimId == 0 {
			continue
		}

		// помечаем как использованных
		processedKillers[killerId] = struct{}{}
		processedVictims[bestVictimId] = struct{}{}

		// уведомляем основной процесс
		for {
			ok := notifyMainProcess(MatchedPair{
				Killer:  killerId,
				Victim:  bestVictimId,
				Quality: bestRating,
			})
			if !ok {
				logger.Warn("Failed to notify main process about new pair: %d and %d", killerId, bestVictimId)
			}
			if ok {
				break
			}
		}

		logger.Debug("Matched killer %d with victim %d (quality %.3f)", killerId, bestVictimId, bestRating)

		// полностью удаляем обе стороны из обоих пулов
		delete(KillerPool, killerId)
		delete(VictimPool, bestVictimId)
	}
}

func notifyMainProcess(pair MatchedPair) bool {
	body, err := json.Marshal(pair)
	if err != nil {
		return false
	}
	client := &http.Client{}
	req, err := http.NewRequest("POST", conf.BotUrl+"/match", bytes.NewBuffer(body))
	if err != nil {
		logger.Error("Failed to create request because of %v", err)
	}
	req.Header.Set("secret-key", conf.SecretKey)
	resp, err := client.Do(req)
	if err != nil {
		logger.Error("Failed to notify main process because of %v", err)
	}
	if resp.StatusCode != 200 {
		return false
	}
	return true
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
