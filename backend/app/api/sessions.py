"""Session Management REST API

Phase 4.4: 세션 관리 및 HITL 재개 엔드포인트
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from langgraph.types import Command

from backend.app.octostrator.checkpointer import create_checkpointer
from backend.app.octostrator.session import get_session_manager, get_session_config
from backend.app.octostrator.supervisor import build_supervisor_graph


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# === Request/Response Models ===

class SessionListResponse(BaseModel):
    """세션 목록 응답"""
    sessions: List[dict]
    total: int


class SessionStateResponse(BaseModel):
    """세션 상태 응답"""
    thread_id: str
    status: str
    state: dict
    checkpoint_id: Optional[str] = None


class ResumeRequest(BaseModel):
    """HITL 재개 요청"""
    response: Optional[str] = None
    approve: bool = False


class ResumeResponse(BaseModel):
    """HITL 재개 응답"""
    success: bool
    message: str
    state: Optional[dict] = None


class CheckpointInfo(BaseModel):
    """체크포인트 정보"""
    checkpoint_id: str
    thread_id: str
    checkpoint_ns: str = ""
    step: int


class CheckpointListResponse(BaseModel):
    """체크포인트 목록 응답"""
    checkpoints: List[CheckpointInfo]
    total: int


# === Session Management Endpoints ===

@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = Query(None, description="특정 사용자의 세션만 조회"),
    status: Optional[str] = Query(None, description="특정 상태의 세션만 조회")
):
    """세션 목록 조회

    Args:
        user_id: 사용자 ID (optional)
        status: 세션 상태 (optional)

    Returns:
        SessionListResponse: 세션 목록
    """
    session_manager = get_session_manager()
    sessions = session_manager.list_sessions(user_id=user_id, status=status)

    return SessionListResponse(
        sessions=sessions,
        total=len(sessions)
    )


@router.get("/{thread_id}", response_model=SessionStateResponse)
async def get_session_state(thread_id: str):
    """특정 세션의 현재 상태 조회

    Args:
        thread_id: 세션 thread_id

    Returns:
        SessionStateResponse: 세션 상태

    Raises:
        HTTPException: 세션을 찾을 수 없거나 에러 발생 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        state = await graph.aget_state(config)

        if not state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # 상태 추출
        is_waiting = state.values.get("is_waiting_human", False)
        next_node = state.next if hasattr(state, 'next') else None

        # 상태 판단
        if is_waiting:
            status = "waiting_human"
        elif next_node:
            status = "in_progress"
        else:
            status = "completed"

        return SessionStateResponse(
            thread_id=thread_id,
            status=status,
            state=state.values,
            checkpoint_id=str(state.config.get("configurable", {}).get("checkpoint_id")) if state.config else None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session state: {str(e)}"
        )


@router.delete("/{thread_id}")
async def delete_session(thread_id: str):
    """세션 삭제

    Args:
        thread_id: 삭제할 세션 thread_id

    Returns:
        dict: 삭제 결과
    """
    session_manager = get_session_manager()
    success = session_manager.delete_session(thread_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

    return {"message": f"Session {thread_id} deleted successfully"}


# === HITL Resume Endpoint ===

@router.post("/{thread_id}/resume", response_model=ResumeResponse)
async def resume_session(thread_id: str, request: ResumeRequest):
    """interrupt된 세션 재개 (HITL)

    Args:
        thread_id: 재개할 세션 thread_id
        request: 재개 요청
            - approve: True면 자동 승인 (None 전달)
            - response: 사용자 응답 텍스트

    Returns:
        ResumeResponse: 재개 결과

    Raises:
        HTTPException: 세션을 찾을 수 없거나 재개 불가 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 확인
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # HITL 대기 중인지 확인
        is_waiting = current_state.values.get("is_waiting_human", False)
        if not is_waiting:
            raise HTTPException(
                status_code=400,
                detail="Session is not waiting for human input"
            )

        # 재개 실행
        if request.approve:
            # 자동 승인: None으로 재개
            result = await graph.ainvoke(None, config=config)
            message = "Session resumed with auto-approval"
        elif request.response:
            # 사용자 응답으로 재개
            result = await graph.ainvoke(
                Command(resume=request.response),
                config=config
            )
            message = f"Session resumed with user response: {request.response}"
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'approve' must be true or 'response' must be provided"
            )

        return ResumeResponse(
            success=True,
            message=message,
            state=result
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume session: {str(e)}"
        )


# === Checkpoint Endpoints ===

@router.get("/{thread_id}/checkpoints", response_model=CheckpointListResponse)
async def list_checkpoints(thread_id: str):
    """세션의 모든 체크포인트 조회

    Args:
        thread_id: 세션 thread_id

    Returns:
        CheckpointListResponse: 체크포인트 목록

    Raises:
        HTTPException: 에러 발생 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Config 생성
        config = get_session_config(thread_id)

        # 체크포인트 목록 조회
        checkpoints = []
        checkpoint_tuples = checkpointer.alist(config)

        step = 0
        async for checkpoint_tuple in checkpoint_tuples:
            checkpoint_config = checkpoint_tuple.config
            checkpoint_id = checkpoint_config.get("configurable", {}).get("checkpoint_id", "")
            checkpoint_ns = checkpoint_config.get("configurable", {}).get("checkpoint_ns", "")

            checkpoints.append(CheckpointInfo(
                checkpoint_id=str(checkpoint_id),
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                step=step
            ))
            step += 1

        return CheckpointListResponse(
            checkpoints=checkpoints,
            total=len(checkpoints)
        )

    except Exception as e:
        import traceback
        error_detail = f"Failed to list checkpoints: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list checkpoints: {str(e)}"
        )


@router.get("/{thread_id}/history")
async def get_session_history(thread_id: str, limit: int = Query(10, ge=1, le=100)):
    """세션 히스토리 조회 (메시지 기록)

    Args:
        thread_id: 세션 thread_id
        limit: 조회할 메시지 수 (기본 10, 최대 100)

    Returns:
        dict: 메시지 히스토리

    Raises:
        HTTPException: 에러 발생 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        state = await graph.aget_state(config)

        if not state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # 메시지 추출
        messages = state.values.get("messages", [])

        # 최근 limit개만 반환
        recent_messages = messages[-limit:] if len(messages) > limit else messages

        # 메시지를 dict로 변환
        message_dicts = []
        for msg in recent_messages:
            message_dicts.append({
                "type": msg.__class__.__name__,
                "content": msg.content
            })

        return {
            "thread_id": thread_id,
            "total_messages": len(messages),
            "returned_messages": len(message_dicts),
            "messages": message_dicts
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session history: {str(e)}"
        )
