"""Intent to Todo Mapper - Intent에서 Todo 생성

사용자 의도를 기반으로 적절한 Todo 아이템을 생성합니다.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from backend.app.dream_agent.cognitive.intent_types import (
    IntentResult,
    PrimaryIntent,
    SubIntent,
    get_tools_for_intent
)
from backend.app.dream_agent.models.todo import (
    TodoItem,
    TodoMetadata,
    TodoExecutionConfig,
    TodoDataConfig,
    TodoDependencyConfig,
    TodoApproval,
)
from backend.app.dream_agent.workflow_manager.todo_manager import create_todo
from backend.app.dream_agent.planning.tool_catalog import (
    get_catalog,
    ToolCatalogLoader,
    ToolMetadata
)


# ============================================================
# Intent to Todo Mapping Configuration
# ============================================================

class IntentMappingConfig:
    """Intent 매핑 설정"""

    # SubIntent별 기본 Todo 템플릿
    TEMPLATES: Dict[SubIntent, Dict[str, Any]] = {
        # ANALYSIS 관련
        SubIntent.CHANNEL_ANALYSIS: {
            "task_prefix": "채널 분석",
            "ml_pipeline": ["collector", "preprocessor", "analyzer"],
            "biz_pipeline": ["report_agent"],
            "default_params": {
                "analysis_type": "comprehensive"
            }
        },
        SubIntent.MARKET_ANALYSIS: {
            "task_prefix": "시장 분석",
            "ml_pipeline": ["collector", "preprocessor", "analyzer", "insight"],
            "biz_pipeline": ["report_agent", "dashboard_agent"],
            "default_params": {
                "analysis_type": "trend"
            }
        },
        SubIntent.COMPETITOR_ANALYSIS: {
            "task_prefix": "경쟁사 분석",
            "ml_pipeline": ["collector", "preprocessor", "analyzer"],
            "biz_pipeline": ["report_agent"],
            "default_params": {
                "analysis_type": "comparison"
            }
        },
        SubIntent.TREND_ANALYSIS: {
            "task_prefix": "트렌드 분석",
            "ml_pipeline": ["collector", "preprocessor", "analyzer", "insight"],
            "biz_pipeline": ["report_agent", "dashboard_agent"],
            "default_params": {}
        },
        SubIntent.SALES_ANALYSIS: {
            "task_prefix": "매출 분석",
            "ml_pipeline": ["collector", "preprocessor", "analyzer"],
            "biz_pipeline": ["report_agent", "dashboard_agent"],
            "default_params": {}
        },
        SubIntent.CUSTOMER_ANALYSIS: {
            "task_prefix": "고객 분석",
            "ml_pipeline": ["collector", "preprocessor", "analyzer", "insight"],
            "biz_pipeline": ["report_agent"],
            "default_params": {
                "analysis_type": "sentiment"
            }
        },
        SubIntent.PRODUCT_ANALYSIS: {
            "task_prefix": "제품 분석",
            "ml_pipeline": ["collector", "preprocessor", "analyzer"],
            "biz_pipeline": ["report_agent"],
            "default_params": {}
        },

        # CREATE 관련
        SubIntent.CREATE_REPORT: {
            "task_prefix": "리포트 생성",
            "ml_pipeline": [],
            "biz_pipeline": ["report_agent"],
            "default_params": {
                "format": "markdown"
            }
        },
        SubIntent.CREATE_DASHBOARD: {
            "task_prefix": "대시보드 생성",
            "ml_pipeline": [],
            "biz_pipeline": ["dashboard_agent"],
            "default_params": {
                "layout": "standard"
            }
        },
        SubIntent.CREATE_STORYBOARD: {
            "task_prefix": "스토리보드 생성",
            "ml_pipeline": [],
            "biz_pipeline": ["storyboard_agent"],
            "default_params": {
                "content_type": "instagram"
            }
        },
        SubIntent.CREATE_VIDEO: {
            "task_prefix": "비디오 생성",
            "ml_pipeline": [],
            "biz_pipeline": ["storyboard_agent", "video_agent"],
            "default_params": {
                "resolution": "1080p"
            }
        },
        SubIntent.CREATE_AD_CREATIVE: {
            "task_prefix": "광고 크리에이티브 생성",
            "ml_pipeline": [],
            "biz_pipeline": ["ad_creative_agent"],
            "default_params": {
                "platform": "instagram",
                "tone": "professional"
            }
        },
        SubIntent.CREATE_PRESENTATION: {
            "task_prefix": "프레젠테이션 생성",
            "ml_pipeline": [],
            "biz_pipeline": ["report_agent"],
            "default_params": {
                "format": "pptx"
            }
        },

        # COMPARE 관련
        SubIntent.COMPARE_BRANDS: {
            "task_prefix": "브랜드 비교",
            "ml_pipeline": ["collector", "preprocessor", "analyzer"],
            "biz_pipeline": ["report_agent", "dashboard_agent"],
            "default_params": {
                "analysis_type": "comparison"
            }
        },
        SubIntent.COMPARE_CHANNELS: {
            "task_prefix": "채널 비교",
            "ml_pipeline": ["collector", "preprocessor", "analyzer"],
            "biz_pipeline": ["report_agent", "dashboard_agent"],
            "default_params": {}
        },
        SubIntent.COMPARE_PERIODS: {
            "task_prefix": "기간 비교",
            "ml_pipeline": ["collector", "preprocessor", "analyzer"],
            "biz_pipeline": ["report_agent", "dashboard_agent"],
            "default_params": {}
        },
        SubIntent.COMPARE_MARKETS: {
            "task_prefix": "시장 비교",
            "ml_pipeline": ["collector", "preprocessor", "analyzer"],
            "biz_pipeline": ["report_agent", "dashboard_agent"],
            "default_params": {}
        },

        # RECOMMEND 관련
        SubIntent.RECOMMEND_STRATEGY: {
            "task_prefix": "전략 추천",
            "ml_pipeline": ["analyzer", "insight"],
            "biz_pipeline": ["report_agent"],
            "default_params": {}
        },
        SubIntent.RECOMMEND_CHANNEL: {
            "task_prefix": "채널 추천",
            "ml_pipeline": ["analyzer", "insight"],
            "biz_pipeline": ["report_agent"],
            "default_params": {}
        },
        SubIntent.RECOMMEND_PRODUCT: {
            "task_prefix": "제품 추천",
            "ml_pipeline": ["analyzer", "insight"],
            "biz_pipeline": ["report_agent"],
            "default_params": {}
        },
        SubIntent.RECOMMEND_CONTENT: {
            "task_prefix": "콘텐츠 추천",
            "ml_pipeline": ["analyzer", "insight"],
            "biz_pipeline": ["storyboard_agent", "ad_creative_agent"],
            "default_params": {}
        },
    }


# ============================================================
# Intent to Todo Mapper
# ============================================================

class IntentToTodoMapper:
    """
    Intent에서 Todo 아이템 생성

    IntentResult를 분석하여 적절한 TodoItem 리스트를 생성합니다.
    """

    def __init__(self, catalog: Optional[ToolCatalogLoader] = None):
        self.catalog = catalog or get_catalog()
        self.config = IntentMappingConfig()

    def map_intent_to_todos(
        self,
        intent: IntentResult,
        context: Optional[Dict[str, Any]] = None
    ) -> List[TodoItem]:
        """
        Intent를 TodoItem 리스트로 변환

        Args:
            intent: IntentResult
            context: 추가 컨텍스트 (브랜드, 채널, 기간 등)

        Returns:
            List[TodoItem]: 생성된 Todo 리스트
        """
        context = context or {}

        # CHAT 의도는 Todo 없이 직접 응답
        if intent.primary_intent == PrimaryIntent.CHAT:
            return self._create_chat_todos(intent, context)

        # SubIntent가 없으면 기본 Todo 생성
        if not intent.sub_intent:
            return self._create_default_todos(intent, context)

        # SubIntent 기반 Todo 생성
        return self._create_todos_from_template(intent, context)

    def _create_todos_from_template(
        self,
        intent: IntentResult,
        context: Dict[str, Any]
    ) -> List[TodoItem]:
        """템플릿 기반 Todo 생성"""
        template = self.config.TEMPLATES.get(intent.sub_intent)
        if not template:
            return self._create_default_todos(intent, context)

        todos: List[TodoItem] = []
        parent_id = str(uuid.uuid4())  # 최상위 Todo ID
        previous_todo_id: Optional[str] = None

        # 엔티티에서 컨텍스트 추출
        entity_context = self._extract_entity_context(intent)
        merged_context = {**context, **entity_context}

        # ML Pipeline Todo 생성
        for tool_name in template.get("ml_pipeline", []):
            tool_meta = self.catalog.get_tool(tool_name)
            if not tool_meta:
                continue

            todo = self._create_tool_todo(
                tool_meta=tool_meta,
                intent=intent,
                context=merged_context,
                parent_id=parent_id,
                depends_on=[previous_todo_id] if previous_todo_id else [],
                layer="ml_execution",
                default_params=template.get("default_params", {})
            )
            todos.append(todo)
            previous_todo_id = todo.id

        # Biz Pipeline Todo 생성
        for tool_name in template.get("biz_pipeline", []):
            tool_meta = self.catalog.get_tool(tool_name)
            if not tool_meta:
                continue

            todo = self._create_tool_todo(
                tool_meta=tool_meta,
                intent=intent,
                context=merged_context,
                parent_id=parent_id,
                depends_on=[previous_todo_id] if previous_todo_id else [],
                layer="biz_execution",
                default_params=template.get("default_params", {})
            )
            todos.append(todo)
            previous_todo_id = todo.id

        # 응답 Todo 추가
        response_todo = self._create_response_todo(intent, context, parent_id, previous_todo_id)
        todos.append(response_todo)

        return todos

    def _create_tool_todo(
        self,
        tool_meta: ToolMetadata,
        intent: IntentResult,
        context: Dict[str, Any],
        parent_id: str,
        depends_on: List[str],
        layer: str,
        default_params: Dict[str, Any]
    ) -> TodoItem:
        """도구 Todo 생성"""
        # 파라미터 병합
        tool_params = {**default_params}

        # 컨텍스트에서 파라미터 추출
        for param in tool_meta.parameters:
            if param.name in context:
                tool_params[param.name] = context[param.name]

        # 메타데이터 생성
        metadata = TodoMetadata(
            execution=TodoExecutionConfig(
                tool=tool_meta.name,
                tool_params=tool_params,
                timeout=tool_meta.estimated_duration_sec * 2,
                max_retries=tool_meta.max_retries
            ),
            dependency=TodoDependencyConfig(
                depends_on=depends_on
            ),
            approval=TodoApproval(
                requires_approval=tool_meta.requires_approval
            ),
            context={
                "intent_id": id(intent),
                "sub_intent": intent.sub_intent.value if intent.sub_intent else None,
                "original_query": intent.original_query
            }
        )

        return TodoItem(
            task=f"{tool_meta.display_name} 실행",
            task_type=f"{layer}_{tool_meta.name}",
            layer=layer,
            priority=self._calculate_priority(tool_meta, intent),
            parent_id=parent_id,
            metadata=metadata
        )

    def _create_response_todo(
        self,
        intent: IntentResult,
        context: Dict[str, Any],
        parent_id: str,
        depends_on: Optional[str]
    ) -> TodoItem:
        """응답 Todo 생성"""
        metadata = TodoMetadata(
            dependency=TodoDependencyConfig(
                depends_on=[depends_on] if depends_on else []
            ),
            context={
                "language": intent.detected_language,
                "original_query": intent.original_query
            }
        )

        return TodoItem(
            task="결과 응답 생성",
            task_type="response",
            layer="response",
            priority=1,  # 가장 낮은 우선순위 (마지막 실행)
            parent_id=parent_id,
            metadata=metadata
        )

    def _create_chat_todos(
        self,
        intent: IntentResult,
        context: Dict[str, Any]
    ) -> List[TodoItem]:
        """CHAT 의도용 Todo 생성"""
        metadata = TodoMetadata(
            context={
                "chat_type": intent.sub_intent.value if intent.sub_intent else "general",
                "language": intent.detected_language,
                "original_query": intent.original_query
            }
        )

        return [TodoItem(
            task="대화 응답 생성",
            task_type="chat_response",
            layer="response",
            priority=10,
            metadata=metadata
        )]

    def _create_default_todos(
        self,
        intent: IntentResult,
        context: Dict[str, Any]
    ) -> List[TodoItem]:
        """기본 Todo 생성 (템플릿 없는 경우)"""
        todos: List[TodoItem] = []
        parent_id = str(uuid.uuid4())

        # 기본 분석 파이프라인
        tools = ["collector", "preprocessor", "analyzer", "report_agent"]
        previous_todo_id: Optional[str] = None

        for tool_name in tools:
            tool_meta = self.catalog.get_tool(tool_name)
            if not tool_meta:
                continue

            layer = "ml_execution" if tool_meta.category.value == "ml" else "biz_execution"
            todo = self._create_tool_todo(
                tool_meta=tool_meta,
                intent=intent,
                context=context,
                parent_id=parent_id,
                depends_on=[previous_todo_id] if previous_todo_id else [],
                layer=layer,
                default_params={}
            )
            todos.append(todo)
            previous_todo_id = todo.id

        # 응답 Todo
        response_todo = self._create_response_todo(intent, context, parent_id, previous_todo_id)
        todos.append(response_todo)

        return todos

    def _extract_entity_context(self, intent: IntentResult) -> Dict[str, Any]:
        """엔티티에서 컨텍스트 추출"""
        context = {}

        for entity in intent.entities:
            # 엔티티 타입별 처리
            if entity.entity_type == "brand":
                context["brand"] = entity.normalized_value or entity.value
            elif entity.entity_type == "channel":
                context["source"] = entity.normalized_value or entity.value
            elif entity.entity_type == "market":
                context["market"] = entity.normalized_value or entity.value
            elif entity.entity_type == "period":
                context["date_range"] = entity.value
            elif entity.entity_type == "format":
                context["format"] = entity.normalized_value or entity.value
            elif entity.entity_type == "platform":
                context["platform"] = entity.normalized_value or entity.value

        return context

    def _calculate_priority(self, tool_meta: ToolMetadata, intent: IntentResult) -> int:
        """도구 우선순위 계산"""
        # 기본 우선순위 (높을수록 먼저 실행)
        phase_priorities = {
            "collection": 10,
            "preprocessing": 8,
            "analysis": 6,
            "insight": 4,
            "output": 2
        }

        base_priority = phase_priorities.get(tool_meta.phase.value, 5)

        # 신뢰도 높은 의도는 우선순위 상향
        if intent.confidence >= 0.8:
            base_priority += 1

        return min(base_priority, 10)

    def get_required_approvals(self, todos: List[TodoItem]) -> List[TodoItem]:
        """승인이 필요한 Todo 목록 반환"""
        return [
            todo for todo in todos
            if todo.metadata.approval.requires_approval
        ]

    def get_async_todos(self, todos: List[TodoItem]) -> List[TodoItem]:
        """비동기 실행 Todo 목록 반환"""
        async_tools = {tool.name for tool in self.catalog.get_async_tools()}
        return [
            todo for todo in todos
            if todo.metadata.execution.tool in async_tools
        ]

    def estimate_total_duration(self, todos: List[TodoItem]) -> int:
        """전체 예상 실행 시간 (초)"""
        total = 0
        for todo in todos:
            tool_name = todo.metadata.execution.tool
            if tool_name:
                tool_meta = self.catalog.get_tool(tool_name)
                if tool_meta:
                    total += tool_meta.estimated_duration_sec
        return total

    def estimate_total_cost(self, todos: List[TodoItem]) -> float:
        """전체 예상 비용 (USD)"""
        total = 0.0
        for todo in todos:
            tool_name = todo.metadata.execution.tool
            if tool_name:
                tool_meta = self.catalog.get_tool(tool_name)
                if tool_meta and tool_meta.has_cost:
                    total += tool_meta.cost_per_call
        return total


# ============================================================
# Global Instance
# ============================================================

_mapper: Optional[IntentToTodoMapper] = None


def get_mapper() -> IntentToTodoMapper:
    """전역 Mapper 인스턴스 반환"""
    global _mapper
    if _mapper is None:
        _mapper = IntentToTodoMapper()
    return _mapper
