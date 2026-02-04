"""Video Agent Graph - 비디오 생성 Subgraph

스토리보드 기반 비디오 생성 에이전트
ComfyUI 워크플로우를 통해 비디오를 생성합니다.

Mock 모드 지원:
- Mock 모드: 즉시 Mock 응답 반환 (개발/테스트용)
- Real 모드: RunPod ComfyUI API 호출 (프로덕션용)
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from backend.app.dream_agent.biz_execution.base_agent_graph import BaseBizAgentGraph
from backend.app.dream_agent.biz_execution.agent_registry import register_biz_agent
from backend.app.dream_agent.biz_execution.agents.video.nodes import (
    storyboard_validator_node,
    comfyui_config_builder_node,
    comfyui_prompt_generator_node,
    comfyui_executor_node,
    video_postprocessor_node,
    error_handler_node
)
from backend.app.dream_agent.biz_execution.agents.video.video_tools import (
    validate_storyboard,
    save_video_metadata
)
from backend.app.dream_agent.biz_execution.agents.video.comfyui_tools import (
    generate_comfyui_workflow,
    generate_scene_prompts,
    call_comfyui_api
)


# ============================================================
# State Definition
# ============================================================

class VideoAgentState(TypedDict, total=False):
    """Video Agent 상태"""
    # 입력
    storyboard: Dict[str, Any]
    resolution: str
    fps: int
    use_mock: bool

    # 중간 결과
    validation_result: Dict[str, Any]
    workflow: Dict[str, Any]
    scene_prompts: List[Dict[str, Any]]
    comfyui_result: Dict[str, Any]

    # 출력
    output_path: str
    final_result: Dict[str, Any]

    # 에러
    error: str


# ============================================================
# Video Agent Graph
# ============================================================

@register_biz_agent
class VideoAgentGraph(BaseBizAgentGraph):
    """
    비디오 생성 Agent Subgraph

    Flow:
        START
          ↓
        storyboard_validator
          ↓
        comfyui_config_builder
          ↓
        comfyui_prompt_generator
          ↓
        comfyui_executor (Mock/Real)
          ↓
        video_postprocessor
          ↓
        END

    Usage:
        # Mock 모드 (개발/테스트)
        agent = VideoAgentGraph(use_mock=True)
        graph = agent.get_compiled_graph()
        result = graph.invoke({
            "storyboard": {...},
            "resolution": "1080p",
            "fps": 30
        })

        # Real 모드 (프로덕션)
        agent = VideoAgentGraph(use_mock=False)
        graph = agent.get_compiled_graph()
        result = graph.invoke({
            "storyboard": {...},
            "resolution": "1080p",
            "fps": 30
        })
    """

    name = "video_agent"
    description = "스토리보드 기반 비디오 생성 (ComfyUI)"
    version = "1.0.0"

    requires_approval = True  # 비용 발생 가능성
    supports_mock = True

    tools = [
        validate_storyboard,
        generate_comfyui_workflow,
        generate_scene_prompts,
        call_comfyui_api,
        save_video_metadata
    ]

    def build_graph(self) -> StateGraph:
        """
        Video Agent Subgraph 구성

        Returns:
            StateGraph: 비디오 생성 그래프
        """
        graph = StateGraph(VideoAgentState)

        # 노드 추가
        graph.add_node("storyboard_validator", storyboard_validator_node)
        graph.add_node("comfyui_config_builder", comfyui_config_builder_node)
        graph.add_node("comfyui_prompt_generator", comfyui_prompt_generator_node)
        graph.add_node("comfyui_executor", comfyui_executor_node)
        graph.add_node("video_postprocessor", video_postprocessor_node)
        graph.add_node("error_handler", error_handler_node)

        # 엣지 추가
        graph.add_edge(START, "storyboard_validator")

        # Conditional edge: validation 성공 시 계속, 실패 시 에러 처리
        graph.add_conditional_edges(
            "storyboard_validator",
            self._should_continue_after_validation,
            {
                "continue": "comfyui_config_builder",
                "error": "error_handler"
            }
        )

        graph.add_edge("comfyui_config_builder", "comfyui_prompt_generator")
        graph.add_edge("comfyui_prompt_generator", "comfyui_executor")

        # Conditional edge: executor 성공 시 postprocess, 실패 시 에러 처리
        graph.add_conditional_edges(
            "comfyui_executor",
            self._should_continue_after_executor,
            {
                "continue": "video_postprocessor",
                "error": "error_handler"
            }
        )

        graph.add_edge("video_postprocessor", END)
        graph.add_edge("error_handler", END)

        return graph

    def _should_continue_after_validation(self, state: VideoAgentState) -> str:
        """Validation 후 분기 결정"""
        if "error" in state:
            return "error"

        validation_result = state.get("validation_result", {})
        if not validation_result.get("valid", False):
            return "error"

        return "continue"

    def _should_continue_after_executor(self, state: VideoAgentState) -> str:
        """Executor 후 분기 결정"""
        if "error" in state:
            return "error"

        comfyui_result = state.get("comfyui_result")
        if not comfyui_result:
            return "error"

        return "continue"

    def _get_mock_tools(self) -> List[Any]:
        """
        Mock 모드용 Tools 반환

        Mock 모드에서는 call_comfyui_api가 자동으로 Mock 응답을 반환합니다.
        (환경변수 USE_MOCK_COMFYUI=true 설정 시)
        """
        # Mock 모드에서도 같은 Tools 사용
        # call_comfyui_api 내부에서 use_mock 플래그에 따라 자동 전환
        return self.tools


# ============================================================
# Helper Functions
# ============================================================

def create_video_agent(use_mock: bool = True) -> VideoAgentGraph:
    """
    Video Agent 인스턴스 생성 헬퍼

    Args:
        use_mock: Mock 모드 사용 여부

    Returns:
        VideoAgentGraph 인스턴스
    """
    return VideoAgentGraph(use_mock=use_mock)


def invoke_video_agent(
    storyboard: Dict[str, Any],
    resolution: str = "1080p",
    fps: int = 30,
    use_mock: bool = True
) -> Dict[str, Any]:
    """
    Video Agent 실행 헬퍼

    Args:
        storyboard: 스토리보드 데이터
        resolution: 해상도 (720p/1080p/4k)
        fps: 프레임레이트
        use_mock: Mock 모드 사용 여부

    Returns:
        final_result: 최종 결과
    """
    agent = create_video_agent(use_mock=use_mock)
    graph = agent.get_compiled_graph()

    result = graph.invoke({
        "storyboard": storyboard,
        "resolution": resolution,
        "fps": fps,
        "use_mock": use_mock
    })

    return result.get("final_result", {})
