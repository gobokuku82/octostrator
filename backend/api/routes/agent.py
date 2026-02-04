"""Agent Execution Routes"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import uuid

from ..schemas.agent import AgentRequest, AgentResponse, AgentStatus
from .websocket import manager

router = APIRouter()

# In-memory session storage (TODO: Redis로 교체)
sessions: dict = {}


@router.post("/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """
    Agent 실행 (동기)

    짧은 작업에 적합. 응답이 올 때까지 대기.
    """
    from backend.app.dream_agent.orchestrator import create_agent
    from backend.app.dream_agent.states import create_initial_state

    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Agent 생성
        agent = create_agent()

        # 초기 상태 생성
        state = create_initial_state(
            user_input=request.user_input,
            language=request.language,
            session_id=session_id,
        )

        # Agent 실행
        config = {"configurable": {"thread_id": session_id}}
        final_state = None

        async for event in agent.astream(state, config):
            final_state = event

        # 결과 반환
        return AgentResponse(
            session_id=session_id,
            status="completed",
            response=final_state.get("response", "") if final_state else "",
            todos=[],  # TODO: Todo 직렬화
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-async", response_model=AgentResponse)
async def run_agent_async(
    request: AgentRequest,
    background_tasks: BackgroundTasks,
):
    """
    Agent 실행 (비동기)

    긴 작업에 적합. WebSocket으로 진행 상황 전송.
    """
    session_id = request.session_id or str(uuid.uuid4())

    # 세션 초기화
    sessions[session_id] = {
        "status": "running",
        "request": request.model_dump(),
    }

    # 백그라운드에서 Agent 실행
    background_tasks.add_task(
        _run_agent_background,
        session_id,
        request.user_input,
        request.language,
    )

    return AgentResponse(
        session_id=session_id,
        status="running",
        response=None,
        todos=[],
    )


async def _run_agent_background(
    session_id: str,
    user_input: str,
    language: str,
):
    """백그라운드 Agent 실행"""
    from backend.app.dream_agent.orchestrator import create_agent
    from backend.app.dream_agent.states import create_initial_state

    try:
        agent = create_agent()
        state = create_initial_state(
            user_input=user_input,
            language=language,
            session_id=session_id,
        )

        config = {"configurable": {"thread_id": session_id}}

        async for event in agent.astream(state, config):
            # WebSocket으로 상태 업데이트 전송
            if "todos" in event:
                # Todo 객체를 직렬화
                todos_data = []
                for todo in event["todos"]:
                    if hasattr(todo, "model_dump"):
                        todos_data.append(todo.model_dump())
                    elif hasattr(todo, "dict"):
                        todos_data.append(todo.dict())
                    elif isinstance(todo, dict):
                        todos_data.append(todo)
                    else:
                        todos_data.append({
                            "id": getattr(todo, "id", str(uuid.uuid4())),
                            "task": getattr(todo, "task", str(todo)),
                            "status": getattr(todo, "status", "pending"),
                            "layer": getattr(todo, "layer", "planning"),
                            "metadata": getattr(todo, "metadata", {}),
                        })

                await manager.send_update(session_id, {
                    "type": "todo_update",
                    "data": {"todos": todos_data},
                })

        # 완료 메시지
        final_response = event.get("response", "") if event else ""
        sessions[session_id]["status"] = "completed"
        sessions[session_id]["response"] = final_response

        await manager.send_update(session_id, {
            "type": "complete",
            "data": {"response": final_response},
        })

    except Exception as e:
        sessions[session_id]["status"] = "failed"
        sessions[session_id]["error"] = str(e)

        await manager.send_update(session_id, {
            "type": "error",
            "data": {"error": str(e)},
        })


@router.get("/status/{session_id}", response_model=AgentStatus)
async def get_agent_status(session_id: str):
    """Agent 실행 상태 조회"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    return AgentStatus(
        session_id=session_id,
        status=session["status"],
        response=session.get("response"),
        error=session.get("error"),
    )


@router.post("/stop/{session_id}")
async def stop_agent(session_id: str):
    """Agent 실행 중지 (HITL)"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # TODO: 실제 Agent 중지 로직 구현
    sessions[session_id]["status"] = "stopped"

    return {"message": "Agent stopped", "session_id": session_id}
