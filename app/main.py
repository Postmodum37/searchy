"""Main FastAPI application for YouTube search service."""

import hashlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import (
    ErrorResponse,
    HealthResponse,
    VideoDetail,
    VideoSearchResponse,
)
from app.services.youtube import YouTubeService
from app.utils.cache import get_cache, get_or_compute

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Version
VERSION = settings.api_version


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info(f"Starting Searchy API v{VERSION}")
    yield
    # Shutdown
    logger.info("Shutting down Searchy API")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
youtube_service = YouTubeService()
cache = get_cache()


@app.get("/", response_model=dict[str, str])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "service": "Searchy",
        "version": VERSION,
        "description": "YouTube search API service",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with service status
    """
    return HealthResponse(status="healthy", version=VERSION)


@app.get("/search", response_model=VideoSearchResponse)
async def search_videos(
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(
        settings.default_search_limit,
        description="Maximum number of results",
        ge=1,
        le=settings.max_search_results,
    ),
    no_cache: bool = Query(False, description="Skip cache and force fresh results"),
) -> VideoSearchResponse:
    """
    Search YouTube for videos.

    Args:
        q: Search query string
        limit: Maximum number of results (1-50, default: 10)
        no_cache: Skip cache and force fresh results (default: False)

    Returns:
        VideoSearchResponse with search results

    Raises:
        HTTPException: If search fails
    """
    try:
        # Generate cache key
        cache_key = f"search:{hashlib.md5(f'{q}:{limit}'.encode()).hexdigest()}"

        # Define computation function
        async def compute_search() -> VideoSearchResponse:
            results = await youtube_service.search(q, limit)
            return VideoSearchResponse(query=q, results=results, count=len(results))

        # Get from cache or compute
        return await get_or_compute(
            cache_key=cache_key,
            compute_fn=compute_search,
            ttl=settings.cache_ttl_search,
            no_cache=no_cache,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@app.get("/video/{video_id}", response_model=VideoDetail)
async def get_video(
    video_id: str,
    no_cache: bool = Query(False, description="Skip cache and force fresh results"),
) -> VideoDetail:
    """
    Get detailed information about a specific video.

    Args:
        video_id: YouTube video ID
        no_cache: Skip cache and force fresh results (default: False)

    Returns:
        VideoDetail with comprehensive video information

    Raises:
        HTTPException: If video not found or retrieval fails
    """
    try:
        # Generate cache key
        cache_key = f"video:{video_id}"

        # Define computation function
        async def compute_video() -> VideoDetail:
            video = await youtube_service.get_video_details(video_id)
            if not video:
                raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
            return video

        # Get from cache or compute
        return await get_or_compute(
            cache_key=cache_key,
            compute_fn=compute_video,
            ttl=settings.cache_ttl_video,
            no_cache=no_cache,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video: {str(e)}") from e


@app.delete("/cache")
async def clear_cache() -> dict[str, str]:
    """
    Clear all cached data.

    Returns:
        Confirmation message
    """
    await cache.clear()
    return {"message": "Cache cleared successfully"}


@app.get("/cache/stats")
async def cache_stats() -> dict[str, int]:
    """
    Get cache statistics.

    Returns:
        Cache statistics including size
    """
    return {"size": cache.size()}


# Exception handler for custom error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: object, exc: HTTPException) -> JSONResponse:
    """
    Custom HTTP exception handler.

    Args:
        request: Request object
        exc: HTTPException

    Returns:
        JSONResponse with error details
    """
    error_response = ErrorResponse(error=exc.detail or "An error occurred", detail=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=error_response.model_dump(mode="json"))


@app.exception_handler(Exception)
async def general_exception_handler(request: object, exc: Exception) -> JSONResponse:
    """
    General exception handler for unexpected errors.

    Args:
        request: Request object
        exc: Exception

    Returns:
        JSONResponse with error details
    """
    error_response = ErrorResponse(error="Internal server error", detail=str(exc))
    return JSONResponse(status_code=500, content=error_response.model_dump(mode="json"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
