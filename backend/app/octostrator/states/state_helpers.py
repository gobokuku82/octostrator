"""
StateHelper: State 조회 및 분석 유틸리티

State를 쉽게 조회하고 분석할 수 있는 헬퍼 함수 모음

Author: Specialist Agent Development Team
Date: 2025-11-06
Version: 1.0
"""
from typing import Dict, List, Optional, Any
from datetime import datetime


class StateHelpers:
    """State 조회 및 분석 헬퍼 클래스"""

    @staticmethod
    def get_action_at_step(state: Dict, step: int) -> Optional[Dict]:
        """특정 step의 작업 조회"""
        history = state.get("action_history", [])
        for action in history:
            if action.get("step") == step:
                return action
        return None

    @staticmethod
    def get_all_actions_summary(state: Dict) -> str:
        """모든 작업 내역 요약"""
        history = state.get("action_history", [])
        if not history:
            return "작업 내역이 없습니다."

        lines = ["=== 작업 내역 ==="]
        for action in history:
            step = action.get("step", "?")
            action_name = action.get("action", "unknown")
            timestamp = action.get("timestamp", "")
            duration = action.get("duration_ms", 0)

            # 시간 포맷 (HH:MM:SS)
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp

            lines.append(
                f"Step {step:2d} [{time_str}] {action_name:30s} ({duration}ms)"
            )

        return "\n".join(lines)

    @staticmethod
    def get_todo_status(state: Dict) -> Dict[str, Any]:
        """Todo 상태 통계"""
        todos = state.get("todos", [])

        total = len(todos)
        completed = sum(1 for t in todos if t.get("status") == "completed")
        failed = sum(1 for t in todos if t.get("status") == "failed")
        pending = sum(1 for t in todos if t.get("status") == "pending")
        in_progress = sum(1 for t in todos if t.get("status") == "in_progress")
        skipped = sum(1 for t in todos if t.get("status") == "skipped")

        progress = completed / total if total > 0 else 0.0

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "in_progress": in_progress,
            "skipped": skipped,
            "progress": progress
        }

    @staticmethod
    def get_plan_version(state: Dict, version: int) -> Optional[Dict]:
        """특정 버전의 Plan 조회"""
        plan_history = state.get("plan_history", [])
        for plan_entry in plan_history:
            if plan_entry.get("version") == version:
                return plan_entry
        return None

    @staticmethod
    def get_latest_plan(state: Dict) -> Optional[Dict]:
        """최신 Plan 조회"""
        plan_history = state.get("plan_history", [])
        if not plan_history:
            return None
        return plan_history[-1]

    @staticmethod
    def get_user_interaction_summary(state: Dict) -> List[str]:
        """사용자 개입 내역 요약"""
        interactions = state.get("user_interactions", [])
        if not interactions:
            return ["사용자 개입 내역이 없습니다."]

        summary = []
        for interaction in interactions:
            itype = interaction.get("type", "unknown")
            timestamp = interaction.get("timestamp", "")
            details = interaction.get("details", {})

            # 시간 포맷
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = timestamp

            if itype == "interrupt":
                summary.append(f"[{time_str}] 중단: {details.get('message', '')}")
            elif itype == "modify_todo":
                action = details.get("action", "")
                summary.append(f"[{time_str}] Todo {action}")
            elif itype == "resume":
                summary.append(f"[{time_str}] 재개")
            else:
                summary.append(f"[{time_str}] {itype}")

        return summary

    @staticmethod
    def get_execution_summary(state: Dict) -> Dict[str, Any]:
        """실행 상황 전체 요약"""
        # 세션 정보
        session_id = state.get("session_id", "unknown")
        created_at = state.get("created_at", "")
        total_steps = state.get("total_steps", len(state.get("action_history", [])))

        # 소요 시간 계산
        try:
            start = datetime.fromisoformat(created_at)
            now = datetime.now()
            duration = str(now - start).split('.')[0]  # HH:MM:SS
        except:
            duration = "unknown"

        # Todo 상태
        todo_status = StateHelpers.get_todo_status(state)

        # Plan 버전
        plan_history = state.get("plan_history", [])
        plan_version = len(plan_history)

        # 사용자 개입 횟수
        user_interactions = len(state.get("user_interactions", []))

        # 전체 상태 판단
        if state.get("error"):
            status = "error"
        elif state.get("requires_approval"):
            status = "waiting_human"
        elif todo_status["progress"] == 1.0:
            status = "completed"
        else:
            status = "in_progress"

        return {
            "session_id": session_id,
            "created_at": created_at,
            "duration": duration,
            "total_steps": total_steps,
            "todo_status": todo_status,
            "plan_version": plan_version,
            "user_interactions": user_interactions,
            "status": status
        }
