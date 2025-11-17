package internal

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"
)

func StartupHttp() {
	http.HandleFunc("/ping/", ping)
	http.HandleFunc("/health/", health)
	http.HandleFunc("/add/killer/", addKiller)
	http.HandleFunc("/add/victim/", addVictim)
	http.HandleFunc("/get/queues/", getQueues)
	http.HandleFunc("/get/queues/len/", getQueuesLen)
	http.HandleFunc("/get/player/{tg_id}", getPlayerByTgId)

	addr := fmt.Sprintf(":%d", conf.Port)
	logger.Info("HTTP server starting on %s", addr)

	if err := http.ListenAndServe(addr, nil); err != nil {
		logger.Error("HTTP server failed: %v", err)
		os.Exit(1)
	}
}

func ping(w http.ResponseWriter, r *http.Request) {
	logger.Info("Ping endpoint called from %s", r.RemoteAddr)
	w.Header().Set("Content-Type", "application/json")

	_, err := fmt.Fprintf(w, "{\"message\": \"ok\"}")
	if err != nil {
		logger.Error("Failed to write ping response: %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		return
	}
}

func health(w http.ResponseWriter, r *http.Request) {
	logger.Info("Health check from %s", r.RemoteAddr)

	w.Header().Set("Content-Type", "application/json")
	_, err := fmt.Fprintf(w, `{"status": "healthy", "timestamp": "%s"}`, time.Now().Format(time.RFC3339))
	if err != nil {
		logger.Error("Failed to write health response: %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		return
	}
}

func addKiller(w http.ResponseWriter, r *http.Request) {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()
	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	// 	1. parse PlayerData from request
	var data PlayerData
	err := json.NewDecoder(r.Body).Decode(&data)
	if err != nil {
		_, _ = w.Write([]byte("failed to parse PlayerData from json request"))
		w.WriteHeader(400)
	}
	// 2. put player into killer queue
	addPlayerToPool(KillerPool, data)
	w.WriteHeader(201)
	logger.Info("Add killer with data request from %s with data %v", r.RemoteAddr, data)
}

func addVictim(w http.ResponseWriter, r *http.Request) {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()
	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	// 	1. parse PlayerData from request
	var data PlayerData
	err := json.NewDecoder(r.Body).Decode(&data)
	w.Header().Set("Content-Type", "application/json")
	if err != nil {
		_, _ = w.Write([]byte(`{"message"": "failed to parse PlayerData from json request"}`))
		w.WriteHeader(400)
	}
	// 2. put player into victim queue
	addPlayerToPool(VictimPool, data)
	w.WriteHeader(201)
	logger.Info("Add victim with data request from %s with data %v", r.RemoteAddr, data)
}

func addPlayerToPool(pool map[uint64]QueuePlayer, data PlayerData) {
	pool[data.TgId] = QueuePlayer{
		TgId:       data.TgId,
		JoinedAt:   time.Now(),
		PlayerData: data,
	}
}

func getQueues(w http.ResponseWriter, r *http.Request) {
	queues := getPools()
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(queues)
	logger.Info("Get queues request %s", r.RemoteAddr)
}

func getPools() any {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()
	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	ret := struct {
		Killers []PlayerData
		Victims []PlayerData
	}{}
	ret.Killers = getPool(KillerPool, ret.Killers)
	ret.Victims = getPool(VictimPool, ret.Victims)
	return ret
}

func getPool(pool map[uint64]QueuePlayer, trg []PlayerData) []PlayerData {
	for _, player := range pool {
		trg = append(trg, player.PlayerData)
	}
	return trg
}

func getQueuesLen(w http.ResponseWriter, r *http.Request) {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()
	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(struct {
		Killers int
		Victims int
	}{
		Killers: len(KillerPool),
		Victims: len(VictimPool),
	})
	logger.Info("Get queues len request from %s", r.RemoteAddr)
}

func getPlayerByTgId(w http.ResponseWriter, r *http.Request) {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()
	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	tgId, err := strconv.ParseUint(r.PathValue("tg_id"), 10, 64)
	if err != nil {
		w.WriteHeader(400)
		_, _ = w.Write([]byte("non-string tg id supplied"))
	}
	w.Header().Set("Content-Type", "application/json")

	killer, queuedKiller := KillerPool[tgId]
	victim, queuedVictim := VictimPool[tgId]

	_ = json.NewEncoder(w).Encode(struct {
		QueuedKiller bool
		Killer       QueuePlayer
		QueuedVictim bool
		Victim       QueuePlayer
	}{
		QueuedKiller: queuedKiller,
		Killer:       killer,
		QueuedVictim: queuedVictim,
		Victim:       victim,
	})
}
