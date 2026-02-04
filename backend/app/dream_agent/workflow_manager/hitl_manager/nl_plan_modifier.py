"""Natural Language Plan Modifier

자연어 입력으로 계획 수정을 처리하는 핵심 모듈

사용자 입력 예시:
- "2번 데이터 수집은 건너뛰고 바로 분석으로 가줘"
- "3번 todo를 1번으로 옮겨줘"
- "분석 단계 전에 데이터 정제 추가해줘"
- "전체 계획 취소하고 보고서만 만들어줘"
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import re
import logging

from ...models.plan import Plan
from ...models.todo import TodoItem
from .plan_editor import PlanEditor, PlanEdit, EditOperation, get_plan_editor

logger = logging.getLogger(__name__)


class ModificationDecision(str, Enum):
    """수정 결정"""
    MAINTAIN = "maintain"           # 기존 계획 유지
    MODIFY = "modify"               # 계획 수정
    NEED_CLARIFICATION = "need_clarification"  # 추가 정보 필요


@dataclass
class ModificationAnalysis:
    """LLM 분석 결과"""
    decision: ModificationDecision
    reason: str
    proposed_edits: List[Dict[str, Any]]  # PlanEdit으로 변환될 데이터
    clarification_question: Optional[str] = None  # 추가 질문
    confidence: float = 1.0  # 분석 신뢰도 (0.0 ~ 1.0)


@dataclass
class ModificationResult:
    """수정 결과"""
    success: bool
    decision: ModificationDecision
    message: str
    applied_edits: List[Dict[str, Any]]
    plan_version: int
    history_entry: Optional[Dict[str, Any]] = None


class NLPlanModifier:
    """
    자연어 기반 계획 수정기

    LLM을 사용하여 사용자의 자연어 요청을 분석하고,
    적절한 계획 수정을 제안/적용합니다.
    """

    # LLM 분석 프롬프트
    ANALYSIS_SYSTEM_PROMPT = '''당신은 작업 계획 수정 분석가입니다.
사용자의 자연어 요청을 분석하여 계획 수정 여부를 결정하세요.

## 분석 지침

1. 사용자의 의도를 정확히 파악하세요
2. 요청이 현재 계획에서 실행 가능한지 판단하세요
3. 결정을 내리세요:
   - **maintain**: 요청이 부적절하거나, 이미 반영되어 있거나, 변경이 불필요한 경우
   - **modify**: 계획 수정이 필요한 경우
   - **need_clarification**: 추가 정보가 필요한 경우

## 수정 작업 유형

- **add**: 새 todo 추가
- **update**: todo 내용/상태 수정
- **delete**: todo 삭제
- **reorder**: todo 순서 변경
- **skip**: todo 건너뛰기 (상태를 skipped로 변경)

## 출력 형식 (JSON)

반드시 다음 JSON 형식으로만 응답하세요:

{
    "decision": "maintain" | "modify" | "need_clarification",
    "reason": "결정 이유를 한국어로 설명",
    "confidence": 0.0 ~ 1.0,
    "proposed_edits": [
        {
            "operation": "add" | "update" | "delete" | "reorder" | "skip",
            "todo_id": "대상 todo ID (update/delete/reorder/skip 시 필수)",
            "data": {
                "task": "작업 설명 (add/update 시)",
                "layer": "ml_execution | biz_execution (add 시)",
                "tool": "도구명 (add 시)",
                "status": "상태 (update 시)",
                "depends_on": ["의존 ID 목록"]
            },
            "position": 0 (add/reorder 시 위치)
        }
    ],
    "clarification_question": "추가 질문 (need_clarification 시)"
}

JSON만 출력하세요. 다른 텍스트 없이 JSON 객체만 반환하세요.'''

    ANALYSIS_USER_TEMPLATE = '''## 현재 계획

{current_plan}

## 사용자 요청

"{user_input}"

위 요청을 분석하고 JSON으로 응답하세요.'''

    def __init__(self, llm_client, session_id: str):
        """
        Args:
            llm_client: LLMClient 인스턴스
            session_id: 세션 ID
        """
        self.llm_client = llm_client
        self.session_id = session_id
        self.plan_editor = get_plan_editor(session_id)
        self._history: List[Dict[str, Any]] = []
        self._created_at = datetime.now()

    async def process_natural_language_request(
        self,
        user_input: str,
        plan_obj: Plan,
        state: Optional[Dict[str, Any]] = None
    ) -> ModificationResult:
        """
        자연어 요청 처리

        Args:
            user_input: 사용자 자연어 입력
            plan_obj: 현재 Plan 객체
            state: 현재 AgentState (optional, 추가 컨텍스트용)

        Returns:
            ModificationResult
        """
        logger.info(f"[NLPlanModifier] Processing request: {user_input[:50]}...")

        # 1. 현재 계획 포맷팅
        current_plan_str = self._format_plan_for_llm(plan_obj)

        # 2. LLM 분석
        analysis = await self._analyze_with_llm(
            user_input,
            current_plan_str
        )

        # 3. 결정에 따른 처리
        if analysis.decision == ModificationDecision.MAINTAIN:
            history_entry = self._create_history_entry(
                user_input, analysis, []
            )
            self._history.append(history_entry)

            return ModificationResult(
                success=True,
                decision=ModificationDecision.MAINTAIN,
                message=analysis.reason,
                applied_edits=[],
                plan_version=plan_obj.current_version,
                history_entry=history_entry
            )

        elif analysis.decision == ModificationDecision.NEED_CLARIFICATION:
            history_entry = self._create_history_entry(
                user_input, analysis, []
            )
            self._history.append(history_entry)

            return ModificationResult(
                success=False,
                decision=ModificationDecision.NEED_CLARIFICATION,
                message=analysis.clarification_question or "추가 정보가 필요합니다",
                applied_edits=[],
                plan_version=plan_obj.current_version,
                history_entry=history_entry
            )

        elif analysis.decision == ModificationDecision.MODIFY:
            # PlanEdit 리스트로 변환
            edits = self._convert_to_plan_edits(analysis.proposed_edits, plan_obj)

            if not edits:
                return ModificationResult(
                    success=False,
                    decision=ModificationDecision.MODIFY,
                    message="수정 사항을 변환할 수 없습니다",
                    applied_edits=[],
                    plan_version=plan_obj.current_version
                )

            # 편집 적용
            updated_plan, state_update = await self.plan_editor.apply_edits(
                plan_obj, edits, actor="nl_modifier"
            )

            # 히스토리 기록
            history_entry = self._create_history_entry(
                user_input, analysis, [e.to_dict() for e in edits]
            )
            self._history.append(history_entry)

            logger.info(
                f"[NLPlanModifier] Applied {len(edits)} edits, "
                f"plan version: {updated_plan.current_version}"
            )

            return ModificationResult(
                success=True,
                decision=ModificationDecision.MODIFY,
                message=analysis.reason,
                applied_edits=analysis.proposed_edits,
                plan_version=updated_plan.current_version,
                history_entry=history_entry
            )

        # 알 수 없는 결정
        return ModificationResult(
            success=False,
            decision=ModificationDecision.MAINTAIN,
            message="처리할 수 없는 요청입니다",
            applied_edits=[],
            plan_version=plan_obj.current_version
        )

    async def _analyze_with_llm(
        self,
        user_input: str,
        current_plan_str: str
    ) -> ModificationAnalysis:
        """LLM으로 분석"""
        user_message = self.ANALYSIS_USER_TEMPLATE.format(
            current_plan=current_plan_str,
            user_input=user_input
        )

        try:
            response = await self.llm_client.chat_with_system(
                system_prompt=self.ANALYSIS_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.3,  # 낮은 temperature로 일관성 있는 분석
            )

            # JSON 파싱
            result = self._parse_llm_response(response)

            decision_str = result.get("decision", "maintain")
            try:
                decision = ModificationDecision(decision_str)
            except ValueError:
                decision = ModificationDecision.MAINTAIN

            return ModificationAnalysis(
                decision=decision,
                reason=result.get("reason", "분석 결과"),
                proposed_edits=result.get("proposed_edits", []),
                clarification_question=result.get("clarification_question"),
                confidence=result.get("confidence", 0.8)
            )

        except Exception as e:
            logger.error(f"[NLPlanModifier] LLM analysis failed: {e}")
            return ModificationAnalysis(
                decision=ModificationDecision.MAINTAIN,
                reason=f"분석 중 오류가 발생했습니다: {str(e)}",
                proposed_edits=[],
                confidence=0.0
            )

    def _format_plan_for_llm(self, plan_obj: Plan) -> str:
        """Plan을 LLM용 문자열로 포맷"""
        lines = ["## Todo 리스트", ""]

        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌",
            "skipped": "⏭️",
            "blocked": "🚫",
            "needs_approval": "👤",
            "cancelled": "🚷",
        }

        for i, todo in enumerate(plan_obj.todos, 1):
            # 상태 이모지
            status_str = str(todo.status.value) if hasattr(todo.status, 'value') else str(todo.status)
            emoji = status_emoji.get(status_str, "❓")

            # 의존성
            deps_str = ""
            if todo.metadata and todo.metadata.dependency:
                dep_ids = todo.metadata.dependency.depends_on
                if dep_ids:
                    deps_str = f" (의존: {', '.join(dep_ids[:3])})"
                    if len(dep_ids) > 3:
                        deps_str = deps_str[:-1] + f" 외 {len(dep_ids)-3}개)"

            # 도구
            tool_str = ""
            if todo.metadata and todo.metadata.execution and todo.metadata.execution.tool:
                tool_str = f" [도구: {todo.metadata.execution.tool}]"

            lines.append(
                f"{i}. [{todo.id}] {emoji} {todo.task}"
                f" - Layer: {todo.layer}{tool_str}{deps_str}"
            )

        # 통계 추가
        lines.append("")
        lines.append("## 통계")
        stats = plan_obj.get_todo_statistics()
        lines.append(f"- 전체: {stats.get('total', 0)}개")
        lines.append(f"- 대기: {stats.get('pending', 0)}개")
        lines.append(f"- 진행중: {stats.get('in_progress', 0)}개")
        lines.append(f"- 완료: {stats.get('completed', 0)}개")

        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """LLM 응답 파싱"""
        # 1. JSON 블록 추출 (```json ... ```)
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 2. 직접 JSON 파싱 시도
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 3. 중괄호 추출
        brace_match = re.search(r'\{[\s\S]*\}', response)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        # 4. 파싱 실패
        logger.warning(f"[NLPlanModifier] Could not parse LLM response: {response[:200]}")
        raise ValueError("Could not parse LLM response as JSON")

    def _convert_to_plan_edits(
        self,
        proposed_edits: List[Dict[str, Any]],
        plan_obj: Plan
    ) -> List[PlanEdit]:
        """제안된 편집을 PlanEdit으로 변환"""
        edits = []

        for edit in proposed_edits:
            operation = edit.get("operation", "").lower()
            todo_id = edit.get("todo_id")
            data = edit.get("data", {})
            position = edit.get("position")

            # todo_id가 인덱스일 수 있음 (예: "2번" -> index 1)
            if todo_id and todo_id.isdigit():
                idx = int(todo_id) - 1
                if 0 <= idx < len(plan_obj.todos):
                    todo_id = plan_obj.todos[idx].id

            try:
                if operation == "skip":
                    # skip은 status를 skipped로 변경
                    edits.append(PlanEdit(
                        operation=EditOperation.SKIP,
                        todo_id=todo_id,
                    ))

                elif operation == "add":
                    edits.append(PlanEdit(
                        operation=EditOperation.ADD,
                        data=data,
                        position=position
                    ))

                elif operation == "update":
                    edits.append(PlanEdit(
                        operation=EditOperation.UPDATE,
                        todo_id=todo_id,
                        data=data
                    ))

                elif operation == "delete":
                    edits.append(PlanEdit(
                        operation=EditOperation.DELETE,
                        todo_id=todo_id
                    ))

                elif operation == "reorder":
                    edits.append(PlanEdit(
                        operation=EditOperation.REORDER,
                        todo_id=todo_id,
                        position=position or 0
                    ))

                else:
                    logger.warning(f"[NLPlanModifier] Unknown operation: {operation}")

            except Exception as e:
                logger.error(f"[NLPlanModifier] Failed to convert edit: {e}")

        return edits

    def _create_history_entry(
        self,
        user_input: str,
        analysis: ModificationAnalysis,
        applied_edits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """히스토리 엔트리 생성"""
        return {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "decision": analysis.decision.value,
            "reason": analysis.reason,
            "confidence": analysis.confidence,
            "proposed_edits": analysis.proposed_edits,
            "applied_edits": applied_edits,
            "clarification_question": analysis.clarification_question,
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """수정 히스토리 반환"""
        return self._history.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Modifier 요약 정보"""
        decisions = {}
        for entry in self._history:
            dec = entry.get("decision", "unknown")
            decisions[dec] = decisions.get(dec, 0) + 1

        return {
            "session_id": self.session_id,
            "created_at": self._created_at.isoformat(),
            "total_requests": len(self._history),
            "decisions_summary": decisions,
        }


# ============================================================
# Session별 Modifier 관리
# ============================================================

_modifiers: Dict[str, NLPlanModifier] = {}


def get_nl_plan_modifier(session_id: str, llm_client=None) -> NLPlanModifier:
    """
    Session별 NLPlanModifier 반환

    Args:
        session_id: 세션 ID
        llm_client: LLMClient 인스턴스 (없으면 자동 생성)

    Returns:
        NLPlanModifier 인스턴스
    """
    if session_id not in _modifiers:
        if llm_client is None:
            from ...llm_manager.client import get_llm_client
            llm_client = get_llm_client()
        _modifiers[session_id] = NLPlanModifier(llm_client, session_id)
    return _modifiers[session_id]


def remove_nl_plan_modifier(session_id: str) -> bool:
    """
    NLPlanModifier 제거

    Args:
        session_id: 세션 ID

    Returns:
        제거 여부
    """
    if session_id in _modifiers:
        del _modifiers[session_id]
        return True
    return False


def get_all_modifiers() -> Dict[str, NLPlanModifier]:
    """모든 Modifier 반환"""
    return _modifiers.copy()
