# SEARCHY - PROJECT KNOWLEDGE BASE

YouTube search API service. FastAPI + yt-dlp. No API keys required.

## OVERVIEW

REST API providing YouTube search, video metadata, and audio stream URL extraction. In-memory TTL caching, async throughout, browser cookie fallback for age-restricted content.

## RUNTIME

- **Language**: Python 3.13+
- **Framework**: FastAPI with uvicorn
- **Package manager**: uv (Astral)
- **Type checking**: mypy (`--strict`)
- **Linting**: Ruff (format + lint + isort)
- **Pre-commit**: Enforced (ruff + mypy)

## STRUCTURE

```
searchy/
├── app/
│   ├── main.py           # FastAPI routes, middleware, error handlers, lifespan
│   ├── models.py         # Pydantic request/response models
│   ├── config.py         # pydantic-settings (SEARCHY_ env prefix)
│   ├── services/
│   │   └── youtube.py    # yt-dlp wrapper (search, video, audio extraction)
│   └── utils/
│       └── cache.py      # In-memory TTL cache with async locks
├── tests/
│   ├── conftest.py       # Fixtures: async_client, sample data
│   ├── test_api.py       # Endpoint tests
│   └── test_age_restriction.py  # Age-restricted content tests
├── pyproject.toml        # Dependencies, ruff/mypy/pytest config
└── Dockerfile            # Multi-stage Python build with uv
```

## KEY IMPLEMENTATION DETAILS

### Search (`services/youtube.py:56-89`)
- yt-dlp syntax: `ytsearch{limit}:{query}`
- Uses `extract_flat: "in_playlist"` for lighter extraction
- Filters out None/invalid entries; skips videos that fail to parse

### Audio Stream (`services/youtube.py:266-321`)
- Audio-only selection: `vcodec == "none" and acodec != "none"`
- Best quality: highest `abr` (audio bitrate) or fallback to `tbr`
- Returns direct CDN URL (expires ~6 hours)

### Caching (`utils/cache.py`)
- In-memory with async locks for thread safety
- `get_or_compute(key, ttl, compute_fn)` — cache-aside pattern
- All endpoints accept `no_cache=true` query param to bypass

### Age-Restricted Content (`services/youtube.py:133-169`)
- Fallback chain: chrome → firefox → edge → safari → opera → brave → no-cookies
- Requires user to be logged into YouTube in at least one browser

## CODE STYLE

- **Indentation**: 4 spaces
- **Line length**: 100 characters
- **Quotes**: Double quotes
- **Target**: Python 3.13+
- **Import sorting**: isort-compatible via Ruff
- **Ruff rules**: E, W, F, I, B, C4, UP, ARG, SIM, TCH, PTH, ASYNC
- **Ignored**: B008 (FastAPI `Query()`/`Depends()` in defaults)

## COMMANDS

```bash
# Setup
uv sync --all-extras                    # Install all deps including dev
uv run pre-commit install               # Install git hooks

# Server
uv run uvicorn app.main:app --reload                    # Dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000  # Prod

# Testing
uv run pytest                           # All tests
uv run pytest --cov=app                 # With coverage
uv run pytest -m "not integration"      # Unit only
uv run pytest -m integration            # Integration only (needs YouTube)

# Code Quality
uv run ruff format .                    # Format
uv run ruff check --fix .              # Lint + auto-fix
uv run mypy app                         # Type check (strict)
uv run pre-commit run --all-files       # All hooks manually
```

## TESTING

- **Framework**: pytest + pytest-asyncio (`asyncio_mode = "auto"`)
- **HTTP client**: `AsyncClient` with `ASGITransport` (no real server needed)
- **Markers**: `@pytest.mark.integration` (requires YouTube connectivity), `@pytest.mark.slow`
- **Fixtures** (`conftest.py`): `async_client`, `sample_video_id` ("dQw4w9WgXcQ"), `sample_search_query`
- **mypy relaxed** for tests: `disallow_untyped_defs = false`

## ENVIRONMENT

All env vars use `SEARCHY_` prefix (via pydantic-settings):
```
SEARCHY_CACHE_TTL_SEARCH=300      # 5 min
SEARCHY_CACHE_TTL_VIDEO=600       # 10 min
SEARCHY_CACHE_TTL_AUDIO=60        # 1 min
SEARCHY_MAX_SEARCH_RESULTS=50
SEARCHY_DEFAULT_SEARCH_LIMIT=10
SEARCHY_LOG_LEVEL=INFO
SEARCHY_CORS_ORIGINS=["*"]
SEARCHY_YOUTUBE_DEFAULT_BROWSER=chrome
SEARCHY_YOUTUBE_FALLBACK_BROWSERS=["firefox","edge","safari","opera","brave"]
```

## PRODUCTION CONSIDERATIONS

- **CORS**: Restrict origins (currently `["*"]`)
- **Caching**: Consider Redis for multi-instance deployments
- **Rate limiting**: Not implemented — add for production
- **TLS**: Use reverse proxy (nginx/Caddy) for SSL termination
- **yt-dlp**: Monitor updates — YouTube may break extraction

## HIERARCHY

```
searchy/AGENTS.md (this file)
└── app/AGENTS.md
```
