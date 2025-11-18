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
	SecretKey string  `json:"secret_key"`
	Victim    uint64  `json:"victim"`
	Killer    uint64  `json:"killer"`
	Quality   float64 `json:"quality"`
}

type QueuePlayer struct {
	TgId     uint64
	JoinedAt time.Time
	PlayerData
}

func MatchmakingTicker() {
	ticker := time.NewTicker(time.Second * time.Duration(conf.ConfigMatchmaking.Interval))
	chosenVictimTicker := time.NewTicker(time.Second * time.Duration(conf.ConfigMatchmaking.Interval) * 100)
	defer ticker.Stop()

	logger.Info("Matchmaking ticker started with interval: %d seconds", conf.Interval)

	for {
		select {
		case <-ticker.C:
			go matchmaking()
		case <-chosenVictimTicker.C:
			ChosenVictimMutex.Lock()
			ChosenVictim = make(map[uint64]uint64) // clearing chosen victims
			ChosenVictimMutex.Unlock()
		}
	}
}

var KillerPool = make(map[uint64]QueuePlayer)
var KillerPoolMutex = sync.Mutex{}
var VictimPool = make(map[uint64]QueuePlayer)
var VictimPoolMutex = sync.Mutex{}
var ChosenVictim = make(map[uint64]uint64) // killer → victim
var ChosenVictimMutex = sync.Mutex{}

// matchmaking basically does all the heavy lifting needed for this microservice
func matchmaking() {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()

	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	ChosenVictimMutex.Lock()
	defer ChosenVictimMutex.Unlock()

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

			// анти-цикл: victim уже выбрал killer как цель?
			if prevVictim, ok := ChosenVictim[victimId]; ok && prevVictim == killerId {
				continue // взаимный цикл — пропускаем
			}

			// считаем рейтинг пары
			rating := RatePlayerPair(&killer, &victim, curTime)
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
		ChosenVictim[killerId] = bestVictimId

		// уведомляем основной процесс
		for {
			ok := notifyMainProcess(MatchedPair{
				SecretKey: conf.SecretKey,
				Killer:    killerId,
				Victim:    bestVictimId,
				Quality:   bestRating,
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

//type MatchmakingQueuesResponse struct {
//	KillersQueue []int `json:"killers_queue"`
//	VictimsQueue []int `json:"victims_queue"`
//}

/*
async def get_queue_info(request: web.Request) -> web.StreamResponse:
    # по сути все игроки которые is_in_game, но у которых нету цели/нет убийцы подлежат помещению в очередь на матчмейкинг
    # можно сделать уебищную логику через все кто не в KillEvent, но надо TODO: добавить схему очереди в дб
    game = await Game.filter(end_date=None).first()
    found_victims = set()
    found_killers = set()
    for ke in await KillEvent.filter(game=game).all():
        found_killers.add(ke.killer)
        found_victims.add(ke.victim)
    potential_killers = await User.filter(is_in_game=True, id__not_in=found_killers).all()
    potential_victims = await User.filter(is_in_game=True, id__not_in=found_victims).all()
    return web.json_response(status=200, data={
        "killers_queue": [i.tg_id for i in potential_killers],
        "victims_queue": [i.tg_id for i in potential_victims],
    })
*/

//func restoreMatchmakingQueue() {
//	response, err := http.NewRequest("GET", "http://bot:8000/restore/", nil)
//	if err != nil {
//		panic(fmt.Errorf("failed to restore queue state, err: %w", err))
//	}
//	var queues MatchmakingQueuesResponse
//	err = json.NewDecoder(response.Body).Decode(&queues)
//	if err != nil {
//		panic(fmt.Errorf("failed to restore queue state, err: %w", err))
//	}
//}
