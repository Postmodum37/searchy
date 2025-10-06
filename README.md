# Searchy

Efficient YouTube search API service without API key requirements. Built with FastAPI, yt-dlp, and modern Python tooling.

## Features

- 🔍 **Search YouTube** - Search for videos without API keys
- 📊 **Detailed Metadata** - Get comprehensive video information including formats, audio options, and more
- 🎵 **Music-Optimized** - Extracts audio-only formats perfect for music applications
- 🔒 **Age-Restriction Bypass** - Automatically handles age-restricted content using browser cookies
- ⚡ **Fast & Efficient** - Built with FastAPI and async support
- 💾 **Smart Caching** - In-memory caching to reduce redundant requests
- 🐳 **Docker Ready** - Multi-stage Docker builds for production deployment
- 📝 **Type Safe** - Full type hints with mypy validation
- ✅ **Well Tested** - Comprehensive test suite with pytest
- 📖 **Auto Documentation** - OpenAPI/Swagger docs at `/docs`

## Tech Stack

- **Python 3.13+**
- **FastAPI** - Modern web framework
- **yt-dlp** - YouTube data extraction
- **uvicorn** - ASGI server
- **uv** - Fast Python package manager
- **ruff** - Linting and formatting
- **mypy** - Static type checking
- **pytest** - Testing framework

## Quick Start

### Using uv (Recommended)

```bash
# Install dependencies
uv sync

# Run the development server
uv run uvicorn app.main:app --reload

# Visit http://localhost:8000/docs for interactive API documentation
```

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Visit http://localhost:8000/docs
```

### Using Docker directly

```bash
# Build image
docker build -t searchy .

# Run container
docker run -p 8000:8000 searchy
```

## API Endpoints

### Search Videos

```bash
GET /search?q={query}&limit={limit}
```

**Parameters:**
- `q` (required): Search query
- `limit` (optional): Number of results (1-50, default: 10)
- `no_cache` (optional): Skip cache and force fresh results (default: false)

**Example:**
```bash
curl "http://localhost:8000/search?q=python%20tutorial&limit=5"
```

**Response:**
```json
{
  "query": "python tutorial",
  "results": [
    {
      "video_id": "xyz123",
      "title": "Python Tutorial for Beginners",
      "url": "https://www.youtube.com/watch?v=xyz123",
      "duration": 3600,
      "view_count": 1000000,
      "like_count": 50000,
      "channel": "Tech Channel",
      "channel_id": "UCxyz",
      "upload_date": "20250101",
      "description": "Learn Python...",
      "thumbnail": "https://...",
      "categories": ["Education"],
      "tags": ["python", "tutorial"]
    }
  ],
  "count": 5,
  "timestamp": "2025-01-01T12:00:00"
}
```

### Get Video Details

```bash
GET /video/{video_id}
```

**Parameters:**
- `video_id` (required): YouTube video ID
- `no_cache` (optional): Skip cache and force fresh results

**Example:**
```bash
curl "http://localhost:8000/video/dQw4w9WgXcQ"
```

**Response:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "duration": 212,
  "formats": [...],
  "audio_only_formats": [...],
  "best_audio_format": {
    "format_id": "140",
    "ext": "m4a",
    "abr": 128,
    "acodec": "mp4a.40.2"
  }
}
```

### Health Check

```bash
GET /health
```

### Cache Management

```bash
# Get cache statistics
GET /cache/stats

# Clear cache
DELETE /cache
```

## Development

### Setup Development Environment

```bash
# Install dependencies including dev tools
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run only unit tests (skip integration)
uv run pytest -m "not integration"
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Fix linting issues automatically
uv run ruff check --fix .

# Type check
uv run mypy app
```

### Run Pre-commit Hooks Manually

```bash
uv run pre-commit run --all-files
```

## Project Structure

```
searchy/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app & routes
│   ├── models.py            # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   └── youtube.py       # yt-dlp wrapper
│   └── utils/
│       ├── __init__.py
│       └── cache.py         # Caching utility
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   └── test_api.py          # API tests
├── pyproject.toml           # Project config & dependencies
├── .pre-commit-config.yaml  # Pre-commit hooks
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # Docker Compose config
└── README.md
```

## Configuration

### Environment Variables

Currently, the service works without configuration. Future additions:

- `CACHE_TTL` - Cache time-to-live in seconds (default: 300)
- `MAX_SEARCH_RESULTS` - Maximum search results allowed (default: 50)

### CORS

CORS is enabled for all origins by default. For production, configure allowed origins in `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Update this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Age-Restricted Content

The service automatically handles age-restricted videos by extracting cookies from installed browsers. It tries browsers in this order:

1. Chrome (default)
2. Firefox
3. Edge
4. Safari
5. Opera
6. Brave

**Requirements:** You must be logged into YouTube in at least one of these browsers for age-restricted content to work.

If no browser cookies are available, the service will still work but may skip age-restricted videos.

## Production Deployment

### Docker

The included `Dockerfile` uses multi-stage builds for optimal image size and security:

- Non-root user execution
- Minimal runtime dependencies
- Health checks included

### Considerations

- Consider adding Redis for distributed caching in multi-instance deployments
- Set up rate limiting for production use
- Configure proper CORS origins
- Use a reverse proxy (nginx, Caddy) for SSL/TLS
- Monitor yt-dlp updates as YouTube may change

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube data extraction
- [uv](https://github.com/astral-sh/uv) - Python package manager
- [ruff](https://github.com/astral-sh/ruff) - Linter and formatter
