"""Health Check Routes"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": "dream-agent-api"}


@router.get("/ready")
async def readiness_check():
    """Readiness check - verify all dependencies"""
    # TODO: LLM 연결 체크, 기타 의존성 체크
    return {
        "status": "ready",
        "checks": {
            "api": True,
            "agent": True,
        }
    }
