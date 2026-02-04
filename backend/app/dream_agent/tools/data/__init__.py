"""Data Tools - 데이터 수집 및 처리 도구

데이터 수집, 전처리, 외부 API 연동 도구를 제공합니다.

모듈:
- collector.py: 멀티 플랫폼 리뷰/댓글 수집
- preprocessor.py: 텍스트 전처리
- external_api.py: Google Trends 등 외부 API
- mock_loader.py: data/mock 폴더에서 테스트 데이터 로드

Mock 모드:
    환경변수 USE_MOCK_DATA=true 설정 시 data/mock 폴더에서 데이터 로드
"""

# Collector Tools
from .collector import (
    # @tool 함수
    collect_reviews,
    collect_reviews_from_platform,
    get_available_platforms,
    collect_youtube_comments,
    collect_and_save_reviews,
    COLLECTOR_TOOLS,
    # BaseTool 클래스
    CollectorTool,
    # 상수
    REAL_CRAWLER_PLATFORMS,
    MOCK_ONLY_PLATFORMS,
    ALL_PLATFORMS,
    # Direct 함수
    collect_reviews_direct,
    collect_from_amazon,
    collect_from_oliveyoung,
    collect_from_youtube,
    # 헬퍼 함수
    check_and_filter_duplicates,
    save_reviews_to_db,
)

# Preprocessor Tools
from .preprocessor import (
    # @tool 함수
    preprocess_reviews,
    PREPROCESSOR_TOOLS,
    # BaseTool 클래스
    PreprocessorTool,
    # Direct 함수
    preprocess_reviews_direct,
)

# External API Tools (Google Trends 등)
from .external_api import (
    # @tool 함수
    analyze_trends,
    compare_brand_trends,
    EXTERNAL_API_TOOLS,
    # BaseTool 클래스
    GoogleTrendsTool,
    # Direct 함수
    analyze_trends_direct,
    compare_brand_trends_direct,
)

# Mock Data Loader
from .mock_loader import (
    MockDataLoader,
    get_mock_loader,
    reset_mock_loader,
    is_mock_mode,
    get_mock_data_path,
)

__all__ = [
    # Collector @tool 함수
    "collect_reviews",
    "collect_reviews_from_platform",
    "get_available_platforms",
    "collect_youtube_comments",
    "collect_and_save_reviews",
    "COLLECTOR_TOOLS",
    # Collector BaseTool 클래스
    "CollectorTool",
    # Collector 상수
    "REAL_CRAWLER_PLATFORMS",
    "MOCK_ONLY_PLATFORMS",
    "ALL_PLATFORMS",
    # Collector Direct 함수
    "collect_reviews_direct",
    "collect_from_amazon",
    "collect_from_oliveyoung",
    "collect_from_youtube",
    # Collector 헬퍼 함수
    "check_and_filter_duplicates",
    "save_reviews_to_db",
    # Preprocessor @tool 함수
    "preprocess_reviews",
    "PREPROCESSOR_TOOLS",
    # Preprocessor BaseTool 클래스
    "PreprocessorTool",
    # Preprocessor Direct 함수
    "preprocess_reviews_direct",
    # External API @tool 함수
    "analyze_trends",
    "compare_brand_trends",
    "EXTERNAL_API_TOOLS",
    # External API BaseTool 클래스
    "GoogleTrendsTool",
    # External API Direct 함수
    "analyze_trends_direct",
    "compare_brand_trends_direct",
    # Mock Data Loader
    "MockDataLoader",
    "get_mock_loader",
    "reset_mock_loader",
    "is_mock_mode",
    "get_mock_data_path",
]
