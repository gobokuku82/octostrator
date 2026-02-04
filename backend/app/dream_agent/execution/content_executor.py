"""ContentExecutor - 콘텐츠 생성 실행기

report, video, ad_creative 도구를 실행합니다.
"""

from typing import Any, Dict, Optional, List
import logging

from .core import BaseExecutor
from .core.base_executor import register_executor, ExecutionResult

logger = logging.getLogger(__name__)


@register_executor("content_executor")
class ContentExecutor(BaseExecutor):
    """콘텐츠 생성 실행기

    Attributes:
        supported_tools: report, video, ad_creative

    지원하는 작업:
    - 분석 리포트 생성 (report)
    - 비디오 콘텐츠 생성 (video)
    - 광고 크리에이티브 생성 (ad_creative)

    Example:
        ```python
        executor = ContentExecutor()
        result = await executor.execute(todo, context)
        ```
    """

    name: str = "content_executor"
    category: str = "content"
    supported_tools: List[str] = [
        "report",
        "report_agent",  # Alias
        "video",
        "video_agent",  # Alias
        "storyboard_agent",  # Alias
        "ad_creative",
        "ad_creative_agent",  # Alias
    ]
    version: str = "1.0.0"

    def __init__(self, enable_hitl: bool = True, **kwargs):
        """콘텐츠 실행기 초기화

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
            # 콘텐츠 도구 모듈 임포트 (lazy loading)
            from ..tools import content
            self._content_module = content
            self._tools_initialized = True
            logger.info(f"[{self.name}] Content tools initialized")
        except ImportError as e:
            logger.warning(f"[{self.name}] Content tools import failed: {e}")
            self._tools_initialized = False

        self._initialized = True

    async def _execute_impl(self, todo: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """콘텐츠 도구 실행

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
        if tool_name in ("report", "report_agent"):
            return await self._execute_report(params)
        elif tool_name in ("video", "video_agent", "storyboard_agent"):
            return await self._execute_video(params)
        elif tool_name in ("ad_creative", "ad_creative_agent"):
            return await self._execute_ad_creative(params)
        else:
            raise ValueError(f"Unsupported tool: {tool_name}")

    async def _execute_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """리포트 생성 실행

        Args:
            params: 리포트 생성 파라미터
                - analysis_result: 분석 결과
                - report_type: 리포트 유형 (optional)
                - format: 출력 형식 (optional)

        Returns:
            리포트 생성 결과
        """
        from ..tools.content import generate_report_direct

        analysis_result = params.get("analysis_result", {})
        report_type = params.get("report_type", "summary")
        output_format = params.get("format", "markdown")

        # context에서 분석 결과 조합
        if not analysis_result:
            analysis_result = self._build_analysis_result_from_context(params)

        result = generate_report_direct(
            analysis_result=analysis_result,
            report_type=report_type,
            format=output_format,
        )

        return {
            "tool": "report",
            "report_id": result.get("report_id"),
            "report_type": report_type,
            "content": result.get("content", ""),
            "format": output_format,
            "success": result.get("success", True),
        }

    async def _execute_video(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """비디오 생성 실행

        Args:
            params: 비디오 생성 파라미터
                - storyboard: 스토리보드 데이터
                - scenes: 씬 목록
                - style: 비디오 스타일 (optional)

        Returns:
            비디오 생성 결과
        """
        from ..tools.content import (
            validate_storyboard_direct,
            generate_workflow_direct,
            generate_video_direct,
            call_comfyui_api_async,
        )

        storyboard = params.get("storyboard", {})
        scenes = params.get("scenes", [])
        style = params.get("style", "realistic")

        # 스토리보드 유효성 검사
        if storyboard:
            validation = validate_storyboard_direct(storyboard=storyboard)
            if not validation.get("valid", False):
                return {
                    "tool": "video",
                    "success": False,
                    "error": f"Invalid storyboard: {validation.get('errors', [])}",
                }

        # 비디오 생성
        try:
            result = generate_video_direct(
                storyboard=storyboard,
                scenes=scenes,
                style=style,
            )

            return {
                "tool": "video",
                "video_id": result.get("video_id"),
                "scenes": result.get("scenes", []),
                "workflow": result.get("workflow", {}),
                "output_path": result.get("output_path"),
                "success": result.get("success", True),
            }
        except Exception as e:
            logger.error(f"[{self.name}] Video generation failed: {e}")
            return {
                "tool": "video",
                "success": False,
                "error": str(e),
            }

    async def _execute_ad_creative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """광고 크리에이티브 생성 실행

        Args:
            params: 광고 크리에이티브 생성 파라미터
                - product_info: 제품 정보
                - target_audience: 타겟 오디언스 (optional)
                - platform: 광고 플랫폼 (optional)
                - style: 크리에이티브 스타일 (optional)

        Returns:
            광고 크리에이티브 생성 결과
        """
        from ..tools.content import generate_ad_creative_direct

        product_info = params.get("product_info", {})
        target_audience = params.get("target_audience", "general")
        platform = params.get("platform", "instagram")
        style = params.get("style", "modern")

        if not product_info:
            # context에서 제품 정보 추출
            product_info = {
                "name": params.get("product_name", ""),
                "category": params.get("category", ""),
                "keywords": params.get("keywords", []),
                "insights": params.get("insights", []),
            }

        result = generate_ad_creative_direct(
            product_info=product_info,
            target_audience=target_audience,
            platform=platform,
            style=style,
        )

        return {
            "tool": "ad_creative",
            "creative_id": result.get("creative_id"),
            "headlines": result.get("headlines", []),
            "body_copy": result.get("body_copy", []),
            "call_to_action": result.get("call_to_action", ""),
            "visual_suggestions": result.get("visual_suggestions", []),
            "platform": platform,
            "success": result.get("success", True),
        }

    def _build_analysis_result_from_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트에서 분석 결과 조합

        Args:
            context: 실행 컨텍스트

        Returns:
            분석 결과 딕셔너리
        """
        analysis_result = {}

        # 이전 실행 결과에서 데이터 추출
        if "sentiment_result" in context:
            analysis_result["sentiment"] = context["sentiment_result"]
        if "keyword_result" in context:
            analysis_result["keywords"] = context["keyword_result"]
        if "problem_result" in context:
            analysis_result["problems"] = context["problem_result"]
        if "competitor_result" in context:
            analysis_result["competitor"] = context["competitor_result"]
        if "insight_result" in context:
            analysis_result["insights"] = context["insight_result"]

        return analysis_result

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
