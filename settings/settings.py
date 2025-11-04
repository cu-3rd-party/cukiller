from typing import Any

from aiogram.types import ChatInviteLink
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""

    # ^ Base
    tz: str = Field(default="Europe/Moscow", alias="TZ")
    project_name: str = Field(default="MyProject", alias="PROJECT_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="very_secret_key", alias="SECRET_KEY")

    # ^ Bot
    bot_name: str = Field(default="cu_killer_bot", alias="BOT_NAME")
    bot_token: str = Field(default="ERROR_TOKEN", alias="BOT_TOKEN")
    admin_chat_id: int = Field(alias="ADMIN_CHAT_ID")
    discussion_chat_id: int = Field(alias="DISCUSSION_ID")
    discussion_chat_invite_link: ChatInviteLink | None = Field(default=None)
    admin_ids_raw: str | None = Field(default=None, alias="ADMIN_IDS")
    report_link: str = Field(alias="REPORT_LINK")
    game_info_link: str = Field(alias="NEXT_GAME_LINK")

    # ^ PostgreSQL
    pg_host: str = Field(default="db", alias="POSTGRES_HOST")
    pg_port: int = Field(default=5432, alias="POSTGRES_PORT")
    pg_db: str = Field(default="db", alias="POSTGRES_DB")
    pg_user: str = Field(default="admin", alias="POSTGRES_USER")
    pg_password: str = Field(default="admin", alias="POSTGRES_PASSWORD")

    # ^ Tortoise ORM
    tortoise_app: str = Field(default="models", alias="TORTOISE_APP")
    tortoise_models: tuple[str, ...] = Field(
        default=("db.models",), alias="TORTOISE_MODELS"
    )
    tortoise_generate_schemas: bool = Field(
        default=False, alias="TORTOISE_GENERATE_SCHEMAS"
    )

    # ^ Matchmaking
    matchmaking_interval: int = Field(default=5, alias="MATCHMAKING_INTERVAL")
    quality_threshold: float = Field(default=0.6, alias="QUALITY_THRESHOLD")

    matchmaking_service_url: str = Field(default="http://localhost:65432", alias="MATCHMAKING_URL")
    max_rating_diff: float = Field(default=1000, alias="MAX_RATING_DIFF")
    course_coefficient: float = Field(default=0.3, alias="COURSE_COEFFICIENT")
    group_coefficient: float = Field(default=-0.2, alias="GROUP_COEFFICIENT")
    type_coefficient: float = Field(default=-0.6, alias="TYPE_COEFFICIENT")
    time_coefficient: float = Field(default=0.001, alias="TIME_COEFFICIENT")

    @computed_field
    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.pg_user}:{self.pg_password}@"
            f"{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @computed_field
    @property
    def tortoise_db_url(self) -> str:
        return (
            f"postgres://{self.pg_user}:{self.pg_password}@"
            f"{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @computed_field
    @property
    def tortoise_config(self) -> dict[str, Any]:
        return {
            "connections": {"default": self.tortoise_db_url},
            "apps": {
                self.tortoise_app: {
                    "models": self.tortoise_models,
                    "default_connection": "default",
                }
            },
        }

    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
