"""PostgreSQL Checkpointer

Phase 4.1: AsyncPostgresSaver 초기화 및 관리
CheckpointerManager 패턴을 사용하여 연결 생명주기 관리
"""
import os
from typing import Optional, Dict
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


class CheckpointerManager:
    """AsyncPostgresSaver 연결 생명주기 관리

    Context manager와 checkpointer 인스턴스를 모두 캐싱하여
    연결이 닫히지 않도록 유지합니다.
    """

    def __init__(self):
        """CheckpointerManager 초기화"""
        self._checkpointers: Dict[str, AsyncPostgresSaver] = {}
        self._context_managers: Dict[str, object] = {}

    async def create_checkpointer(
        self,
        conn_string: Optional[str] = None
    ) -> AsyncPostgresSaver:
        """AsyncPostgresSaver 인스턴스 생성 및 캐싱

        Args:
            conn_string: PostgreSQL 연결 문자열. None이면 POSTGRES_URL 환경변수 사용

        Returns:
            AsyncPostgresSaver: 초기화된 checkpointer 인스턴스

        Raises:
            ValueError: POSTGRES_URL이 설정되지 않은 경우
        """
        # 연결 문자열 가져오기
        if conn_string is None:
            conn_string = os.getenv("POSTGRES_URL")

        if not conn_string:
            raise ValueError(
                "POSTGRES_URL 환경 변수가 설정되지 않았습니다. "
                ".env 파일을 확인하세요."
            )

        # 이미 캐시된 checkpointer가 있으면 반환
        if conn_string in self._checkpointers:
            print(f"[CheckpointerManager] ✓ 캐시된 Checkpointer 반환: {conn_string}")
            return self._checkpointers[conn_string]

        print(f"[CheckpointerManager] 새 Checkpointer 생성 중: {conn_string}")

        # AsyncPostgresSaver.from_conn_string()은 async context manager를 반환
        # 연결을 유지하려면 context manager를 명시적으로 enter하고 캐싱해야 함
        context_manager = AsyncPostgresSaver.from_conn_string(conn_string)

        # Async context manager에 진입
        actual_checkpointer = await context_manager.__aenter__()

        # PostgreSQL 테이블 생성
        print("[CheckpointerManager] Checkpoint 테이블 생성/확인 중...")
        await actual_checkpointer.setup()
        print("[CheckpointerManager] ✓ Checkpoint 테이블 생성/확인 완료")

        # 중요: checkpointer와 context manager를 모두 캐싱
        # context manager를 유지해야 연결이 닫히지 않음
        self._checkpointers[conn_string] = actual_checkpointer
        self._context_managers[conn_string] = context_manager

        print("[CheckpointerManager] ✓ Checkpointer 생성 및 캐싱 완료")

        return actual_checkpointer

    async def close_checkpointer(self, conn_string: Optional[str] = None):
        """특정 checkpointer와 연결을 닫기

        Args:
            conn_string: PostgreSQL 연결 문자열. None이면 POSTGRES_URL 환경변수 사용
        """
        if conn_string is None:
            conn_string = os.getenv("POSTGRES_URL")

        if not conn_string:
            return

        if conn_string in self._context_managers:
            context_manager = self._context_managers[conn_string]

            # Context manager 정상 종료
            await context_manager.__aexit__(None, None, None)

            # 캐시에서 제거
            self._context_managers.pop(conn_string, None)
            self._checkpointers.pop(conn_string, None)

            print(f"[CheckpointerManager] ✓ Checkpointer 연결 종료: {conn_string}")

    async def close_all(self):
        """모든 checkpointer 연결 닫기"""
        print("[CheckpointerManager] 모든 Checkpointer 연결 종료 중...")

        # 모든 context manager 종료
        for conn_string, context_manager in list(self._context_managers.items()):
            try:
                await context_manager.__aexit__(None, None, None)
                print(f"[CheckpointerManager] ✓ 연결 종료: {conn_string}")
            except Exception as e:
                print(f"[CheckpointerManager] ⚠ 연결 종료 실패: {conn_string} - {e}")

        # 캐시 초기화
        self._checkpointers.clear()
        self._context_managers.clear()

        print("[CheckpointerManager] ✓ 모든 연결 종료 완료")


# 전역 CheckpointerManager 인스턴스 (싱글톤)
_checkpointer_manager: Optional[CheckpointerManager] = None


def get_checkpointer_manager() -> CheckpointerManager:
    """CheckpointerManager 싱글톤 인스턴스 가져오기

    Returns:
        CheckpointerManager: CheckpointerManager 인스턴스
    """
    global _checkpointer_manager

    if _checkpointer_manager is None:
        _checkpointer_manager = CheckpointerManager()
        print("[CheckpointerManager] ✓ 새 CheckpointerManager 인스턴스 생성")

    return _checkpointer_manager


async def create_checkpointer(conn_string: Optional[str] = None) -> AsyncPostgresSaver:
    """Checkpointer 생성 (편의 함수)

    Args:
        conn_string: PostgreSQL 연결 문자열. None이면 POSTGRES_URL 환경변수 사용

    Returns:
        AsyncPostgresSaver: 초기화된 checkpointer 인스턴스
    """
    manager = get_checkpointer_manager()
    return await manager.create_checkpointer(conn_string)


async def setup_tables(conn_string: Optional[str] = None):
    """Checkpoint 테이블 생성 (편의 함수)

    create_checkpointer()를 호출하면 자동으로 setup()이 실행되므로
    이 함수는 명시적으로 테이블 생성만 원할 때 사용합니다.

    Args:
        conn_string: PostgreSQL 연결 문자열. None이면 POSTGRES_URL 환경변수 사용
    """
    # create_checkpointer()가 이미 setup()을 호출하므로
    # 단순히 create_checkpointer()를 호출하면 됨
    await create_checkpointer(conn_string)
    print("[Checkpointer] ✓ Checkpoint 테이블 설정 완료")


# 호환성을 위한 별칭
get_checkpointer = create_checkpointer
