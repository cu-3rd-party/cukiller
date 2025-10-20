"""Settings helpers for the CU Killer bot."""

from functools import lru_cache

import redis

from .settings import Settings


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()

@lru_cache
def get_redis_client() -> redis.Redis:
    _settings = get_settings()
    return redis.Redis(
        host=_settings.redis_host,
        port=_settings.redis_port,
        password=_settings.redis_password,
        db=_settings.redis_db,
        decode_responses=True,
    )


__all__ = ["get_settings", "get_redis_client", "Settings"]
