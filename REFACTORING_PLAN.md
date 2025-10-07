# Refactoring & Improvement Plan

## Summary
Comprehensive analysis of codebase for potential improvements focusing on:
- Code duplication removal
- Better configuration management
- Improved error handling
- Performance optimizations
- Type safety improvements

---

## High Priority Issues

### 1. **app/main.py** - Duplicate Cache Logic
**Lines:** 110-113, 153-156

**Issue:** Identical cache retrieval code repeated twice
```python
# Duplicated in search_videos() and get_video()
if not no_cache:
    cached_result = await cache.get(cache_key)
    if cached_result:
        return cached_result
```

**Solution:** Create a cache decorator or helper function
```python
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
T = TypeVar("T")

def with_cache(cache_key_fn: Callable[..., str], ttl: int):
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            no_cache = kwargs.get('no_cache', False)
            if not no_cache:
                key = cache_key_fn(*args, **kwargs)
                cached = await cache.get(key)
                if cached:
                    return cached

            result = await func(*args, **kwargs)
            key = cache_key_fn(*args, **kwargs)
            await cache.set(key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
```

---

### 2. **app/main.py** - Magic Numbers (Configuration)
**Lines:** 107, 122, 150, 165

**Issue:** Hardcoded TTL values and missing environment variables
```python
ttl=300  # 5 minutes - hardcoded
ttl=600  # 10 minutes - hardcoded
```

**Solution:** Create configuration file
```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API
    api_title: str = "Searchy"
    api_version: str = "0.1.0"
    api_description: str = "Efficient YouTube search API service"

    # Cache TTL (seconds)
    cache_ttl_search: int = 300  # 5 minutes
    cache_ttl_video: int = 600   # 10 minutes
    cache_default_ttl: int = 300

    # CORS
    cors_origins: list[str] = ["*"]

    # Limits
    max_search_results: int = 50
    default_search_limit: int = 10

    # YouTube Service
    youtube_age_limit: int = 21
    youtube_default_browser: str = "chrome"
    youtube_fallback_browsers: list[str] = ["firefox", "edge", "safari", "opera", "brave"]

    class Config:
        env_prefix = "SEARCHY_"
        env_file = ".env"

settings = Settings()
```

---

### 3. **app/main.py** - Use Logging Instead of Print
**Lines:** 33, 36

**Issue:** Using print() for startup/shutdown messages
```python
print(f"Starting Searchy API v{VERSION}")
print("Shutting down Searchy API")
```

**Solution:** Use proper logging
```python
import logging

logger = logging.getLogger(__name__)

# In lifespan:
logger.info(f"Starting Searchy API v{VERSION}")
logger.info("Shutting down Searchy API")
```

---

### 4. **app/main.py** - Error Handler Redundancy
**Line:** 211

**Issue:** Redundant error detail handling
```python
error_response = ErrorResponse(error=exc.detail or "An error occurred", detail=str(exc.detail))
```

**Solution:** Simplify
```python
error_response = ErrorResponse(
    error=str(exc.detail) if exc.detail else "An error occurred",
    detail=str(exc.detail)
)
```

---

### 5. **app/services/youtube.py** - Deprecated asyncio Method
**Lines:** 67, 103

**Issue:** Using deprecated `asyncio.get_event_loop()`
```python
loop = asyncio.get_event_loop()
```

**Solution:** Use `asyncio.get_running_loop()` or `asyncio.to_thread()`
```python
# Python 3.13 - use to_thread for better performance
results = await asyncio.to_thread(self._extract_info, search_query, self.search_opts)
```

---

### 6. **app/services/youtube.py** - Duplicate Keys in Dict
**Lines:** 45-50

**Issue:** search_opts duplicates keys from default_opts
```python
self.search_opts = {
    **self.default_opts,
    "extract_flat": "in_playlist",
    "quiet": True,        # Already in default_opts
    "no_warnings": True,  # Already in default_opts
}
```

**Solution:** Remove duplicates
```python
self.search_opts = {
    **self.default_opts,
    "extract_flat": "in_playlist",
}
```

---

### 7. **app/services/youtube.py** - Hardcoded Browser List
**Line:** 134

**Issue:** Browser list is hardcoded in method
```python
browsers = ["firefox", "edge", "safari", "opera", "brave"]
```

**Solution:** Make it a class constant or config
```python
class YouTubeService:
    FALLBACK_BROWSERS = ["firefox", "edge", "safari", "opera", "brave"]
    DEFAULT_BROWSER = "chrome"

    # Use from config:
    # browsers = settings.youtube_fallback_browsers
```

---

### 8. **app/services/youtube.py** - List Comprehension Opportunity
**Lines:** 79-86

**Issue:** Manual list building with try/except
```python
valid_results = []
for entry in entries:
    if entry and isinstance(entry, dict) and entry.get("id"):
        try:
            valid_results.append(self._parse_search_result(entry))
        except Exception:
            continue
```

**Solution:** Use list comprehension with helper
```python
def _safe_parse(self, entry: dict[str, Any]) -> VideoSearchResult | None:
    try:
        return self._parse_search_result(entry)
    except Exception:
        return None

# Then:
valid_results = [
    result
    for entry in entries
    if entry and isinstance(entry, dict) and entry.get("id")
    if (result := self._safe_parse(entry)) is not None
]
```

---

### 9. **app/services/youtube.py** - Type Annotation Issue
**Line:** 15

**Issue:** suppress_stderr() returns Any
```python
def suppress_stderr() -> Any:
```

**Solution:** Use proper Generator type
```python
from collections.abc import Generator

@contextlib.contextmanager
def suppress_stderr() -> Generator[None, None, None]:
    """Context manager to suppress stderr output."""
    ...
```

---

### 10. **app/utils/cache.py** - Unused Method
**Lines:** 79-88

**Issue:** `cleanup_expired()` is never called automatically
```python
async def cleanup_expired(self) -> None:
    """Remove all expired entries from the cache."""
    ...
```

**Solution:** Add background task or remove if not needed
```python
# In app/main.py lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    logger.info(f"Starting Searchy API v{VERSION}")

    # Start background cache cleanup
    cleanup_task = asyncio.create_task(periodic_cache_cleanup())

    yield

    # Shutdown
    cleanup_task.cancel()
    logger.info("Shutting down Searchy API")

async def periodic_cache_cleanup():
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        await cache.cleanup_expired()
```

---

### 11. **app/models.py** - Timezone-Naive Datetime
**Lines:** 46, 78, 86

**Issue:** Using `datetime.now()` without timezone
```python
timestamp: datetime = Field(default_factory=datetime.now, ...)
```

**Solution:** Use timezone-aware datetime
```python
from datetime import datetime, timezone

# Update default_factory:
timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    description="Response timestamp"
)
```

---

### 12. **app/services/youtube.py** - URL Construction Duplication
**Lines:** 166, 219

**Issue:** Same URL construction logic repeated
```python
url=entry.get("webpage_url", f"https://www.youtube.com/watch?v={entry.get('id')}")
```

**Solution:** Create helper method
```python
def _build_video_url(self, entry: dict[str, Any]) -> str:
    """Build YouTube video URL from entry data."""
    return entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
```

---

## Medium Priority Issues

### 13. **app/utils/cache.py** - Unnecessary Lock in size()
**Line:** 90-97

**Issue:** size() doesn't need async lock
```python
def size(self) -> int:
    return len(self._cache)
```
This is already atomic in Python.

---

### 14. **Missing Request ID for Tracing**

**Solution:** Add middleware for request tracking
```python
# app/middleware.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

---

### 15. **Missing Rate Limiting**

**Solution:** Add simple rate limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# On endpoints:
@app.get("/search")
@limiter.limit("10/minute")
async def search_videos(...):
    ...
```

---

## Low Priority / Nice to Have

### 16. **Add Metrics/Monitoring**
Consider adding prometheus metrics or basic stats tracking

### 17. **Add API Key Support (Optional)**
For production, might want optional API key authentication

### 18. **Add Response Compression**
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 19. **Add OpenTelemetry Tracing**
For production observability

### 20. **Add Validation for video_id Format**
```python
from pydantic import Field, field_validator

video_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{11}$")
```

---

## Testing Improvements

### 21. **Add Performance Tests**
Test response times and throughput

### 22. **Add Property-Based Tests**
Using `hypothesis` for edge cases

### 23. **Add Load Tests**
Using `locust` or `k6`

---

## Documentation Improvements

### 24. **Add API Usage Examples**
Include curl, Python, JavaScript examples in README

### 25. **Add Architecture Diagram**
Show component interactions

### 26. **Add Contributing Guidelines**
CONTRIBUTING.md with setup and PR guidelines

---

## Estimated Impact

| Priority | Issues | Impact | Effort |
|----------|--------|--------|--------|
| High | 1-12 | Major code quality & maintainability | Medium |
| Medium | 13-15 | Production readiness | Low-Medium |
| Low | 16-26 | Nice to have features | High |

## Recommended Implementation Order

1. **Phase 1** (High Priority):
   - Add config.py with environment variables
   - Replace print with logging
   - Fix deprecated asyncio calls
   - Fix timezone-aware datetime
   - Remove duplicate code

2. **Phase 2** (Medium Priority):
   - Add request ID middleware
   - Implement cache cleanup background task
   - Consider rate limiting

3. **Phase 3** (Low Priority):
   - Add metrics/monitoring
   - Enhanced documentation
   - Performance optimization
