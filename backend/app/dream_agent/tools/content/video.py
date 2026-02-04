"""Video Tool - 비디오 콘텐츠 생성

스토리보드 기반 비디오 생성, ComfyUI 워크플로우 관리 도구를 제공합니다.
Mock 모드와 Real 모드를 지원합니다.

(기존 biz_execution/agents/video/에서 이전)
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def validate_storyboard(storyboard: Dict[str, Any]) -> Dict[str, Any]:
    """
    스토리보드 유효성 검증

    Args:
        storyboard: 스토리보드 데이터

    Returns:
        {"valid": bool, "errors": List[str], "warnings": List[str]}
    """
    logger.info("[Video] Validating storyboard")

    errors = []
    warnings = []

    # 필수 필드 확인
    if "scenes" not in storyboard:
        errors.append("Missing 'scenes' field")

    scenes = storyboard.get("scenes", [])
    if len(scenes) == 0:
        errors.append("No scenes found in storyboard")

    # Scene 유효성 검증
    for idx, scene in enumerate(scenes):
        if "description" not in scene:
            errors.append(f"Scene {idx+1}: Missing 'description'")
        if "duration" not in scene:
            warnings.append(f"Scene {idx+1}: Missing 'duration', using default 3s")

    # 총 길이 확인
    total_duration = sum(s.get("duration", 3) for s in scenes)
    if total_duration > 60:
        warnings.append(f"Total duration {total_duration}s exceeds recommended 60s")
    elif total_duration < 5:
        warnings.append(f"Total duration {total_duration}s is too short")

    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "scene_count": len(scenes),
        "total_duration": total_duration
    }

    logger.info(f"[Video] Storyboard validation: valid={result['valid']}, errors={len(errors)}")
    return result


@tool
def save_video_metadata(
    comfyui_result: Dict[str, Any],
    storyboard: Dict[str, Any]
) -> str:
    """
    비디오 메타데이터 저장

    Args:
        comfyui_result: ComfyUI 실행 결과
        storyboard: 원본 스토리보드

    Returns:
        저장된 메타데이터 파일 경로
    """
    logger.info("[Video] Saving video metadata")

    output_dir = Path("data/output/videos")
    output_dir.mkdir(parents=True, exist_ok=True)

    job_id = comfyui_result.get("job_id", "unknown")
    meta_path = output_dir / f"{job_id}_meta.json"

    metadata = {
        "job_id": job_id,
        "status": comfyui_result.get("status"),
        "storyboard_id": storyboard.get("id"),
        "video_url": comfyui_result.get("output", {}).get("video_url"),
        "thumbnail_url": comfyui_result.get("output", {}).get("thumbnail_url"),
        "frames": comfyui_result.get("output", {}).get("frames", []),
        "metadata": comfyui_result.get("metadata", {}),
        "cost": comfyui_result.get("cost", 0),
        "mock": comfyui_result.get("mock", False),
        "created_at": datetime.now().isoformat()
    }

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"[Video] Metadata saved: {meta_path}")
    return str(meta_path)


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
    logger.info(f"[Video] Generating ComfyUI workflow (resolution={resolution}, fps={fps})")

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

    logger.info(f"[Video] Workflow generated: {workflow['workflow_id']}")
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
    logger.info(f"[Video] Generating scene prompts for {len(storyboard.get('scenes', []))} scenes")

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

    logger.info(f"[Video] Generated {len(scene_prompts)} scene prompts")
    return scene_prompts


@tool
def call_comfyui_api(
    workflow: Dict[str, Any],
    scene_prompts: List[Dict[str, Any]],
    use_mock: bool = None
) -> Dict[str, Any]:
    """
    ComfyUI API 호출 (Mock/Real 전환 가능)

    환경변수 USE_MOCK_COMFYUI=true/false로 전환 가능

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

    logger.info(f"[Video] Calling ComfyUI API (mock={use_mock})")

    if use_mock:
        return _mock_comfyui_response(workflow, scene_prompts)
    else:
        # Real 모드는 async 함수 필요
        raise NotImplementedError(
            "Real ComfyUI API call requires async implementation. "
            "Set USE_MOCK_COMFYUI=true or use call_comfyui_api_async()."
        )


def _mock_comfyui_response(
    workflow: Dict[str, Any],
    scene_prompts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Mock ComfyUI 응답 반환"""
    try:
        from backend.app.dream_agent.biz_execution.toolkit.mock_provider import MockDataProvider
        provider = MockDataProvider()
        return provider.get_mock_comfyui_response(
            workflow_id=workflow.get("workflow_id", "unknown"),
            scene_count=len(scene_prompts)
        )
    except ImportError:
        # Fallback mock response
        return {
            "job_id": f"mock_{workflow.get('workflow_id', 'unknown')}",
            "status": "COMPLETED",
            "mock": True,
            "output": {
                "video_url": "https://example.com/mock_video.mp4",
                "thumbnail_url": "https://example.com/mock_thumb.jpg",
                "frames": []
            },
            "metadata": workflow.get("metadata", {}),
            "cost": 0
        }


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
    """실제 RunPod ComfyUI API 호출"""
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


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("video")
class VideoTool(BaseTool):
    """비디오 콘텐츠 생성 도구

    BaseTool 패턴으로 구현된 Video Generator.
    스토리보드 기반 비디오 생성, ComfyUI 워크플로우 관리를 담당합니다.
    """

    name: str = "video"
    description: str = "스토리보드 기반 비디오 콘텐츠 생성 (ComfyUI)"
    category: str = "content"
    version: str = "1.0.0"

    # 지원 해상도
    RESOLUTIONS = ["720p", "1080p", "4k"]

    def execute(
        self,
        storyboard: Dict[str, Any],
        resolution: str = "1080p",
        fps: int = 30,
        use_mock: bool = None,
        **kwargs
    ) -> Dict[str, Any]:
        """비디오 생성 파이프라인 실행

        Args:
            storyboard: 스토리보드 데이터
            resolution: 해상도 (720p/1080p/4k)
            fps: 프레임레이트
            use_mock: Mock 모드 사용 여부

        Returns:
            비디오 생성 결과
        """
        # 1. 스토리보드 검증
        validation = validate_storyboard.invoke({"storyboard": storyboard})
        if not validation["valid"]:
            return {
                "success": False,
                "error": "Invalid storyboard",
                "errors": validation["errors"]
            }

        # 2. 워크플로우 생성
        workflow = generate_comfyui_workflow.invoke({
            "storyboard": storyboard,
            "resolution": resolution,
            "fps": fps
        })

        # 3. Scene 프롬프트 생성
        scene_prompts = generate_scene_prompts.invoke({"storyboard": storyboard})

        # 4. ComfyUI API 호출
        result = call_comfyui_api.invoke({
            "workflow": workflow,
            "scene_prompts": scene_prompts,
            "use_mock": use_mock
        })

        # 5. 메타데이터 저장
        meta_path = save_video_metadata.invoke({
            "comfyui_result": result,
            "storyboard": storyboard
        })

        return {
            "success": True,
            "job_id": result.get("job_id"),
            "status": result.get("status"),
            "output": result.get("output"),
            "meta_path": meta_path,
            "mock": result.get("mock", False)
        }

    async def aexecute(
        self,
        storyboard: Dict[str, Any],
        resolution: str = "1080p",
        fps: int = 30,
        use_mock: bool = None,
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 비디오 생성 파이프라인 실행"""
        # 1. 스토리보드 검증
        validation = await validate_storyboard.ainvoke({"storyboard": storyboard})
        if not validation["valid"]:
            return {
                "success": False,
                "error": "Invalid storyboard",
                "errors": validation["errors"]
            }

        # 2. 워크플로우 생성
        workflow = await generate_comfyui_workflow.ainvoke({
            "storyboard": storyboard,
            "resolution": resolution,
            "fps": fps
        })

        # 3. Scene 프롬프트 생성
        scene_prompts = await generate_scene_prompts.ainvoke({"storyboard": storyboard})

        # 4. ComfyUI API 호출 (async 버전)
        result = await call_comfyui_api_async(workflow, scene_prompts, use_mock)

        # 5. 메타데이터 저장
        meta_path = await save_video_metadata.ainvoke({
            "comfyui_result": result,
            "storyboard": storyboard
        })

        return {
            "success": True,
            "job_id": result.get("job_id"),
            "status": result.get("status"),
            "output": result.get("output"),
            "meta_path": meta_path,
            "mock": result.get("mock", False)
        }


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def validate_storyboard_direct(storyboard: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 없이 직접 스토리보드 검증"""
    return validate_storyboard.invoke({"storyboard": storyboard})


def generate_workflow_direct(
    storyboard: Dict[str, Any],
    resolution: str = "1080p"
) -> Dict[str, Any]:
    """Agent 없이 직접 워크플로우 생성"""
    return generate_comfyui_workflow.invoke({
        "storyboard": storyboard,
        "resolution": resolution,
        "fps": 30
    })


def generate_video_direct(
    storyboard: Dict[str, Any],
    scenes: List[Dict[str, Any]] = None,
    style: str = "realistic",
    resolution: str = "1080p",
    fps: int = 30,
    use_mock: bool = True
) -> Dict[str, Any]:
    """Agent 없이 직접 비디오 생성 (Mock 기본)

    Args:
        storyboard: 스토리보드 데이터
        scenes: 씬 목록 (storyboard에 없을 경우 사용)
        style: 비디오 스타일 (realistic, cinematic, animated 등)
        resolution: 해상도 (720p/1080p/4k)
        fps: 프레임레이트
        use_mock: Mock 모드 사용 여부

    Returns:
        비디오 생성 결과
    """
    # scenes가 별도로 전달되면 storyboard에 병합
    if scenes and "scenes" not in storyboard:
        storyboard = {**storyboard, "scenes": scenes}

    # style을 storyboard의 mood로 사용
    if style and "mood" not in storyboard:
        storyboard = {**storyboard, "mood": style}

    tool = VideoTool()
    return tool.execute(
        storyboard=storyboard,
        resolution=resolution,
        fps=fps,
        use_mock=use_mock
    )


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

VIDEO_TOOLS = [
    validate_storyboard,
    save_video_metadata,
    generate_comfyui_workflow,
    generate_scene_prompts,
    call_comfyui_api,
]
