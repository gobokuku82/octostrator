"""Application Context - 런타임 불변 정보

LangGraph 1.0+ Context API 사용
- Context는 State와 별도로 관리되는 불변 런타임 정보
- Checkpoint에 저장되지 않음
- 모든 노드에서 접근 가능

Phase 2 Updates:
- LLMSettings 추가: 노드별 LLM 파라미터 관리
- 환경별 설정 분리 (production/dev/test)
- 비용 최적화: 노드별 max_tokens, temperature 커스터마이징

Phase 3 Updates:
- Debug 모드 추가: 개발 환경에서 상세 로깅
- Trace ID 추가: 분산 추적을 위한 고유 ID
- Metrics 추가: 성능 메트릭 수집
- User Tier 추가: 사용자별 맞춤 설정 (Premium/Standard/Trial)

참고:
- reports/context_management/langgraph_context_analysis.md
- reports/contextAPI/IMPLEMENTATION_GUIDE_CONTEXT_API.md
- reports/contextAPI/PHASE3_QUICK_START_GUIDE.md
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
import uuid
from pydantic import BaseModel, Field


# ==========================================
# LLM Settings Schema
# ==========================================

class LLMSettings(BaseModel):
    """노드별 LLM 설정

    Phase 2: Context API를 통한 노드별 LLM 파라미터 관리
    - 각 노드의 특성에 맞는 temperature/max_tokens 설정
    - Pydantic 검증으로 타입 안정성 확보
    - 환경별 설정 분리 (config/llm_settings.py)

    Node-Specific Configuration:
    - intent: 창의적 의도 파악 (temp 0.7, tokens 1024)
    - planning: 정확한 계획 수립 (temp 0.3, tokens 2048)
    - aggregator: 균형잡힌 분석 (temp 0.5, tokens 3072)
    - chat_generator: 자연스러운 대화 (temp 0.7, tokens 4096)
    - graph_generator: JSON 정확성 (temp 0.2, tokens 2048)
    - report_generator: 긴 보고서 생성 (temp 0.5, tokens 8192)
    """

    # Model Selection
    default_model: str = Field(default="gpt-4o-mini", description="기본 LLM 모델")

    # Intent Understanding Node
    intent_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Intent 노드 temperature")
    intent_max_tokens: int = Field(default=1024, ge=1, le=16384, description="Intent 노드 max tokens")
    intent_model: str = Field(default="gpt-4o-mini", description="Intent 노드 모델")

    # Planning Node
    planning_temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="Planning 노드 temperature")
    planning_max_tokens: int = Field(default=2048, ge=1, le=16384, description="Planning 노드 max tokens")
    planning_model: str = Field(default="gpt-4o-mini", description="Planning 노드 모델")

    # Aggregator Node
    aggregator_temperature: float = Field(default=0.5, ge=0.0, le=2.0, description="Aggregator 노드 temperature")
    aggregator_max_tokens: int = Field(default=3072, ge=1, le=16384, description="Aggregator 노드 max tokens")
    aggregator_model: str = Field(default="gpt-4o-mini", description="Aggregator 노드 모델")

    # Chat Generator Node
    chat_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Chat 노드 temperature")
    chat_max_tokens: int = Field(default=4096, ge=1, le=16384, description="Chat 노드 max tokens")
    chat_model: str = Field(default="gpt-4o-mini", description="Chat 노드 모델")

    # Graph Generator Node
    graph_temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Graph 노드 temperature")
    graph_max_tokens: int = Field(default=2048, ge=1, le=16384, description="Graph 노드 max tokens")
    graph_model: str = Field(default="gpt-4o-mini", description="Graph 노드 모델")

    # Report Generator Node
    report_temperature: float = Field(default=0.5, ge=0.0, le=2.0, description="Report 노드 temperature")
    report_max_tokens: int = Field(default=8192, ge=1, le=16384, description="Report 노드 max tokens")
    report_model: str = Field(default="gpt-4o-mini", description="Report 노드 모델")

    # Agent Nodes (Diet, Workout, Schedule, Member Care, Coaching)
    agent_temperature: float = Field(default=0.5, ge=0.0, le=2.0, description="Agent 노드 기본 temperature")
    agent_max_tokens: int = Field(default=4096, ge=1, le=16384, description="Agent 노드 기본 max tokens")
    agent_model: str = Field(default="gpt-4o-mini", description="Agent 노드 기본 모델")


# ==========================================
# User Tier Enum (Phase 3)
# ==========================================

class UserTier(str, Enum):
    """사용자 등급

    Phase 3: 사용자별 맞춤 설정을 위한 Tier 시스템
    - PREMIUM: 프리미엄 사용자 (높은 품질, 많은 토큰, 긴 timeout)
    - STANDARD: 일반 사용자 (균형잡힌 설정)
    - TRIAL: 체험 사용자 (낮은 품질, 적은 토큰, 짧은 timeout)
    """
    PREMIUM = "premium"
    STANDARD = "standard"
    TRIAL = "trial"


# ==========================================
# Application Context
# ==========================================

@dataclass
class AppContext:
    """Application 런타임 Context

    Phase 2 Updates:
    - llm_settings 추가: 노드별 LLM 파라미터 관리
    - Runtime을 통해 모든 노드에서 접근 가능

    Phase 3 Updates:
    - debug: 디버그 모드 (개발 환경 상세 로깅)
    - trace_id: 분산 추적 ID (요청 추적)
    - metrics: 성능 메트릭 수집 (Todo, HITL, Node 성능)
    - log_level: 로그 레벨 (DEBUG/INFO/WARNING/ERROR)
    - user_tier: 사용자 등급 (Premium/Standard/Trial)

    불변 정보만 포함:
    - user_id: 사용자 ID
    - session_id: 세션 ID
    - llm_settings: 노드별 LLM 설정 (Phase 2 신규)
    - db_conn: DB 연결 (Phase 5에서 추가 예정)
    """

    # 사용자 정보
    user_id: str
    session_id: str

    # LLM 설정 (Phase 2: 노드별 커스터마이징)
    llm_settings: LLMSettings

    # ===== Phase 3: Debug & Monitoring =====
    # 디버그 모드 (개발 환경에서 상세 로깅)
    debug: bool = False

    # 분산 추적 ID (요청 추적용)
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 메트릭 수집 (성능 추적)
    metrics: Dict[str, Any] = field(default_factory=dict)

    # 로그 레벨 (DEBUG/INFO/WARNING/ERROR)
    log_level: str = "INFO"

    # ===== Phase 3: User Tier =====
    # 사용자 등급 (Premium/Standard/Trial)
    user_tier: UserTier = UserTier.STANDARD

    # DB 연결 (Phase 5에서 활성화)
    db_conn: Optional[str] = None


# ==========================================
# Context Factory Functions (Phase 3)
# ==========================================

def get_user_tier(user_id: str) -> UserTier:
    """사용자 ID로부터 Tier 추출

    Phase 3: 사용자 ID의 prefix를 분석하여 Tier 결정
    - "premium_"로 시작: PREMIUM
    - "trial_"로 시작: TRIAL
    - 그 외: STANDARD

    Args:
        user_id: 사용자 ID

    Returns:
        UserTier: 사용자 등급

    Examples:
        >>> get_user_tier("premium_user123")
        UserTier.PREMIUM

        >>> get_user_tier("trial_user456")
        UserTier.TRIAL

        >>> get_user_tier("regular_user789")
        UserTier.STANDARD
    """
    if user_id.startswith("premium_"):
        return UserTier.PREMIUM
    elif user_id.startswith("trial_"):
        return UserTier.TRIAL
    else:
        return UserTier.STANDARD


def create_app_context(
    user_id: str,
    session_id: str,
    llm_settings: LLMSettings,
    debug: bool = False,
    trace_id: Optional[str] = None,
    user_tier: Optional[UserTier] = None,
) -> AppContext:
    """AppContext 생성 Factory 함수

    Phase 3: Context 생성을 단순화하는 Factory 함수
    - user_tier가 None이면 user_id로부터 자동 추출
    - trace_id가 None이면 UUID 자동 생성
    - debug 모드에 따라 log_level 자동 설정

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        llm_settings: LLM 설정
        debug: 디버그 모드 (기본: False)
        trace_id: 분산 추적 ID (기본: 자동 생성)
        user_tier: 사용자 등급 (기본: user_id로부터 추출)

    Returns:
        AppContext: 생성된 Context 인스턴스

    Examples:
        >>> from backend.app.config.llm_settings import get_llm_settings
        >>> settings = get_llm_settings()
        >>> context = create_app_context(
        ...     user_id="premium_user123",
        ...     session_id="session_001",
        ...     llm_settings=settings,
        ...     debug=True
        ... )
        >>> context.user_tier
        UserTier.PREMIUM
        >>> context.log_level
        'DEBUG'
    """
    # User Tier 자동 추출
    if user_tier is None:
        user_tier = get_user_tier(user_id)

    # Trace ID 자동 생성
    if trace_id is None:
        trace_id = str(uuid.uuid4())

    # Debug 모드에 따른 log_level 설정
    log_level = "DEBUG" if debug else "INFO"

    return AppContext(
        user_id=user_id,
        session_id=session_id,
        llm_settings=llm_settings,
        debug=debug,
        trace_id=trace_id,
        metrics={},
        log_level=log_level,
        user_tier=user_tier,
        db_conn=None,
    )
