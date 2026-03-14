"""
DiaIntel — Redis Cache Utilities
Small async helpers for API response caching.
"""

import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis, from_url

from app.config import settings

logger = logging.getLogger("diaintel.utils.cache")

_redis: Optional[Redis] = None


def get_redis() -> Redis:
    """Return a shared async Redis client."""
    global _redis

    if _redis is None:
        _redis = from_url(settings.REDIS_URL, decode_responses=True)

    return _redis


async def get_cached_json(cache_key: str) -> Optional[Any]:
    """Read and deserialize a JSON payload from Redis."""
    try:
        raw_value = await get_redis().get(cache_key)
        if not raw_value:
            return None
        return json.loads(raw_value)
    except Exception as exc:
        logger.warning("Redis cache read failed for %s: %s", cache_key, exc)
        return None


async def set_cached_json(cache_key: str, payload: Any, ttl_seconds: int) -> None:
    """Write a JSON payload to Redis with a TTL."""
    try:
        await get_redis().set(cache_key, json.dumps(payload, default=str), ex=ttl_seconds)
    except Exception as exc:
        logger.warning("Redis cache write failed for %s: %s", cache_key, exc)
