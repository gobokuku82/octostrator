"""Session Manager

Phase 4.1: thread_id 기반 세션 생성 및 관리
"""
import uuid
from typing import Dict, Optional
from datetime import datetime


class SessionManager:
    """세션 관리 클래스

    thread_id 기반으로 세션을 생성하고 관리합니다.
    """

    def __init__(self):
        """SessionManager 초기화"""
        self._sessions: Dict[str, dict] = {}

    def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """새 세션 생성

        Args:
            user_id: 사용자 ID (선택적)
            metadata: 추가 메타데이터 (선택적)

        Returns:
            str: 생성된 thread_id
        """
        thread_id = f"thread_{uuid.uuid4().hex[:16]}"

        session_data = {
            "thread_id": thread_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "status": "active",
            "metadata": metadata or {}
        }

        self._sessions[thread_id] = session_data

        print(f"[SessionManager] ✓ 새 세션 생성: {thread_id}")
        return thread_id

    def get_session(self, thread_id: str) -> Optional[dict]:
        """세션 조회

        Args:
            thread_id: 조회할 thread_id

        Returns:
            dict: 세션 데이터, 없으면 None
        """
        session = self._sessions.get(thread_id)

        if session:
            # 마지막 접근 시간 업데이트
            session["last_accessed"] = datetime.now().isoformat()

        return session

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> list:
        """세션 목록 조회

        Args:
            user_id: 특정 사용자의 세션만 조회 (선택적)
            status: 특정 상태의 세션만 조회 (선택적)

        Returns:
            list: 세션 목록
        """
        sessions = list(self._sessions.values())

        if user_id:
            sessions = [s for s in sessions if s.get("user_id") == user_id]

        if status:
            sessions = [s for s in sessions if s.get("status") == status]

        return sessions

    def update_session_status(self, thread_id: str, status: str) -> bool:
        """세션 상태 업데이트

        Args:
            thread_id: 업데이트할 thread_id
            status: 새 상태 (active, completed, waiting_human, failed)

        Returns:
            bool: 성공 여부
        """
        if thread_id in self._sessions:
            self._sessions[thread_id]["status"] = status
            self._sessions[thread_id]["last_accessed"] = datetime.now().isoformat()
            return True
        return False

    def delete_session(self, thread_id: str) -> bool:
        """세션 삭제

        Args:
            thread_id: 삭제할 thread_id

        Returns:
            bool: 성공 여부
        """
        if thread_id in self._sessions:
            del self._sessions[thread_id]
            print(f"[SessionManager] ✓ 세션 삭제: {thread_id}")
            return True
        return False


# 전역 SessionManager 인스턴스
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """SessionManager 싱글톤 인스턴스 가져오기

    Returns:
        SessionManager: SessionManager 인스턴스
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager()

    return _session_manager


def create_session(user_id: Optional[str] = None, metadata: Optional[dict] = None) -> str:
    """새 세션 생성 (편의 함수)

    Args:
        user_id: 사용자 ID (선택적)
        metadata: 추가 메타데이터 (선택적)

    Returns:
        str: 생성된 thread_id
    """
    manager = get_session_manager()
    return manager.create_session(user_id=user_id, metadata=metadata)


def get_session_config(thread_id: str) -> dict:
    """LangGraph Config 생성 (편의 함수)

    Args:
        thread_id: 세션 thread_id

    Returns:
        dict: LangGraph config 객체
    """
    return {"configurable": {"thread_id": thread_id}}
