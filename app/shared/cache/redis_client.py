"""
Redis connection pool for caching and distributed locking.

Security notes:
- Redis URL built from env vars — password never hardcoded.
- TODO(security): Enable TLS for Redis connection in production
  (redis://<host> → rediss://<host>).
"""
import logging
from typing import Generator, Optional

import redis
from redis import Redis

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

_redis_pool: Optional[redis.ConnectionPool] = None


def _get_pool() -> redis.ConnectionPool:
    """Lazily initialize and return the Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            _settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_pool


def get_redis() -> Generator[Redis, None, None]:
    """
    FastAPI dependency that provides a Redis client from the connection pool.

    Yields:
        Redis: An active Redis client.

    Usage:
        def my_endpoint(redis_client: Redis = Depends(get_redis)):
            ...
    """
    client = Redis(connection_pool=_get_pool())
    try:
        yield client
    finally:
        client.close()


def get_redis_client() -> Redis:
    """Return a Redis client for non-FastAPI usage (e.g., background tasks)."""
    return Redis(connection_pool=_get_pool())


def check_redis_connection() -> bool:
    """Health check: verify Redis connectivity."""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as exc:
        logger.error("Redis health check failed: %s", type(exc).__name__)
        return False
