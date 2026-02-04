"""Report Agent Graph - 분석 리포트 생성 Subgraph

ML 분석 결과를 기반으로 비즈니스 리포트를 생성합니다.
HTML, PDF, Markdown 등 다양한 형식으로 출력 가능합니다.

Mock 모드 지원:
- Mock 모드: Mock ML 결과 데이터 사용
- Real 모드: 실제 ML 분석 결과 사용
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from backend.app.dream_agent.biz_execution.base_agent_graph import BaseBizAgentGraph
from backend.app.dream_agent.biz_execution.agent_registry import register_biz_agent
from backend.app.dream_agent.biz_execution.agents.report.nodes import (
    ml_result_validator_node,
    insight_extractor_node,
    report_structure_builder_node,
    report_renderer_node,
    error_handler_node
)
from backend.app.dream_agent.biz_execution.agents.report.report_tools import (
    validate_ml_result,
    extract_key_insights,
    generate_report_structure,
    render_report
)


# ============================================================
# State Definition
# ============================================================

class ReportAgentState(TypedDict, total=False):
    """Report Agent 상태"""
    # 입력
    ml_result: Dict[str, Any]
    report_type: str  # comprehensive/summary/executive
    output_format: str  # html/json/markdown

    # 중간 결과
    validation_result: Dict[str, Any]
    insights: List[Dict[str, Any]]
    report_structure: Dict[str, Any]

    # 출력
    output_path: str
    final_result: Dict[str, Any]

    # 에러
    error: str


# ============================================================
# Report Agent Graph
# ============================================================

@register_biz_agent
class ReportAgentGraph(BaseBizAgentGraph):
    """
    리포트 생성 Agent Subgraph

    Flow:
        START
          ↓
        ml_result_validator
          ↓
        insight_extractor
          ↓
        report_structure_builder
          ↓
        report_renderer
          ↓
        END

    Usage:
        # Mock 모드 (개발/테스트)
        agent = ReportAgentGraph(use_mock=True)
        graph = agent.get_compiled_graph()
        result = graph.invoke({
            "ml_result": {...},
            "report_type": "comprehensive",
            "output_format": "html"
        })

        # Real 모드 (프로덕션)
        agent = ReportAgentGraph(use_mock=False)
        graph = agent.get_compiled_graph()
        result = graph.invoke({
            "ml_result": {...},
            "report_type": "summary",
            "output_format": "pdf"
        })
    """

    name = "report_agent"
    description = "ML 분석 결과 기반 비즈니스 리포트 생성"
    version = "1.0.0"

    requires_approval = False  # 리포트 생성은 비용이 크지 않음
    supports_mock = True

    tools = [
        validate_ml_result,
        extract_key_insights,
        generate_report_structure,
        render_report
    ]

    def build_graph(self) -> StateGraph:
        """
        Report Agent Subgraph 구성

        Returns:
            StateGraph: 리포트 생성 그래프
        """
        graph = StateGraph(ReportAgentState)

        # 노드 추가
        graph.add_node("ml_result_validator", ml_result_validator_node)
        graph.add_node("insight_extractor", insight_extractor_node)
        graph.add_node("report_structure_builder", report_structure_builder_node)
        graph.add_node("report_renderer", report_renderer_node)
        graph.add_node("error_handler", error_handler_node)

        # 엣지 추가
        graph.add_edge(START, "ml_result_validator")

        # Conditional edge: validation 성공 시 계속, 실패 시 에러 처리
        graph.add_conditional_edges(
            "ml_result_validator",
            self._should_continue_after_validation,
            {
                "continue": "insight_extractor",
                "error": "error_handler"
            }
        )

        graph.add_edge("insight_extractor", "report_structure_builder")

        # Conditional edge: structure 생성 성공 시 렌더링, 실패 시 에러 처리
        graph.add_conditional_edges(
            "report_structure_builder",
            self._should_continue_after_structure,
            {
                "continue": "report_renderer",
                "error": "error_handler"
            }
        )

        graph.add_edge("report_renderer", END)
        graph.add_edge("error_handler", END)

        return graph

    def _should_continue_after_validation(self, state: ReportAgentState) -> str:
        """Validation 후 분기 결정"""
        if "error" in state:
            return "error"

        validation_result = state.get("validation_result", {})
        if not validation_result.get("valid", False):
            return "error"

        return "continue"

    def _should_continue_after_structure(self, state: ReportAgentState) -> str:
        """Structure 생성 후 분기 결정"""
        if "error" in state:
            return "error"

        report_structure = state.get("report_structure")
        if not report_structure:
            return "error"

        return "continue"

    def _get_mock_tools(self) -> List[Any]:
        """
        Mock 모드용 Tools 반환

        Mock 모드에서는 MockDataProvider의 ML 결과를 사용합니다.
        """
        # Report Agent는 ML 결과를 입력으로 받으므로
        # 동일한 Tools 사용 (입력 데이터만 Mock)
        return self.tools


# ============================================================
# Helper Functions
# ============================================================

def create_report_agent(use_mock: bool = False) -> ReportAgentGraph:
    """
    Report Agent 인스턴스 생성 헬퍼

    Args:
        use_mock: Mock 모드 사용 여부

    Returns:
        ReportAgentGraph 인스턴스
    """
    return ReportAgentGraph(use_mock=use_mock)


def invoke_report_agent(
    ml_result: Dict[str, Any],
    report_type: str = "comprehensive",
    output_format: str = "html",
    use_mock: bool = False
) -> Dict[str, Any]:
    """
    Report Agent 실행 헬퍼

    Args:
        ml_result: ML 분석 결과
        report_type: 리포트 유형 (comprehensive/summary/executive)
        output_format: 출력 형식 (html/json/markdown)
        use_mock: Mock 모드 사용 여부

    Returns:
        final_result: 최종 결과
    """
    agent = create_report_agent(use_mock=use_mock)
    graph = agent.get_compiled_graph()

    result = graph.invoke({
        "ml_result": ml_result,
        "report_type": report_type,
        "output_format": output_format
    })

    return result.get("final_result", {})
