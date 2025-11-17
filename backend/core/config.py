"""Configuration settings for Octostrator"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "Octostrator"
    app_version: str = "1.0.0"
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/octostrator",
        alias="DATABASE_URL"
    )
    postgres_user: str = Field(default="octostrator", alias="POSTGRES_USER")
    postgres_password: str = Field(default="octostrator123", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="octostrator", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    # Security
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=1440, alias="JWT_EXPIRATION_MINUTES")

    # LangSmith
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        alias="LANGCHAIN_ENDPOINT"
    )
    langchain_api_key: Optional[str] = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="octostrator", alias="LANGCHAIN_PROJECT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    @property
    def async_database_url(self) -> str:
        """Get async database URL"""
        if "postgresql://" in self.database_url:
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL"""
        if "postgresql+asyncpg://" in self.database_url:
            return self.database_url.replace("postgresql+asyncpg://", "postgresql://")
        return self.database_url


# Global settings instance
settings = Settings()