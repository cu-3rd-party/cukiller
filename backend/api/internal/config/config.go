package config

import (
	"fmt"

	"github.com/caarlos0/env/v11"
)

type Config struct {
	APIBasePath   string `env:"API_PATH" envDefault:"/"`
	Port          string `env:"PORT" envDefault:"8080"`
	EnableMetrics bool   `env:"API_ENABLE_METRICS" envDefault:"true"`
	LogLevel      string `env:"LOG_LEVEL" envDefault:"info"`
	DbHost        string `env:"DB_HOST" envDefault:"db"`
	DbName        string `env:"DB_NAME" envDefault:"db"`
	DbUser        string `env:"DB_USER" envDefault:"admin"`
	DbPassword    string `env:"DB_PASSWORD" envDefault:"admin"`
}

func Load() (Config, error) {
	cfg := Config{}
	return cfg, env.Parse(&cfg)
}

const DbPort = "5432"

func (c *Config) DbURL() string {
	return fmt.Sprintf(
		"postgres://%s:%s@%s:%s/%s?sslmode=disable",
		c.DbUser, c.DbPassword,
		c.DbHost, DbPort,
		c.DbName,
	)
}
