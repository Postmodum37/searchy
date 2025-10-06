"""YouTube service for interacting with yt-dlp."""

import asyncio
from typing import Any

import yt_dlp

from app.models import VideoDetail, VideoFormat, VideoSearchResult


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
            "age_limit": 21,  # Bypass age restrictions
            "cookiesfrombrowser": (
                "chrome",
            ),  # Try to use Chrome cookies for age-restricted content
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
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, self._extract_info, search_query, self.default_opts
        )

        if not results:
            return []

        # Extract entries from search results
        entries = results.get("entries", [])

        return [self._parse_search_result(entry) for entry in entries if entry]

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
        loop = asyncio.get_event_loop()
        try:
            info = await loop.run_in_executor(
                None, self._extract_info, video_url, self.default_opts
            )
            if not info:
                return None
            return self._parse_video_detail(info)
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
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)  # type: ignore[no-any-return]
        except Exception:
            pass

        # Fallback: try with different browsers for cookies
        browsers = ["firefox", "edge", "safari", "opera", "brave"]
        for browser in browsers:
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
            url=entry.get("webpage_url", f"https://www.youtube.com/watch?v={entry.get('id')}"),
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
            url=info.get("webpage_url", f"https://www.youtube.com/watch?v={info.get('id')}"),
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
