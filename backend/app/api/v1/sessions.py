"""Session API endpoints"""

from typing import Optional, Dict
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from loguru import logger

from backend.schema.session import SessionCreate, SessionResponse
from backend.schema.response import SuccessResponse, ErrorResponse

router = APIRouter()

# In-memory session storage (replace with database/Redis later)
sessions_storage: Dict[str, SessionResponse] = {}


@router.post("/sessions", response_model=SessionResponse)
async def create_session(session_create: SessionCreate):
    """Create a new session"""
    try:
        session_id = uuid4()
        session_token = f"token_{uuid4()}"
        thread_id = f"thread_{uuid4()}"

        session = SessionResponse(
            id=session_id,
            user_id=session_create.user_id,
            session_token=session_token,
            thread_id=thread_id,
            is_active=True,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24),
            metadata=session_create.metadata
        )

        sessions_storage[str(session_id)] = session

        return session

    except Exception as e:
        logger.error(f"Create session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID):
    """Get session details"""
    try:
        session_key = str(session_id)
        if session_key not in sessions_storage:
            raise HTTPException(status_code=404, detail="Session not found")

        session = sessions_storage[session_key]

        # Check if session is expired
        if session.expires_at < datetime.now():
            session.is_active = False

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: UUID):
    """Delete/invalidate a session"""
    try:
        session_key = str(session_id)
        if session_key not in sessions_storage:
            raise HTTPException(status_code=404, detail="Session not found")

        del sessions_storage[session_key]

        return SuccessResponse(message="Session deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/refresh", response_model=SessionResponse)
async def refresh_session(session_id: UUID):
    """Refresh session expiration"""
    try:
        session_key = str(session_id)
        if session_key not in sessions_storage:
            raise HTTPException(status_code=404, detail="Session not found")

        session = sessions_storage[session_key]

        # Extend expiration
        session.expires_at = datetime.now() + timedelta(hours=24)
        session.is_active = True

        sessions_storage[session_key] = session

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))