"""OpsExecutor - 운영(Ops) 실행기

sales, inventory, dashboard 도구를 실행합니다.
"""

from typing import Any, Dict, Optional, List
import logging

from .core import BaseExecutor
from .core.base_executor import register_executor, ExecutionResult

logger = logging.getLogger(__name__)


@register_executor("ops_executor")
class OpsExecutor(BaseExecutor):
    """운영(Operations) 실행기

    Attributes:
        supported_tools: sales, inventory, dashboard

    지원하는 작업:
    - 세일즈 전략 생성 (sales)
    - 재고 관리 (inventory)
    - 대시보드 생성 (dashboard)

    Example:
        ```python
        executor = OpsExecutor()
        result = await executor.execute(todo, context)
        ```
    """

    name: str = "ops_executor"
    category: str = "ops"
    supported_tools: List[str] = ["sales", "inventory", "dashboard"]
    version: str = "1.0.0"

    def __init__(self, enable_hitl: bool = True, **kwargs):
        """운영 실행기 초기화

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
            # 비즈니스 도구 모듈 임포트 (lazy loading)
            from ..tools import business
            self._business_module = business
            self._tools_initialized = True
            logger.info(f"[{self.name}] Business tools initialized")
        except ImportError as e:
            logger.warning(f"[{self.name}] Business tools import failed: {e}")
            self._tools_initialized = False

        self._initialized = True

    async def _execute_impl(self, todo: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """운영 도구 실행

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
        if tool_name == "sales":
            return await self._execute_sales(params)
        elif tool_name == "inventory":
            return await self._execute_inventory(params)
        elif tool_name == "dashboard":
            return await self._execute_dashboard(params)
        else:
            raise ValueError(f"Unsupported tool: {tool_name}")

    async def _execute_sales(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """세일즈 전략 실행

        Args:
            params: 세일즈 파라미터
                - product_info: 제품 정보
                - insights: 인사이트 (optional)
                - target_market: 타겟 시장 (optional)
                - goals: 목표 (optional)

        Returns:
            세일즈 전략 결과
        """
        from ..tools.business import generate_sales_plan_direct

        product_info = params.get("product_info", {})
        insights = params.get("insights", [])
        target_market = params.get("target_market", "korea")
        goals = params.get("goals", [])

        if not product_info:
            # context에서 제품 정보 추출
            product_info = {
                "name": params.get("product_name", ""),
                "category": params.get("category", ""),
                "brand": params.get("brand", ""),
            }

        result = generate_sales_plan_direct(
            product_info=product_info,
            insights=insights,
            target_market=target_market,
            goals=goals,
        )

        return {
            "tool": "sales",
            "plan_id": result.get("plan_id"),
            "strategy": result.get("strategy", {}),
            "tactics": result.get("tactics", []),
            "timeline": result.get("timeline", {}),
            "kpis": result.get("kpis", []),
            "success": result.get("success", True),
        }

    async def _execute_inventory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """재고 관리 실행

        Args:
            params: 재고 파라미터
                - action: 동작 유형 (status, check_reorder, update)
                - product_ids: 제품 ID 목록 (optional)
                - quantities: 수량 딕셔너리 (update 시)

        Returns:
            재고 관리 결과
        """
        from ..tools.business import (
            get_inventory_direct,
            check_reorder_direct,
        )

        action = params.get("action", "status")
        product_ids = params.get("product_ids", [])

        if action == "status":
            result = get_inventory_direct(product_ids=product_ids)
            return {
                "tool": "inventory",
                "action": "status",
                "inventory": result.get("inventory", []),
                "total_value": result.get("total_value", 0),
                "success": result.get("success", True),
            }

        elif action == "check_reorder":
            result = check_reorder_direct(product_ids=product_ids)
            return {
                "tool": "inventory",
                "action": "check_reorder",
                "reorder_needed": result.get("reorder_needed", []),
                "recommendations": result.get("recommendations", []),
                "success": result.get("success", True),
            }

        elif action == "update":
            # 재고 업데이트는 HITL 승인 필요할 수 있음
            quantities = params.get("quantities", {})
            if not quantities:
                return {
                    "tool": "inventory",
                    "action": "update",
                    "success": False,
                    "error": "No quantities provided for update",
                }

            # Stub: 실제 업데이트 로직 (Phase 2에서 구현)
            return {
                "tool": "inventory",
                "action": "update",
                "updated_items": list(quantities.keys()),
                "success": True,
                "message": "Inventory update scheduled (stub)",
            }

        else:
            raise ValueError(f"Unknown inventory action: {action}")

    async def _execute_dashboard(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """대시보드 생성 실행

        Args:
            params: 대시보드 파라미터
                - analysis_data: 분석 데이터
                - dashboard_type: 대시보드 유형 (optional)
                - date_range: 날짜 범위 (optional)

        Returns:
            대시보드 생성 결과
        """
        from ..tools.business import (
            generate_dashboard_direct,
            get_metrics_direct,
        )

        analysis_data = params.get("analysis_data", {})
        dashboard_type = params.get("dashboard_type", "overview")
        date_range = params.get("date_range", {})

        # context에서 분석 데이터 조합
        if not analysis_data:
            analysis_data = self._build_analysis_data_from_context(params)

        # 메트릭 먼저 가져오기
        metrics = get_metrics_direct(
            analysis_data=analysis_data,
            date_range=date_range,
        )

        # 대시보드 생성
        result = generate_dashboard_direct(
            analysis_data=analysis_data,
            metrics=metrics.get("metrics", {}),
            dashboard_type=dashboard_type,
        )

        return {
            "tool": "dashboard",
            "dashboard_id": result.get("dashboard_id"),
            "dashboard_type": dashboard_type,
            "html_content": result.get("html_content", ""),
            "output_path": result.get("output_path"),
            "metrics": metrics.get("metrics", {}),
            "charts": result.get("charts", []),
            "success": result.get("success", True),
        }

    def _build_analysis_data_from_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트에서 분석 데이터 조합

        Args:
            context: 실행 컨텍스트

        Returns:
            분석 데이터 딕셔너리
        """
        analysis_data = {}

        # 이전 실행 결과에서 데이터 추출
        if "sentiment_result" in context:
            analysis_data["sentiment"] = context["sentiment_result"]
        if "keyword_result" in context:
            analysis_data["keywords"] = context["keyword_result"]
        if "problem_result" in context:
            analysis_data["problems"] = context["problem_result"]
        if "competitor_result" in context:
            analysis_data["competitor"] = context["competitor_result"]
        if "insight_result" in context:
            analysis_data["insights"] = context["insight_result"]
        if "trends_result" in context:
            analysis_data["trends"] = context["trends_result"]

        return analysis_data

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
