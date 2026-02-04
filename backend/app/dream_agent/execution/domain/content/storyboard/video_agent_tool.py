"""Video Agent Tool - 비디오 생성 (RunPod/ComfyUI 연동)

스토리보드 기반 비디오를 생성합니다.
RunPod Serverless API를 통해 ComfyUI 워크플로우를 실행합니다.
"""

import json
import asyncio
import httpx
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from backend.app.dream_agent.biz_execution.base_tool import (
    BaseBizTool,
    BizResult,
    BizResultStatus,
    BizResultMetadata,
    ApprovalType,
    ValidationResult
)
from backend.app.dream_agent.biz_execution.tool_registry import register_tool
from backend.app.dream_agent.models.todo import TodoItem
from backend.app.core.config import settings


class VideoGenerationStatus(str, Enum):
    """비디오 생성 상태"""
    QUEUED = "queued"
    PROCESSING = "processing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


@register_tool
class VideoAgentTool(BaseBizTool):
    """
    비디오 생성 도구

    스토리보드를 기반으로 비디오를 생성합니다.
    RunPod Serverless API를 통해 ComfyUI 워크플로우를 실행합니다.
    """

    name = "video_agent"
    description = "스토리보드 기반 비디오 생성 (RunPod/ComfyUI)"
    version = "1.0.0"

    requires_approval = True
    approval_type = ApprovalType.COST

    is_async = True
    estimated_duration_sec = 600

    required_input_types = ["storyboard"]
    output_type = "video"

    has_cost = True
    cost_per_call = 2.5

    def __init__(self):
        super().__init__()
        self.resolutions = ["720p", "1080p", "4k"]
        self.fps_options = [24, 30, 60]

        self.runpod_api_key: Optional[str] = getattr(settings, 'RUNPOD_API_KEY', None)
        self.runpod_endpoint: Optional[str] = getattr(settings, 'RUNPOD_ENDPOINT', None)

    def validate_input(self, todo: TodoItem, context: Dict[str, Any]) -> ValidationResult:
        """입력 검증"""
        errors = []
        warnings = []

        params = todo.metadata.execution.tool_params
        resolution = params.get("resolution", "1080p")
        fps = params.get("fps", 30)

        if resolution not in self.resolutions:
            errors.append(f"Unsupported resolution: {resolution}")

        if fps not in self.fps_options:
            warnings.append(f"Non-standard FPS: {fps}, using 30")

        if "storyboard" not in context:
            errors.append("Storyboard is required in context")

        if not self.runpod_api_key or not self.runpod_endpoint:
            errors.append("RunPod API key and endpoint must be configured")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def get_estimated_cost(self, todo: TodoItem, context: Dict[str, Any]) -> float:
        """비용 추정"""
        params = todo.metadata.execution.tool_params
        resolution = params.get("resolution", "1080p")

        resolution_multiplier = {
            "720p": 0.7,
            "1080p": 1.0,
            "4k": 2.5
        }

        base_cost = self.cost_per_call
        multiplier = resolution_multiplier.get(resolution, 1.0)

        storyboard = context.get("storyboard", {})
        num_scenes = len(storyboard.get("scenes", []))
        scene_multiplier = max(1.0, num_scenes / 5)

        return round(base_cost * multiplier * scene_multiplier, 2)

    def get_approval_data(self, todo: TodoItem, context: Dict[str, Any]) -> Dict[str, Any]:
        """승인 데이터 (비용 정보 포함)"""
        params = todo.metadata.execution.tool_params
        storyboard = context.get("storyboard", {})

        return {
            "tool_name": self.name,
            "description": self.description,
            "estimated_cost": self.get_estimated_cost(todo, context),
            "estimated_duration": self.estimated_duration_sec,
            "approval_type": "cost",
            "details": {
                "resolution": params.get("resolution", "1080p"),
                "fps": params.get("fps", 30),
                "scenes": len(storyboard.get("scenes", [])),
                "duration_sec": storyboard.get("duration_sec", 30),
                "platform": storyboard.get("platform", "Instagram")
            },
            "warning": "이 작업은 유료 API를 사용합니다. 비용이 청구됩니다."
        }

    async def execute(
        self,
        todo: TodoItem,
        context: Dict[str, Any],
        log: Any
    ) -> BizResult:
        """비디오 생성 실행"""
        start_time = datetime.now()

        try:
            params = todo.metadata.execution.tool_params
            resolution = params.get("resolution", "1080p")
            fps = params.get("fps", 30)

            storyboard = context.get("storyboard")
            if not storyboard:
                raise ValueError("Storyboard is required")

            result = await self._execute_runpod(storyboard, resolution, fps)

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return self.create_result(
                todo=todo,
                status=BizResultStatus.SUCCESS,
                result_type="video",
                output_path=result["output_path"],
                output_data={
                    "job_id": result["job_id"],
                    "resolution": resolution,
                    "fps": fps,
                    "duration_sec": storyboard.get("duration_sec", 30),
                    "scenes_generated": len(storyboard.get("scenes", []))
                },
                summary=f"비디오 생성 완료 ({resolution}, {fps}fps)",
                preview=f"Video Job ID: {result['job_id']}",
                metadata=BizResultMetadata(
                    processing_time_ms=processing_time,
                    estimated_cost=self.get_estimated_cost(todo, context),
                    actual_cost=result.get("actual_cost", 0)
                )
            )

        except Exception as e:
            return self.create_error_result(
                todo=todo,
                error_message=str(e),
                error_code="VIDEO_GENERATION_ERROR"
            )

    async def _execute_runpod(
        self,
        storyboard: Dict[str, Any],
        resolution: str,
        fps: int
    ) -> Dict[str, Any]:
        """
        RunPod 실행 - 실제 비디오 생성

        RunPod Serverless API를 호출하여 ComfyUI 워크플로우를 실행합니다.
        """
        if not self.runpod_api_key or not self.runpod_endpoint:
            raise ValueError("RunPod API key and endpoint are not configured")

        output_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "data/output/videos"
        output_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=600.0) as client:
            # 1. 작업 제출
            response = await client.post(
                f"{self.runpod_endpoint}/run",
                headers={"Authorization": f"Bearer {self.runpod_api_key}"},
                json={
                    "input": {
                        "storyboard": storyboard,
                        "resolution": resolution,
                        "fps": fps
                    }
                }
            )
            response.raise_for_status()
            job_data = response.json()
            job_id = job_data["id"]

            # 2. 상태 폴링
            while True:
                status_response = await client.get(
                    f"{self.runpod_endpoint}/status/{job_id}",
                    headers={"Authorization": f"Bearer {self.runpod_api_key}"}
                )
                status_response.raise_for_status()
                status = status_response.json()

                if status["status"] == "COMPLETED":
                    break
                elif status["status"] == "FAILED":
                    raise RuntimeError(f"RunPod job failed: {status.get('error', 'Unknown error')}")

                await asyncio.sleep(5)

            # 3. 결과 메타데이터 저장
            meta_path = output_dir / f"{job_id}_meta.json"
            meta_data = {
                "job_id": job_id,
                "status": "completed",
                "storyboard_id": storyboard.get("id", "unknown"),
                "resolution": resolution,
                "fps": fps,
                "duration_sec": storyboard.get("duration_sec", 30),
                "scenes": len(storyboard.get("scenes", [])),
                "created_at": datetime.now().isoformat(),
                "video_url": status.get("output", {}).get("video_url"),
                "thumbnail_url": status.get("output", {}).get("thumbnail_url")
            }
            meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")

            return {
                "job_id": job_id,
                "output_path": str(meta_path),
                "status": VideoGenerationStatus.COMPLETED.value,
                "actual_cost": status.get("cost", 0)
            }

    def configure_runpod(self, api_key: str, endpoint: str) -> None:
        """
        RunPod 설정

        Args:
            api_key: RunPod API 키
            endpoint: RunPod Serverless 엔드포인트
        """
        self.runpod_api_key = api_key
        self.runpod_endpoint = endpoint
