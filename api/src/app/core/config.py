"""Core configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = "development"

    # Database
    database_url: str = "sqlite+aiosqlite:///./test.db"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Valkey/Redis
    valkey_url: str = "redis://localhost:6379/0"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    cors_origins: str = "http://localhost:3000"

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # External APIs
    github_token: str | None = None
    libraries_io_api_key: str | None = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # OpenTelemetry
    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str = "http://jaeger:4317"
    otel_service_name: str = "wump-api"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"


# Global settings instance
settings = Settings()
