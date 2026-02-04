"""Result Models - 레이어별 결과 모델

이 파일은 states/results.py에서 models/로 이동됨.
Pydantic 모델만 포함.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class IntentResult(BaseModel):
    """Cognitive 레이어 결과 - 의도 파악"""
    intent_type: str  # "simple_question" | "ml_analysis" | "report_generation" | "business_task"
    confidence: float = Field(ge=0.0, le=1.0)
    requires_ml: bool
    requires_biz: bool
    summary: str
    extracted_entities: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class PlanResult(BaseModel):
    """Planning 레이어 결과 - 계획 수립"""
    plan_description: str
    total_steps: int
    estimated_complexity: str  # "low" | "medium" | "high"
    workflow_type: str  # "linear" | "parallel" | "conditional"
    ml_pipeline: Optional[list[str]] = None  # ML 실행 파이프라인 순서
    biz_pipeline: Optional[list[str]] = None  # Biz 실행 파이프라인 순서
    timestamp: datetime = Field(default_factory=datetime.now)


class MLResult(BaseModel):
    """ML Execution 레이어 결과"""
    result_type: str  # "data_collection" | "preprocessing" | "analysis" | "insight"
    data_path: Optional[str] = None  # 대용량 데이터는 파일 경로로 저장
    summary: dict = Field(default_factory=dict)  # 요약 정보만 상태에 저장
    metrics: dict = Field(default_factory=dict)  # 성능 지표, 통계 등
    visualizations: list[str] = Field(default_factory=list)  # 시각화 파일 경로
    insights: list[str] = Field(default_factory=list)  # 주요 인사이트
    timestamp: datetime = Field(default_factory=datetime.now)


class BizResult(BaseModel):
    """Biz Execution 레이어 결과"""
    result_type: str  # "report" | "ad_creative" | "sales_support" | "inventory"
    output_path: Optional[str] = None  # 생성된 파일 경로 (보고서, 이미지 등)
    preview: str  # 미리보기 텍스트
    metadata: dict = Field(default_factory=dict)  # 메타데이터
    deliverables: list[str] = Field(default_factory=list)  # 산출물 목록
    timestamp: datetime = Field(default_factory=datetime.now)


class FinalResponse(BaseModel):
    """Response 레이어 최종 결과"""
    response_text: str
    summary: str
    attachments: list[str] = Field(default_factory=list)  # 첨부 파일 경로
    next_actions: list[str] = Field(default_factory=list)  # 추천 다음 액션
    timestamp: datetime = Field(default_factory=datetime.now)
