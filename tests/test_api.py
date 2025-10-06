"""Tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(async_client: AsyncClient) -> None:
    """Test root endpoint."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Searchy"
    assert "version" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    """Test health check endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_videos(async_client: AsyncClient, sample_search_query: str) -> None:
    """Test video search endpoint."""
    response = await async_client.get(f"/search?q={sample_search_query}&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == sample_search_query
    assert "results" in data
    assert "count" in data
    assert isinstance(data["results"], list)
    assert data["count"] <= 5


@pytest.mark.asyncio
async def test_search_videos_validation(async_client: AsyncClient) -> None:
    """Test search endpoint validation."""
    # Test missing query
    response = await async_client.get("/search")
    assert response.status_code == 422  # Validation error

    # Test invalid limit
    response = await async_client.get("/search?q=test&limit=0")
    assert response.status_code == 422  # Validation error

    # Test limit too high
    response = await async_client.get("/search?q=test&limit=100")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_video_details(async_client: AsyncClient, sample_video_id: str) -> None:
    """Test video details endpoint."""
    response = await async_client.get(f"/video/{sample_video_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == sample_video_id
    assert "title" in data
    assert "url" in data
    assert "formats" in data


@pytest.mark.asyncio
async def test_get_nonexistent_video(async_client: AsyncClient) -> None:
    """Test fetching a non-existent video."""
    response = await async_client.get("/video/invalid_id_123")
    # Should return 404 or 500 depending on yt-dlp behavior
    assert response.status_code in [404, 500]


@pytest.mark.asyncio
async def test_cache_endpoints(async_client: AsyncClient) -> None:
    """Test cache management endpoints."""
    # Test cache stats
    response = await async_client.get("/cache/stats")
    assert response.status_code == 200
    data = response.json()
    assert "size" in data

    # Test clear cache
    response = await async_client.delete("/cache")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

    # Verify cache is empty
    response = await async_client.get("/cache/stats")
    data = response.json()
    assert data["size"] == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_caching_behavior(async_client: AsyncClient, sample_search_query: str) -> None:
    """Test that caching works correctly."""
    # First request (not cached)
    response1 = await async_client.get(f"/search?q={sample_search_query}&limit=3")
    assert response1.status_code == 200
    data1 = response1.json()

    # Second request (should be cached)
    response2 = await async_client.get(f"/search?q={sample_search_query}&limit=3")
    assert response2.status_code == 200
    data2 = response2.json()

    # Responses should be identical
    assert data1["count"] == data2["count"]
    assert len(data1["results"]) == len(data2["results"])

    # Test no_cache parameter
    response3 = await async_client.get(f"/search?q={sample_search_query}&limit=3&no_cache=true")
    assert response3.status_code == 200
