"""Simple in-memory cache utility for API responses."""

import asyncio
import hashlib
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


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


def cached(
    cache_key_fn: Callable[..., str], ttl: int, cache_instance: SimpleCache | None = None
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator to cache async function results.

    Args:
        cache_key_fn: Function to generate cache key from function arguments
        ttl: Time-to-live in seconds
        cache_instance: Cache instance to use (uses global cache if None)

    Returns:
        Decorated function with caching
    """
    cache = cache_instance or _cache

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check if cache should be bypassed
            no_cache = kwargs.get("no_cache", False)

            if not no_cache:
                # Generate cache key
                key = cache_key_fn(*args, **kwargs)
                # Try to get from cache
                cached_result = await cache.get(key)
                if cached_result is not None:
                    return cached_result  # type: ignore[no-any-return]

            # Call the original function
            result = await func(*args, **kwargs)

            # Cache the result
            key = cache_key_fn(*args, **kwargs)
            await cache.set(key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Generate a cache key from prefix and arguments.

    Args:
        prefix: Cache key prefix
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key (no_cache is excluded)

    Returns:
        MD5 hash-based cache key
    """
    # Exclude no_cache from key generation
    filtered_kwargs = {k: v for k, v in kwargs.items() if k != "no_cache"}

    # Create string representation
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}:{v}" for k, v in sorted(filtered_kwargs.items()))

    key_string = ":".join(key_parts)
    return f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"


async def get_or_compute[T](
    cache_key: str,
    compute_fn: Callable[[], Awaitable[T]],
    ttl: int,
    no_cache: bool = False,
    cache_instance: SimpleCache | None = None,
) -> T:
    """
    Get value from cache or compute it if not cached.

    Args:
        cache_key: Cache key to use
        compute_fn: Async function to compute the value if not cached
        ttl: Time-to-live in seconds for cached result
        no_cache: Skip cache and force fresh computation
        cache_instance: Cache instance to use (uses global cache if None)

    Returns:
        Cached or computed value
    """
    cache = cache_instance or _cache

    # Try to get from cache if caching is enabled
    if not no_cache:
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            return cached_result  # type: ignore[no-any-return]

    # Compute the value
    result = await compute_fn()

    # Cache the result
    await cache.set(cache_key, result, ttl=ttl)

    return result
