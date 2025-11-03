"""FastAPI 엔드포인트 테스트"""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.fixture
async def client():
    """비동기 HTTP 클라이언트 픽스처"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """루트 엔드포인트 테스트"""
    # When: 루트 엔드포인트 호출
    response = await client.get("/")

    # Then: 200 응답 및 메시지 확인
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "LangGraph Chatbot API"
    assert data["version"] == "0.2.0"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """헬스 체크 엔드포인트 테스트"""
    # When: 헬스 체크 엔드포인트 호출
    response = await client.get("/health")

    # Then: 200 응답 및 상태 확인
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_endpoint(client):
    """채팅 엔드포인트 테스트"""
    # Given: 채팅 요청
    request_data = {"message": "Hello!"}

    # When: 채팅 엔드포인트 호출
    response = await client.post("/chat", json=request_data)

    # Then: 200 응답 및 응답 메시지 확인
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0


@pytest.mark.asyncio
async def test_chat_endpoint_korean(client):
    """한국어 채팅 테스트"""
    # Given: 한국어 메시지
    request_data = {"message": "안녕하세요!"}

    # When: 채팅 엔드포인트 호출
    response = await client.post("/chat", json=request_data)

    # Then: 200 응답 및 한국어 응답 확인
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0


@pytest.mark.asyncio
async def test_chat_endpoint_empty_message(client):
    """빈 메시지 테스트"""
    # Given: 빈 메시지
    request_data = {"message": ""}

    # When: 채팅 엔드포인트 호출
    response = await client.post("/chat", json=request_data)

    # Then: 응답 확인 (빈 메시지도 처리 가능)
    # LLM은 빈 입력에도 응답을 생성할 수 있음
    assert response.status_code in [200, 422]  # 200(성공) 또는 422(검증 실패)
