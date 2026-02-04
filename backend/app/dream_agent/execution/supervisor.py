"""ExecutionSupervisor - 실행 관리 감독자

모든 Executor를 관리하고 Todo 기반 실행을 조율합니다.
Phase 1: ToolDiscovery 통합으로 YAML 기반 동적 도구 매핑 지원.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import logging
import asyncio

from .core import (
    BaseExecutor,
    ExecutorRegistry,
    get_executor_registry,
    ExecutionCache,
    get_execution_cache,
)
from .core.base_executor import ExecutionResult

# Phase 1: Tool Discovery 통합
from ..tools.discovery import get_tool_discovery

logger = logging.getLogger(__name__)


# ============================================================
# Legacy 도구 -> Executor 매핑 (하위 호환성 유지)
# Phase 1 이후: ToolDiscovery에서 layer 기반으로 동적 결정
# ============================================================
TOOL_TO_EXECUTOR: Dict[str, str] = {
    # Data Executor (ML Layer)
    "collector": "data_executor",
    "review_collector": "data_executor",  # YAML 이름
    "preprocessor": "data_executor",
    "google_trends": "data_executor",
    # Insight Executor (ML Layer)
    "sentiment": "insight_executor",
    "sentiment_analyzer": "insight_executor",  # YAML 이름
    "keyword": "insight_executor",
    "keyword_extractor": "insight_executor",
    "hashtag": "insight_executor",
    "hashtag_analyzer": "insight_executor",  # YAML 이름
    "problem": "insight_executor",
    "problem_classifier": "insight_executor",  # YAML 이름
    "competitor": "insight_executor",
    "competitor_analyzer": "insight_executor",  # YAML 이름
    "insight": "insight_executor",
    "insight_generator": "insight_executor",
    "insight_with_trends": "insight_executor",
    "analyzer": "insight_executor",
    "absa_analyzer": "insight_executor",
    # Content Executor (BIZ Layer)
    "report": "content_executor",
    "report_agent": "content_executor",
    "report_generator": "content_executor",  # YAML 이름
    "video": "content_executor",
    "video_agent": "content_executor",
    "ad_creative": "content_executor",
    "ad_creative_agent": "content_executor",
    "storyboard_agent": "content_executor",
    # Ops Executor (BIZ Layer)
    "sales": "ops_executor",
    "sales_agent": "ops_executor",
    "inventory": "ops_executor",
    "inventory_agent": "ops_executor",
    "dashboard": "ops_executor",
    "dashboard_agent": "ops_executor",
}

# Layer -> Executor 매핑 (Phase 1: YAML 기반 동적 결정용)
LAYER_TO_EXECUTOR_MAP: Dict[str, str] = {
    "ml_execution": "insight_executor",  # 기본 ML 레이어
    "biz_execution": "content_executor",  # 기본 BIZ 레이어
    "data_collection": "data_executor",
}


class ExecutionSupervisor:
    """실행 관리 감독자

    Todo 리스트를 받아 적절한 Executor로 라우팅하고
    실행 결과를 관리합니다.

    Attributes:
        enable_hitl: HITL 활성화 여부
        enable_cache: 캐싱 활성화 여부
        parallel_execution: 병렬 실행 활성화 여부

    Example:
        ```python
        supervisor = ExecutionSupervisor()

        # 단일 Todo 실행
        result = await supervisor.execute_todo(todo, context)

        # Todo 리스트 실행
        results = await supervisor.execute_todos(todos, context)
        ```
    """

    def __init__(
        self,
        enable_hitl: bool = True,
        enable_cache: bool = True,
        parallel_execution: bool = False,
    ):
        """ExecutionSupervisor 초기화

        Args:
            enable_hitl: HITL 활성화 여부
            enable_cache: 결과 캐싱 활성화 여부
            parallel_execution: 독립적인 Todo의 병렬 실행 여부

        Note:
            Mock 데이터 모드는 환경변수 USE_MOCK_DATA로 제어됩니다.
            실제 Executor가 mock_loader를 통해 data/mock 폴더에서 데이터를 로드합니다.
        """
        self.enable_hitl = enable_hitl
        self.enable_cache = enable_cache
        self.parallel_execution = parallel_execution

        self._registry = get_executor_registry()
        self._cache = get_execution_cache() if enable_cache else None
        self._execution_context: Dict[str, Any] = {}
        self._execution_history: List[Dict[str, Any]] = []

        logger.info(
            f"ExecutionSupervisor initialized "
            f"(hitl={enable_hitl}, cache={enable_cache}, parallel={parallel_execution})"
        )

    def get_executor_for_tool(self, tool_name: str) -> Optional[BaseExecutor]:
        """도구에 해당하는 Executor 반환

        Args:
            tool_name: 도구 이름

        Returns:
            Executor 인스턴스 또는 None

        Note:
            Phase 1: ToolDiscovery를 통한 동적 Executor 결정을 우선 시도하고,
            실패 시 static TOOL_TO_EXECUTOR 매핑을 사용합니다.
            Mock 데이터는 각 Executor 내부에서 mock_loader를 통해 처리됩니다.
        """
        executor_name = None

        # Phase 1: ToolDiscovery에서 layer 기반으로 Executor 결정
        discovery = get_tool_discovery()
        spec = discovery.get(tool_name)
        if spec and spec.layer:
            executor_name = LAYER_TO_EXECUTOR_MAP.get(spec.layer)
            if executor_name:
                logger.debug(f"[Phase 1] Resolved executor '{executor_name}' from ToolDiscovery layer: {spec.layer}")

        # Fallback: Legacy static 매핑
        if not executor_name:
            executor_name = TOOL_TO_EXECUTOR.get(tool_name)

        if not executor_name:
            # Registry에서 동적으로 찾기
            executor = self._registry.get_by_tool(tool_name)
            if executor:
                return executor

            logger.warning(f"No executor found for tool: {tool_name}")
            return None

        try:
            return self._registry.get(executor_name, enable_hitl=self.enable_hitl)
        except KeyError:
            logger.warning(f"Executor not registered: {executor_name}")
            return None

    def get_execution_order(self, tool_names: List[str]) -> List[str]:
        """ToolDiscovery를 통한 의존성 기반 실행 순서 결정

        Args:
            tool_names: 도구 이름 리스트

        Returns:
            정렬된 도구 이름 리스트 (의존성 순서)

        Note:
            Phase 1: YAML에 정의된 dependencies를 기반으로 위상 정렬합니다.
        """
        discovery = get_tool_discovery()
        return discovery.get_execution_order(tool_names)

    def get_tool_dependencies(self, tool_name: str) -> List[str]:
        """도구의 의존성 목록 조회

        Args:
            tool_name: 도구 이름

        Returns:
            의존하는 도구 이름 리스트
        """
        discovery = get_tool_discovery()
        return discovery.get_dependencies(tool_name)

    def get_tool_spec(self, tool_name: str) -> Optional[Any]:
        """도구의 ToolSpec 조회

        Args:
            tool_name: 도구 이름

        Returns:
            ToolSpec 인스턴스 또는 None
        """
        discovery = get_tool_discovery()
        return discovery.get(tool_name)

    async def execute_todo(
        self,
        todo: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """단일 Todo 실행

        Args:
            todo: TodoItem 인스턴스
            context: 실행 컨텍스트 (optional)

        Returns:
            ExecutionResult 인스턴스
        """
        context = context or {}
        start_time = datetime.now()

        # 도구 이름 추출
        tool_name = self._get_tool_name(todo)
        if not tool_name:
            return ExecutionResult(
                success=False,
                error=f"No tool specified in todo: {getattr(todo, 'id', None)}",
                todo_id=getattr(todo, "id", None),
            )

        # 캐시 확인
        if self.enable_cache and self._cache:
            cache_key = self._make_cache_key(todo)
            cached_result = self._cache.get(cache_key)
            if cached_result:
                logger.info(f"[Supervisor] Cache hit for todo: {getattr(todo, 'id', None)}")
                return ExecutionResult(
                    success=True,
                    data=cached_result,
                    todo_id=getattr(todo, "id", None),
                    metadata={"cached": True},
                )

        # Executor 가져오기
        executor = self.get_executor_for_tool(tool_name)
        if not executor:
            return ExecutionResult(
                success=False,
                error=f"No executor available for tool: {tool_name}",
                todo_id=getattr(todo, "id", None),
            )

        # 컨텍스트 병합 (누적 실행 결과 포함)
        merged_context = {**self._execution_context, **context}

        # 실행
        logger.info(f"[Supervisor] Executing todo: {getattr(todo, 'id', None)} with {executor.name}")
        result = await executor.execute(todo, merged_context)

        # 결과 캐싱
        if result.success and self.enable_cache and self._cache:
            cache_key = self._make_cache_key(todo)
            self._cache.set(cache_key, result.data)

        # 컨텍스트 업데이트 (다음 실행에 전달)
        if result.success and result.data:
            self._update_execution_context(tool_name, result.data)

        # 실행 이력 기록
        execution_time = (datetime.now() - start_time).total_seconds()
        self._execution_history.append({
            "todo_id": getattr(todo, "id", None),
            "tool": tool_name,
            "executor": executor.name,
            "success": result.success,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
        })

        return result

    async def execute_todos(
        self,
        todos: List[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, ExecutionResult]:
        """Todo 리스트 실행

        Args:
            todos: TodoItem 인스턴스 리스트
            context: 실행 컨텍스트 (optional)

        Returns:
            todo_id -> ExecutionResult 매핑
        """
        context = context or {}
        results: Dict[str, ExecutionResult] = {}

        if self.parallel_execution:
            # 독립적인 Todo들은 병렬 실행
            independent_todos, dependent_todos = self._partition_todos(todos)

            # 독립적인 Todo 병렬 실행
            if independent_todos:
                tasks = [
                    self.execute_todo(todo, context)
                    for todo in independent_todos
                ]
                independent_results = await asyncio.gather(*tasks, return_exceptions=True)

                for todo, result in zip(independent_todos, independent_results):
                    todo_id = getattr(todo, "id", str(todo))
                    if isinstance(result, Exception):
                        results[todo_id] = ExecutionResult(
                            success=False,
                            error=str(result),
                            todo_id=todo_id,
                        )
                    else:
                        results[todo_id] = result

            # 의존성 있는 Todo 순차 실행
            for todo in dependent_todos:
                todo_id = getattr(todo, "id", str(todo))
                results[todo_id] = await self.execute_todo(todo, context)
        else:
            # 순차 실행
            for todo in todos:
                todo_id = getattr(todo, "id", str(todo))
                results[todo_id] = await self.execute_todo(todo, context)

        return results

    async def execute_ready_todos(
        self,
        todos: List[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, ExecutionResult], List[Any]]:
        """준비된(Ready) Todo만 실행

        의존성이 해결된 Todo만 실행하고 나머지는 반환합니다.

        Args:
            todos: TodoItem 인스턴스 리스트
            context: 실행 컨텍스트 (optional)

        Returns:
            (실행 결과 딕셔너리, 남은 Todo 리스트) 튜플
        """
        ready_todos = []
        remaining_todos = []

        for todo in todos:
            if self._is_todo_ready(todo):
                ready_todos.append(todo)
            else:
                remaining_todos.append(todo)

        results = await self.execute_todos(ready_todos, context)

        return results, remaining_todos

    def _partition_todos(self, todos: List[Any]) -> Tuple[List[Any], List[Any]]:
        """Todo를 독립/의존으로 분할

        Args:
            todos: TodoItem 리스트

        Returns:
            (독립적인 Todo, 의존적인 Todo) 튜플
        """
        independent = []
        dependent = []

        for todo in todos:
            if self._has_dependencies(todo):
                dependent.append(todo)
            else:
                independent.append(todo)

        return independent, dependent

    def _has_dependencies(self, todo: Any) -> bool:
        """Todo의 의존성 여부 확인"""
        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "dependency") and metadata.dependency:
                depends_on = metadata.dependency.depends_on or []
                return len(depends_on) > 0
        return False

    def _is_todo_ready(self, todo: Any) -> bool:
        """Todo가 실행 준비 상태인지 확인

        - pending 상태
        - 의존성이 없거나 모든 의존성이 완료됨
        """
        # 상태 확인
        status = getattr(todo, "status", "pending")
        if status != "pending":
            return False

        # 의존성 확인
        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "dependency") and metadata.dependency:
                depends_on = metadata.dependency.depends_on or []
                if depends_on:
                    # 모든 의존성 Todo가 완료되었는지 확인
                    # (실제 구현에서는 Todo 리스트를 조회해야 함)
                    return False

        return True

    def _get_tool_name(self, todo: Any) -> Optional[str]:
        """Todo에서 도구 이름 추출"""
        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "execution") and metadata.execution:
                return metadata.execution.tool

        if hasattr(todo, "tool"):
            return todo.tool

        return None

    def _make_cache_key(self, todo: Any) -> str:
        """Todo의 캐시 키 생성"""
        tool_name = self._get_tool_name(todo) or "unknown"
        params = {}

        if hasattr(todo, "metadata"):
            metadata = todo.metadata
            if hasattr(metadata, "execution") and metadata.execution:
                params = metadata.execution.tool_params or {}

        return self._cache.make_key(tool_name, params) if self._cache else ""

    def _update_execution_context(self, tool_name: str, result_data: Dict[str, Any]) -> None:
        """실행 컨텍스트 업데이트

        이전 실행 결과를 다음 실행에 전달하기 위해 컨텍스트에 저장합니다.

        Args:
            tool_name: 도구 이름
            result_data: 실행 결과 데이터
        """
        context_key = f"{tool_name}_result"
        self._execution_context[context_key] = result_data

        # 특정 데이터는 공용 키로도 저장
        if "reviews" in result_data:
            self._execution_context["reviews"] = result_data["reviews"]
        if "processed_texts" in result_data:
            self._execution_context["texts"] = result_data["processed_texts"]
        if "keywords" in result_data:
            self._execution_context["keywords"] = result_data["keywords"]
        if "insights" in result_data:
            self._execution_context["insights"] = result_data["insights"]

    def get_execution_context(self) -> Dict[str, Any]:
        """현재 실행 컨텍스트 반환"""
        return self._execution_context.copy()

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """실행 이력 반환"""
        return self._execution_history.copy()

    def clear_context(self) -> None:
        """실행 컨텍스트 초기화"""
        self._execution_context.clear()
        logger.debug("Execution context cleared")

    def clear_history(self) -> None:
        """실행 이력 초기화"""
        self._execution_history.clear()
        logger.debug("Execution history cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """실행 통계 반환"""
        if not self._execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
            }

        total = len(self._execution_history)
        successes = sum(1 for h in self._execution_history if h["success"])
        total_time = sum(h["execution_time"] for h in self._execution_history)

        return {
            "total_executions": total,
            "success_count": successes,
            "failure_count": total - successes,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_execution_time": total_time / total if total > 0 else 0.0,
            "tools_used": list(set(h["tool"] for h in self._execution_history)),
            "executors_used": list(set(h["executor"] for h in self._execution_history)),
        }


# 싱글톤 인스턴스
_supervisor_instance: Optional[ExecutionSupervisor] = None


def get_execution_supervisor(
    enable_hitl: bool = True,
    enable_cache: bool = True,
    parallel_execution: bool = False,
) -> ExecutionSupervisor:
    """ExecutionSupervisor 싱글톤 인스턴스 반환

    Args:
        enable_hitl: HITL 활성화 여부
        enable_cache: 캐싱 활성화 여부
        parallel_execution: 병렬 실행 활성화 여부

    Returns:
        ExecutionSupervisor 인스턴스
    """
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = ExecutionSupervisor(
            enable_hitl=enable_hitl,
            enable_cache=enable_cache,
            parallel_execution=parallel_execution,
        )
    return _supervisor_instance
