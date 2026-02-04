"""File-based Storage Utilities

로컬 파일 기반 저장소 (JSON/YAML).
개발 및 디버깅용으로 쉽게 접근/편집 가능.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

# 기본 저장 경로
DATA_SYSTEM_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "system"
TODOS_DIR = DATA_SYSTEM_DIR / "todos"
SESSIONS_DIR = TODOS_DIR / "sessions"


class TodoFileItem(BaseModel):
    """파일 저장용 Todo 아이템"""
    id: str
    task: str
    status: str  # pending, in_progress, completed, failed
    priority: int = 0
    layer: str = "unknown"
    created_at: str = ""
    updated_at: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SessionTodos(BaseModel):
    """세션별 Todo 컬렉션"""
    session_id: str
    created_at: str
    updated_at: str
    user_input: str = ""
    language: str = "KOR"
    status: str = "active"  # active, completed, failed
    todos: List[TodoFileItem] = []


class TodoFileStorage:
    """
    파일 기반 Todo 저장소

    경로: data/system/todos/sessions/{session_id}.json
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.sessions_dir = base_dir or SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """세션 파일 경로 반환"""
        return self.sessions_dir / f"{session_id}.json"

    def _now(self) -> str:
        """현재 시간 ISO 형식"""
        return datetime.now().isoformat()

    # ========== Session Operations ==========

    def create_session(
        self,
        session_id: str,
        user_input: str = "",
        language: str = "KOR",
    ) -> SessionTodos:
        """새 세션 생성"""
        session = SessionTodos(
            session_id=session_id,
            created_at=self._now(),
            updated_at=self._now(),
            user_input=user_input,
            language=language,
            status="active",
            todos=[],
        )
        self.save_session(session)
        return session

    def load_session(self, session_id: str) -> Optional[SessionTodos]:
        """세션 로드"""
        path = self._get_session_path(session_id)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SessionTodos(**data)

    def save_session(self, session: SessionTodos) -> None:
        """세션 저장"""
        session.updated_at = self._now()
        path = self._get_session_path(session.session_id)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, ensure_ascii=False, indent=2)

    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        path = self._get_session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self) -> List[str]:
        """모든 세션 ID 목록"""
        return [p.stem for p in self.sessions_dir.glob("*.json")]

    # ========== Todo Operations ==========

    def add_todo(
        self,
        session_id: str,
        todo_id: str,
        task: str,
        status: str = "pending",
        priority: int = 0,
        layer: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TodoFileItem]:
        """Todo 추가"""
        session = self.load_session(session_id)
        if not session:
            return None

        todo = TodoFileItem(
            id=todo_id,
            task=task,
            status=status,
            priority=priority,
            layer=layer,
            created_at=self._now(),
            updated_at=self._now(),
            metadata=metadata or {},
        )
        session.todos.append(todo)
        self.save_session(session)
        return todo

    def update_todo(
        self,
        session_id: str,
        todo_id: str,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[TodoFileItem]:
        """Todo 상태 업데이트"""
        session = self.load_session(session_id)
        if not session:
            return None

        for todo in session.todos:
            if todo.id == todo_id:
                if status:
                    todo.status = status
                if result is not None:
                    todo.result = result
                if error is not None:
                    todo.error = error
                todo.updated_at = self._now()
                self.save_session(session)
                return todo
        return None

    def get_todo(self, session_id: str, todo_id: str) -> Optional[TodoFileItem]:
        """특정 Todo 조회"""
        session = self.load_session(session_id)
        if not session:
            return None

        for todo in session.todos:
            if todo.id == todo_id:
                return todo
        return None

    def get_todos_by_status(
        self,
        session_id: str,
        status: str,
    ) -> List[TodoFileItem]:
        """상태별 Todo 목록"""
        session = self.load_session(session_id)
        if not session:
            return []
        return [t for t in session.todos if t.status == status]

    def get_pending_todos(self, session_id: str) -> List[TodoFileItem]:
        """대기 중인 Todo 목록"""
        return self.get_todos_by_status(session_id, "pending")

    def get_all_todos(self, session_id: str) -> List[TodoFileItem]:
        """모든 Todo 목록"""
        session = self.load_session(session_id)
        return session.todos if session else []


# Global instance
todo_file_storage = TodoFileStorage()


# ========== Convenience Functions ==========

def create_session(session_id: str, user_input: str = "", language: str = "KOR") -> SessionTodos:
    """세션 생성"""
    return todo_file_storage.create_session(session_id, user_input, language)


def load_session(session_id: str) -> Optional[SessionTodos]:
    """세션 로드"""
    return todo_file_storage.load_session(session_id)


def save_todo(
    session_id: str,
    todo_id: str,
    task: str,
    status: str = "pending",
    **kwargs,
) -> Optional[TodoFileItem]:
    """Todo 저장"""
    return todo_file_storage.add_todo(session_id, todo_id, task, status, **kwargs)


def update_todo_status(
    session_id: str,
    todo_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Optional[TodoFileItem]:
    """Todo 상태 업데이트"""
    return todo_file_storage.update_todo(session_id, todo_id, status, result, error)
