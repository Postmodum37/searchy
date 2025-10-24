"""YouTube service for interacting with yt-dlp."""

import asyncio
import contextlib
import io
import sys
from collections.abc import Generator
from typing import Any

import yt_dlp

from app.config import settings
from app.models import (
    AudioFormatInfo,
    AudioStreamResponse,
    VideoDetail,
    VideoFormat,
    VideoSearchResult,
)


@contextlib.contextmanager
def suppress_stderr() -> Generator[None]:
    """Context manager to suppress stderr output."""
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stderr = old_stderr


class YouTubeService:
    """Service for searching and retrieving YouTube video information."""

    def __init__(self) -> None:
        """Initialize the YouTube service with default yt-dlp options."""
        self.default_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
            "no_check_certificate": True,
            "age_limit": settings.youtube_age_limit,
            "cookiesfrombrowser": (settings.youtube_default_browser,),
            "ignoreerrors": True,  # Continue on download errors
            "no_color": True,  # Disable color in output
        }

        # Separate options for search (lighter extraction)
        self.search_opts = {
            **self.default_opts,
            "extract_flat": "in_playlist",  # Don't extract full details during search
        }

    async def search(self, query: str, limit: int = 10) -> list[VideoSearchResult]:
        """
        Search YouTube for videos matching the query.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of VideoSearchResult objects
        """
        search_query = f"ytsearch{limit}:{query}"

        # Run yt-dlp in a thread pool to avoid blocking
        # Use search_opts for lighter extraction during search
        results = await asyncio.to_thread(self._extract_info, search_query, self.search_opts)

        if not results:
            return []

        # Extract entries from search results
        entries = results.get("entries", [])

        # Filter out None entries and parse valid ones
        valid_results = []
        for entry in entries:
            if entry and isinstance(entry, dict) and entry.get("id"):
                try:
                    valid_results.append(self._parse_search_result(entry))
                except Exception:
                    # Skip entries that fail to parse
                    continue

        return valid_results

    async def get_video_details(self, video_id: str) -> VideoDetail | None:
        """
        Get detailed information about a specific video.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoDetail object or None if video not found
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Run yt-dlp in a thread pool to avoid blocking
        try:
            info = await asyncio.to_thread(self._extract_info, video_url, self.default_opts)
            if not info:
                return None
            return self._parse_video_detail(info)
        except Exception:
            return None

    async def get_audio_stream_url(self, video_id: str) -> AudioStreamResponse | None:
        """
        Get direct audio stream URL for music playback.

        Args:
            video_id: YouTube video ID

        Returns:
            AudioStreamResponse with direct audio URL and metadata, or None if not found
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Run yt-dlp in a thread pool to avoid blocking
        try:
            info = await asyncio.to_thread(self._extract_info, video_url, self.default_opts)
            if not info:
                return None
            return self._parse_audio_stream(info)
        except Exception:
            return None

    def _extract_info(self, url: str, opts: dict[str, Any]) -> dict[str, Any] | None:
        """
        Extract information from YouTube using yt-dlp.

        Args:
            url: YouTube URL or search query
            opts: yt-dlp options

        Returns:
            Extracted information dictionary
        """
        # Try with default options (including cookies)
        with suppress_stderr():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False)  # type: ignore[no-any-return]
            except Exception:
                pass

            # Fallback: try with different browsers for cookies
            for browser in settings.youtube_fallback_browsers:
                try:
                    fallback_opts = opts.copy()
                    fallback_opts["cookiesfrombrowser"] = (browser,)
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        return ydl.extract_info(url, download=False)  # type: ignore[no-any-return]
                except Exception:
                    continue

            # Last fallback: try without cookies
            try:
                fallback_opts = opts.copy()
                fallback_opts.pop("cookiesfrombrowser", None)
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    return ydl.extract_info(url, download=False)  # type: ignore[no-any-return]
            except Exception:
                return None

    def _build_video_url(self, entry: dict[str, Any]) -> str:
        """
        Build YouTube video URL from entry data.

        Args:
            entry: Raw entry from yt-dlp

        Returns:
            YouTube video URL
        """
        return entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id')}"

    def _parse_search_result(self, entry: dict[str, Any]) -> VideoSearchResult:
        """
        Parse a search result entry into a VideoSearchResult model.

        Args:
            entry: Raw entry from yt-dlp

        Returns:
            VideoSearchResult object
        """
        return VideoSearchResult(
            video_id=entry.get("id", ""),
            title=entry.get("title", ""),
            url=self._build_video_url(entry),
            duration=entry.get("duration"),
            view_count=entry.get("view_count"),
            like_count=entry.get("like_count"),
            channel=entry.get("uploader") or entry.get("channel"),
            channel_id=entry.get("channel_id"),
            upload_date=entry.get("upload_date"),
            description=entry.get("description"),
            thumbnail=entry.get("thumbnail"),
            categories=entry.get("categories"),
            tags=entry.get("tags"),
        )

    def _parse_video_detail(self, info: dict[str, Any]) -> VideoDetail:
        """
        Parse detailed video information into a VideoDetail model.

        Args:
            info: Raw info from yt-dlp

        Returns:
            VideoDetail object
        """
        # Parse all formats
        formats = []
        audio_only_formats = []

        for fmt in info.get("formats", []):
            video_format = VideoFormat(
                format_id=fmt.get("format_id", ""),
                ext=fmt.get("ext", ""),
                quality=fmt.get("quality_label"),
                filesize=fmt.get("filesize"),
                acodec=fmt.get("acodec"),
                vcodec=fmt.get("vcodec"),
                abr=fmt.get("abr"),
                vbr=fmt.get("vbr"),
                format_note=fmt.get("format_note"),
            )
            formats.append(video_format)

            # Filter audio-only formats (for music)
            if fmt.get("vcodec") == "none" and fmt.get("acodec") != "none":
                audio_only_formats.append(video_format)

        # Find best audio format (highest bitrate)
        best_audio = None
        if audio_only_formats:
            best_audio = max(audio_only_formats, key=lambda f: f.abr if f.abr else 0, default=None)

        return VideoDetail(
            video_id=info.get("id", ""),
            title=info.get("title", ""),
            url=self._build_video_url(info),
            duration=info.get("duration"),
            view_count=info.get("view_count"),
            like_count=info.get("like_count"),
            channel=info.get("uploader") or info.get("channel"),
            channel_id=info.get("channel_id"),
            channel_url=info.get("channel_url"),
            upload_date=info.get("upload_date"),
            description=info.get("description"),
            thumbnail=info.get("thumbnail"),
            categories=info.get("categories"),
            tags=info.get("tags"),
            formats=formats if formats else None,
            audio_only_formats=audio_only_formats if audio_only_formats else None,
            best_audio_format=best_audio,
        )

    def _parse_audio_stream(self, info: dict[str, Any]) -> AudioStreamResponse:
        """
        Parse video info and extract the best audio stream URL.

        Args:
            info: Raw info from yt-dlp

        Returns:
            AudioStreamResponse with direct audio URL and metadata
        """
        # Find audio-only formats
        audio_formats = [
            fmt
            for fmt in info.get("formats", [])
            if fmt.get("vcodec") == "none" and fmt.get("acodec") != "none" and fmt.get("url")
        ]

        # Find best audio format (highest bitrate)
        if not audio_formats:
            # Fallback: use any format with audio
            audio_formats = [
                fmt
                for fmt in info.get("formats", [])
                if fmt.get("acodec") != "none" and fmt.get("url")
            ]

        if not audio_formats:
            raise ValueError("No audio format found for this video")

        # Get best audio format by bitrate
        best_format = max(audio_formats, key=lambda f: f.get("abr") or f.get("tbr") or 0)

        # Create AudioFormatInfo
        audio_format = AudioFormatInfo(
            format_id=best_format.get("format_id", ""),
            url=best_format.get("url", ""),
            ext=best_format.get("ext", ""),
            acodec=best_format.get("acodec"),
            abr=best_format.get("abr") or best_format.get("tbr"),
            filesize=best_format.get("filesize") or best_format.get("filesize_approx"),
            quality=best_format.get("format_note"),
        )

        # YouTube URLs typically expire in ~6 hours
        url_expires_in = 21600  # 6 hours in seconds

        return AudioStreamResponse(
            video_id=info.get("id", ""),
            title=info.get("title", ""),
            url=self._build_video_url(info),
            duration=info.get("duration"),
            channel=info.get("uploader") or info.get("channel"),
            thumbnail=info.get("thumbnail"),
            audio_format=audio_format,
            url_expires_in=url_expires_in,
        )
