"""Settings helpers for the CU Killer bot."""

from functools import lru_cache

from .settings import Settings


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


__all__ = ["get_settings", "Settings"]
