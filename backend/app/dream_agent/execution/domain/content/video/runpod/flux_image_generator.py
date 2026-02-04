"""FLUX Image Generator - RunPod FLUX API를 통한 이미지 생성

FLUX 모델을 사용하여 텍스트 프롬프트로부터 이미지를 생성합니다.
ComfyUI 워크플로우 형식으로 RunPod API를 호출합니다.
"""

import os
import random
import asyncio
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from .base_runpod_client import BaseRunPodClient, RunPodJobResult


class ImageGenerateInput(BaseModel):
    """이미지 생성 입력"""
    prompt: str = Field(..., description="이미지 생성 프롬프트", min_length=1)
    negative_prompt: str = Field(
        default="low quality, blurry, distorted, bad anatomy",
        description="네거티브 프롬프트"
    )
    width: int = Field(default=480, description="이미지 너비", ge=256, le=2048)
    height: int = Field(default=832, description="이미지 높이", ge=256, le=2048)
    steps: int = Field(default=20, description="샘플링 스텝 수", ge=1, le=50)
    seed: Optional[int] = Field(default=None, description="랜덤 시드")
    cfg_scale: float = Field(default=1.0, description="CFG 스케일", ge=0.0, le=20.0)


class ImageGenerateOutput(BaseModel):
    """이미지 생성 출력"""
    success: bool
    job_id: Optional[str] = None
    image_data: Optional[str] = None  # base64
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[int] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class FluxImageGenerator(BaseRunPodClient):
    """
    RunPod FLUX 이미지 생성기

    FLUX 모델 (flux1-dev-fp8.safetensors)을 사용하여 이미지를 생성합니다.

    Usage:
        generator = FluxImageGenerator()

        # 단일 이미지 생성
        result = await generator.generate(ImageGenerateInput(
            prompt="a beautiful sunset over mountains",
            width=1024,
            height=1024
        ))

        # 배치 생성
        results = await generator.generate_batch([
            {"prompt": "scene 1...", "width": 480, "height": 832},
            {"prompt": "scene 2...", "width": 480, "height": 832},
        ])
    """

    def __init__(
        self,
        endpoint_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 300,
        poll_interval: int = 5
    ):
        super().__init__(
            endpoint_id=endpoint_id,
            api_key=api_key,
            timeout=timeout,
            poll_interval=poll_interval
        )

    def _get_default_endpoint_id(self) -> Optional[str]:
        """FLUX 엔드포인트 ID"""
        return os.getenv("RUNPOD_ENDPOINT_ID")

    def _build_flux_workflow(self, input_data: ImageGenerateInput) -> Dict[str, Any]:
        """
        FLUX ComfyUI 워크플로우 생성

        Args:
            input_data: 이미지 생성 입력

        Returns:
            ComfyUI 워크플로우 JSON
        """
        seed = input_data.seed if input_data.seed is not None else random.randint(1, 999999999)

        return {
            "3": {
                "inputs": {
                    "seed": seed,
                    "steps": input_data.steps,
                    "cfg": input_data.cfg_scale,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": "flux1-dev-fp8.safetensors"
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": input_data.width,
                    "height": input_data.height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": input_data.prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": input_data.negative_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }

    def _parse_result(
        self,
        result: RunPodJobResult,
        input_data: ImageGenerateInput
    ) -> ImageGenerateOutput:
        """
        RunPod 결과를 ImageGenerateOutput으로 변환

        Args:
            result: RunPod Job 결과
            input_data: 원본 입력

        Returns:
            ImageGenerateOutput
        """
        if not result.success:
            return ImageGenerateOutput(
                success=False,
                job_id=result.job_id,
                error=result.error
            )

        # 이미지 데이터 추출
        output = result.output or {}
        images = output.get("images", [])

        if not images:
            return ImageGenerateOutput(
                success=False,
                job_id=result.job_id,
                error="No images in output"
            )

        image_data = images[0].get("data") if images else None

        return ImageGenerateOutput(
            success=True,
            job_id=result.job_id,
            image_data=image_data,
            width=input_data.width,
            height=input_data.height,
            seed=input_data.seed,
            execution_time_ms=result.execution_time_ms
        )

    async def generate(self, input_data: ImageGenerateInput) -> ImageGenerateOutput:
        """
        단일 이미지 생성

        Args:
            input_data: 이미지 생성 입력

        Returns:
            ImageGenerateOutput: 생성 결과
        """
        workflow = self._build_flux_workflow(input_data)
        result = await self.run_and_wait(workflow, use_workflow=True)
        return self._parse_result(result, input_data)

    async def generate_batch(
        self,
        inputs: List[Dict[str, Any]],
        parallel: bool = True,
        max_concurrent: int = 4
    ) -> List[ImageGenerateOutput]:
        """
        배치 이미지 생성

        Args:
            inputs: 입력 데이터 목록 (dict 또는 ImageGenerateInput)
            parallel: 병렬 처리 여부
            max_concurrent: 최대 동시 처리 수

        Returns:
            List[ImageGenerateOutput]: 생성 결과 목록
        """
        # 입력 정규화
        normalized_inputs = []
        for inp in inputs:
            if isinstance(inp, dict):
                normalized_inputs.append(ImageGenerateInput(**inp))
            else:
                normalized_inputs.append(inp)

        if parallel:
            # 동시 처리 제한을 위한 세마포어
            semaphore = asyncio.Semaphore(max_concurrent)

            async def generate_with_semaphore(input_data: ImageGenerateInput) -> ImageGenerateOutput:
                async with semaphore:
                    return await self.generate(input_data)

            tasks = [generate_with_semaphore(inp) for inp in normalized_inputs]
            return await asyncio.gather(*tasks)
        else:
            # 순차 처리
            results = []
            for inp in normalized_inputs:
                result = await self.generate(inp)
                results.append(result)
            return results
