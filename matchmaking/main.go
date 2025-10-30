package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"
)

type Config struct {
	Port int
	MatchmakingConfig
}

type MatchmakingConfig struct {
	Interval int
}

func getConfig() Config {
	var err error
	conf := Config{}

	port := os.Getenv("MATCHMAKING_PORT")
	if conf.Port, err = strconv.Atoi(port); err != nil {
		fmt.Printf("Failed to convert PORT number %q to int\n", port)
		conf.Port = 5432
	}

	interval := os.Getenv("MATCHMAKING_INTERVAL")
	if conf.MatchmakingConfig.Interval, err = strconv.Atoi(interval); err != nil {
		fmt.Printf("Failed to convert MATCHMAKING_INTERVAL number %q to int\n", interval)
		conf.MatchmakingConfig.Interval = 5
	}

	return conf
}

func main() {
	conf := getConfig()
	go matchmakingTicker(conf)
	startupHttp(conf)
}

func matchmakingTicker(conf Config) {
	ticker := time.NewTimer(time.Second * time.Duration(conf.MatchmakingConfig.Interval))
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			matchmaking(conf)
		}
	}
}

func matchmaking(conf Config) {

}

func startupHttp(conf Config) {
	http.HandleFunc("/ping/", ping)

	addr := fmt.Sprintf(":%d", conf.Port)
	fmt.Printf("Http server started at %q\n", addr)
	log.Fatal(http.ListenAndServe(addr, nil))
}

func ping(w http.ResponseWriter, r *http.Request) {
	_, err := fmt.Fprintf(w, "Hello, world!\n")
	if err != nil {
		w.WriteHeader(500)
		return
	}
	w.WriteHeader(200)
}
