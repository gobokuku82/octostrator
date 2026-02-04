"""Intent Types - 의도 분류 타입 정의

K-Beauty 리테일 인사이트 에이전트를 위한 Intent 분류 체계
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# Primary Intent - 주요 의도 분류
# ============================================================

class PrimaryIntent(str, Enum):
    """
    주요 의도 분류

    사용자의 핵심 요청 유형을 분류합니다.
    """
    ANALYSIS = "analysis"      # 분석 요청 (시장, 채널, 경쟁사 등)
    CREATE = "create"          # 생성 요청 (리포트, 대시보드, 영상 등)
    QUERY = "query"            # 조회 요청 (데이터 조회, 상태 확인)
    COMPARE = "compare"        # 비교 요청 (브랜드 비교, 기간 비교)
    RECOMMEND = "recommend"    # 추천 요청 (전략 추천, 채널 추천)
    CHAT = "chat"              # 일반 대화 (인사, 도움말 등)


# ============================================================
# Sub Intent - 세부 의도 분류 (K-Beauty 특화)
# ============================================================

class SubIntent(str, Enum):
    """
    세부 의도 분류 - K-Beauty 도메인 특화

    주요 의도 하위의 구체적인 작업 유형을 분류합니다.
    """
    # ANALYSIS 하위
    CHANNEL_ANALYSIS = "channel_analysis"           # 채널 분석 (올리브영, 쿠팡 등)
    MARKET_ANALYSIS = "market_analysis"             # 시장 분석
    COMPETITOR_ANALYSIS = "competitor_analysis"     # 경쟁사 분석
    TREND_ANALYSIS = "trend_analysis"               # 트렌드 분석
    SALES_ANALYSIS = "sales_analysis"               # 매출 분석
    CUSTOMER_ANALYSIS = "customer_analysis"         # 고객 분석
    PRODUCT_ANALYSIS = "product_analysis"           # 제품 분석

    # CREATE 하위
    CREATE_REPORT = "create_report"                 # 리포트 생성
    CREATE_DASHBOARD = "create_dashboard"           # 대시보드 생성
    CREATE_STORYBOARD = "create_storyboard"         # 스토리보드 생성
    CREATE_VIDEO = "create_video"                   # 영상 생성
    CREATE_AD_CREATIVE = "create_ad_creative"       # 광고 크리에이티브 생성
    CREATE_PRESENTATION = "create_presentation"     # 프레젠테이션 생성

    # QUERY 하위
    QUERY_DATA = "query_data"                       # 데이터 조회
    QUERY_STATUS = "query_status"                   # 상태 조회
    QUERY_HISTORY = "query_history"                 # 이력 조회

    # COMPARE 하위
    COMPARE_BRANDS = "compare_brands"               # 브랜드 비교
    COMPARE_CHANNELS = "compare_channels"           # 채널 비교
    COMPARE_PERIODS = "compare_periods"             # 기간 비교
    COMPARE_MARKETS = "compare_markets"             # 시장 비교

    # RECOMMEND 하위
    RECOMMEND_STRATEGY = "recommend_strategy"       # 전략 추천
    RECOMMEND_CHANNEL = "recommend_channel"         # 채널 추천
    RECOMMEND_PRODUCT = "recommend_product"         # 제품 추천
    RECOMMEND_CONTENT = "recommend_content"         # 콘텐츠 추천

    # CHAT 하위
    CHAT_GREETING = "chat_greeting"                 # 인사
    CHAT_HELP = "chat_help"                         # 도움말
    CHAT_FEEDBACK = "chat_feedback"                 # 피드백
    CHAT_GENERAL = "chat_general"                   # 일반 대화


# ============================================================
# Intent Confidence Level
# ============================================================

class ConfidenceLevel(str, Enum):
    """의도 분류 신뢰도 레벨"""
    HIGH = "high"          # 0.8 이상
    MEDIUM = "medium"      # 0.5 ~ 0.8
    LOW = "low"            # 0.3 ~ 0.5
    UNCERTAIN = "uncertain" # 0.3 미만


# ============================================================
# Intent Entity - 추출된 엔티티
# ============================================================

class IntentEntity(BaseModel):
    """의도에서 추출된 엔티티"""
    entity_type: str              # 엔티티 타입 (brand, channel, market, period 등)
    value: str                    # 엔티티 값
    normalized_value: Optional[str] = None  # 정규화된 값
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "entity_type": "brand",
                "value": "설화수",
                "normalized_value": "SULWHASOO",
                "confidence": 0.95
            }
        }


# ============================================================
# Intent Result - 의도 분류 결과
# ============================================================

class IntentResult(BaseModel):
    """
    의도 분류 결과

    Cognitive 레이어에서 사용자 입력을 분석한 결과를 담습니다.
    """
    # 핵심 의도
    primary_intent: PrimaryIntent
    sub_intent: Optional[SubIntent] = None

    # 신뢰도
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.UNCERTAIN

    # 추출된 엔티티들
    entities: List[IntentEntity] = Field(default_factory=list)

    # 원본 입력
    original_query: str = ""
    normalized_query: Optional[str] = None

    # 언어 정보
    detected_language: str = "ko"  # ko, en, ja, zh

    # 컨텍스트 정보
    context: Dict[str, Any] = Field(default_factory=dict)

    # 분류 메서드
    classification_method: str = "unknown"  # llm, keyword, hybrid

    # 추가 의도 (복합 요청인 경우)
    secondary_intents: List["IntentResult"] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "primary_intent": "analysis",
                "sub_intent": "channel_analysis",
                "confidence": 0.92,
                "confidence_level": "high",
                "entities": [
                    {
                        "entity_type": "channel",
                        "value": "올리브영",
                        "normalized_value": "OLIVEYOUNG",
                        "confidence": 0.98
                    },
                    {
                        "entity_type": "brand",
                        "value": "라네즈",
                        "normalized_value": "LANEIGE",
                        "confidence": 0.95
                    }
                ],
                "original_query": "올리브영에서 라네즈 판매 현황 분석해줘",
                "detected_language": "ko",
                "classification_method": "llm"
            }
        }


# ============================================================
# Intent Mapping - 의도와 도구 매핑
# ============================================================

# Primary Intent -> 가능한 Sub Intents 매핑
PRIMARY_TO_SUB_INTENTS: Dict[PrimaryIntent, List[SubIntent]] = {
    PrimaryIntent.ANALYSIS: [
        SubIntent.CHANNEL_ANALYSIS,
        SubIntent.MARKET_ANALYSIS,
        SubIntent.COMPETITOR_ANALYSIS,
        SubIntent.TREND_ANALYSIS,
        SubIntent.SALES_ANALYSIS,
        SubIntent.CUSTOMER_ANALYSIS,
        SubIntent.PRODUCT_ANALYSIS,
    ],
    PrimaryIntent.CREATE: [
        SubIntent.CREATE_REPORT,
        SubIntent.CREATE_DASHBOARD,
        SubIntent.CREATE_STORYBOARD,
        SubIntent.CREATE_VIDEO,
        SubIntent.CREATE_AD_CREATIVE,
        SubIntent.CREATE_PRESENTATION,
    ],
    PrimaryIntent.QUERY: [
        SubIntent.QUERY_DATA,
        SubIntent.QUERY_STATUS,
        SubIntent.QUERY_HISTORY,
    ],
    PrimaryIntent.COMPARE: [
        SubIntent.COMPARE_BRANDS,
        SubIntent.COMPARE_CHANNELS,
        SubIntent.COMPARE_PERIODS,
        SubIntent.COMPARE_MARKETS,
    ],
    PrimaryIntent.RECOMMEND: [
        SubIntent.RECOMMEND_STRATEGY,
        SubIntent.RECOMMEND_CHANNEL,
        SubIntent.RECOMMEND_PRODUCT,
        SubIntent.RECOMMEND_CONTENT,
    ],
    PrimaryIntent.CHAT: [
        SubIntent.CHAT_GREETING,
        SubIntent.CHAT_HELP,
        SubIntent.CHAT_FEEDBACK,
        SubIntent.CHAT_GENERAL,
    ],
}


# Sub Intent -> 필요한 도구 매핑
SUB_INTENT_TO_TOOLS: Dict[SubIntent, Dict[str, List[str]]] = {
    # Analysis
    SubIntent.CHANNEL_ANALYSIS: {
        "ml_tools": ["collector", "preprocessor", "analyzer"],
        "biz_tools": ["report_agent", "dashboard_agent"]
    },
    SubIntent.MARKET_ANALYSIS: {
        "ml_tools": ["collector", "preprocessor", "analyzer", "insight"],
        "biz_tools": ["report_agent", "dashboard_agent"]
    },
    SubIntent.COMPETITOR_ANALYSIS: {
        "ml_tools": ["collector", "preprocessor", "analyzer"],
        "biz_tools": ["report_agent"]
    },
    SubIntent.TREND_ANALYSIS: {
        "ml_tools": ["collector", "preprocessor", "analyzer", "insight"],
        "biz_tools": ["report_agent", "dashboard_agent"]
    },
    SubIntent.SALES_ANALYSIS: {
        "ml_tools": ["collector", "preprocessor", "analyzer"],
        "biz_tools": ["report_agent", "dashboard_agent"]
    },
    SubIntent.CUSTOMER_ANALYSIS: {
        "ml_tools": ["collector", "preprocessor", "analyzer", "insight"],
        "biz_tools": ["report_agent"]
    },
    SubIntent.PRODUCT_ANALYSIS: {
        "ml_tools": ["collector", "preprocessor", "analyzer"],
        "biz_tools": ["report_agent"]
    },

    # Create
    SubIntent.CREATE_REPORT: {
        "ml_tools": [],
        "biz_tools": ["report_agent"]
    },
    SubIntent.CREATE_DASHBOARD: {
        "ml_tools": [],
        "biz_tools": ["dashboard_agent"]
    },
    SubIntent.CREATE_STORYBOARD: {
        "ml_tools": [],
        "biz_tools": ["storyboard_agent"]
    },
    SubIntent.CREATE_VIDEO: {
        "ml_tools": [],
        "biz_tools": ["storyboard_agent", "video_agent"]
    },
    SubIntent.CREATE_AD_CREATIVE: {
        "ml_tools": [],
        "biz_tools": ["ad_creative_agent"]
    },
    SubIntent.CREATE_PRESENTATION: {
        "ml_tools": [],
        "biz_tools": ["report_agent"]  # PPTX 렌더링
    },

    # Query
    SubIntent.QUERY_DATA: {
        "ml_tools": ["collector"],
        "biz_tools": []
    },
    SubIntent.QUERY_STATUS: {
        "ml_tools": [],
        "biz_tools": []
    },
    SubIntent.QUERY_HISTORY: {
        "ml_tools": [],
        "biz_tools": []
    },

    # Compare
    SubIntent.COMPARE_BRANDS: {
        "ml_tools": ["collector", "preprocessor", "analyzer"],
        "biz_tools": ["report_agent", "dashboard_agent"]
    },
    SubIntent.COMPARE_CHANNELS: {
        "ml_tools": ["collector", "preprocessor", "analyzer"],
        "biz_tools": ["report_agent", "dashboard_agent"]
    },
    SubIntent.COMPARE_PERIODS: {
        "ml_tools": ["collector", "preprocessor", "analyzer"],
        "biz_tools": ["report_agent", "dashboard_agent"]
    },
    SubIntent.COMPARE_MARKETS: {
        "ml_tools": ["collector", "preprocessor", "analyzer"],
        "biz_tools": ["report_agent", "dashboard_agent"]
    },

    # Recommend
    SubIntent.RECOMMEND_STRATEGY: {
        "ml_tools": ["analyzer", "insight"],
        "biz_tools": ["report_agent"]
    },
    SubIntent.RECOMMEND_CHANNEL: {
        "ml_tools": ["analyzer", "insight"],
        "biz_tools": ["report_agent"]
    },
    SubIntent.RECOMMEND_PRODUCT: {
        "ml_tools": ["analyzer", "insight"],
        "biz_tools": ["report_agent"]
    },
    SubIntent.RECOMMEND_CONTENT: {
        "ml_tools": ["analyzer", "insight"],
        "biz_tools": ["storyboard_agent", "ad_creative_agent"]
    },

    # Chat
    SubIntent.CHAT_GREETING: {
        "ml_tools": [],
        "biz_tools": []
    },
    SubIntent.CHAT_HELP: {
        "ml_tools": [],
        "biz_tools": []
    },
    SubIntent.CHAT_FEEDBACK: {
        "ml_tools": [],
        "biz_tools": []
    },
    SubIntent.CHAT_GENERAL: {
        "ml_tools": [],
        "biz_tools": []
    },
}


# ============================================================
# Helper Functions
# ============================================================

def get_confidence_level(confidence: float) -> ConfidenceLevel:
    """신뢰도 값을 레벨로 변환"""
    if confidence >= 0.8:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.5:
        return ConfidenceLevel.MEDIUM
    elif confidence >= 0.3:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.UNCERTAIN


def get_tools_for_intent(sub_intent: SubIntent) -> Dict[str, List[str]]:
    """Sub Intent에 필요한 도구 목록 반환"""
    return SUB_INTENT_TO_TOOLS.get(sub_intent, {"ml_tools": [], "biz_tools": []})


def get_valid_sub_intents(primary_intent: PrimaryIntent) -> List[SubIntent]:
    """Primary Intent에 해당하는 유효한 Sub Intent 목록 반환"""
    return PRIMARY_TO_SUB_INTENTS.get(primary_intent, [])


def create_intent_result(
    primary_intent: PrimaryIntent,
    sub_intent: Optional[SubIntent] = None,
    confidence: float = 0.0,
    original_query: str = "",
    entities: Optional[List[IntentEntity]] = None,
    classification_method: str = "unknown",
    detected_language: str = "ko",
    context: Optional[Dict[str, Any]] = None
) -> IntentResult:
    """IntentResult 생성 헬퍼 함수"""
    return IntentResult(
        primary_intent=primary_intent,
        sub_intent=sub_intent,
        confidence=confidence,
        confidence_level=get_confidence_level(confidence),
        entities=entities or [],
        original_query=original_query,
        detected_language=detected_language,
        classification_method=classification_method,
        context=context or {}
    )
