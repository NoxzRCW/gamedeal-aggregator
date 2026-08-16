import json

import redis.asyncio as redis

from .config import settings

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def cache_get(key: str):
    try:
        raw = await get_client().get(key)
    except Exception:
        return None
    return json.loads(raw) if raw else None


async def cache_set(key: str, value, ttl: int = settings.cache_ttl_seconds):
    try:
        await get_client().set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass
