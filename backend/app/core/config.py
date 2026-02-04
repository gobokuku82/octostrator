"""Configuration Settings

환경변수 기반 설정 관리.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application Settings"""

    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")

    # LLM Settings
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4o-mini", env="DEFAULT_LLM_MODEL")
    LLM_TEMPERATURE: float = Field(default=0.7, env="LLM_TEMPERATURE")
    LLM_MAX_TOKENS: Optional[int] = Field(default=None, env="LLM_MAX_TOKENS")

    # API Settings
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Database (Phase 2)
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")

    # Checkpoint Database (LangGraph AsyncPostgresSaver)
    CHECKPOINT_DB_URI: str = Field(
        default="postgresql://postgres:root1234@localhost:5432/dream_agent",
        env="CHECKPOINT_DB_URI"
    )

    @property
    def checkpoint_db_uri(self) -> str:
        """Checkpoint DB URI (checkpointer.py에서 사용)"""
        return self.CHECKPOINT_DB_URI

    # Redis (Phase 2)
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
