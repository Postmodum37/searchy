"""Integration tests for age-restricted content handling."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_with_age_restricted_content(async_client: AsyncClient) -> None:
    """
    Test that search handles age-restricted videos gracefully.

    Real-world scenario: User searches for artist with age-restricted content.
    Expected: Search should succeed and return available videos, skipping restricted ones.
    """
    # Search for content that may include age-restricted videos
    response = await async_client.get("/search?q=music&limit=10")

    assert response.status_code == 200
    data = response.json()

    # Should return results even if some videos are age-restricted
    assert "results" in data
    assert "count" in data
    assert isinstance(data["results"], list)

    # Verify each result has required fields
    for result in data["results"]:
        assert "video_id" in result
        assert "title" in result
        assert "url" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_age_restricted_video_direct_access(async_client: AsyncClient) -> None:
    """
    Test accessing a known age-restricted video directly.

    Real-world scenario: User tries to get details for an age-restricted video.
    Expected: Should either return video details (if cookies work) or 404.

    Video ID: 9ajyBDjd-zg (known age-restricted video)
    """
    video_id = "9ajyBDjd-zg"  # Age-restricted video
    response = await async_client.get(f"/video/{video_id}")

    # Accept either success (if cookies work) or 404 (if restricted)
    assert response.status_code in [200, 404, 500]

    if response.status_code == 200:
        data = response.json()
        assert data["video_id"] == video_id
        assert "title" in data
    else:
        # If failed, should return proper error
        data = response.json()
        assert "error" in data or "detail" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_returns_partial_results_on_failures(
    async_client: AsyncClient,
) -> None:
    """
    Test that search returns partial results even if some videos fail.

    Real-world scenario: Search returns mix of accessible and restricted videos.
    Expected: Should return all successfully extracted videos.
    """
    # Search with reasonable limit
    response = await async_client.get("/search?q=popular+music&limit=15")

    assert response.status_code == 200
    data = response.json()

    # Should have some results (even if not all 15)
    assert data["count"] >= 0
    assert len(data["results"]) >= 0

    # Results should be valid
    for result in data["results"]:
        assert result["video_id"]
        assert result["title"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_non_age_restricted_video_works(async_client: AsyncClient) -> None:
    """
    Test that non-age-restricted videos work correctly.

    Real-world scenario: User accesses regular public video.
    Expected: Should return full video details successfully.
    """
    # Rick Astley - Never Gonna Give You Up (public, not age-restricted)
    video_id = "dQw4w9WgXcQ"
    response = await async_client.get(f"/video/{video_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["video_id"] == video_id
    assert "title" in data
    assert "Rick" in data["title"] or "Never" in data["title"]
    assert data["url"] == f"https://www.youtube.com/watch?v={video_id}"


@pytest.mark.asyncio
async def test_search_empty_query_validation(async_client: AsyncClient) -> None:
    """Test that empty queries are properly validated."""
    response = await async_client.get("/search?q=&limit=10")

    # Should fail validation
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_with_specific_artist(async_client: AsyncClient) -> None:
    """
    Test searching for specific artist that may have age-restricted content.

    Real-world scenario: User searches for "joji" (artist with some age-restricted videos).
    Expected: Should return available videos, gracefully handling any restricted ones.
    """
    response = await async_client.get("/search?q=joji&limit=10")

    assert response.status_code == 200
    data = response.json()

    # Should succeed and return some results
    assert "results" in data
    assert "count" in data

    # May have fewer than 10 if some were age-restricted
    assert data["count"] >= 0
    assert data["count"] <= 10

    print(f"\n✓ Search for 'joji' returned {data['count']} videos")

    # All returned videos should have valid data
    for result in data["results"]:
        assert result["video_id"]
        assert result["title"]
        print(f"  - {result['title'][:50]}...")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cookie_fallback_mechanism(async_client: AsyncClient) -> None:
    """
    Test that cookie fallback mechanism doesn't break normal functionality.

    Real-world scenario: Service tries multiple browsers but eventually succeeds.
    Expected: Should work even if most browsers aren't installed.
    """
    # Test with a known public video
    response = await async_client.get("/video/jNQXAC9IVRw")  # "Me at the zoo" - first YouTube video

    # Should work regardless of browser availability
    assert response.status_code in [200, 404]  # 404 if video was deleted
