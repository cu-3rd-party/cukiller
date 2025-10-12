from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ^ Base
    tz: str = Field(default="Europe/Moscow", alias="TZ")
    project_name: str = Field(default="MyProject", alias="PROJECT_NAME")
    debug: bool = Field(default=False, alias="DEBUG")

    # ^ Bot
    bot_name: str = Field(default="cu_killer_bot", alias="BOT_NAME")
    bot_token: str = Field(default="ERROR_TOKEN", alias="BOT_TOKEN")

    # ^ PostgreSQL
    pg_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    pg_port: int = Field(default=5432, alias="POSTGRES_PORT")
    pg_db: str = Field(default="db", alias="POSTGRES_DB")
    pg_user: str = Field(default="admin", alias="POSTGRES_USER")
    pg_password: str = Field(default="admin", alias="POSTGRES_PASSWORD")

    # ^ Redis
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    @computed_field
    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.pg_user}:{self.pg_password}@"
            f"{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @computed_field
    @property
    def dsn_orm_database_uri(self) -> str:
        return (
            f"postgresql+asyncpg://{self.pg_user}:{self.pg_password}@"
            f"{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
