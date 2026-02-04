"""ComfyUI Tools - ComfyUI 워크플로우 생성 및 실행 Tools

Mock 모드와 Real 모드를 지원합니다.
환경변수 USE_MOCK_COMFYUI=true/false로 전환 가능
"""

from typing import Dict, Any, List
from langchain_core.tools import tool
import os


@tool
def generate_comfyui_workflow(
    storyboard: Dict[str, Any],
    resolution: str = "1080p",
    fps: int = 30
) -> Dict[str, Any]:
    """
    ComfyUI 워크플로우 설정 생성

    Args:
        storyboard: 스토리보드
        resolution: 해상도 (720p/1080p/4k)
        fps: 프레임레이트

    Returns:
        ComfyUI workflow JSON
    """
    # 해상도 맵핑
    resolution_map = {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "4k": (3840, 2160)
    }
    width, height = resolution_map.get(resolution, (1920, 1080))

    workflow = {
        "workflow_id": f"video_gen_{storyboard.get('id', 'unknown')}",
        "metadata": {
            "storyboard_id": storyboard.get("id"),
            "resolution": resolution,
            "fps": fps,
            "scene_count": len(storyboard.get("scenes", []))
        },
        "nodes": {
            "load_checkpoint": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}
            },
            "empty_latent": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            "text_prompt": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "{{SCENE_PROMPT}}",
                    "clip": ["load_checkpoint", 1]
                }
            },
            "negative_prompt": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "low quality, blurry, distorted, watermark",
                    "clip": ["load_checkpoint", 1]
                }
            },
            "sampler": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": "{{SEED}}",
                    "steps": 30,
                    "cfg": 7.5,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["load_checkpoint", 0],
                    "positive": ["text_prompt", 0],
                    "negative": ["negative_prompt", 0],
                    "latent_image": ["empty_latent", 0]
                }
            },
            "vae_decode": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["sampler", 0],
                    "vae": ["load_checkpoint", 2]
                }
            },
            "save_image": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["vae_decode", 0],
                    "filename_prefix": "video_scene_"
                }
            }
        },
        "output_node": "save_image"
    }

    return workflow


@tool
def generate_scene_prompts(storyboard: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    각 Scene별 ComfyUI 프롬프트 생성

    Args:
        storyboard: 스토리보드

    Returns:
        Scene별 프롬프트 목록
    """
    scene_prompts = []

    for scene in storyboard.get("scenes", []):
        # Scene 정보 추출
        description = scene.get("description", "")
        visual = scene.get("visual", "")
        mood = storyboard.get("mood", "professional")

        # 프롬프트 생성
        prompt = f"{description}, {visual}, {mood} style, high quality, 4k resolution, cinematic"

        # Negative 프롬프트
        negative_prompt = "low quality, blurry, distorted, watermark, text, logo, bad anatomy"

        scene_prompt = {
            "scene_id": scene.get("scene_id"),
            "duration": scene.get("duration", 3),
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": scene.get("seed", 42)
        }

        scene_prompts.append(scene_prompt)

    return scene_prompts


@tool
def call_comfyui_api(
    workflow: Dict[str, Any],
    scene_prompts: List[Dict[str, Any]],
    use_mock: bool = None
) -> Dict[str, Any]:
    """
    ComfyUI API 호출 (Mock/Real 전환 가능)

    Args:
        workflow: ComfyUI 워크플로우
        scene_prompts: Scene별 프롬프트 목록
        use_mock: Mock 모드 사용 여부 (None이면 환경변수 확인)

    Returns:
        ComfyUI 실행 결과
    """
    # Mock 모드 확인 (환경변수 우선)
    if use_mock is None:
        use_mock = os.getenv("USE_MOCK_COMFYUI", "true").lower() == "true"

    if use_mock:
        return _mock_comfyui_response(workflow, scene_prompts)
    else:
        # Real 모드는 async 함수 필요
        # 현재는 동기 tool이므로 에러 반환
        raise NotImplementedError(
            "Real ComfyUI API call requires async implementation. "
            "Set USE_MOCK_COMFYUI=true or implement async version."
        )


def _mock_comfyui_response(
    workflow: Dict[str, Any],
    scene_prompts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Mock ComfyUI 응답 반환

    Returns:
        Mock 응답 데이터
    """
    from backend.app.dream_agent.biz_execution.toolkit.mock_provider import MockDataProvider

    provider = MockDataProvider()
    return provider.get_mock_comfyui_response(
        workflow_id=workflow.get("workflow_id", "unknown"),
        scene_count=len(scene_prompts)
    )


# ============================================================
# Async 버전 (Real RunPod API 호출용)
# ============================================================

async def call_comfyui_api_async(
    workflow: Dict[str, Any],
    scene_prompts: List[Dict[str, Any]],
    use_mock: bool = None
) -> Dict[str, Any]:
    """
    ComfyUI API 비동기 호출 (Mock/Real 전환 가능)

    Args:
        workflow: ComfyUI 워크플로우
        scene_prompts: Scene별 프롬프트 목록
        use_mock: Mock 모드 사용 여부

    Returns:
        ComfyUI 실행 결과
    """
    # Mock 모드 확인
    if use_mock is None:
        use_mock = os.getenv("USE_MOCK_COMFYUI", "true").lower() == "true"

    if use_mock:
        return _mock_comfyui_response(workflow, scene_prompts)
    else:
        return await _real_comfyui_api_call(workflow, scene_prompts)


async def _real_comfyui_api_call(
    workflow: Dict[str, Any],
    scene_prompts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    실제 RunPod ComfyUI API 호출

    Returns:
        RunPod API 응답
    """
    import httpx
    import asyncio

    # RunPod 설정
    runpod_api_key = os.getenv("RUNPOD_API_KEY")
    runpod_endpoint = os.getenv("RUNPOD_ENDPOINT")

    if not runpod_api_key or not runpod_endpoint:
        raise ValueError(
            "RunPod API key and endpoint must be configured. "
            "Set RUNPOD_API_KEY and RUNPOD_ENDPOINT environment variables."
        )

    async with httpx.AsyncClient(timeout=600.0) as client:
        # 1. 작업 제출
        response = await client.post(
            f"{runpod_endpoint}/run",
            headers={"Authorization": f"Bearer {runpod_api_key}"},
            json={
                "input": {
                    "workflow": workflow,
                    "scene_prompts": scene_prompts
                }
            }
        )
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data["id"]

        # 2. 상태 폴링
        while True:
            status_response = await client.get(
                f"{runpod_endpoint}/status/{job_id}",
                headers={"Authorization": f"Bearer {runpod_api_key}"}
            )
            status_response.raise_for_status()
            status = status_response.json()

            if status["status"] == "COMPLETED":
                return status
            elif status["status"] == "FAILED":
                raise RuntimeError(
                    f"RunPod job failed: {status.get('error', 'Unknown error')}"
                )

            # 5초 대기
            await asyncio.sleep(5)
