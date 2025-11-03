"""설정 테스트"""
import pytest
from backend.app.config.system import SystemConfig


def test_system_config_load():
    """SystemConfig 로드 테스트"""
    # When: SystemConfig 인스턴스 생성
    config = SystemConfig()

    # Then: 필수 설정 확인
    assert config.openai_api_key is not None
    assert len(config.openai_api_key) > 0

    # 기본값 확인
    assert config.system_api_host == "0.0.0.0"
    assert config.system_api_port == 8000
    assert config.system_debug == False


def test_system_config_postgres_url():
    """PostgreSQL URL 확인 테스트"""
    # When: SystemConfig 인스턴스 생성
    config = SystemConfig()

    # Then: PostgreSQL URL 확인
    assert config.postgres_url is not None
    assert config.postgres_url.startswith("postgresql://")
