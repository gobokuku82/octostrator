"""시스템 설정 관리

Pydantic Settings를 사용한 환경 변수 관리
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class SystemConfig(BaseSettings):
    """시스템 설정 (최소 버전)

    .env 파일에서 환경 변수를 자동으로 로드
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # OpenAI API
    openai_api_key: str

    # PostgreSQL
    postgres_url: str = "postgresql://user:password@localhost:5432/octo_chatbot"

    # System
    system_debug: bool = False
    system_api_host: str = "0.0.0.0"
    system_api_port: int = 8000


# 싱글톤 인스턴스
config = SystemConfig()
