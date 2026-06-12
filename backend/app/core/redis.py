"""Shared Redis client — singleton connection pool."""

from functools import lru_cache

import redis

from app.core.config import get_settings

SYNC_STATUS_KEY = "firemaster:sync:status"


@lru_cache
def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
