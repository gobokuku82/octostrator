"""Collector Tool - 멀티 플랫폼 리뷰 데이터 수집

지원 플랫폼: amazon, oliveyoung, youtube, tiktok (크롤링), hwahae (Mock)

기능:
- Playwright 기반 크롤링 (Amazon, OliveYoung, TikTok)
- YouTube API 기반 댓글 수집
- CAPTCHA 감지 및 Skip 처리
- 히스토리 기반 재시작 지원 (중복 수집 방지)
- CSV 중간 저장
- 구조화된 로깅

(기존 ml_execution/agents/collector_agent.py에서 이전)
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# 지원 플랫폼 상수
# ============================================================

# 실제 크롤링 지원 플랫폼
REAL_CRAWLER_PLATFORMS = ["amazon", "oliveyoung", "youtube", "tiktok"]

# Mock 데이터만 지원하는 플랫폼
MOCK_ONLY_PLATFORMS = ["hwahae"]

# 모든 지원 플랫폼
ALL_PLATFORMS = REAL_CRAWLER_PLATFORMS + MOCK_ONLY_PLATFORMS


# ============================================================
# 헬퍼 함수
# ============================================================

def _collect_with_real_crawler(
    platform: str,
    keyword: str,
    limit: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """크롤러로 수집 (Playwright/API 기반)"""
    from backend.app.services.ml.collectors.collector_service import get_collector

    logger.debug(f"[Collector] Starting real crawl from {platform} for '{keyword}'...")

    collector = get_collector(platform)
    reviews = collector.collect(
        keyword=keyword,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
    )

    # Dict 형태로 변환
    formatted_reviews = _format_reviews(reviews, platform)

    logger.debug(f"[Collector] Formatted {len(formatted_reviews)} reviews from {platform}")
    return formatted_reviews


def _format_reviews(reviews: List[Any], platform: str) -> List[Dict[str, Any]]:
    """리뷰 데이터를 표준 형식으로 변환"""
    formatted_reviews = []

    for r in reviews:
        if isinstance(r, dict):
            formatted_reviews.append({
                "text": r.get("text", ""),
                "source": r.get("source", platform),
                "product_name": r.get("product_name", ""),
                "rating": r.get("rating"),
                "author": r.get("author", ""),
                "date": r.get("date", ""),
                "skin_type": r.get("skin_type"),
                "effectiveness": r.get("skin_concern") or r.get("effectiveness"),
                "likes": r.get("likes", 0),
                # YouTube 전용 필드
                "video_id": r.get("video_id"),
                "video_title": r.get("video_title"),
                "channel_name": r.get("channel_name"),
                "video_link": r.get("video_link"),
                "comment_id": r.get("comment_id"),
                # TikTok 전용 필드
                "video_url": r.get("video_url"),
                "hashtags": r.get("hashtags", []),
                "views": r.get("views", 0),
                "shares": r.get("shares", 0),
                "comments_count": r.get("comments_count", 0),
                "type": r.get("type"),  # "video" or "comment"
            })
        else:
            formatted_reviews.append({
                "text": getattr(r, "text", ""),
                "source": getattr(r, "source", platform),
                "product_name": getattr(r, "product_name", ""),
                "rating": getattr(r, "rating", None),
                "author": getattr(r, "author", ""),
                "date": getattr(r, "date", ""),
                "skin_type": getattr(r, "skin_type", None),
                "effectiveness": getattr(r, "effectiveness", None),
                "likes": getattr(r, "likes", 0),
            })

    return formatted_reviews


def _collect_with_mock(
    platform: str,
    keyword: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Mock 데이터로 수집 (data/mock 폴더에서 로드)"""
    from .mock_loader import get_mock_loader, is_mock_mode

    # data/mock 폴더 기반 mock 데이터 사용
    if is_mock_mode():
        logger.debug(f"[Collector] Loading mock data from data/mock for {platform}...")
        loader = get_mock_loader()
        reviews = loader.load_reviews(platform)[:limit]
        logger.debug(f"[Collector] Loaded {len(reviews)} mock reviews from data/mock")
        return reviews

    # 기존 서비스 기반 mock (fallback)
    try:
        from backend.app.services.ml.collectors import get_mock_collector

        logger.debug(f"[Collector] Using service mock data for {platform}...")
        collector = get_mock_collector(platform)
        raw_reviews = collector.collect(keyword, limit=limit)

        formatted_reviews = []
        for r in raw_reviews:
            formatted_reviews.append({
                "text": r.text,
                "source": r.source,
                "product_name": r.product_name,
                "rating": r.rating,
                "author": r.author,
                "date": r.date,
                "skin_type": r.skin_type,
                "effectiveness": r.effectiveness,
                "likes": r.likes,
            })
        return formatted_reviews

    except ImportError:
        logger.warning(f"[Collector] Mock collector not available, returning empty list")
        return []


def check_and_filter_duplicates(reviews: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    DB 기반 중복 필터링

    Args:
        reviews: 수집된 리뷰 리스트

    Returns:
        (filtered_reviews, duplicate_count)
    """
    try:
        from backend.app.services.ml.review_storage_service import get_review_storage_service

        service = get_review_storage_service()
        filtered = []
        duplicate_count = 0

        for review in reviews:
            is_dup, _ = service.is_duplicate_in_db(review)
            if is_dup:
                duplicate_count += 1
            else:
                filtered.append(review)

        logger.info(f"[Collector] Duplicate filter: {duplicate_count} duplicates found, {len(filtered)} unique")
        return filtered, duplicate_count

    except Exception as e:
        logger.warning(f"[Collector] Duplicate check error: {e}")
        return reviews, 0


def save_reviews_to_db(
    reviews: List[Dict[str, Any]],
    product_id: int,
    skip_duplicate_check: bool = False,
) -> Dict[str, Any]:
    """
    수집된 리뷰를 DB에 저장

    Args:
        reviews: 수집된 리뷰 리스트
        product_id: 제품 ID
        skip_duplicate_check: 중복 체크 건너뛰기

    Returns:
        저장 결과
    """
    try:
        from backend.app.services.ml.review_storage_service import save_reviews

        result = save_reviews(
            reviews=reviews,
            product_id=product_id,
            skip_duplicate_check=skip_duplicate_check,
        )

        logger.info(
            f"[Collector] DB save result: "
            f"inserted={result.new_inserted}, "
            f"duplicates={result.duplicates_skipped}"
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"[Collector] DB save error: {e}")
        return {
            "total_received": len(reviews),
            "new_inserted": 0,
            "duplicates_skipped": 0,
            "errors": len(reviews),
            "error_messages": [str(e)],
        }


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def collect_reviews(
    keyword: str,
    platforms: Optional[List[str]] = None,
    limit: int = 10,
    use_real_crawler: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    멀티 플랫폼에서 리뷰 데이터 수집

    Args:
        keyword: 검색 키워드 (예: "laneige", "설화수", "cosrx", "innisfree")
        platforms: 수집할 플랫폼 목록 ["amazon", "oliveyoung", "youtube", "tiktok", "hwahae"]
                   - amazon, oliveyoung, youtube, tiktok: 실제 크롤링
                   - hwahae: Mock 데이터
        limit: 플랫폼당 최대 수집 개수
        use_real_crawler: True면 크롤링, False면 Mock 데이터 사용
        start_date: 시작 날짜 (YYYY-MM-DD 형식, 선택사항)
        end_date: 종료 날짜 (YYYY-MM-DD 형식, 선택사항)

    Returns:
        수집된 리뷰 데이터:
        {
            "reviews": [...],  # 수집된 리뷰 리스트
            "total": int,      # 총 수집 개수
            "by_platform": {   # 플랫폼별 수집 통계
                "amazon": {"count": 10, "success": True},
                ...
            },
            "keyword": str,    # 검색 키워드
            "collected_at": str,  # 수집 시각
        }
    """
    if platforms is None:
        platforms = ["amazon", "oliveyoung"]

    collection_start = datetime.now()
    logger.info(f"[Collector] Starting collection - keyword: '{keyword}', platforms: {platforms}, limit: {limit}")

    all_reviews = []
    stats = {}

    for platform in platforms:
        platform_start = datetime.now()
        logger.info(f"[Collector] Collecting from {platform}...")

        try:
            # 크롤링 가능한 플랫폼이고 use_real_crawler가 True인 경우
            if platform in REAL_CRAWLER_PLATFORMS and use_real_crawler:
                reviews = _collect_with_real_crawler(
                    platform=platform,
                    keyword=keyword,
                    limit=limit,
                    start_date=start_date,
                    end_date=end_date,
                )
            else:
                # Mock 데이터 사용
                reviews = _collect_with_mock(
                    platform=platform,
                    keyword=keyword,
                    limit=limit,
                )

            all_reviews.extend(reviews)
            duration = (datetime.now() - platform_start).total_seconds()

            stats[platform] = {
                "count": len(reviews),
                "success": True,
                "duration_sec": duration,
            }
            logger.info(f"[Collector] {platform}: collected {len(reviews)} reviews in {duration:.2f}s")

        except Exception as e:
            duration = (datetime.now() - platform_start).total_seconds()
            error_msg = str(e)
            logger.error(f"[Collector] Error collecting from {platform}: {error_msg}")

            stats[platform] = {
                "count": 0,
                "success": False,
                "error": error_msg,
                "duration_sec": duration,
            }

    total_duration = (datetime.now() - collection_start).total_seconds()
    logger.info(f"[Collector] Collection complete - total: {len(all_reviews)} reviews in {total_duration:.2f}s")

    return {
        "reviews": all_reviews,
        "total": len(all_reviews),
        "by_platform": stats,
        "keyword": keyword,
        "collected_at": datetime.now().isoformat(),
        "duration_sec": total_duration,
    }


@tool
def collect_reviews_from_platform(
    platform: str,
    keyword: str,
    limit: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    특정 플랫폼에서만 리뷰 데이터 수집

    Args:
        platform: 수집할 플랫폼 ("amazon", "oliveyoung", "youtube")
        keyword: 검색 키워드
        limit: 최대 수집 개수
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        수집 결과
    """
    logger.info(f"[Collector] Single platform collection: {platform}, keyword: '{keyword}'")

    return collect_reviews.invoke({
        "keyword": keyword,
        "platforms": [platform],
        "limit": limit,
        "use_real_crawler": True,
        "start_date": start_date,
        "end_date": end_date,
    })


@tool
def get_available_platforms() -> Dict[str, Any]:
    """
    사용 가능한 플랫폼 목록 반환

    Returns:
        플랫폼 정보:
        {
            "real_crawler": ["amazon", "oliveyoung", "youtube"],  # 크롤링 지원
            "mock_only": ["tiktok", "hwahae"],  # Mock만 지원
            "all": ["amazon", "oliveyoung", "youtube", "tiktok", "hwahae"]
        }
    """
    return {
        "real_crawler": REAL_CRAWLER_PLATFORMS,
        "mock_only": MOCK_ONLY_PLATFORMS,
        "all": ALL_PLATFORMS,
    }


@tool
def collect_youtube_comments(
    keyword: str,
    limit: int = 100,
    max_videos: int = 10,
) -> Dict[str, Any]:
    """
    YouTube 댓글 수집 (전용 도구)

    Args:
        keyword: 검색 키워드 (브랜드명)
        limit: 총 수집할 댓글 수
        max_videos: 검색할 최대 동영상 수

    Returns:
        수집 결과
    """
    logger.info(f"[Collector] YouTube collection: keyword='{keyword}', limit={limit}, max_videos={max_videos}")

    try:
        from backend.app.services.ml.collectors import YouTubeCollector, YouTubeCollectorConfig

        config = YouTubeCollectorConfig(
            max_videos=max_videos,
            max_comments_per_video=min(limit // max_videos + 10, 100),
        )
        collector = YouTubeCollector(config=config)
        comments = collector.collect(keyword=keyword, limit=limit)

        formatted = _format_reviews(comments, "youtube")

        logger.info(f"[Collector] YouTube: collected {len(formatted)} comments")

        return {
            "reviews": formatted,
            "total": len(formatted),
            "by_platform": {"youtube": {"count": len(formatted), "success": True}},
            "keyword": keyword,
            "collected_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"[Collector] YouTube collection error: {e}")
        return {
            "reviews": [],
            "total": 0,
            "by_platform": {"youtube": {"count": 0, "success": False, "error": str(e)}},
            "keyword": keyword,
            "collected_at": datetime.now().isoformat(),
        }


@tool
def collect_and_save_reviews(
    keyword: str,
    platforms: Optional[List[str]] = None,
    limit: int = 10,
    product_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    리뷰 수집 후 DB에 저장 (중복 제외)

    Args:
        keyword: 검색 키워드
        platforms: 플랫폼 목록
        limit: 플랫폼당 수집 개수
        product_id: 제품 ID (DB 저장 시 필요)

    Returns:
        수집 및 저장 결과
    """
    # 1. 수집
    collection_result = collect_reviews.invoke({
        "keyword": keyword,
        "platforms": platforms or ["amazon", "oliveyoung"],
        "limit": limit,
        "use_real_crawler": True,
    })

    reviews = collection_result.get("reviews", [])

    # 2. 중복 필터링
    unique_reviews, duplicate_count = check_and_filter_duplicates(reviews)

    # 3. DB 저장 (product_id가 있는 경우)
    storage_result = None
    if product_id and unique_reviews:
        storage_result = save_reviews_to_db(
            reviews=unique_reviews,
            product_id=product_id,
            skip_duplicate_check=True,  # 이미 위에서 체크함
        )

    return {
        "collection": collection_result,
        "duplicate_filter": {
            "total_collected": len(reviews),
            "unique_count": len(unique_reviews),
            "duplicates_skipped": duplicate_count,
        },
        "storage": storage_result,
    }


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("collector")
class CollectorTool(BaseTool):
    """멀티 플랫폼 리뷰 수집 도구

    BaseTool 패턴으로 구현된 Collector.
    기존 @tool 함수들을 래핑합니다.
    """

    name: str = "collector"
    description: str = "멀티 플랫폼에서 리뷰 데이터를 수집합니다"
    category: str = "data"
    version: str = "1.0.0"

    def execute(
        self,
        keyword: str,
        platforms: Optional[List[str]] = None,
        limit: int = 10,
        use_real_crawler: bool = True,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """리뷰 수집 실행

        Args:
            keyword: 검색 키워드
            platforms: 수집할 플랫폼 목록
            limit: 플랫폼당 최대 수집 개수
            use_real_crawler: 실제 크롤러 사용 여부
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            수집된 리뷰 데이터
        """
        return collect_reviews.invoke({
            "keyword": keyword,
            "platforms": platforms,
            "limit": limit,
            "use_real_crawler": use_real_crawler,
            "start_date": start_date,
            "end_date": end_date,
        })

    async def aexecute(
        self,
        keyword: str,
        platforms: Optional[List[str]] = None,
        limit: int = 10,
        use_real_crawler: bool = True,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 리뷰 수집 실행"""
        return await collect_reviews.ainvoke({
            "keyword": keyword,
            "platforms": platforms,
            "limit": limit,
            "use_real_crawler": use_real_crawler,
            "start_date": start_date,
            "end_date": end_date,
        })


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def collect_reviews_direct(
    keyword: str,
    platforms: List[str] = None,
    limit: int = 10,
    use_real_crawler: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Agent 없이 직접 리뷰 수집"""
    logger.info(f"[Collector] Direct collection: keyword='{keyword}', platforms={platforms}")

    return collect_reviews.invoke({
        "keyword": keyword,
        "platforms": platforms or ["amazon", "oliveyoung"],
        "limit": limit,
        "use_real_crawler": use_real_crawler,
        "start_date": start_date,
        "end_date": end_date,
    })


def collect_from_amazon(keyword: str, limit: int = 10) -> Dict[str, Any]:
    """Amazon에서만 수집"""
    return collect_reviews_from_platform.invoke({
        "platform": "amazon",
        "keyword": keyword,
        "limit": limit,
    })


def collect_from_oliveyoung(keyword: str, limit: int = 10) -> Dict[str, Any]:
    """OliveYoung에서만 수집"""
    return collect_reviews_from_platform.invoke({
        "platform": "oliveyoung",
        "keyword": keyword,
        "limit": limit,
    })


def collect_from_youtube(keyword: str, limit: int = 100) -> Dict[str, Any]:
    """YouTube에서만 수집"""
    return collect_youtube_comments.invoke({
        "keyword": keyword,
        "limit": limit,
    })


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

COLLECTOR_TOOLS = [
    collect_reviews,
    collect_reviews_from_platform,
    get_available_platforms,
    collect_youtube_comments,
    collect_and_save_reviews,
]
