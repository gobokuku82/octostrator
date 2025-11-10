"""Checkpoint Strategy

Agent별 선택적 Checkpoint 전략 구현
각 Agent의 특성에 따라 Checkpoint 사용 여부와 저장 주기를 결정합니다.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)


class CheckpointMode(Enum):
    """Checkpoint 모드"""
    NONE = "none"  # Checkpoint 사용 안 함 (Stateless)
    MANUAL = "manual"  # 수동으로만 저장
    AUTO = "auto"  # 자동 저장 (매 노드 실행 후)
    PERIODIC = "periodic"  # 주기적 저장 (N초마다)
    ON_COMPLETE = "on_complete"  # 완료 시에만 저장


class CheckpointStrategy:
    """Checkpoint 전략 관리 클래스

    Agent별로 다른 Checkpoint 전략을 적용할 수 있습니다.
    """

    # Agent별 기본 전략 정의
    DEFAULT_STRATEGIES = {
        # 복잡한 작업을 하는 Agent는 AUTO
        "diet_agent": CheckpointMode.AUTO,
        "workout_agent": CheckpointMode.AUTO,
        "coaching_agent": CheckpointMode.AUTO,
        "payment_agent": CheckpointMode.AUTO,  # 결제는 반드시 상태 저장

        # 간단한 작업을 하는 Agent는 NONE
        "notification_agent": CheckpointMode.NONE,
        "reporting_agent": CheckpointMode.NONE,
        "summary_agent": CheckpointMode.NONE,

        # 스케줄 관련은 주기적 저장
        "schedule_agent": CheckpointMode.PERIODIC,
        "reminder_agent": CheckpointMode.PERIODIC,
    }

    def __init__(self, checkpointer_manager=None):
        """CheckpointStrategy 초기화

        Args:
            checkpointer_manager: CheckpointerManager 인스턴스
        """
        self.checkpointer_manager = checkpointer_manager
        self.strategies: Dict[str, CheckpointMode] = self.DEFAULT_STRATEGIES.copy()
        self.checkpointers: Dict[str, AsyncPostgresSaver] = {}
        self.last_checkpoint_times: Dict[str, datetime] = {}

        logger.info("[CheckpointStrategy] Initialized with default strategies")

    def set_strategy(self, agent_id: str, mode: CheckpointMode):
        """Agent의 Checkpoint 전략 설정

        Args:
            agent_id: Agent ID
            mode: Checkpoint 모드
        """
        self.strategies[agent_id] = mode
        logger.info(f"[CheckpointStrategy] Set {agent_id} strategy to {mode.value}")

    def get_strategy(self, agent_id: str) -> CheckpointMode:
        """Agent의 Checkpoint 전략 조회

        Args:
            agent_id: Agent ID

        Returns:
            Checkpoint 모드
        """
        # 등록된 전략이 없으면 Agent 이름으로 추론
        if agent_id not in self.strategies:
            # 기본적으로 복잡한 Agent는 AUTO, 단순한 Agent는 NONE
            if any(keyword in agent_id for keyword in ["diet", "workout", "coaching", "payment"]):
                return CheckpointMode.AUTO
            elif any(keyword in agent_id for keyword in ["notification", "reporting", "summary"]):
                return CheckpointMode.NONE
            elif any(keyword in agent_id for keyword in ["schedule", "reminder"]):
                return CheckpointMode.PERIODIC
            else:
                # 기본값: 중간 복잡도는 ON_COMPLETE
                return CheckpointMode.ON_COMPLETE

        return self.strategies[agent_id]

    def should_use_checkpoint(self, agent_id: str) -> bool:
        """Agent가 Checkpoint를 사용해야 하는지 확인

        Args:
            agent_id: Agent ID

        Returns:
            Checkpoint 사용 여부
        """
        strategy = self.get_strategy(agent_id)
        return strategy != CheckpointMode.NONE

    async def get_checkpointer(self, agent_id: str) -> Optional[AsyncPostgresSaver]:
        """Agent용 Checkpointer 가져오기

        Args:
            agent_id: Agent ID

        Returns:
            AsyncPostgresSaver 인스턴스 또는 None
        """
        # Checkpoint를 사용하지 않는 Agent
        if not self.should_use_checkpoint(agent_id):
            return None

        # 이미 생성된 checkpointer가 있으면 반환
        if agent_id in self.checkpointers:
            return self.checkpointers[agent_id]

        # CheckpointerManager를 통해 생성
        if self.checkpointer_manager:
            try:
                # service_agent의 CheckpointerManager 사용
                from app.service_agent.foundation.checkpointer import create_checkpointer
                checkpointer = await create_checkpointer()
                self.checkpointers[agent_id] = checkpointer
                logger.info(f"[CheckpointStrategy] Created checkpointer for {agent_id}")
                return checkpointer
            except ImportError:
                # octostrator의 CheckpointerManager 사용
                from app.octostrator.checkpointer.postgres_checkpointer import create_checkpointer
                checkpointer = await create_checkpointer()
                self.checkpointers[agent_id] = checkpointer
                logger.info(f"[CheckpointStrategy] Created checkpointer for {agent_id}")
                return checkpointer

        logger.warning(f"[CheckpointStrategy] No checkpointer manager available for {agent_id}")
        return None

    def should_save_checkpoint(
        self,
        agent_id: str,
        node_name: str,
        elapsed_seconds: Optional[float] = None
    ) -> bool:
        """현재 시점에 Checkpoint를 저장해야 하는지 판단

        Args:
            agent_id: Agent ID
            node_name: 현재 실행 중인 노드 이름
            elapsed_seconds: 경과 시간 (초)

        Returns:
            저장 여부
        """
        strategy = self.get_strategy(agent_id)

        # 전략별 판단
        if strategy == CheckpointMode.NONE:
            return False

        elif strategy == CheckpointMode.AUTO:
            # 모든 노드 실행 후 자동 저장
            return True

        elif strategy == CheckpointMode.MANUAL:
            # 수동 저장만 허용
            return False

        elif strategy == CheckpointMode.ON_COMPLETE:
            # 완료 노드에서만 저장
            return node_name in ["complete", "final", "end", "output"]

        elif strategy == CheckpointMode.PERIODIC:
            # 주기적 저장 (기본 30초)
            if agent_id not in self.last_checkpoint_times:
                self.last_checkpoint_times[agent_id] = datetime.now()
                return True

            last_time = self.last_checkpoint_times[agent_id]
            current_time = datetime.now()

            # 30초 이상 경과했으면 저장
            if (current_time - last_time) > timedelta(seconds=30):
                self.last_checkpoint_times[agent_id] = current_time
                return True

            return False

        return False

    def get_thread_id(self, session_id: str, agent_id: str) -> str:
        """Agent용 thread_id 생성

        Args:
            session_id: 세션 ID
            agent_id: Agent ID

        Returns:
            thread_id
        """
        strategy = self.get_strategy(agent_id)

        if strategy == CheckpointMode.NONE:
            # Stateless Agent는 thread_id 불필요
            return f"{session_id}_stateless"

        # Checkpoint를 사용하는 Agent는 고유 thread_id
        return f"{session_id}_{agent_id}"

    def estimate_checkpoint_size(self, agent_id: str, state_size: int) -> Dict[str, Any]:
        """Checkpoint 크기 추정 및 최적화 제안

        Args:
            agent_id: Agent ID
            state_size: State 크기 (bytes)

        Returns:
            추정 정보와 최적화 제안
        """
        strategy = self.get_strategy(agent_id)

        # 크기별 권장 전략
        if state_size < 1024:  # 1KB 미만
            recommended = CheckpointMode.AUTO
            reason = "Small state size, auto-checkpoint is efficient"
        elif state_size < 10240:  # 10KB 미만
            recommended = CheckpointMode.ON_COMPLETE
            reason = "Medium state size, save on completion"
        elif state_size < 102400:  # 100KB 미만
            recommended = CheckpointMode.PERIODIC
            reason = "Large state size, periodic saves recommended"
        else:  # 100KB 이상
            recommended = CheckpointMode.MANUAL
            reason = "Very large state, manual checkpoint control needed"

        return {
            "agent_id": agent_id,
            "state_size_bytes": state_size,
            "state_size_readable": self._format_bytes(state_size),
            "current_strategy": strategy.value,
            "recommended_strategy": recommended.value,
            "recommendation_reason": reason,
            "estimated_save_time_ms": state_size / 1024 * 5,  # 약 5ms per KB
        }

    @staticmethod
    def _format_bytes(size: int) -> str:
        """바이트를 읽기 쉬운 형식으로 변환

        Args:
            size: 바이트 크기

        Returns:
            포맷된 문자열
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def get_statistics(self) -> Dict[str, Any]:
        """Checkpoint 전략 통계

        Returns:
            통계 정보
        """
        stats = {
            "total_strategies": len(self.strategies),
            "by_mode": {},
            "active_checkpointers": len(self.checkpointers),
        }

        # 모드별 집계
        for mode in CheckpointMode:
            count = sum(1 for s in self.strategies.values() if s == mode)
            if count > 0:
                stats["by_mode"][mode.value] = count

        # Checkpoint 사용 Agent 목록
        checkpoint_agents = [
            agent_id for agent_id, mode in self.strategies.items()
            if mode != CheckpointMode.NONE
        ]
        stats["checkpoint_enabled_agents"] = checkpoint_agents

        # Stateless Agent 목록
        stateless_agents = [
            agent_id for agent_id, mode in self.strategies.items()
            if mode == CheckpointMode.NONE
        ]
        stats["stateless_agents"] = stateless_agents

        return stats

    async def cleanup(self):
        """리소스 정리"""
        # 모든 checkpointer 정리
        if self.checkpointer_manager:
            # CheckpointerManager가 있으면 위임
            logger.info("[CheckpointStrategy] Delegating cleanup to CheckpointerManager")
        else:
            # 직접 정리
            for agent_id in list(self.checkpointers.keys()):
                logger.info(f"[CheckpointStrategy] Cleanup checkpointer for {agent_id}")
                del self.checkpointers[agent_id]

        self.last_checkpoint_times.clear()
        logger.info("[CheckpointStrategy] Cleanup completed")


# 전역 CheckpointStrategy 인스턴스
_checkpoint_strategy: Optional[CheckpointStrategy] = None


def get_checkpoint_strategy() -> CheckpointStrategy:
    """CheckpointStrategy 싱글톤 인스턴스 가져오기

    Returns:
        CheckpointStrategy 인스턴스
    """
    global _checkpoint_strategy

    if _checkpoint_strategy is None:
        _checkpoint_strategy = CheckpointStrategy()

    return _checkpoint_strategy