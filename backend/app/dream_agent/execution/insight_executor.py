"""InsightExecutor - 인사이트 생성 실행기

분석 도구(sentiment, keyword, hashtag, problem, competitor) 및
인사이트 생성기(insight_generator)를 실행합니다.
"""

from typing import Any, Dict, Optional, List
import logging

from .core import BaseExecutor
from .core.base_executor import register_executor, ExecutionResult

logger = logging.getLogger(__name__)


@register_executor("insight_executor")
class InsightExecutor(BaseExecutor):
    """인사이트 생성 실행기

    Attributes:
        supported_tools: sentiment, keyword, hashtag, problem, competitor, insight

    지원하는 작업:
    - 감성 분석 (sentiment)
    - 키워드 추출 (keyword)
    - 해시태그 분석 (hashtag)
    - 문제점 분류 (problem)
    - 경쟁사 분석 (competitor)
    - 종합 인사이트 생성 (insight)

    Example:
        ```python
        executor = InsightExecutor()
        result = await executor.execute(todo, context)
        ```
    """

    name: str = "insight_executor"
    category: str = "insight"
    supported_tools: List[str] = [
        "sentiment",
        "keyword",
        "keyword_extractor",  # Alias
        "hashtag",
        "problem",
        "competitor",
        "insight",
        "insight_generator",  # Alias
        "insight_with_trends",  # K-Beauty 트렌드
        "analyzer",  # Alias (sentiment + keyword)
        "absa_analyzer",  # ABSA 감성 분석
    ]
    version: str = "1.0.0"

    def __init__(self, enable_hitl: bool = True, **kwargs):
        """인사이트 실행기 초기화

        Args:
            enable_hitl: HITL 활성화 여부
            **kwargs: 추가 설정
        """
        super().__init__(enable_hitl=enable_hitl, **kwargs)
        self._tools_initialized = False

    def initialize(self) -> None:
        """도구 임포트 및 초기화"""
        if self._initialized:
            return

        try:
            # 분석 도구 모듈 임포트 (lazy loading)
            from ..tools import analysis
            self._analysis_module = analysis
            self._tools_initialized = True
            logger.info(f"[{self.name}] Analysis tools initialized")
        except ImportError as e:
            logger.warning(f"[{self.name}] Analysis tools import failed: {e}")
            self._tools_initialized = False

        self._initialized = True

    async def _execute_impl(self, todo: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """분석/인사이트 도구 실행

        Args:
            todo: TodoItem 인스턴스
            context: 실행 컨텍스트

        Returns:
            실행 결과 딕셔너리
        """
        # 도구 이름 추출
        tool_name = self._get_tool_name(todo)
        if not tool_name:
            raise ValueError(f"No tool specified in todo: {getattr(todo, 'id', None)}")

        # 도구 파라미터 추출
        params = self._get_tool_params(todo, context)

        logger.info(f"[{self.name}] Executing tool: {tool_name} with params: {list(params.keys())}")

        # 도구별 실행 (alias 포함)
        if tool_name in ("sentiment", "absa_analyzer"):
            return await self._execute_sentiment(params)
        elif tool_name in ("keyword", "keyword_extractor"):
            return await self._execute_keyword(params)
        elif tool_name == "hashtag":
            return await self._execute_hashtag(params)
        elif tool_name == "problem":
            return await self._execute_problem(params)
        elif tool_name == "competitor":
            return await self._execute_competitor(params)
        elif tool_name in ("insight", "insight_generator", "insight_with_trends"):
            # insight_with_trends는 K-Beauty 트렌드 포함
            if tool_name == "insight_with_trends":
                params["with_trends"] = True
            return await self._execute_insight(params)
        elif tool_name == "analyzer":
            # "analyzer"는 sentiment + keyword 조합 실행
            sentiment_result = await self._execute_sentiment(params)
            keyword_result = await self._execute_keyword(params)
            return {
                "tool": "analyzer",
                "sentiment": sentiment_result,
                "keywords": keyword_result,
                "success": sentiment_result.get("success", True) and keyword_result.get("success", True),
            }
        else:
            raise ValueError(f"Unsupported tool: {tool_name}")

    async def _execute_sentiment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """감성 분석 실행

        Args:
            params: 감성 분석 파라미터
                - reviews: 분석할 리뷰 목록 (List[Dict])

        Returns:
            감성 분석 결과
        """
        from ..tools.analysis import analyze_sentiment_direct

        # reviews 파라미터 추출 (전처리된 리뷰 데이터)
        reviews = params.get("reviews", [])

        if not reviews:
            return {
                "tool": "sentiment",
                "result": {},
                "success": True,
                "message": "No reviews to analyze",
            }

        result = analyze_sentiment_direct(reviews=reviews)

        return {
            "tool": "sentiment",
            "positive_reviews": result.get("positive_reviews", []),
            "negative_reviews": result.get("negative_reviews", []),
            "stats": result.get("stats", {}),
            "success": True,
        }

    async def _execute_keyword(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """키워드 추출 실행

        Args:
            params: 키워드 추출 파라미터
                - reviews: 분석할 리뷰 목록 (List[Dict])
                - top_n: 상위 키워드 개수 (optional)

        Returns:
            키워드 추출 결과
        """
        from ..tools.analysis import extract_keywords_direct

        # reviews 파라미터 추출 (전처리된 리뷰 데이터)
        reviews = params.get("reviews", [])

        if not reviews:
            return {
                "tool": "keyword",
                "keywords": [],
                "success": True,
                "message": "No reviews to analyze",
            }

        top_n = params.get("top_n", 20)
        result = extract_keywords_direct(reviews=reviews, top_n=top_n)

        return {
            "tool": "keyword",
            "keywords": result.get("keywords", []),
            "bigrams": result.get("bigrams", []),
            "success": True,
        }

    async def _execute_hashtag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """해시태그 분석 실행

        Args:
            params: 해시태그 분석 파라미터
                - reviews: 분석할 리뷰 목록 (List[Dict])
                - top_n: 상위 해시태그 개수 (optional)

        Returns:
            해시태그 분석 결과
        """
        from ..tools.analysis import extract_hashtags_direct

        # reviews 파라미터 추출 (전처리된 리뷰 데이터)
        reviews = params.get("reviews", [])

        if not reviews:
            return {
                "tool": "hashtag",
                "hashtags": [],
                "success": True,
                "message": "No reviews to analyze",
            }

        top_n = params.get("top_n", 20)
        result = extract_hashtags_direct(reviews=reviews, top_n=top_n)

        return {
            "tool": "hashtag",
            "hashtags": result.get("hashtags", []),
            "trending": result.get("trending", []),
            "success": True,
        }

    async def _execute_problem(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """문제점 분류 실행

        Args:
            params: 문제점 분류 파라미터
                - negative_reviews: 부정 리뷰 목록 (List[Dict])
                - reviews: 리뷰 목록 (negative_reviews가 없을 때 사용)

        Returns:
            문제점 분류 결과
        """
        from ..tools.analysis import classify_problems_direct

        # negative_reviews 우선, 없으면 reviews에서 부정 리뷰 필터링
        negative_reviews = params.get("negative_reviews", [])

        if not negative_reviews:
            # sentiment 분석 결과에서 negative_reviews 추출
            sentiment_result = params.get("sentiment_result", {})
            negative_reviews = sentiment_result.get("negative_reviews", [])

        if not negative_reviews:
            return {
                "tool": "problem",
                "problems": [],
                "success": True,
                "message": "No negative reviews to analyze",
            }

        result = classify_problems_direct(negative_reviews=negative_reviews)

        return {
            "tool": "problem",
            "problems": result.get("problems", []),
            "summary": result.get("summary", {}),
            "success": True,
        }

    async def _execute_competitor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """경쟁사 분석 실행

        Args:
            params: 경쟁사 분석 파라미터
                - brand_reviews: 브랜드별 리뷰 딕셔너리 (Dict[str, List[Dict]])
                - metrics: 비교 메트릭 목록 (optional)

        Returns:
            경쟁사 분석 결과
        """
        from ..tools.analysis import compare_brands_direct

        # brand_reviews: {brand_name: [review_dicts]}
        brand_reviews = params.get("brand_reviews", {})

        if not brand_reviews:
            return {
                "tool": "competitor",
                "comparison": {},
                "success": True,
                "message": "No brand reviews provided",
            }

        metrics = params.get("metrics", None)
        result = compare_brands_direct(brand_reviews=brand_reviews, metrics=metrics)

        return {
            "tool": "competitor",
            "comparison": result.get("comparison", {}),
            "ranking": result.get("ranking", []),
            "success": True,
        }

    async def _execute_insight(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """종합 인사이트 생성 실행

        Args:
            params: 인사이트 생성 파라미터
                - ml_result: ML 분석 결과 딕셔너리
                - brand: 타겟 브랜드 (optional)
                - with_trends: K-Beauty 트렌드 포함 여부 (optional)

        Returns:
            인사이트 리포트
        """
        from .insight_agents.insight_generator.insight_generator_agent import (
            generate_insights_direct,
            generate_insights_with_trends_direct,
        )

        ml_result = params.get("ml_result", {})
        brand = params.get("brand", "Amorepacific")
        with_trends = params.get("with_trends", False)

        if not ml_result:
            # context에서 이전 분석 결과 조합
            ml_result = self._build_ml_result_from_context(params)

        if not ml_result:
            return {
                "tool": "insight",
                "insights": [],
                "success": True,
                "message": "No ML results to generate insights from",
            }

        try:
            if with_trends:
                result = generate_insights_with_trends_direct(
                    ml_result=ml_result,
                    brand=brand,
                )
            else:
                result = generate_insights_direct(ml_result=ml_result)

            return {
                "tool": "insight",
                "report_id": result.get("report_id"),
                "insights": result.get("insights", []),
                "summary": result.get("summary", ""),
                "key_metrics": result.get("key_metrics", {}),
                "trend_context": result.get("trend_context"),
                "kbeauty_insights": result.get("kbeauty_insights"),
                "success": True,
            }
        except Exception as e:
            logger.error(f"[{self.name}] Insight generation failed: {e}")
            return {
                "tool": "insight",
                "insights": [],
                "success": False,
                "error": str(e),
            }

    def _build_ml_result_from_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트에서 ML 결과 조합

        Args:
            context: 실행 컨텍스트

        Returns:
            ML 결과 딕셔너리
        """
        ml_result = {}

        # 이전 실행 결과에서 데이터 추출
        if "sentiment_result" in context:
            ml_result["absa_analyzer"] = context["sentiment_result"]
        if "keyword_result" in context:
            ml_result["extractor"] = context["keyword_result"]
        if "problem_result" in context:
            ml_result["problem_classifier"] = context["problem_result"]
        if "trends_result" in context:
            ml_result["google_trends"] = context["trends_result"]

        return ml_result

    def _get_tool_name(self, todo: Any) -> Optional[str]:
        """Todo에서 도구 이름 추출

        Args:
            todo: TodoItem 인스턴스

        Returns:
            도구 이름 또는 None
        """
        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "execution") and metadata.execution:
                return metadata.execution.tool

        if hasattr(todo, "tool"):
            return todo.tool

        return None

    def _get_tool_params(self, todo: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Todo에서 도구 파라미터 추출

        Args:
            todo: TodoItem 인스턴스
            context: 실행 컨텍스트

        Returns:
            파라미터 딕셔너리
        """
        params = {}

        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "execution") and metadata.execution:
                tool_params = metadata.execution.tool_params or {}
                params.update(tool_params)

            if hasattr(metadata, "data") and metadata.data:
                input_data = metadata.data.input_data or {}
                params.update(input_data)

        params.update(context)

        return params
