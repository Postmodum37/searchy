# APP - SEARCHY API CORE

FastAPI YouTube search service. No API keys — uses yt-dlp for extraction.

## OVERVIEW

5 modules: routes (main.py), models, config, YouTube service, cache. Async throughout with `asyncio.to_thread` for blocking yt-dlp calls.

## STRUCTURE

```
app/
├── main.py              # FastAPI routes, middleware, error handlers, lifespan
├── models.py            # Pydantic request/response models
├── config.py            # pydantic-settings with SEARCHY_ env prefix
├── services/
│   └── youtube.py       # yt-dlp wrapper (search, video details, audio extraction)
└── utils/
    └── cache.py         # In-memory TTL cache with async locks
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add endpoint | `main.py` | Add route + import model from `models.py` |
| Add response model | `models.py` | Pydantic BaseModel with Field descriptions |
| Change cache TTL | `config.py` | `cache_ttl_search`, `cache_ttl_video`, `cache_ttl_audio` |
| Audio format logic | `services/youtube.py:276-296` | Best bitrate: `vcodec=="none" and acodec!="none"` |
| Age-restriction flow | `services/youtube.py:133-169` | Browser cookie fallback: chrome→firefox→edge→... |
| Cache-aside pattern | `utils/cache.py` | `get_or_compute(key, ttl, compute_fn)` |

## REQUEST FLOW

```
Client → FastAPI route (main.py)
  → get_or_compute(cache_key, ttl, lambda: ...)
    → cache hit? return cached
    → cache miss? YouTubeService.method() via asyncio.to_thread
      → yt-dlp extraction (sync, runs in thread)
    → store in cache, return
```

## CONVENTIONS

### Route Pattern
```python
@app.get("/endpoint", response_model=ResponseModel, responses={...})
async def endpoint(param: str = Query(..., description="..."), no_cache: bool = Query(False)):
    cache_key = hashlib.md5(f"prefix:{param}".encode()).hexdigest()
    result = await get_or_compute(cache_key, settings.cache_ttl_x, lambda: service.method(param))
    return ResponseModel(**result)
```

### Error Handling
- `HTTPException` → structured JSON via custom handler
- Generic `Exception` → 500 with safe message
- All errors include timestamp via `ErrorResponse` model
- `no_cache=true` query param bypasses cache on any endpoint

### Config (env vars with SEARCHY_ prefix)
- `SEARCHY_CACHE_TTL_SEARCH=300` / `SEARCHY_CACHE_TTL_VIDEO=600` / `SEARCHY_CACHE_TTL_AUDIO=60`
- `SEARCHY_LOG_LEVEL=INFO` / `SEARCHY_CORS_ORIGINS=["*"]`
- `SEARCHY_YOUTUBE_DEFAULT_BROWSER=chrome`

## ANTI-PATTERNS

- **Never** call yt-dlp synchronously in route handlers — use `asyncio.to_thread`
- **Never** skip Pydantic model for new endpoints
- **Never** use `B008` violations (function calls in defaults) except FastAPI `Query()`/`Depends()`

## NOTES

- Global `settings = Settings()` singleton in config.py
- `YouTubeService` is stateless — instantiated per-use, no singleton needed
- Audio URLs expire ~6 hours (YouTube CDN), cached only 1 minute
- Age-restricted: tries chrome→firefox→edge→safari→opera→brave→no-cookies
- CORS allows all origins — restrict in production
- Pre-commit hooks enforced: ruff format + ruff check + mypy
