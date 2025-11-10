"""Agent Management API

Phase 2: Agent 관리 API (2025-11-06)
사용 가능한 Agent 목록 조회
"""
from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/api/agents", tags=["agents"])


# === Response Models ===

class AgentInfo(BaseModel):
    """Agent 정보"""
    name: str
    description: str
    capabilities: List[str]
    status: str  # "available", "busy", "offline"


class AgentListResponse(BaseModel):
    """Agent 목록 응답"""
    agents: List[AgentInfo]
    total: int


# === Agent Management Endpoints ===

@router.get("", response_model=AgentListResponse)
async def list_agents():
    """사용 가능한 Agent 목록 조회 (Phase 2)

    Returns:
        AgentListResponse: Agent 목록

    Note:
        현재는 하드코딩된 Agent 목록을 반환합니다.
        향후 Agent Registry에서 동적으로 조회하도록 개선 예정
    """
    # TODO: Agent Registry에서 동적으로 조회
    # 현재는 하드코딩된 목록 반환
    agents = [
        AgentInfo(
            name="DietAgent",
            description="식단 및 영양 관리 Agent",
            capabilities=[
                "meal_planning",
                "calorie_calculation",
                "nutrition_analysis",
                "allergy_check"
            ],
            status="available"
        ),
        AgentInfo(
            name="WorkoutAgent",
            description="운동 프로그램 생성 Agent",
            capabilities=[
                "workout_planning",
                "exercise_recommendation",
                "fitness_assessment",
                "progress_tracking"
            ],
            status="available"
        ),
        AgentInfo(
            name="HealthAssessmentAgent",
            description="건강 상태 평가 Agent",
            capabilities=[
                "health_check",
                "risk_assessment",
                "medical_history_analysis"
            ],
            status="available"
        ),
        AgentInfo(
            name="ReportAgent",
            description="보고서 생성 Agent",
            capabilities=[
                "report_generation",
                "data_visualization",
                "summary_creation"
            ],
            status="available"
        )
    ]

    return AgentListResponse(
        agents=agents,
        total=len(agents)
    )
