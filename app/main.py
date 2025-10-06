"""Main FastAPI application for YouTube search service."""

import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models import (
    ErrorResponse,
    HealthResponse,
    VideoDetail,
    VideoSearchResponse,
)
from app.services.youtube import YouTubeService
from app.utils.cache import get_cache

# Version
VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    print(f"Starting Searchy API v{VERSION}")
    yield
    # Shutdown
    print("Shutting down Searchy API")


# Create FastAPI app
app = FastAPI(
    title="Searchy",
    description="Efficient YouTube search API service without API key requirements",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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
    limit: int = Query(10, description="Maximum number of results", ge=1, le=50),
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

        # Try to get from cache
        if not no_cache:
            cached_result = await cache.get(cache_key)
            if cached_result:
                return cached_result  # type: ignore[no-any-return]

        # Perform search
        results = await youtube_service.search(q, limit)

        # Create response
        response = VideoSearchResponse(query=q, results=results, count=len(results))

        # Cache the results
        await cache.set(cache_key, response, ttl=300)  # 5 minutes

        return response

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

        # Try to get from cache
        if not no_cache:
            cached_result = await cache.get(cache_key)
            if cached_result:
                return cached_result  # type: ignore[no-any-return]

        # Get video details
        video = await youtube_service.get_video_details(video_id)

        if not video:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

        # Cache the results
        await cache.set(cache_key, video, ttl=600)  # 10 minutes

        return video

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
