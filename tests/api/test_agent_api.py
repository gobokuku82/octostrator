"""Agent API 테스트

Phase 2 Agent 관리 API 엔드포인트 테스트
- GET /api/agents

Author: AI PT Manager Development Team
Date: 2025-11-06
"""

import pytest
from httpx import AsyncClient
from backend.app.main import app


# === Test GET /api/agents ===

@pytest.mark.asyncio
async def test_list_agents_success():
    """Agent 목록 조회 성공 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    assert response.status_code == 200
    data = response.json()

    # 응답 구조 검증
    assert "agents" in data
    assert "total" in data
    assert isinstance(data["agents"], list)
    assert data["total"] == len(data["agents"])


@pytest.mark.asyncio
async def test_list_agents_content():
    """Agent 목록 내용 검증"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    data = response.json()
    agents = data["agents"]

    # 최소 4개 Agent 존재
    assert len(agents) >= 4

    # Agent 이름 검증
    agent_names = [agent["name"] for agent in agents]
    assert "DietAgent" in agent_names
    assert "WorkoutAgent" in agent_names
    assert "HealthAssessmentAgent" in agent_names
    assert "ReportAgent" in agent_names


@pytest.mark.asyncio
async def test_agent_structure():
    """각 Agent 정보 구조 검증"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    agents = response.json()["agents"]

    for agent in agents:
        # 필수 필드 존재 확인
        assert "name" in agent
        assert "description" in agent
        assert "capabilities" in agent
        assert "status" in agent

        # 타입 검증
        assert isinstance(agent["name"], str)
        assert isinstance(agent["description"], str)
        assert isinstance(agent["capabilities"], list)
        assert isinstance(agent["status"], str)

        # capabilities 검증
        assert len(agent["capabilities"]) > 0
        for cap in agent["capabilities"]:
            assert isinstance(cap, str)

        # status 검증
        assert agent["status"] in ["available", "busy", "offline"]


@pytest.mark.asyncio
async def test_diet_agent_details():
    """DietAgent 상세 정보 검증"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    agents = response.json()["agents"]
    diet_agent = next((a for a in agents if a["name"] == "DietAgent"), None)

    assert diet_agent is not None
    assert "식단" in diet_agent["description"] or "영양" in diet_agent["description"]
    assert "meal_planning" in diet_agent["capabilities"]
    assert "calorie_calculation" in diet_agent["capabilities"]


@pytest.mark.asyncio
async def test_workout_agent_details():
    """WorkoutAgent 상세 정보 검증"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    agents = response.json()["agents"]
    workout_agent = next((a for a in agents if a["name"] == "WorkoutAgent"), None)

    assert workout_agent is not None
    assert "운동" in workout_agent["description"]
    assert "workout_planning" in workout_agent["capabilities"]
    assert "exercise_recommendation" in workout_agent["capabilities"]


@pytest.mark.asyncio
async def test_health_assessment_agent_details():
    """HealthAssessmentAgent 상세 정보 검증"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    agents = response.json()["agents"]
    health_agent = next((a for a in agents if a["name"] == "HealthAssessmentAgent"), None)

    assert health_agent is not None
    assert "건강" in health_agent["description"]
    assert "health_check" in health_agent["capabilities"]
    assert "risk_assessment" in health_agent["capabilities"]


@pytest.mark.asyncio
async def test_report_agent_details():
    """ReportAgent 상세 정보 검증"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    agents = response.json()["agents"]
    report_agent = next((a for a in agents if a["name"] == "ReportAgent"), None)

    assert report_agent is not None
    assert "보고서" in report_agent["description"]
    assert "report_generation" in report_agent["capabilities"]
    assert "data_visualization" in report_agent["capabilities"]


@pytest.mark.asyncio
async def test_agents_all_available():
    """모든 Agent가 available 상태인지 검증"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    agents = response.json()["agents"]

    # 현재는 모두 "available" 상태여야 함
    for agent in agents:
        assert agent["status"] == "available"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
