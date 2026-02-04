"""WebSocket Callback - WebSocket 이벤트 발행"""

from datetime import datetime
from typing import Dict, Any
from fastapi import WebSocket


class WebSocketCallback:
    """WebSocket 이벤트 발행 콜백"""

    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id

    async def on_agent_start(self, user_input: str):
        """Agent 시작"""
        await self.websocket.send_json({
            "type": "agent_start",
            "session_id": self.session_id,
            "user_input": user_input,
            "timestamp": datetime.now().isoformat()
        })

    async def on_node_start(self, node_name: str, state: Dict[str, Any]):
        """노드 시작"""
        await self.websocket.send_json({
            "type": "node_start",
            "session_id": self.session_id,
            "node": node_name,
            "timestamp": datetime.now().isoformat(),
            "state_snapshot": {
                "current_layer": state.get("next_layer"),
                "todos_count": len(state.get("todos", [])),
                "pending_count": len([
                    t for t in state.get("todos", [])
                    if t.status == "pending"
                ])
            }
        })

    async def on_node_end(self, node_name: str):
        """노드 종료"""
        await self.websocket.send_json({
            "type": "node_end",
            "session_id": self.session_id,
            "node": node_name,
            "timestamp": datetime.now().isoformat()
        })

    async def on_todos_update(self, todos):
        """Todos 업데이트"""
        todos_data = [
            {
                "id": todo.id,
                "task": todo.task,
                "layer": todo.layer,
                "status": todo.status,
                "priority": todo.priority,
                "metadata": todo.metadata
            }
            for todo in todos
        ]
        await self.websocket.send_json({
            "type": "todo_update",
            "session_id": self.session_id,
            "todos": todos_data,
            "timestamp": datetime.now().isoformat()
        })

    async def on_plan_ready(self, plan: Dict[str, Any], todos):
        """계획 준비 완료 (승인 필요)"""
        todos_data = [
            {
                "id": todo.id,
                "task": todo.task,
                "layer": todo.layer,
                "priority": todo.priority,
                "metadata": todo.metadata
            }
            for todo in todos
        ]
        await self.websocket.send_json({
            "type": "plan_approval_required",
            "session_id": self.session_id,
            "plan": plan,
            "todos": todos_data,
            "message": "계획이 생성되었습니다. 승인하시겠습니까?",
            "timestamp": datetime.now().isoformat()
        })

    async def on_intent(self, intent: Dict[str, Any]):
        """의도 분석 완료"""
        await self.websocket.send_json({
            "type": "intent",
            "session_id": self.session_id,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })

    async def on_plan(self, plan: Dict[str, Any]):
        """계획 생성 완료"""
        await self.websocket.send_json({
            "type": "plan",
            "session_id": self.session_id,
            "plan": plan,
            "timestamp": datetime.now().isoformat()
        })

    async def on_ml_result(self, ml_result):
        """ML 결과"""
        if isinstance(ml_result, list) and ml_result:
            latest_result = ml_result[-1]
        else:
            latest_result = ml_result

        await self.websocket.send_json({
            "type": "result",
            "result_type": "ml_result",
            "session_id": self.session_id,
            "data": latest_result,
            "timestamp": datetime.now().isoformat()
        })

    async def on_biz_result(self, biz_result):
        """Biz 결과"""
        if isinstance(biz_result, list) and biz_result:
            latest_result = biz_result[-1]
        else:
            latest_result = biz_result

        await self.websocket.send_json({
            "type": "result",
            "result_type": "biz_result",
            "session_id": self.session_id,
            "data": latest_result,
            "timestamp": datetime.now().isoformat()
        })

    async def on_response(self, response: str):
        """최종 응답"""
        await self.websocket.send_json({
            "type": "response",
            "session_id": self.session_id,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

    async def on_error(self, error: str, error_type: str):
        """에러 발생"""
        await self.websocket.send_json({
            "type": "error",
            "session_id": self.session_id,
            "error": error,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        })

    async def on_agent_complete(self):
        """Agent 완료"""
        await self.websocket.send_json({
            "type": "agent_complete",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat()
        })

    # ============================================================
    # HITL Events (Phase 2)
    # ============================================================

    async def on_hitl_pause(self, reason: str, message: str = None):
        """
        HITL: 일시정지

        Args:
            reason: 일시정지 사유 (user_request, input_required, approval_required, error_recovery)
            message: 사용자에게 표시할 메시지
        """
        await self.websocket.send_json({
            "type": "hitl_pause",
            "session_id": self.session_id,
            "reason": reason,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_resume(self, previous_mode: str, pause_duration: float = None):
        """
        HITL: 실행 재개

        Args:
            previous_mode: 이전 모드 (paused, plan_edit, input_request, approval_wait)
            pause_duration: 일시정지 지속 시간 (초)
        """
        await self.websocket.send_json({
            "type": "hitl_resume",
            "session_id": self.session_id,
            "previous_mode": previous_mode,
            "pause_duration": pause_duration,
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_plan_edit_start(self):
        """HITL: 계획 편집 모드 시작"""
        await self.websocket.send_json({
            "type": "hitl_plan_edit_start",
            "session_id": self.session_id,
            "message": "계획 편집 모드가 시작되었습니다",
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_plan_edit_end(self, saved: bool, changes: Dict[str, Any] = None):
        """
        HITL: 계획 편집 모드 종료

        Args:
            saved: 저장 여부
            changes: 변경 내용 요약
        """
        await self.websocket.send_json({
            "type": "hitl_plan_edit_end",
            "session_id": self.session_id,
            "saved": saved,
            "changes": changes or {},
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_input_request(
        self,
        request_id: str,
        field_name: str,
        input_type: str,
        message: str,
        options: list = None,
        default_value: Any = None
    ):
        """
        HITL: 입력 요청

        Args:
            request_id: 요청 ID
            field_name: 필드명
            input_type: 입력 유형 (text, select, multi_select, number 등)
            message: 사용자에게 표시할 메시지
            options: 선택 옵션 (select 시)
            default_value: 기본값
        """
        await self.websocket.send_json({
            "type": "hitl_input_request",
            "session_id": self.session_id,
            "request_id": request_id,
            "field_name": field_name,
            "input_type": input_type,
            "message": message,
            "options": options or [],
            "default_value": default_value,
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_input_received(self, request_id: str, field_name: str, value: Any):
        """
        HITL: 입력 수신 완료

        Args:
            request_id: 요청 ID
            field_name: 필드명
            value: 입력값
        """
        await self.websocket.send_json({
            "type": "hitl_input_received",
            "session_id": self.session_id,
            "request_id": request_id,
            "field_name": field_name,
            "value": value,
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_input_timeout(self, request_id: str, field_name: str):
        """
        HITL: 입력 타임아웃

        Args:
            request_id: 요청 ID
            field_name: 필드명
        """
        await self.websocket.send_json({
            "type": "hitl_input_timeout",
            "session_id": self.session_id,
            "request_id": request_id,
            "field_name": field_name,
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_approval_request(
        self,
        approval_type: str,
        message: str,
        details: Dict[str, Any] = None
    ):
        """
        HITL: 승인 요청

        Args:
            approval_type: 승인 유형 (plan, cost, action 등)
            message: 사용자에게 표시할 메시지
            details: 상세 정보
        """
        await self.websocket.send_json({
            "type": "hitl_approval_request",
            "session_id": self.session_id,
            "approval_type": approval_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_approval_result(self, approved: bool, reason: str = None):
        """
        HITL: 승인 결과

        Args:
            approved: 승인 여부
            reason: 사유
        """
        await self.websocket.send_json({
            "type": "hitl_approval_result",
            "session_id": self.session_id,
            "approved": approved,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_decision_request(
        self,
        request_id: str,
        context: Dict[str, Any],
        options: list,
        message: str
    ):
        """
        HITL: 결정 요청 (에러 복구 등)

        Args:
            request_id: 요청 ID
            context: 결정 컨텍스트
            options: 선택 옵션
            message: 사용자에게 표시할 메시지
        """
        await self.websocket.send_json({
            "type": "hitl_decision_request",
            "session_id": self.session_id,
            "request_id": request_id,
            "context": context,
            "options": options,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_decision_result(self, request_id: str, action: str, data: Dict[str, Any] = None):
        """
        HITL: 결정 결과

        Args:
            request_id: 요청 ID
            action: 선택된 액션 (retry, skip, cancel, abort)
            data: 추가 데이터
        """
        await self.websocket.send_json({
            "type": "hitl_decision_result",
            "session_id": self.session_id,
            "request_id": request_id,
            "action": action,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_nl_plan_modify(
        self,
        user_input: str,
        decision: str,
        message: str,
        applied_edits: list = None
    ):
        """
        HITL: 자연어 계획 수정 결과

        Args:
            user_input: 사용자 입력
            decision: 결정 (maintain, modify, need_clarification)
            message: 결과 메시지
            applied_edits: 적용된 편집 목록
        """
        await self.websocket.send_json({
            "type": "hitl_nl_plan_modify",
            "session_id": self.session_id,
            "user_input": user_input,
            "decision": decision,
            "message": message,
            "applied_edits": applied_edits or [],
            "timestamp": datetime.now().isoformat()
        })

    async def on_hitl_mode_change(self, old_mode: str, new_mode: str, trigger: str):
        """
        HITL: 모드 변경

        Args:
            old_mode: 이전 모드
            new_mode: 새 모드
            trigger: 변경 트리거
        """
        await self.websocket.send_json({
            "type": "hitl_mode_change",
            "session_id": self.session_id,
            "old_mode": old_mode,
            "new_mode": new_mode,
            "trigger": trigger,
            "timestamp": datetime.now().isoformat()
        })
