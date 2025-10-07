"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="SEARCHY_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API
    api_title: str = "Searchy"
    api_version: str = "0.1.0"
    api_description: str = "Efficient YouTube search API service without API key requirements"

    # Cache TTL (seconds)
    cache_ttl_search: int = 300  # 5 minutes
    cache_ttl_video: int = 600  # 10 minutes
    cache_default_ttl: int = 300

    # CORS
    cors_origins: list[str] = ["*"]

    # Limits
    max_search_results: int = 50
    default_search_limit: int = 10

    # YouTube Service
    youtube_age_limit: int = 21
    youtube_default_browser: str = "chrome"
    youtube_fallback_browsers: list[str] = ["firefox", "edge", "safari", "opera", "brave"]

    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
