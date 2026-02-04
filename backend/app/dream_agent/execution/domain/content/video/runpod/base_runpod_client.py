"""Base RunPod Client - RunPod Serverless API 공통 클라이언트

RunPod API 호출, 폴링, 에러 처리를 위한 베이스 클래스
"""

import os
import asyncio
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from enum import Enum

import httpx
from pydantic import BaseModel


class JobStatus(str, Enum):
    """RunPod Job 상태"""
    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class RunPodError(Exception):
    """RunPod API 에러"""
    def __init__(self, message: str, job_id: Optional[str] = None, status: Optional[str] = None):
        self.message = message
        self.job_id = job_id
        self.status = status
        super().__init__(self.message)


class RunPodJobResult(BaseModel):
    """RunPod Job 결과"""
    success: bool
    job_id: str
    status: JobStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class BaseRunPodClient(ABC):
    """RunPod Serverless API 베이스 클라이언트"""

    def __init__(
        self,
        endpoint_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 600,
        poll_interval: int = 5
    ):
        """
        Args:
            endpoint_id: RunPod Serverless 엔드포인트 ID
            api_key: RunPod API 키
            timeout: 최대 대기 시간 (초)
            poll_interval: 상태 폴링 간격 (초)
        """
        self.endpoint_id = endpoint_id or self._get_default_endpoint_id()
        self.api_key = api_key or os.getenv("RUNPOD_API_KEY")
        self.timeout = timeout
        self.poll_interval = poll_interval

        if not self.api_key:
            raise ValueError("RUNPOD_API_KEY is not set")
        if not self.endpoint_id:
            raise ValueError("RunPod endpoint ID is not set")

        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"

    @abstractmethod
    def _get_default_endpoint_id(self) -> Optional[str]:
        """기본 엔드포인트 ID 반환 (서브클래스에서 구현)"""
        pass

    def _get_headers(self) -> Dict[str, str]:
        """API 요청 헤더"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def submit_job(
        self,
        input_data: Dict[str, Any],
        use_workflow: bool = False
    ) -> str:
        """
        Job 제출

        Args:
            input_data: 입력 데이터
            use_workflow: ComfyUI 워크플로우 형식 사용 여부

        Returns:
            job_id: 제출된 Job ID
        """
        if use_workflow:
            payload = {"input": {"workflow": input_data}}
        else:
            payload = {"input": input_data}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/run",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            job_data = response.json()

            return job_data["id"]

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Job 상태 조회

        Args:
            job_id: Job ID

        Returns:
            상태 정보
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/status/{job_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def wait_for_completion(self, job_id: str) -> RunPodJobResult:
        """
        Job 완료까지 대기

        Args:
            job_id: Job ID

        Returns:
            RunPodJobResult: 최종 결과
        """
        max_polls = self.timeout // self.poll_interval
        start_time = asyncio.get_event_loop().time()

        for _ in range(max_polls):
            status_data = await self.get_job_status(job_id)
            status = status_data.get("status", "UNKNOWN")

            if status == JobStatus.COMPLETED:
                execution_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
                return RunPodJobResult(
                    success=True,
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    output=status_data.get("output", {}),
                    execution_time_ms=execution_time
                )

            elif status == JobStatus.FAILED:
                return RunPodJobResult(
                    success=False,
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error=status_data.get("error", "Unknown error")
                )

            elif status in [JobStatus.CANCELLED, JobStatus.TIMED_OUT]:
                return RunPodJobResult(
                    success=False,
                    job_id=job_id,
                    status=JobStatus(status),
                    error=f"Job {status.lower()}"
                )

            await asyncio.sleep(self.poll_interval)

        # 타임아웃
        return RunPodJobResult(
            success=False,
            job_id=job_id,
            status=JobStatus.TIMED_OUT,
            error=f"Timeout after {self.timeout} seconds"
        )

    async def run_and_wait(
        self,
        input_data: Dict[str, Any],
        use_workflow: bool = False
    ) -> RunPodJobResult:
        """
        Job 제출 및 완료 대기

        Args:
            input_data: 입력 데이터
            use_workflow: ComfyUI 워크플로우 형식 사용 여부

        Returns:
            RunPodJobResult: 최종 결과
        """
        try:
            job_id = await self.submit_job(input_data, use_workflow)
            return await self.wait_for_completion(job_id)
        except httpx.HTTPStatusError as e:
            return RunPodJobResult(
                success=False,
                job_id="",
                status=JobStatus.FAILED,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            return RunPodJobResult(
                success=False,
                job_id="",
                status=JobStatus.FAILED,
                error=str(e)
            )

    async def cancel_job(self, job_id: str) -> bool:
        """
        Job 취소

        Args:
            job_id: Job ID

        Returns:
            성공 여부
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/cancel/{job_id}",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return True
        except Exception:
            return False
