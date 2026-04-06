import json
import time
from typing import Optional

from config import get_settings

settings = get_settings()

# Try Redis, fall back to in-memory dict
_pool = None
_redis_available = None
_memory_cache: dict[str, tuple[float, str]] = {}  # key -> (expires_at, json_str)


async def _try_redis():
    global _pool, _redis_available
    if _redis_available is False:
        return None
    if _pool is not None:
        return _pool
    try:
        import redis.asyncio as redis
        pool = redis.from_url(
            settings.REDIS_URL, decode_responses=True, max_connections=20
        )
        await pool.ping()
        _pool = pool
        _redis_available = True
        return _pool
    except Exception:
        _redis_available = False
        return None


async def cache_get(key: str) -> Optional[dict]:
    r = await _try_redis()
    if r:
        data = await r.get(key)
        if data:
            return json.loads(data)
        return None
    # In-memory fallback
    entry = _memory_cache.get(key)
    if entry and entry[0] > time.time():
        return json.loads(entry[1])
    if entry:
        del _memory_cache[key]
    return None


async def cache_set(key: str, value, ttl: Optional[int] = None):
    ttl = ttl or settings.CACHE_TTL_SECONDS
    json_str = json.dumps(value, default=str)
    r = await _try_redis()
    if r:
        await r.setex(key, ttl, json_str)
    else:
        _memory_cache[key] = (time.time() + ttl, json_str)


async def cache_delete(key: str):
    r = await _try_redis()
    if r:
        await r.delete(key)
    else:
        _memory_cache.pop(key, None)


async def cache_flush_pattern(pattern: str):
    r = await _try_redis()
    if r:
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor, match=pattern, count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
    else:
        import fnmatch
        to_del = [k for k in _memory_cache if fnmatch.fnmatch(k, pattern)]
        for k in to_del:
            del _memory_cache[k]
