"""Mock Data Loader - data/mock 폴더에서 테스트 데이터 로드

Todo 테스트를 위한 mock 데이터를 로드합니다.
실제 로직은 동작하지만, 데이터만 mock에서 가져옵니다.

사용법:
    from .mock_loader import MockDataLoader

    loader = MockDataLoader()
    reviews = loader.load_reviews("naver")
    trends = loader.load_trends()
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Mock 데이터 루트 경로
# backend/app/dream_agent/tools/data/mock_loader.py -> data/mock/
MOCK_DATA_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "data" / "mock"


def get_mock_data_path() -> Path:
    """Mock 데이터 루트 경로 반환"""
    return MOCK_DATA_ROOT


def is_mock_mode() -> bool:
    """Mock 모드 여부 확인 (환경변수 USE_MOCK_DATA)"""
    return os.environ.get("USE_MOCK_DATA", "true").lower() == "true"


class MockDataLoader:
    """Mock 데이터 로더

    data/mock/ 폴더 구조:
    ├── reviews/          # 리뷰 데이터
    │   ├── naver_reviews.json
    │   └── instagram_reviews.json
    ├── analysis/         # 분석 결과
    │   ├── sentiment_result.json
    │   └── keywords_result.json
    ├── insights/         # 인사이트
    │   └── insight_result.json
    ├── trends/           # Google Trends
    │   └── google_trends.json
    ├── internal/         # 내부 데이터
    │   └── products.json
    └── ads/              # 광고 데이터
        └── ad_prompts.json
    """

    def __init__(self, mock_root: Optional[Path] = None):
        self.root = mock_root or MOCK_DATA_ROOT
        logger.debug(f"[MockLoader] Initialized with root: {self.root}")

    def _load_json(self, relative_path: str) -> Dict[str, Any]:
        """JSON 파일 로드"""
        file_path = self.root / relative_path

        if not file_path.exists():
            logger.warning(f"[MockLoader] File not found: {file_path}")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"[MockLoader] Loaded: {relative_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"[MockLoader] JSON parse error in {relative_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"[MockLoader] Error loading {relative_path}: {e}")
            return {}

    # ============================================================
    # 리뷰 데이터 로드
    # ============================================================

    def load_reviews(self, platform: str = "naver") -> List[Dict[str, Any]]:
        """플랫폼별 리뷰 데이터 로드

        Args:
            platform: "naver", "instagram" 등

        Returns:
            리뷰 리스트
        """
        filename = f"{platform}_reviews.json"
        data = self._load_json(f"reviews/{filename}")
        return data.get("reviews", [])

    def load_all_reviews(self) -> Dict[str, List[Dict[str, Any]]]:
        """모든 플랫폼 리뷰 로드"""
        reviews_dir = self.root / "reviews"
        all_reviews = {}

        if reviews_dir.exists():
            for file in reviews_dir.glob("*_reviews.json"):
                platform = file.stem.replace("_reviews", "")
                all_reviews[platform] = self.load_reviews(platform)

        return all_reviews

    def collect_mock_reviews(
        self,
        keyword: str,
        platforms: List[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """수집 결과 형태로 mock 리뷰 반환

        Args:
            keyword: 검색 키워드 (로깅용)
            platforms: 플랫폼 목록 ["naver", "instagram"]
            limit: 플랫폼당 최대 개수

        Returns:
            collect_reviews와 동일한 형식의 결과
        """
        from datetime import datetime

        if platforms is None:
            platforms = ["naver", "instagram"]

        all_reviews = []
        stats = {}

        for platform in platforms:
            reviews = self.load_reviews(platform)[:limit]
            all_reviews.extend(reviews)
            stats[platform] = {
                "count": len(reviews),
                "success": True,
                "duration_sec": 0.1,  # mock이므로 빠름
            }

        logger.info(f"[MockLoader] Collected {len(all_reviews)} mock reviews for '{keyword}'")

        return {
            "reviews": all_reviews,
            "total": len(all_reviews),
            "by_platform": stats,
            "keyword": keyword,
            "collected_at": datetime.now().isoformat(),
            "duration_sec": 0.1,
            "is_mock": True,
        }

    # ============================================================
    # 분석 결과 로드
    # ============================================================

    def load_sentiment_result(self) -> Dict[str, Any]:
        """감성 분석 결과 로드"""
        return self._load_json("analysis/sentiment_result.json")

    def load_keywords_result(self) -> Dict[str, Any]:
        """키워드 분석 결과 로드"""
        return self._load_json("analysis/keywords_result.json")

    def get_preprocessed_reviews(self) -> Dict[str, Any]:
        """전처리된 리뷰 형태로 반환 (preprocess_reviews 결과 형식)"""
        sentiment = self.load_sentiment_result()

        # 감성 분석 결과에서 전처리된 형태 추출
        reviews = sentiment.get("reviews", [])

        preprocessed = []
        lang_stats = {"ko": 0, "en": 0}

        for review in reviews:
            preprocessed.append({
                "text": review.get("text", ""),
                "cleaned_text": review.get("text", ""),  # mock에서는 동일
                "language": "ko",
                "tokens": review.get("text", "").split()[:10],
                "hashtags": review.get("hashtags", []),
                "quality_score": 0.85,
                "source": review.get("source", "mock"),
                "sentiment": review.get("sentiment", {}),
            })
            lang_stats["ko"] += 1

        return {
            "reviews": preprocessed,
            "count": len(preprocessed),
            "filtered_count": 0,
            "language_stats": lang_stats,
            "is_mock": True,
        }

    # ============================================================
    # 트렌드 데이터 로드
    # ============================================================

    def load_trends(self) -> Dict[str, Any]:
        """Google Trends mock 데이터 로드"""
        return self._load_json("trends/google_trends.json")

    def get_trends_result(
        self,
        keyword: str,
        timeframe: str = "today 3-m",
        geo: str = "KR",
    ) -> Dict[str, Any]:
        """analyze_trends 결과 형식으로 반환"""
        trends = self.load_trends()
        keyword_data = trends.get("trends_data", {}).get(keyword, {})

        if not keyword_data:
            # 키워드가 없으면 첫 번째 데이터 반환
            first_key = list(trends.get("trends_data", {}).keys())[0] if trends.get("trends_data") else None
            keyword_data = trends.get("trends_data", {}).get(first_key, {}) if first_key else {}

        return {
            "success": True,
            "is_mock": True,
            "data": {
                "keyword": keyword,
                "timeframe": timeframe,
                "geo": geo,
                "interest_over_time": keyword_data.get("interest_over_time", []),
                "rising_queries": trends.get("related_queries", {}).get(keyword, {}).get("rising", []),
                "top_queries": trends.get("related_queries", {}).get(keyword, {}).get("top", []),
                "top_regions": [],
                "trend_direction": keyword_data.get("trend_direction", "stable"),
                "change_percent": 0.0,
            }
        }

    # ============================================================
    # 인사이트 데이터 로드
    # ============================================================

    def load_insights(self) -> Dict[str, Any]:
        """인사이트 결과 로드"""
        return self._load_json("insights/insight_result.json")

    def get_insights_result(self) -> Dict[str, Any]:
        """인사이트 생성 결과 형식으로 반환"""
        insights = self.load_insights()
        return {
            **insights,
            "is_mock": True,
        }

    # ============================================================
    # 내부 데이터 로드
    # ============================================================

    def load_products(self) -> Dict[str, Any]:
        """제품 정보 로드"""
        return self._load_json("internal/products.json")

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """제품 ID로 조회"""
        products = self.load_products()
        for product in products.get("products", []):
            if product.get("product_id") == product_id:
                return product
        return None

    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """제품 검색"""
        products = self.load_products()
        query_lower = query.lower()

        results = []
        for product in products.get("products", []):
            name = product.get("name", "").lower()
            category = product.get("category", "").lower()

            if query_lower in name or query_lower in category:
                results.append(product)

        return results

    # ============================================================
    # 광고 데이터 로드
    # ============================================================

    def load_ad_prompts(self) -> Dict[str, Any]:
        """광고 프롬프트 로드"""
        return self._load_json("ads/ad_prompts.json")

    def get_ad_concepts(self) -> List[Dict[str, Any]]:
        """광고 컨셉 목록 반환"""
        data = self.load_ad_prompts()
        return data.get("ad_concepts", [])

    def get_video_script(self) -> Dict[str, Any]:
        """비디오 스크립트 반환"""
        data = self.load_ad_prompts()
        return data.get("video_script", {})


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_mock_loader: Optional[MockDataLoader] = None


def get_mock_loader() -> MockDataLoader:
    """Mock 데이터 로더 싱글톤 인스턴스"""
    global _mock_loader
    if _mock_loader is None:
        _mock_loader = MockDataLoader()
    return _mock_loader


def reset_mock_loader():
    """Mock 로더 리셋 (테스트용)"""
    global _mock_loader
    _mock_loader = None
