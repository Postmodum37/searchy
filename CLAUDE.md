# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Searchy is a YouTube search API service built with FastAPI that provides search and metadata extraction without requiring YouTube API keys. It uses yt-dlp for video data extraction and includes smart caching, age-restriction handling via browser cookies, and audio stream URL extraction for music applications.

## Development Commands

### Environment Setup
```bash
# Install all dependencies including dev tools
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Running the Server
```bash
# Development server with auto-reload
uv run uvicorn app.main:app --reload

# Production server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=app

# Run specific test file
uv run pytest tests/test_api.py

# Run only unit tests (skip integration tests)
uv run pytest -m "not integration"

# Run integration tests only
uv run pytest -m integration
```

### Code Quality
```bash
# Format code with ruff
uv run ruff format .

# Lint code
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Type checking with mypy
uv run mypy app

# Run all pre-commit hooks manually
uv run pre-commit run --all-files
```

## Architecture

### Request Flow
1. **FastAPI App** (`app/main.py`) - Routes and middleware
2. **Service Layer** (`app/services/youtube.py`) - yt-dlp wrapper with async support
3. **Cache Layer** (`app/utils/cache.py`) - In-memory TTL-based caching
4. **Response Models** (`app/models.py`) - Pydantic validation

### Core Components

**YouTubeService** (`app/services/youtube.py:27-316`)
- Wraps yt-dlp with async execution using `asyncio.to_thread`
- Implements multi-browser cookie fallback for age-restricted content
- Tries browsers in order: chrome → firefox → edge → safari → opera → brave
- Falls back to no-cookie mode if all browser attempts fail
- Suppresses stderr to avoid console pollution from yt-dlp

**Caching Strategy** (`app/utils/cache.py:14-104`)
- In-memory cache with async locks for thread safety
- Different TTLs per endpoint type (configurable via `app/config.py`):
  - Search results: 5 minutes (frequently changing)
  - Video details: 10 minutes (relatively stable)
  - Audio URLs: 1 minute (URLs expire in ~6 hours but cached briefly)
- Helper function `get_or_compute()` implements cache-aside pattern
- All endpoints support `no_cache` query parameter to bypass cache

**Configuration** (`app/config.py:6-43`)
- Uses pydantic-settings with environment variable support
- Prefix: `SEARCHY_` (e.g., `SEARCHY_LOG_LEVEL=DEBUG`)
- All settings have sensible defaults
- Settings instance is a global singleton

### API Endpoints

Three main data endpoints:
- `/search` - Search YouTube videos
- `/video/{video_id}` - Get detailed video metadata including all formats
- `/audio/{video_id}` - Get optimized audio stream URL (for music bots)

Management endpoints:
- `/cache/stats` - Cache statistics
- `DELETE /cache` - Clear cache
- `/health` - Health check

### Error Handling

Custom exception handlers in `app/main.py:258-287`:
- `HTTPException` → Structured JSON error response
- Generic `Exception` → 500 error with safe message
- All errors include timestamp via `ErrorResponse` model

### Age-Restricted Content

The service handles age-restricted videos by extracting cookies from installed browsers. Configuration in `app/config.py:34-36`:
- Default browser: chrome
- Fallback browsers: firefox, edge, safari, opera, brave
- Requires user to be logged into YouTube in at least one browser

Browser cookie extraction happens in `YouTubeService._extract_info()` (app/services/youtube.py:127-163) with automatic fallback chain.

## Development Patterns

### Type Safety
- Strict mypy configuration in `pyproject.toml`
- Full type hints required (`disallow_untyped_defs = true`)
- Pydantic models for all API request/response data
- Exception: decorators and tests have relaxed rules

### Async Execution
- All route handlers are async
- yt-dlp (synchronous library) is wrapped with `asyncio.to_thread()` to avoid blocking
- Cache operations use async locks for safety

### Testing
- Pytest with async support (`pytest-asyncio`)
- Fixtures in `tests/conftest.py` provide test client and sample data
- Integration tests marked with `@pytest.mark.integration`
- Tests use `AsyncClient` with `ASGITransport` for FastAPI testing

### Code Style
- Ruff for linting and formatting (configured in `pyproject.toml:46-90`)
- Line length: 100 characters
- Target: Python 3.13+
- Import sorting with isort-compatible rules
- Pre-commit hooks enforce all quality checks

## Key Implementation Details

**Search Implementation** (`app/services/youtube.py:50-83`)
- Uses yt-dlp search syntax: `ytsearch{limit}:{query}`
- Filters out None/invalid entries from results
- Uses lighter extraction mode (`extract_flat: "in_playlist"`) for performance
- Error handling: skips videos that fail to parse rather than failing entire request

**Audio Stream Extraction** (`app/services/youtube.py:260-315`)
- Selects best audio-only format by bitrate
- Falls back to any format with audio if pure audio-only not available
- Returns direct stream URL (expires in ~6 hours per YouTube)
- Optimized for Discord bots and music applications

**Format Selection** (`app/services/youtube.py:270-290`)
- Audio-only: `vcodec == "none" and acodec != "none"`
- Best quality: highest `abr` (audio bitrate) or `tbr` (total bitrate)

## Configuration Notes

### Environment Variables
Set via `.env` file or environment with `SEARCHY_` prefix:
- `SEARCHY_CACHE_TTL_SEARCH` - Search cache TTL (default: 300s)
- `SEARCHY_CACHE_TTL_VIDEO` - Video cache TTL (default: 600s)
- `SEARCHY_CACHE_TTL_AUDIO` - Audio cache TTL (default: 60s)
- `SEARCHY_MAX_SEARCH_RESULTS` - Max results per search (default: 50)
- `SEARCHY_LOG_LEVEL` - Logging level (default: INFO)
- `SEARCHY_CORS_ORIGINS` - Allowed CORS origins (default: ["*"])

### Production Considerations
- CORS origins should be restricted (currently allows all origins)
- Consider Redis for distributed caching in multi-instance deployments
- Set up rate limiting (not currently implemented)
- Use reverse proxy (nginx/Caddy) for SSL/TLS termination
- Monitor yt-dlp updates as YouTube may introduce breaking changes
