"""Simple in-memory cache utility for API responses."""

import asyncio
import time
from typing import Any


class SimpleCache:
    """
    A simple in-memory cache with TTL (time-to-live) support.

    This cache stores data in memory with an expiration time.
    Useful for caching YouTube search results to reduce API calls.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """
        Initialize the cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 300 = 5 minutes)
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        async with self._lock:
            if key not in self._cache:
                return None

            value, expiry = self._cache[key]

            # Check if expired
            if time.time() > expiry:
                del self._cache[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        async with self._lock:
            expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
            self._cache[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache.

        Args:
            key: Cache key
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear(self) -> None:
        """Clear all cached values."""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> None:
        """Remove all expired entries from the cache."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expiry) in self._cache.items() if current_time > expiry
            ]

            for key in expired_keys:
                del self._cache[key]

    def size(self) -> int:
        """
        Get the current number of items in the cache.

        Returns:
            Number of cached items
        """
        return len(self._cache)


# Global cache instance
_cache = SimpleCache(default_ttl=300)  # 5 minutes default TTL


def get_cache() -> SimpleCache:
    """
    Get the global cache instance.

    Returns:
        Global SimpleCache instance
    """
    return _cache
