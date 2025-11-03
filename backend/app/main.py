"""FastAPI 메인 애플리케이션

LangGraph Chatbot API 엔트리포인트
Phase 4.3: WebSocket 실시간 스트리밍 추가
"""
import sys
import asyncio
from dotenv import load_dotenv

# Windows에서 psycopg 호환성을 위한 EventLoop 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# .env 파일 로드 (최우선)
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor import build_supervisor_graph
from backend.app.config.system import config

# Phase 4.3: WebSocket 라우터 import
from backend.app.api.websocket import router as websocket_router

# Phase 4.4: Session Management 라우터 import
from backend.app.api.sessions import router as sessions_router


# FastAPI 앱 생성
app = FastAPI(
    title="LangGraph Chatbot",
    version="0.4.0",
    description="LangGraph 1.0 Supervisor Pattern 기반 멀티 에이전트 챗봇 (WebSocket + Session Management)"
)

# Phase 4.3: WebSocket 라우터 등록
app.include_router(websocket_router)

# Phase 4.4: Session Management 라우터 등록
app.include_router(sessions_router)

# Supervisor Graph 초기화
supervisor_graph = build_supervisor_graph()


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "LangGraph Chatbot API",
        "version": "0.2.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """채팅 엔드포인트

    Args:
        request: ChatRequest 모델 (message 필드 포함)

    Returns:
        ChatResponse: LLM 응답

    Raises:
        HTTPException: 처리 중 에러 발생 시
    """
    try:
        # Supervisor Graph 실행
        result = await supervisor_graph.ainvoke({
            "messages": [HumanMessage(content=request.message)]
        })

        # 마지막 메시지 추출
        response_content = result["messages"][-1].content

        return ChatResponse(response=response_content)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=config.system_api_host,
        port=config.system_api_port,
        reload=config.system_debug
    )
