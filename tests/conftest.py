"""Pytest configuration and fixtures."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture providing an async HTTP client for testing.

    Yields:
        AsyncClient configured for the FastAPI app
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_video_id() -> str:
    """
    Fixture providing a sample YouTube video ID for testing.

    Returns:
        A valid YouTube video ID
    """
    return "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up


@pytest.fixture
def sample_search_query() -> str:
    """
    Fixture providing a sample search query.

    Returns:
        A sample search query string
    """
    return "python tutorial"
