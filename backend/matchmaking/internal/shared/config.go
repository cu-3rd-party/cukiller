package shared

type ConfigDatabase struct {
	DbUser      string
	DbPassword  string
	DbHost      string
	DbPort      string
	DbName      string
	DbPingDelay int
}

func GetDbConfig() ConfigDatabase {
	return ConfigDatabase{
		DbUser:      GetEnvString("POSTGRES_USER", "admin"),
		DbPassword:  GetEnvString("POSTGRES_PASSWORD", "admin"),
		DbHost:      GetEnvString("POSTGRES_HOST", "localhost"),
		DbPort:      GetEnvString("POSTGRES_PORT", "5432"),
		DbName:      GetEnvString("POSTGRES_DB", "db"),
		DbPingDelay: GetEnvInt("DB_PING_DELAY", 100),
	}
}
