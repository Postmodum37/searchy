"""Pydantic models for API request and response validation."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class VideoFormat(BaseModel):
    """Model representing a video/audio format."""

    format_id: str = Field(..., description="Format identifier")
    ext: str = Field(..., description="File extension")
    quality: str | None = Field(None, description="Quality label")
    filesize: int | None = Field(None, description="File size in bytes")
    acodec: str | None = Field(None, description="Audio codec")
    vcodec: str | None = Field(None, description="Video codec")
    abr: float | None = Field(None, description="Audio bitrate")
    vbr: float | None = Field(None, description="Video bitrate")
    format_note: str | None = Field(None, description="Format notes")


class VideoSearchResult(BaseModel):
    """Model representing a single video search result."""

    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    url: str = Field(..., description="Video URL")
    duration: int | None = Field(None, description="Duration in seconds")
    view_count: int | None = Field(None, description="Number of views")
    like_count: int | None = Field(None, description="Number of likes")
    channel: str | None = Field(None, description="Channel name")
    channel_id: str | None = Field(None, description="Channel ID")
    upload_date: str | None = Field(None, description="Upload date (YYYYMMDD)")
    description: str | None = Field(None, description="Video description")
    thumbnail: str | None = Field(None, description="Thumbnail URL")
    categories: list[str] | None = Field(None, description="Video categories")
    tags: list[str] | None = Field(None, description="Video tags")


class VideoSearchResponse(BaseModel):
    """Model representing a search response with multiple results."""

    query: str = Field(..., description="Search query")
    results: list[VideoSearchResult] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results returned")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Response timestamp"
    )


class VideoDetail(BaseModel):
    """Model representing detailed video information."""

    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    url: str = Field(..., description="Video URL")
    duration: int | None = Field(None, description="Duration in seconds")
    view_count: int | None = Field(None, description="Number of views")
    like_count: int | None = Field(None, description="Number of likes")
    channel: str | None = Field(None, description="Channel name")
    channel_id: str | None = Field(None, description="Channel ID")
    channel_url: str | None = Field(None, description="Channel URL")
    upload_date: str | None = Field(None, description="Upload date (YYYYMMDD)")
    description: str | None = Field(None, description="Video description")
    thumbnail: str | None = Field(None, description="Thumbnail URL")
    categories: list[str] | None = Field(None, description="Video categories")
    tags: list[str] | None = Field(None, description="Video tags")
    formats: list[VideoFormat] | None = Field(None, description="Available formats")
    audio_only_formats: list[VideoFormat] | None = Field(
        None, description="Audio-only formats (for music)"
    )
    best_audio_format: VideoFormat | None = Field(None, description="Best audio format")


class HealthResponse(BaseModel):
    """Model representing health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Health check timestamp"
    )


class ErrorResponse(BaseModel):
    """Model representing an error response."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Error timestamp"
    )
