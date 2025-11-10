"""Session Management REST API

Phase 4.4: 세션 관리 및 HITL 재개 엔드포인트
Updated 2025-11-06: Phase 2 API 확장 추가
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from langgraph.types import Command

from backend.app.octostrator.checkpointer import create_checkpointer
from backend.app.octostrator.session import get_session_manager, get_session_config
from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph as build_supervisor_graph
from backend.app.octostrator.states import StateHelpers


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


# === New Phase 2 Models ===

class SessionSummaryResponse(BaseModel):
    """세션 요약 응답 (Phase 2)"""
    session_id: str
    created_at: str
    duration: str
    total_steps: int
    todo_status: Dict[str, Any]
    plan_version: int
    user_interactions: int
    status: str
    actions_summary: str
    user_interactions_summary: List[str]


class ActionResponse(BaseModel):
    """특정 Step 작업 조회 응답 (Phase 2)"""
    step: int
    action: Optional[Dict[str, Any]]


class StateUpdateRequest(BaseModel):
    """State 업데이트 요청 (Phase 2)"""
    updates: Dict[str, Any]


class InterruptRequest(BaseModel):
    """세션 중단 요청 (Phase 2)"""
    reason: Optional[str] = "user_requested"
    message: Optional[str] = None


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

        # 상태 추출 (Octostrator format)
        requires_approval = state.values.get("requires_approval", False)
        error = state.values.get("error")
        next_node = state.next if hasattr(state, 'next') else None

        # 상태 판단
        if requires_approval:
            status = "waiting_human"
        elif error:
            status = "error"
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

        # HITL 대기 중인지 확인 (Octostrator format)
        requires_approval = current_state.values.get("requires_approval", False)
        if not requires_approval:
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

        # Octostrator 상태 추출
        plan = state.values.get("plan", {})
        todos = state.values.get("todos", [])
        execution_results = state.values.get("execution_results", {})
        final_response = state.values.get("final_response", "")

        return {
            "thread_id": thread_id,
            "plan": plan,
            "todos": todos[:limit] if len(todos) > limit else todos,
            "total_todos": len(todos),
            "returned_todos": min(len(todos), limit),
            "execution_results": execution_results,
            "final_response": final_response
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session history: {str(e)}"
        )


# === Phase 2: New API Endpoints ===

@router.get("/{thread_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(thread_id: str):
    """작업 내역 전체 요약 (Phase 2)

    사용자가 "지금까지 뭐 했어?" 질문에 답변하기 위한 API

    Args:
        thread_id: 세션 thread_id

    Returns:
        SessionSummaryResponse: 전체 요약 정보

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

        # StateHelpers를 사용한 요약 생성
        summary = StateHelpers.get_execution_summary(state.values)
        summary["actions_summary"] = StateHelpers.get_all_actions_summary(state.values)
        summary["user_interactions_summary"] = StateHelpers.get_user_interaction_summary(state.values)

        return SessionSummaryResponse(**summary)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session summary: {str(e)}"
        )


@router.get("/{thread_id}/action/{step}", response_model=ActionResponse)
async def get_action_at_step(thread_id: str, step: int):
    """특정 step의 작업 조회 (Phase 2)

    Args:
        thread_id: 세션 thread_id
        step: 조회할 step 번호

    Returns:
        ActionResponse: 해당 step의 작업 정보

    Raises:
        HTTPException: 세션을 찾을 수 없거나 step이 존재하지 않을 때
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

        # StateHelpers를 사용한 action 조회
        action = StateHelpers.get_action_at_step(state.values, step)

        if action is None:
            raise HTTPException(status_code=404, detail=f"Action at step {step} not found")

        return ActionResponse(step=step, action=action)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get action at step {step}: {str(e)}"
        )


@router.put("/{thread_id}/state")
async def update_session_state(thread_id: str, request: StateUpdateRequest):
    """세션 State 업데이트 (Phase 2)

    사용자가 State를 직접 수정할 수 있는 API

    Args:
        thread_id: 세션 thread_id
        request: 업데이트할 State 내용

    Returns:
        dict: 업데이트 결과

    Raises:
        HTTPException: 세션을 찾을 수 없거나 업데이트 실패 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # State 업데이트
        await graph.aupdate_state(config, request.updates)

        # user_interactions에 기록
        interaction = {
            "type": "modify_state",
            "details": {
                "updates": request.updates
            }
        }
        await graph.aupdate_state(config, {"user_interactions": [interaction]})

        return {
            "success": True,
            "message": "State updated successfully",
            "updates": request.updates
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update state: {str(e)}"
        )


@router.post("/{thread_id}/interrupt")
async def interrupt_session(thread_id: str, request: InterruptRequest):
    """세션 실행 중단 (Phase 2)

    사용자가 ESC나 "중단" 버튼으로 실행을 중단하는 API

    Args:
        thread_id: 세션 thread_id
        request: 중단 이유 및 메시지

    Returns:
        dict: 중단 결과

    Raises:
        HTTPException: 세션을 찾을 수 없거나 중단 실패 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # user_interactions에 기록
        interaction = {
            "type": "interrupt",
            "reason": request.reason,
            "details": {
                "message": request.message
            }
        }
        await graph.aupdate_state(config, {
            "user_interactions": [interaction],
            "requires_approval": True  # HITL 상태로 전환
        })

        # Todo 상태 통계 조회
        todo_status = StateHelpers.get_todo_status(current_state.values)

        return {
            "success": True,
            "message": "Session interrupted successfully",
            "reason": request.reason,
            "progress": {
                "completed": todo_status["completed"],
                "total": todo_status["total"],
                "progress": todo_status["progress"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to interrupt session: {str(e)}"
        )
