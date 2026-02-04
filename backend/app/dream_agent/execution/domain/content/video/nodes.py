"""Video Agent Nodes - 비디오 생성 Subgraph의 노드 함수들

각 노드는 상태를 받아서 처리 후 업데이트된 상태를 반환합니다.
"""

from typing import Dict, Any
from backend.app.dream_agent.biz_execution.agents.video.video_tools import (
    validate_storyboard,
    save_video_metadata
)
from backend.app.dream_agent.biz_execution.agents.video.comfyui_tools import (
    generate_comfyui_workflow,
    generate_scene_prompts,
    call_comfyui_api
)


def storyboard_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    스토리보드 검증 노드

    Args:
        state: {
            "storyboard": Dict[str, Any],
            "validation_result": Dict[str, Any] | None
        }

    Returns:
        state with updated "validation_result"
    """
    storyboard = state.get("storyboard")

    if not storyboard:
        return {
            **state,
            "validation_result": {
                "valid": False,
                "errors": ["Storyboard not found in state"],
                "warnings": []
            },
            "error": "Missing storyboard"
        }

    # Tool 호출
    validation_result = validate_storyboard.invoke({"storyboard": storyboard})

    return {
        **state,
        "validation_result": validation_result
    }


def comfyui_config_builder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ComfyUI 워크플로우 설정 생성 노드

    Args:
        state: {
            "storyboard": Dict[str, Any],
            "resolution": str,
            "fps": int,
            "workflow": Dict[str, Any] | None
        }

    Returns:
        state with updated "workflow"
    """
    validation_result = state.get("validation_result", {})

    # 검증 실패 시 중단
    if not validation_result.get("valid", False):
        return {
            **state,
            "error": f"Storyboard validation failed: {validation_result.get('errors', [])}"
        }

    storyboard = state.get("storyboard")
    resolution = state.get("resolution", "1080p")
    fps = state.get("fps", 30)

    # Tool 호출
    workflow = generate_comfyui_workflow.invoke({
        "storyboard": storyboard,
        "resolution": resolution,
        "fps": fps
    })

    return {
        **state,
        "workflow": workflow
    }


def comfyui_prompt_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scene별 ComfyUI 프롬프트 생성 노드

    Args:
        state: {
            "storyboard": Dict[str, Any],
            "scene_prompts": List[Dict[str, Any]] | None
        }

    Returns:
        state with updated "scene_prompts"
    """
    storyboard = state.get("storyboard")

    if not storyboard:
        return {
            **state,
            "error": "Missing storyboard for prompt generation"
        }

    # Tool 호출
    scene_prompts = generate_scene_prompts.invoke({"storyboard": storyboard})

    return {
        **state,
        "scene_prompts": scene_prompts
    }


def comfyui_executor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ComfyUI 실행 노드 (Mock/Real 전환 가능)

    Args:
        state: {
            "workflow": Dict[str, Any],
            "scene_prompts": List[Dict[str, Any]],
            "use_mock": bool,
            "comfyui_result": Dict[str, Any] | None
        }

    Returns:
        state with updated "comfyui_result"
    """
    workflow = state.get("workflow")
    scene_prompts = state.get("scene_prompts")
    use_mock = state.get("use_mock", True)

    if not workflow or not scene_prompts:
        return {
            **state,
            "error": "Missing workflow or scene_prompts for ComfyUI execution"
        }

    # Tool 호출
    try:
        comfyui_result = call_comfyui_api.invoke({
            "workflow": workflow,
            "scene_prompts": scene_prompts,
            "use_mock": use_mock
        })

        return {
            **state,
            "comfyui_result": comfyui_result
        }
    except Exception as e:
        return {
            **state,
            "error": f"ComfyUI execution failed: {str(e)}"
        }


def video_postprocessor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    비디오 메타데이터 후처리 및 저장 노드

    Args:
        state: {
            "comfyui_result": Dict[str, Any],
            "storyboard": Dict[str, Any],
            "output_path": str | None
        }

    Returns:
        state with updated "output_path" and "final_result"
    """
    comfyui_result = state.get("comfyui_result")
    storyboard = state.get("storyboard")

    if not comfyui_result:
        return {
            **state,
            "error": "Missing ComfyUI result for postprocessing"
        }

    # Tool 호출
    try:
        output_path = save_video_metadata.invoke({
            "comfyui_result": comfyui_result,
            "storyboard": storyboard
        })

        # 최종 결과 구성
        final_result = {
            "status": "success",
            "output_path": output_path,
            "job_id": comfyui_result.get("job_id"),
            "video_url": comfyui_result.get("output", {}).get("video_url"),
            "thumbnail_url": comfyui_result.get("output", {}).get("thumbnail_url"),
            "mock": comfyui_result.get("mock", False),
            "scene_count": len(state.get("scene_prompts", [])),
            "resolution": state.get("resolution", "1080p"),
            "fps": state.get("fps", 30)
        }

        return {
            **state,
            "output_path": output_path,
            "final_result": final_result
        }
    except Exception as e:
        return {
            **state,
            "error": f"Postprocessing failed: {str(e)}"
        }


def error_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    에러 처리 노드

    에러 발생 시 호출되어 최종 에러 상태 반환
    """
    error_message = state.get("error", "Unknown error")

    return {
        **state,
        "final_result": {
            "status": "failed",
            "error": error_message,
            "output_path": None
        }
    }
