"""Wan2.2 Video Generator - RunPod Wan2.2 API를 통한 Image-to-Video 변환

Wan2.2 with LoRA & LTX2 모델을 사용하여 이미지를 비디오로 변환합니다.
"""

import os
import random
import asyncio
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from .base_runpod_client import BaseRunPodClient, RunPodJobResult


class VideoGenerateInput(BaseModel):
    """비디오 생성 입력"""
    image_base64: str = Field(..., description="입력 이미지 (base64)")
    prompt: str = Field(..., description="모션 프롬프트", min_length=1)
    negative_prompt: str = Field(
        default="low quality, blurry, distorted, static, jerky motion",
        description="네거티브 프롬프트"
    )
    duration: int = Field(default=5, description="비디오 길이 (초)", ge=1, le=10)
    seed: Optional[int] = Field(default=None, description="랜덤 시드")
    enable_safety_checker: bool = Field(default=False, description="안전 검사 활성화")


class VideoGenerateOutput(BaseModel):
    """비디오 생성 출력"""
    success: bool
    job_id: Optional[str] = None
    video_data: Optional[str] = None  # base64
    duration: Optional[int] = None
    seed: Optional[int] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class Wan22VideoGenerator(BaseRunPodClient):
    """
    RunPod Wan2.2 Image-to-Video 생성기

    Wan2.2 with LoRA & LTX2 모델을 사용하여 이미지를 비디오로 변환합니다.

    Usage:
        generator = Wan22VideoGenerator()

        # 이미지 → 비디오 변환
        result = await generator.generate(VideoGenerateInput(
            image_base64="...",
            prompt="gentle camera zoom in, subtle movement",
            duration=5
        ))

        # 배치 변환
        results = await generator.generate_batch([
            {"image_base64": img1, "prompt": "motion 1..."},
            {"image_base64": img2, "prompt": "motion 2..."},
        ])
    """

    def __init__(
        self,
        endpoint_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 900,  # 비디오 생성은 더 오래 걸림
        poll_interval: int = 10
    ):
        super().__init__(
            endpoint_id=endpoint_id,
            api_key=api_key,
            timeout=timeout,
            poll_interval=poll_interval
        )

    def _get_default_endpoint_id(self) -> Optional[str]:
        """Wan2.2 엔드포인트 ID"""
        return os.getenv("RUNPOD_VIDEO_ENDPOINT_ID")

    def _fix_base64_padding(self, base64_str: str) -> str:
        """
        base64 패딩 보정

        Args:
            base64_str: base64 문자열

        Returns:
            패딩이 보정된 base64 문자열
        """
        # data: 접두사 제거
        if base64_str.startswith("data:"):
            base64_str = base64_str.split(",", 1)[1] if "," in base64_str else base64_str

        # 패딩 보정 (길이가 4의 배수가 되도록)
        padding_needed = len(base64_str) % 4
        if padding_needed:
            base64_str += "=" * (4 - padding_needed)

        return base64_str

    def _build_wan22_input(self, input_data: VideoGenerateInput) -> Dict[str, Any]:
        """
        Wan2.2 API 입력 생성

        Args:
            input_data: 비디오 생성 입력

        Returns:
            Wan2.2 API 입력 JSON
        """
        seed = input_data.seed if input_data.seed is not None else random.randint(1, 999999999)
        image_base64 = self._fix_base64_padding(input_data.image_base64)

        return {
            "prompt": input_data.prompt,
            "negative_prompt": input_data.negative_prompt,
            "image": image_base64,
            "duration": input_data.duration,
            "seed": seed,
            "enable_safety_checker": input_data.enable_safety_checker
        }

    def _extract_video_data(self, output: Dict[str, Any]) -> Optional[str]:
        """
        출력에서 비디오 데이터 추출

        Wan2.2 API는 다양한 형식으로 출력할 수 있음:
        - {"video": "data:video/mp4;base64,..."}
        - {"video": "base64..."}
        - {"data": "base64..."}
        - 문자열 직접 반환

        Args:
            output: API 출력

        Returns:
            base64 비디오 데이터
        """
        if not output:
            return None

        # {"video": ...} 형식
        if "video" in output:
            video_data = output["video"]
            if isinstance(video_data, str):
                if video_data.startswith("data:video"):
                    return video_data.split(",", 1)[1]
                return video_data

        # {"data": ...} 형식
        if "data" in output:
            return output["data"]

        # 첫 번째 큰 문자열 값 찾기 (비디오 데이터일 가능성)
        for key, value in output.items():
            if isinstance(value, str) and len(value) > 1000:
                if value.startswith("data:video"):
                    return value.split(",", 1)[1]
                return value

        # 문자열 직접 반환된 경우
        if isinstance(output, str) and len(output) > 1000:
            if output.startswith("data:video"):
                return output.split(",", 1)[1]
            return output

        return None

    def _parse_result(
        self,
        result: RunPodJobResult,
        input_data: VideoGenerateInput
    ) -> VideoGenerateOutput:
        """
        RunPod 결과를 VideoGenerateOutput으로 변환

        Args:
            result: RunPod Job 결과
            input_data: 원본 입력

        Returns:
            VideoGenerateOutput
        """
        if not result.success:
            return VideoGenerateOutput(
                success=False,
                job_id=result.job_id,
                error=result.error
            )

        video_data = self._extract_video_data(result.output or {})

        if not video_data:
            return VideoGenerateOutput(
                success=False,
                job_id=result.job_id,
                error="No video data in output"
            )

        return VideoGenerateOutput(
            success=True,
            job_id=result.job_id,
            video_data=video_data,
            duration=input_data.duration,
            seed=input_data.seed,
            execution_time_ms=result.execution_time_ms
        )

    async def generate(self, input_data: VideoGenerateInput) -> VideoGenerateOutput:
        """
        이미지 → 비디오 변환

        Args:
            input_data: 비디오 생성 입력

        Returns:
            VideoGenerateOutput: 생성 결과
        """
        wan22_input = self._build_wan22_input(input_data)
        # Wan2.2는 workflow 형식이 아닌 직접 input 형식 사용
        result = await self.run_and_wait(wan22_input, use_workflow=False)
        return self._parse_result(result, input_data)

    async def generate_batch(
        self,
        inputs: List[Dict[str, Any]],
        parallel: bool = False,  # 비디오는 순차 처리 권장 (API 부하)
        max_concurrent: int = 2
    ) -> List[VideoGenerateOutput]:
        """
        배치 비디오 생성

        Args:
            inputs: 입력 데이터 목록
            parallel: 병렬 처리 여부 (기본: False - 순차 처리)
            max_concurrent: 최대 동시 처리 수

        Returns:
            List[VideoGenerateOutput]: 생성 결과 목록
        """
        # 입력 정규화
        normalized_inputs = []
        for inp in inputs:
            if isinstance(inp, dict):
                normalized_inputs.append(VideoGenerateInput(**inp))
            else:
                normalized_inputs.append(inp)

        if parallel:
            # 동시 처리 제한
            semaphore = asyncio.Semaphore(max_concurrent)

            async def generate_with_semaphore(input_data: VideoGenerateInput) -> VideoGenerateOutput:
                async with semaphore:
                    return await self.generate(input_data)

            tasks = [generate_with_semaphore(inp) for inp in normalized_inputs]
            return await asyncio.gather(*tasks)
        else:
            # 순차 처리 (권장)
            results = []
            for inp in normalized_inputs:
                result = await self.generate(inp)
                results.append(result)
            return results

    async def generate_from_flux_output(
        self,
        flux_outputs: List[Dict[str, Any]],
        motion_prompts: List[str],
        negative_prompt: str = "low quality, blurry, static",
        duration: int = 5
    ) -> List[VideoGenerateOutput]:
        """
        FLUX 출력으로부터 비디오 생성

        FluxImageGenerator 출력을 직접 사용할 수 있는 편의 메서드

        Args:
            flux_outputs: FLUX 이미지 생성 결과 목록
            motion_prompts: 씬별 모션 프롬프트
            negative_prompt: 공통 네거티브 프롬프트
            duration: 비디오 길이

        Returns:
            List[VideoGenerateOutput]
        """
        inputs = []
        for i, output in enumerate(flux_outputs):
            if not output.get("success") or not output.get("image_data"):
                continue

            motion_prompt = motion_prompts[i] if i < len(motion_prompts) else motion_prompts[-1]

            inputs.append(VideoGenerateInput(
                image_base64=output["image_data"],
                prompt=motion_prompt,
                negative_prompt=negative_prompt,
                duration=duration
            ))

        return await self.generate_batch(inputs, parallel=False)
