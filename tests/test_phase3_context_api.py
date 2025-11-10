"""Phase 3 Context API 테스트

Phase 3: Context API 구현 검증
- UserTier 시스템
- AppContext 생성 및 관리
- LLM Settings 사용자별 설정
- Debug & Monitoring 기능
"""
import pytest
from backend.app.octostrator.contexts.app_context import (
    AppContext,
    UserTier,
    LLMSettings,
    get_user_tier,
    create_app_context
)
from backend.app.config.llm_settings import (
    get_llm_settings_for_user,
    PREMIUM_PRESET,
    STANDARD_PRESET,
    TRIAL_PRESET
)


class TestUserTierDetection:
    """UserTier 자동 감지 테스트"""

    def test_premium_user_detection(self):
        """Premium 사용자 감지"""
        user_id = "premium_user123"
        tier = get_user_tier(user_id)
        assert tier == UserTier.PREMIUM

    def test_trial_user_detection(self):
        """Trial 사용자 감지"""
        user_id = "trial_user456"
        tier = get_user_tier(user_id)
        assert tier == UserTier.TRIAL

    def test_standard_user_detection(self):
        """Standard 사용자 감지 (기본값)"""
        user_id = "regular_user789"
        tier = get_user_tier(user_id)
        assert tier == UserTier.STANDARD

    def test_no_prefix_user_detection(self):
        """Prefix 없는 사용자 (Standard로 분류)"""
        user_id = "user001"
        tier = get_user_tier(user_id)
        assert tier == UserTier.STANDARD


class TestLLMSettings:
    """LLM Settings 사용자별 설정 테스트"""

    def test_premium_settings(self):
        """Premium 사용자 LLM 설정"""
        settings = get_llm_settings_for_user(UserTier.PREMIUM)

        # Premium은 gpt-4o 모델 사용
        assert settings.default_model == "gpt-4o"
        assert settings.agent_model == "gpt-4o"
        assert settings.planning_model == "gpt-4o"

        # Premium은 높은 토큰 수
        assert settings.agent_max_tokens == 8000
        assert settings.report_max_tokens == 15000

    def test_standard_settings(self):
        """Standard 사용자 LLM 설정"""
        settings = get_llm_settings_for_user(UserTier.STANDARD)

        # Standard는 gpt-4o-mini 사용
        assert settings.default_model == "gpt-4o-mini"
        assert settings.agent_model == "gpt-4o-mini"

        # Standard는 중간 토큰 수
        assert settings.agent_max_tokens == 5000
        assert settings.report_max_tokens == 10000

    def test_trial_settings(self):
        """Trial 사용자 LLM 설정"""
        settings = get_llm_settings_for_user(UserTier.TRIAL)

        # Trial은 gpt-4o-mini 사용
        assert settings.default_model == "gpt-4o-mini"
        assert settings.agent_model == "gpt-4o-mini"

        # Trial은 낮은 토큰 수
        assert settings.agent_max_tokens == 2000
        assert settings.report_max_tokens == 3000

    def test_settings_with_override(self):
        """LLM 설정 오버라이드"""
        settings = get_llm_settings_for_user(
            UserTier.STANDARD,
            overrides={"agent_max_tokens": 6000}
        )

        assert settings.agent_max_tokens == 6000

    def test_default_settings(self):
        """기본값으로 설정 생성 (user_tier 미지정)"""
        settings = get_llm_settings_for_user()

        # 기본값은 STANDARD
        assert settings.default_model == "gpt-4o-mini"


class TestAppContextCreation:
    """AppContext 생성 테스트"""

    def test_basic_context_creation(self):
        """기본 AppContext 생성"""
        llm_settings = get_llm_settings_for_user(UserTier.STANDARD)
        context = create_app_context(
            user_id="test_user",
            session_id="session_001",
            llm_settings=llm_settings
        )

        assert context.user_id == "test_user"
        assert context.session_id == "session_001"
        assert context.llm_settings == llm_settings
        assert context.debug is False
        assert context.log_level == "INFO"
        assert context.user_tier == UserTier.STANDARD

    def test_premium_context_auto_detection(self):
        """Premium 사용자 자동 감지"""
        llm_settings = get_llm_settings_for_user(UserTier.PREMIUM)
        context = create_app_context(
            user_id="premium_user123",
            session_id="session_002",
            llm_settings=llm_settings
        )

        assert context.user_tier == UserTier.PREMIUM

    def test_trial_context_auto_detection(self):
        """Trial 사용자 자동 감지"""
        llm_settings = get_llm_settings_for_user(UserTier.TRIAL)
        context = create_app_context(
            user_id="trial_user456",
            session_id="session_003",
            llm_settings=llm_settings
        )

        assert context.user_tier == UserTier.TRIAL

    def test_context_with_debug_mode(self):
        """Debug 모드 활성화"""
        llm_settings = get_llm_settings_for_user()
        context = create_app_context(
            user_id="test_user",
            session_id="session_004",
            llm_settings=llm_settings,
            debug=True
        )

        assert context.debug is True
        assert context.log_level == "DEBUG"

    def test_context_with_custom_trace_id(self):
        """Custom Trace ID 제공"""
        llm_settings = get_llm_settings_for_user()
        custom_trace_id = "trace_12345"

        context = create_app_context(
            user_id="test_user",
            session_id="session_005",
            llm_settings=llm_settings,
            trace_id=custom_trace_id
        )

        assert context.trace_id == custom_trace_id

    def test_context_auto_generates_trace_id(self):
        """Trace ID 자동 생성"""
        llm_settings = get_llm_settings_for_user()
        context = create_app_context(
            user_id="test_user",
            session_id="session_006",
            llm_settings=llm_settings
        )

        assert context.trace_id is not None
        assert len(context.trace_id) > 0

    def test_context_metrics_initialization(self):
        """Metrics 초기화"""
        llm_settings = get_llm_settings_for_user()
        context = create_app_context(
            user_id="test_user",
            session_id="session_007",
            llm_settings=llm_settings
        )

        assert isinstance(context.metrics, dict)
        assert len(context.metrics) == 0

    def test_context_with_explicit_user_tier(self):
        """명시적으로 user_tier 제공"""
        llm_settings = get_llm_settings_for_user(UserTier.PREMIUM)
        context = create_app_context(
            user_id="regular_user",  # prefix가 없어도
            session_id="session_008",
            llm_settings=llm_settings,
            user_tier=UserTier.PREMIUM  # 명시적으로 PREMIUM 지정
        )

        assert context.user_tier == UserTier.PREMIUM


class TestAppContextDataclass:
    """AppContext Dataclass 필드 테스트"""

    def test_required_fields(self):
        """필수 필드 검증"""
        llm_settings = get_llm_settings_for_user()
        context = AppContext(
            user_id="user001",
            session_id="session001",
            llm_settings=llm_settings
        )

        assert context.user_id == "user001"
        assert context.session_id == "session001"
        assert context.llm_settings == llm_settings

    def test_default_values(self):
        """기본값 검증"""
        llm_settings = get_llm_settings_for_user()
        context = AppContext(
            user_id="user001",
            session_id="session001",
            llm_settings=llm_settings
        )

        assert context.debug is False
        assert context.log_level == "INFO"
        assert context.user_tier == UserTier.STANDARD
        assert context.db_conn is None
        assert isinstance(context.metrics, dict)

    def test_trace_id_auto_generation(self):
        """Trace ID 자동 생성 (dataclass field factory)"""
        llm_settings = get_llm_settings_for_user()
        context1 = AppContext(
            user_id="user001",
            session_id="session001",
            llm_settings=llm_settings
        )
        context2 = AppContext(
            user_id="user002",
            session_id="session002",
            llm_settings=llm_settings
        )

        # 각 인스턴스마다 다른 trace_id 생성
        assert context1.trace_id != context2.trace_id


class TestPhase3Integration:
    """Phase 3 통합 테스트"""

    def test_premium_user_workflow(self):
        """Premium 사용자 전체 워크플로우"""
        user_id = "premium_user123"
        session_id = "session_premium_001"

        # 1. User Tier 감지
        tier = get_user_tier(user_id)
        assert tier == UserTier.PREMIUM

        # 2. LLM Settings 생성
        llm_settings = get_llm_settings_for_user(tier)
        assert llm_settings.agent_model == "gpt-4o"

        # 3. AppContext 생성
        context = create_app_context(
            user_id=user_id,
            session_id=session_id,
            llm_settings=llm_settings,
            debug=True
        )

        assert context.user_tier == UserTier.PREMIUM
        assert context.debug is True
        assert context.log_level == "DEBUG"
        assert context.llm_settings.agent_model == "gpt-4o"

    def test_trial_user_workflow(self):
        """Trial 사용자 전체 워크플로우"""
        user_id = "trial_user456"
        session_id = "session_trial_001"

        # 1. User Tier 감지
        tier = get_user_tier(user_id)
        assert tier == UserTier.TRIAL

        # 2. LLM Settings 생성
        llm_settings = get_llm_settings_for_user(tier)
        assert llm_settings.agent_model == "gpt-4o-mini"
        assert llm_settings.agent_max_tokens == 2000

        # 3. AppContext 생성
        context = create_app_context(
            user_id=user_id,
            session_id=session_id,
            llm_settings=llm_settings,
            debug=False
        )

        assert context.user_tier == UserTier.TRIAL
        assert context.debug is False
        assert context.log_level == "INFO"

    def test_standard_user_workflow(self):
        """Standard 사용자 전체 워크플로우"""
        user_id = "user789"
        session_id = "session_standard_001"

        # 1. User Tier 감지
        tier = get_user_tier(user_id)
        assert tier == UserTier.STANDARD

        # 2. LLM Settings 생성
        llm_settings = get_llm_settings_for_user(tier)

        # 3. AppContext 생성
        context = create_app_context(
            user_id=user_id,
            session_id=session_id,
            llm_settings=llm_settings
        )

        assert context.user_tier == UserTier.STANDARD


class TestBackwardCompatibility:
    """Phase 2와의 하위 호환성 테스트"""

    def test_llm_settings_without_user_tier(self):
        """기존 코드 호환성: user_tier 없이 LLM Settings 생성"""
        # Phase 2 방식: get_llm_settings_for_user() 기본값 사용
        settings = get_llm_settings_for_user()

        # 기본값은 STANDARD
        assert settings is not None
        assert isinstance(settings, LLMSettings)

    def test_app_context_without_phase3_fields(self):
        """기존 코드 호환성: Phase 3 필드 없이 AppContext 생성"""
        llm_settings = get_llm_settings_for_user()

        # Phase 2 방식: 최소 필수 필드만 제공
        context = AppContext(
            user_id="user001",
            session_id="session001",
            llm_settings=llm_settings
        )

        # Phase 3 필드는 기본값으로 초기화
        assert context.debug is False
        assert context.log_level == "INFO"
        assert context.user_tier == UserTier.STANDARD


def test_phase3_context_api_summary():
    """Phase 3 Context API 전체 기능 요약 테스트"""
    print("\n" + "=" * 80)
    print("Phase 3 Context API - 기능 요약")
    print("=" * 80)

    # 1. UserTier 시스템
    print("\n1. UserTier 시스템:")
    for user_id, expected_tier in [
        ("premium_user123", UserTier.PREMIUM),
        ("trial_user456", UserTier.TRIAL),
        ("user789", UserTier.STANDARD)
    ]:
        tier = get_user_tier(user_id)
        print(f"   {user_id:20s} -> {tier.value:10s} ✓")
        assert tier == expected_tier

    # 2. LLM Settings 차별화
    print("\n2. LLM Settings 사용자별 차별화:")
    for tier, expected_model, expected_tokens in [
        (UserTier.PREMIUM, "gpt-4o", 8000),
        (UserTier.STANDARD, "gpt-4o-mini", 5000),
        (UserTier.TRIAL, "gpt-4o-mini", 2000)
    ]:
        settings = get_llm_settings_for_user(tier)
        print(f"   {tier.value:10s} -> Model: {settings.agent_model:15s}, Tokens: {settings.agent_max_tokens} ✓")
        assert settings.agent_model == expected_model
        assert settings.agent_max_tokens == expected_tokens

    # 3. AppContext 생성
    print("\n3. AppContext 생성 및 관리:")
    llm_settings = get_llm_settings_for_user(UserTier.PREMIUM)
    context = create_app_context(
        user_id="premium_user123",
        session_id="test_session",
        llm_settings=llm_settings,
        debug=True
    )
    print(f"   User ID:    {context.user_id}")
    print(f"   Session ID: {context.session_id}")
    print(f"   User Tier:  {context.user_tier.value}")
    print(f"   Debug Mode: {context.debug}")
    print(f"   Log Level:  {context.log_level}")
    print(f"   Trace ID:   {context.trace_id[:20]}... ✓")

    # 4. Debug & Monitoring
    print("\n4. Debug & Monitoring 기능:")
    print(f"   Trace ID:  {len(context.trace_id) > 0} ✓")
    print(f"   Metrics:   {isinstance(context.metrics, dict)} ✓")
    print(f"   Log Level: {context.log_level == 'DEBUG'} ✓")

    print("\n" + "=" * 80)
    print("✅ Phase 3 Context API - 모든 기능 정상 동작")
    print("=" * 80)


if __name__ == "__main__":
    # pytest 없이 직접 실행
    print("Phase 3 Context API 테스트 시작...")

    # 개별 테스트 실행
    test_user_tier = TestUserTierDetection()
    test_user_tier.test_premium_user_detection()
    test_user_tier.test_trial_user_detection()
    test_user_tier.test_standard_user_detection()
    print("✓ UserTier 테스트 통과")

    test_llm = TestLLMSettings()
    test_llm.test_premium_settings()
    test_llm.test_standard_settings()
    test_llm.test_trial_settings()
    print("✓ LLM Settings 테스트 통과")

    test_context = TestAppContextCreation()
    test_context.test_basic_context_creation()
    test_context.test_context_with_debug_mode()
    test_context.test_context_auto_generates_trace_id()
    print("✓ AppContext 생성 테스트 통과")

    test_integration = TestPhase3Integration()
    test_integration.test_premium_user_workflow()
    test_integration.test_trial_user_workflow()
    test_integration.test_standard_user_workflow()
    print("✓ 통합 테스트 통과")

    # 전체 요약
    test_phase3_context_api_summary()

    print("\n🎉 Phase 3 Context API 테스트 완료!")
