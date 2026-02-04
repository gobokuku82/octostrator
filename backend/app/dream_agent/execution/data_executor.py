"""DataExecutor - 데이터 수집/처리 실행기

collector, preprocessor, google_trends 도구를 실행합니다.
"""

from typing import Any, Dict, Optional, List
import logging

from .core import BaseExecutor
from .core.base_executor import register_executor, ExecutionResult

logger = logging.getLogger(__name__)


@register_executor("data_executor")
class DataExecutor(BaseExecutor):
    """데이터 수집 및 처리 실행기

    Attributes:
        supported_tools: collector, preprocessor, google_trends

    지원하는 작업:
    - 멀티 플랫폼 리뷰/댓글 수집 (collector)
    - 텍스트 전처리 (preprocessor)
    - Google Trends 분석 (google_trends)

    Example:
        ```python
        executor = DataExecutor()
        result = await executor.execute(todo, context)
        ```
    """

    name: str = "data_executor"
    category: str = "data"
    supported_tools: List[str] = ["collector", "preprocessor", "google_trends"]
    version: str = "1.0.0"

    def __init__(self, enable_hitl: bool = True, **kwargs):
        """데이터 실행기 초기화

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
            # 도구 모듈 임포트 (lazy loading)
            from ..tools import data
            self._data_module = data
            self._tools_initialized = True
            logger.info(f"[{self.name}] Data tools initialized")
        except ImportError as e:
            logger.warning(f"[{self.name}] Data tools import failed: {e}")
            self._tools_initialized = False

        self._initialized = True

    async def _execute_impl(self, todo: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 도구 실행

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

        # 도구별 실행
        if tool_name == "collector":
            return await self._execute_collector(params)
        elif tool_name == "preprocessor":
            return await self._execute_preprocessor(params)
        elif tool_name == "google_trends":
            return await self._execute_google_trends(params)
        else:
            raise ValueError(f"Unsupported tool: {tool_name}")

    async def _execute_collector(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """리뷰 수집 실행

        Args:
            params: 수집 파라미터
                - keyword: 검색 키워드
                - platforms: 수집 플랫폼 목록 (optional)
                - limit: 수집 개수 제한 (optional)

        Returns:
            수집 결과
        """
        from ..tools.data import collect_reviews_direct

        keyword = params.get("keyword")
        if not keyword:
            raise ValueError("collector requires 'keyword' parameter")

        platforms = params.get("platforms")
        limit = params.get("limit", 100)

        # Direct 함수 호출 (동기 함수)
        result = collect_reviews_direct(
            keyword=keyword,
            platforms=platforms,
            limit=limit,
        )

        return {
            "tool": "collector",
            "keyword": keyword,
            "platforms": platforms,
            "reviews": result.get("reviews", []),
            "total_count": result.get("total_count", 0),
            "success": result.get("success", True),
        }

    async def _execute_preprocessor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 전처리 실행

        Args:
            params: 전처리 파라미터
                - texts: 텍스트 목록
                - options: 전처리 옵션 (optional)

        Returns:
            전처리 결과
        """
        from ..tools.data import preprocess_reviews_direct

        texts = params.get("texts", [])
        if not texts:
            # context에서 이전 수집 결과 가져오기
            reviews = params.get("reviews", [])
            if reviews:
                texts = [r.get("content", "") for r in reviews if r.get("content")]

        if not texts:
            return {
                "tool": "preprocessor",
                "processed_texts": [],
                "count": 0,
                "success": True,
                "message": "No texts to preprocess",
            }

        options = params.get("options", {})

        # Direct 함수 호출
        result = preprocess_reviews_direct(texts=texts, **options)

        return {
            "tool": "preprocessor",
            "processed_texts": result.get("processed_texts", []),
            "count": len(result.get("processed_texts", [])),
            "success": result.get("success", True),
        }

    async def _execute_google_trends(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Google Trends 분석 실행

        Args:
            params: Trends 파라미터
                - keywords: 분석할 키워드 목록
                - timeframe: 기간 (optional, default: "today 3-m")
                - geo: 지역 (optional, default: "KR")

        Returns:
            Trends 분석 결과
        """
        from ..tools.data import analyze_trends_direct

        keywords = params.get("keywords", [])
        if not keywords:
            keyword = params.get("keyword")
            if keyword:
                keywords = [keyword]
            else:
                raise ValueError("google_trends requires 'keywords' or 'keyword' parameter")

        timeframe = params.get("timeframe", "today 3-m")
        geo = params.get("geo", "KR")

        # Direct 함수 호출
        result = analyze_trends_direct(
            keywords=keywords,
            timeframe=timeframe,
            geo=geo,
        )

        return {
            "tool": "google_trends",
            "keywords": keywords,
            "timeframe": timeframe,
            "geo": geo,
            "trends_data": result.get("trends_data", {}),
            "success": result.get("success", True),
        }

    def _get_tool_name(self, todo: Any) -> Optional[str]:
        """Todo에서 도구 이름 추출

        Args:
            todo: TodoItem 인스턴스

        Returns:
            도구 이름 또는 None
        """
        # TodoItem.metadata.execution.tool 확인
        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "execution") and metadata.execution:
                return metadata.execution.tool

        # 직접 속성 확인 (fallback)
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

        # TodoItem.metadata.execution.tool_params 확인
        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "execution") and metadata.execution:
                tool_params = metadata.execution.tool_params or {}
                params.update(tool_params)

            # TodoItem.metadata.data.input_data 확인
            if hasattr(metadata, "data") and metadata.data:
                input_data = metadata.data.input_data or {}
                params.update(input_data)

        # context 데이터 병합
        params.update(context)

        return params
