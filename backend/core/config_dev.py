"""Development configuration without Docker"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class DevSettings(BaseSettings):
    """Development settings for local environment without Docker"""

    # Application
    app_name: str = "Octostrator"
    app_version: str = "1.0.0"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"

    # Database - Use SQLite for development
    use_sqlite: bool = True
    sqlite_db_path: str = "octostrator.db"
    database_url: str = Field(
        default="sqlite+aiosqlite:///octostrator.db",
        alias="DATABASE_URL"
    )

    # Memory - Use in-memory store for development
    use_memory_store: bool = True
    redis_url: str = Field(default="memory://", alias="REDIS_URL")

    # Security
    jwt_secret_key: str = "development-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    # Logging
    log_level: str = "DEBUG"
    log_format: str = "text"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    @property
    def async_database_url(self) -> str:
        """Get async database URL"""
        if self.use_sqlite:
            return f"sqlite+aiosqlite:///{self.sqlite_db_path}"
        return self.database_url


# Global settings instance for development
dev_settings = DevSettings()