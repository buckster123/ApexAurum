"""
ApexAurum Cloud - Configuration

All settings loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App
    app_name: str = "ApexAurum Cloud"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    allowed_origins: str = "http://localhost:3000"

    # Database (Railway provides postgresql://, we convert to asyncpg)
    database_url: str = "postgresql://apex:apex@localhost:5432/apex"

    @property
    def async_database_url(self) -> str:
        """Convert standard postgres URL to async format."""
        url = self.database_url
        # Handle both postgres:// and postgresql://
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # S3/MinIO
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_bucket: str = "apex-storage"

    # Anthropic
    anthropic_api_key: Optional[str] = None

    # Optional APIs
    voyage_api_key: Optional[str] = None
    suno_api_key: Optional[str] = None

    # JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS into list."""
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
