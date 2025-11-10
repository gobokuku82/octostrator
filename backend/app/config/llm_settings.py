"""LLM Settings Factory - 환경별 및 사용자 Tier별 LLM 설정

Phase 2: Context API를 위한 환경별 LLM 설정 관리
- Production: 비용 최적화 (낮은 temperature, 적은 tokens)
- Development: 품질 우선 (높은 temperature, 넉넉한 tokens)
- Testing: 재현성 (temperature=0, 최소 tokens)

Phase 3: 사용자 Tier별 LLM 설정 관리
- PREMIUM: 최고 품질 (gpt-4o, 높은 tokens)
- STANDARD: 균형잡힌 설정 (gpt-4o-mini, 중간 tokens)
- TRIAL: 비용 최소화 (gpt-4o-mini, 낮은 tokens)

Usage:
    from backend.app.config.llm_settings import get_llm_settings, Environment
    from backend.app.octostrator.contexts.app_context import UserTier

    # 환경별 설정 (Phase 2)
    settings = get_llm_settings(Environment.PRODUCTION)

    # 사용자 Tier별 설정 (Phase 3)
    from backend.app.config.llm_settings import get_llm_settings_for_user
    settings = get_llm_settings_for_user(UserTier.PREMIUM)

    # Custom 설정
    settings = get_llm_settings(Environment.PRODUCTION, overrides={
        "planning_temperature": 0.2,
        "chat_max_tokens": 3000
    })
"""
import os
from enum import Enum
from typing import Optional, Dict, Any

from backend.app.octostrator.contexts.app_context import LLMSettings, UserTier


class Environment(str, Enum):
    """환경 타입"""
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"


# ==========================================
# Environment-Specific Presets
# ==========================================

PRODUCTION_PRESET = {
    # Model
    "default_model": "gpt-4o-mini",

    # Intent (의도 파악)
    "intent_temperature": 0.5,
    "intent_max_tokens": 800,
    "intent_model": "gpt-4o-mini",

    # Planning (계획 수립)
    "planning_temperature": 0.2,
    "planning_max_tokens": 2048,
    "planning_model": "gpt-4o-mini",

    # Aggregator (집계)
    "aggregator_temperature": 0.4,
    "aggregator_max_tokens": 2500,
    "aggregator_model": "gpt-4o-mini",

    # Chat (대화 + 비용)
    "chat_temperature": 0.6,
    "chat_max_tokens": 3000,
    "chat_model": "gpt-4o-mini",

    # Graph (계획 정확성)
    "graph_temperature": 0.1,
    "graph_max_tokens": 1500,
    "graph_model": "gpt-4o-mini",

    # Report (보고서 생성)
    "report_temperature": 0.4,
    "report_max_tokens": 6000,
    "report_model": "gpt-4o-mini",

    # Agents (균형)
    "agent_temperature": 0.4,
    "agent_max_tokens": 3500,
    "agent_model": "gpt-4o-mini",
}

DEVELOPMENT_PRESET = {
    # Model
    "default_model": "gpt-4o-mini",

    # Intent (창의적 이해)
    "intent_temperature": 0.7,
    "intent_max_tokens": 1024,
    "intent_model": "gpt-4o-mini",

    # Planning (창의적 계획)
    "planning_temperature": 0.5,
    "planning_max_tokens": 4096,
    "planning_model": "gpt-4o-mini",

    # Aggregator (균형잡힌 분석)
    "aggregator_temperature": 0.6,
    "aggregator_max_tokens": 4096,
    "aggregator_model": "gpt-4o-mini",

    # Chat (자연스러운 대화)
    "chat_temperature": 0.7,
    "chat_max_tokens": 6000,
    "chat_model": "gpt-4o-mini",

    # Graph (창의적 구조)
    "graph_temperature": 0.3,
    "graph_max_tokens": 3000,
    "graph_model": "gpt-4o-mini",

    # Report (상세한 분석)
    "report_temperature": 0.6,
    "report_max_tokens": 10000,
    "report_model": "gpt-4o-mini",

    # Agents (풍부한 설명)
    "agent_temperature": 0.5,
    "agent_max_tokens": 5000,
    "agent_model": "gpt-4o-mini",
}

TESTING_PRESET = {
    # Model
    "default_model": "gpt-4o-mini",

    # 모든 노드: 재현성 확보 (temperature=0)
    # 빠른 테스트를 위해 적은 tokens
    "intent_temperature": 0.0,
    "intent_max_tokens": 512,
    "intent_model": "gpt-4o-mini",

    "planning_temperature": 0.0,
    "planning_max_tokens": 1024,
    "planning_model": "gpt-4o-mini",

    "aggregator_temperature": 0.0,
    "aggregator_max_tokens": 1024,
    "aggregator_model": "gpt-4o-mini",

    "chat_temperature": 0.0,
    "chat_max_tokens": 1024,
    "chat_model": "gpt-4o-mini",

    "graph_temperature": 0.0,
    "graph_max_tokens": 1024,
    "graph_model": "gpt-4o-mini",

    "report_temperature": 0.0,
    "report_max_tokens": 2048,
    "report_model": "gpt-4o-mini",

    "agent_temperature": 0.0,
    "agent_max_tokens": 1024,
    "agent_model": "gpt-4o-mini",
}


# ==========================================
# User Tier-Specific Presets (Phase 3)
# ==========================================

# Premium 사용자: 최고 품질 모델, 많은 토큰
PREMIUM_PRESET = {
    # Model
    "default_model": "gpt-4o",

    # Intent (창의적 이해)
    "intent_temperature": 0.7,
    "intent_max_tokens": 2048,
    "intent_model": "gpt-4o",

    # Planning (상세한 계획)
    "planning_temperature": 0.5,
    "planning_max_tokens": 6000,
    "planning_model": "gpt-4o",

    # Aggregator (고품질 분석)
    "aggregator_temperature": 0.6,
    "aggregator_max_tokens": 6000,
    "aggregator_model": "gpt-4o",

    # Chat (자연스러운 대화)
    "chat_temperature": 0.7,
    "chat_max_tokens": 8000,
    "chat_model": "gpt-4o",

    # Graph (정밀한 구조)
    "graph_temperature": 0.3,
    "graph_max_tokens": 4000,
    "graph_model": "gpt-4o",

    # Report (상세한 보고서)
    "report_temperature": 0.6,
    "report_max_tokens": 15000,
    "report_model": "gpt-4o",

    # Agents (풍부한 분석)
    "agent_temperature": 0.5,
    "agent_max_tokens": 8000,
    "agent_model": "gpt-4o",
}

# Standard 사용자: 균형잡힌 설정 (Development와 동일)
STANDARD_PRESET = DEVELOPMENT_PRESET.copy()

# Trial 사용자: 비용 최소화, 적은 토큰
TRIAL_PRESET = {
    # Model
    "default_model": "gpt-4o-mini",

    # Intent (빠른 이해)
    "intent_temperature": 0.5,
    "intent_max_tokens": 512,
    "intent_model": "gpt-4o-mini",

    # Planning (간단한 계획)
    "planning_temperature": 0.3,
    "planning_max_tokens": 1500,
    "planning_model": "gpt-4o-mini",

    # Aggregator (기본 분석)
    "aggregator_temperature": 0.4,
    "aggregator_max_tokens": 2000,
    "aggregator_model": "gpt-4o-mini",

    # Chat (간결한 대화)
    "chat_temperature": 0.6,
    "chat_max_tokens": 2000,
    "chat_model": "gpt-4o-mini",

    # Graph (기본 구조)
    "graph_temperature": 0.2,
    "graph_max_tokens": 1200,
    "graph_model": "gpt-4o-mini",

    # Report (간단한 보고서)
    "report_temperature": 0.4,
    "report_max_tokens": 3000,
    "report_model": "gpt-4o-mini",

    # Agents (기본 분석)
    "agent_temperature": 0.4,
    "agent_max_tokens": 2000,
    "agent_model": "gpt-4o-mini",
}


# ==========================================
# Factory Functions
# ==========================================

def get_llm_settings(
    environment: Environment = Environment.DEVELOPMENT,
    overrides: Optional[Dict[str, Any]] = None
) -> LLMSettings:
    """환경별 LLM 설정 생성

    Args:
        environment: 환경 타입 (production/development/testing)
        overrides: 커스텀 설정 오버라이드 (optional)

    Returns:
        LLMSettings: 환경에 맞춘 LLM 설정 인스턴스

    Examples:
        # Production 환경
        >>> settings = get_llm_settings(Environment.PRODUCTION)
        >>> settings.planning_temperature
        0.2

        # Development 환경
        >>> settings = get_llm_settings(Environment.DEVELOPMENT)
        >>> settings.planning_temperature
        0.5

        # Custom 설정
        >>> settings = get_llm_settings(
        ...     Environment.PRODUCTION,
        ...     overrides={"chat_max_tokens": 5000}
        ... )
        >>> settings.chat_max_tokens
        5000
    """
    # 환경별 preset 선택
    if environment == Environment.PRODUCTION:
        preset = PRODUCTION_PRESET.copy()
    elif environment == Environment.TESTING:
        preset = TESTING_PRESET.copy()
    else:
        preset = DEVELOPMENT_PRESET.copy()

    # 선택적 overrides 적용
    if overrides:
        preset.update(overrides)

    # LLMSettings 인스턴스 생성 (Pydantic 검증)
    return LLMSettings(**preset)


def get_llm_settings_from_env() -> LLMSettings:
    """환경 변수로부터 LLM 설정 가져오기

    SYSTEM_ENV 환경 변수를 읽어서 적절한 설정을 반환:
    - SYSTEM_ENV=production -> Production 설정
    - SYSTEM_ENV=testing -> Testing 설정
    - 기본/미설정 -> Development 설정

    Returns:
        LLMSettings: 환경에 맞춘 LLM 설정 인스턴스
    """
    env_name = os.getenv("SYSTEM_ENV", "development").lower()

    if env_name == "production":
        environment = Environment.PRODUCTION
    elif env_name == "testing":
        environment = Environment.TESTING
    else:
        environment = Environment.DEVELOPMENT

    return get_llm_settings(environment)


def get_llm_settings_for_user(
    user_tier: UserTier = UserTier.STANDARD,
    overrides: Optional[Dict[str, Any]] = None
) -> LLMSettings:
    """사용자 Tier별 LLM 설정 생성 (Phase 3)

    Args:
        user_tier: 사용자 등급 (PREMIUM/STANDARD/TRIAL)
        overrides: 커스텀 설정 오버라이드 (optional)

    Returns:
        LLMSettings: 사용자 Tier에 맞춘 LLM 설정 인스턴스

    Examples:
        # Premium 사용자
        >>> settings = get_llm_settings_for_user(UserTier.PREMIUM)
        >>> settings.agent_model
        'gpt-4o'
        >>> settings.agent_max_tokens
        8000

        # Trial 사용자
        >>> settings = get_llm_settings_for_user(UserTier.TRIAL)
        >>> settings.agent_model
        'gpt-4o-mini'
        >>> settings.agent_max_tokens
        2000

        # Custom 설정
        >>> settings = get_llm_settings_for_user(
        ...     UserTier.PREMIUM,
        ...     overrides={"chat_max_tokens": 10000}
        ... )
        >>> settings.chat_max_tokens
        10000
    """
    # 사용자 Tier별 preset 선택
    if user_tier == UserTier.PREMIUM:
        preset = PREMIUM_PRESET.copy()
    elif user_tier == UserTier.TRIAL:
        preset = TRIAL_PRESET.copy()
    else:
        preset = STANDARD_PRESET.copy()

    # 선택적 overrides 적용
    if overrides:
        preset.update(overrides)

    # LLMSettings 인스턴스 생성 (Pydantic 검증)
    return LLMSettings(**preset)


# ==========================================
# Token Cost Estimation
# ==========================================

def estimate_token_savings() -> Dict[str, Any]:
    """Production vs Development 설정 비용 비교

    Returns:
        Dict: 비용 절감 추정치
    """
    prod = get_llm_settings(Environment.PRODUCTION)
    dev = get_llm_settings(Environment.DEVELOPMENT)

    # 주요 노드의 평균 토큰
    prod_avg = (
        prod.intent_max_tokens +
        prod.planning_max_tokens +
        prod.aggregator_max_tokens +
        prod.chat_max_tokens +
        prod.graph_max_tokens
    ) / 5

    dev_avg = (
        dev.intent_max_tokens +
        dev.planning_max_tokens +
        dev.aggregator_max_tokens +
        dev.chat_max_tokens +
        dev.graph_max_tokens
    ) / 5

    reduction_pct = ((dev_avg - prod_avg) / dev_avg) * 100

    return {
        "production_avg_tokens": prod_avg,
        "development_avg_tokens": dev_avg,
        "token_reduction": dev_avg - prod_avg,
        "reduction_percentage": f"{reduction_pct:.1f}%",
        "estimated_cost_savings": "30-40% (노드 최적화 추가 시 50%)"
    }


# ==========================================
# Debug Utilities
# ==========================================

def print_settings_comparison():
    """환경별 설정 비교 출력 (디버깅)"""
    print("\n=== LLM Settings Comparison ===\n")

    for env in [Environment.PRODUCTION, Environment.DEVELOPMENT, Environment.TESTING]:
        settings = get_llm_settings(env)
        print(f"[{env.value.upper()}]")
        print(f"  Planning: temp={settings.planning_temperature}, tokens={settings.planning_max_tokens}")
        print(f"  Chat:     temp={settings.chat_temperature}, tokens={settings.chat_max_tokens}")
        print(f"  Graph:    temp={settings.graph_temperature}, tokens={settings.graph_max_tokens}")
        print()

    savings = estimate_token_savings()
    print(f"[COST SAVINGS]")
    print(f"  Token Reduction: {savings['reduction_percentage']}")
    print(f"  Estimated Savings: {savings['estimated_cost_savings']}")
    print()


# ==========================================
# Main (테스트용)
# ==========================================

if __name__ == "__main__":
    print("LLM Settings Factory Test\n")

    # 환경별 설정 테스트
    prod_settings = get_llm_settings(Environment.PRODUCTION)
    print(f"Production Planning Temp: {prod_settings.planning_temperature}")

    dev_settings = get_llm_settings(Environment.DEVELOPMENT)
    print(f"Development Planning Temp: {dev_settings.planning_temperature}")

    # 설정 비교
    print_settings_comparison()
