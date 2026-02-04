"""Todo Store - Save/Load with file locking"""

import json
import os
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from backend.app.core.logging import get_logger
from backend.app.dream_agent.models.todo import TodoItem

logger = get_logger(__name__)

# Platform-specific file locking
try:
    import fcntl  # Unix/Linux/Mac
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
    try:
        import msvcrt  # Windows
        HAS_MSVCRT = True
    except ImportError:
        HAS_MSVCRT = False
        logger.warning("No file locking available on this platform")


class TodoStore:
    """Todo 저장/로드 시스템 with file locking"""

    def __init__(self, base_path: str = "data/sessions"):
        """
        Args:
            base_path: Session 데이터 저장 기본 경로
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """Session 경로 반환"""
        session_path = self.base_path / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path

    def _get_todos_file(self, session_id: str) -> Path:
        """Todos 파일 경로 반환"""
        return self._get_session_path(session_id) / "todos.json"

    def _lock_file(self, file_handle):
        """파일 잠금 (플랫폼별)"""
        if HAS_FCNTL:
            # Unix/Linux/Mac
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
        elif HAS_MSVCRT:
            # Windows - msvcrt.locking은 까다로우므로 skip
            # 대신 atomic write (temp file + rename)를 사용
            pass

    def _unlock_file(self, file_handle):
        """파일 잠금 해제 (플랫폼별)"""
        if HAS_FCNTL:
            # Unix/Linux/Mac
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        elif HAS_MSVCRT:
            # Windows - skip
            pass

    def save_todos(
        self,
        session_id: str,
        todos: List[TodoItem],
        backup: bool = True
    ) -> bool:
        """
        Todos를 JSON 파일로 저장 (file locking 포함)

        Args:
            session_id: Session ID
            todos: 저장할 todos
            backup: 기존 파일 백업 여부

        Returns:
            성공 여부
        """
        todos_file = self._get_todos_file(session_id)

        try:
            # 백업 (기존 파일이 있으면)
            if backup and todos_file.exists():
                backup_file = todos_file.with_suffix(
                    f".json.bak.{int(time.time())}"
                )
                todos_file.rename(backup_file)
                logger.info(f"Backup created: {backup_file}")

            # TodoItem을 dict로 변환 (JSON 호환 모드)
            # mode='json'을 사용하면 datetime이 자동으로 ISO format으로 변환됨
            todos_data = [todo.model_dump(mode='json') for todo in todos]

            # Metadata 추가
            data = {
                "session_id": session_id,
                "saved_at": datetime.now().isoformat(),
                "total_todos": len(todos),
                "todos": todos_data
            }

            # 파일 저장 (with locking)
            with open(todos_file, "w", encoding="utf-8") as f:
                # 파일 잠금
                if HAS_FCNTL or HAS_MSVCRT:
                    self._lock_file(f)

                try:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())  # 디스크에 강제 쓰기
                finally:
                    # 파일 잠금 해제
                    if HAS_FCNTL or HAS_MSVCRT:
                        self._unlock_file(f)

            logger.info(
                f"Todos saved: session={session_id}, "
                f"count={len(todos)}, path={todos_file}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save todos: {e}", exc_info=True)
            return False

    def load_todos(
        self,
        session_id: str,
        create_if_missing: bool = True
    ) -> Optional[List[TodoItem]]:
        """
        JSON 파일에서 todos 로드 (file locking 포함)

        Args:
            session_id: Session ID
            create_if_missing: 파일이 없으면 빈 리스트 반환 여부

        Returns:
            TodoItem 리스트 또는 None (실패 시)
        """
        todos_file = self._get_todos_file(session_id)

        # 파일이 없으면
        if not todos_file.exists():
            if create_if_missing:
                logger.info(f"Todos file not found, creating empty list: {todos_file}")
                return []
            else:
                logger.warning(f"Todos file not found: {todos_file}")
                return None

        try:
            # 파일 로드 (with locking)
            with open(todos_file, "r", encoding="utf-8") as f:
                # 파일 잠금 (읽기 잠금)
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                elif HAS_MSVCRT:
                    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

                try:
                    data = json.load(f)
                finally:
                    # 파일 잠금 해제
                    if HAS_FCNTL or HAS_MSVCRT:
                        self._unlock_file(f)

            # 검증
            if not isinstance(data, dict) or "todos" not in data:
                logger.error(f"Invalid todos file format: {todos_file}")
                return None

            # TodoItem으로 변환
            todos_data = data["todos"]
            todos = [TodoItem(**todo_dict) for todo_dict in todos_data]

            logger.info(
                f"Todos loaded: session={session_id}, "
                f"count={len(todos)}, saved_at={data.get('saved_at')}"
            )
            return todos

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse todos JSON: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Failed to load todos: {e}", exc_info=True)
            return None

    def delete_todos(self, session_id: str) -> bool:
        """
        Todos 파일 삭제

        Args:
            session_id: Session ID

        Returns:
            성공 여부
        """
        todos_file = self._get_todos_file(session_id)

        if not todos_file.exists():
            logger.warning(f"Todos file not found: {todos_file}")
            return False

        try:
            todos_file.unlink()
            logger.info(f"Todos deleted: {todos_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete todos: {e}", exc_info=True)
            return False

    def list_sessions(self) -> List[str]:
        """
        저장된 session ID 리스트 반환

        Returns:
            Session ID 리스트
        """
        try:
            sessions = []
            for session_path in self.base_path.iterdir():
                if session_path.is_dir():
                    todos_file = session_path / "todos.json"
                    if todos_file.exists():
                        sessions.append(session_path.name)

            logger.info(f"Found {len(sessions)} sessions with todos")
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}", exc_info=True)
            return []

    def cleanup_old_backups(
        self,
        session_id: str,
        keep_count: int = 5
    ) -> int:
        """
        오래된 백업 파일 정리

        Args:
            session_id: Session ID
            keep_count: 유지할 백업 개수

        Returns:
            삭제된 백업 파일 개수
        """
        session_path = self._get_session_path(session_id)

        try:
            # 백업 파일 찾기
            backup_files = sorted(
                session_path.glob("todos.json.bak.*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # 최신 N개 제외하고 삭제
            deleted_count = 0
            for backup_file in backup_files[keep_count:]:
                backup_file.unlink()
                deleted_count += 1

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} old backups "
                    f"for session {session_id}"
                )

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}", exc_info=True)
            return 0


# 글로벌 인스턴스 (싱글톤 패턴)
todo_store = TodoStore()
