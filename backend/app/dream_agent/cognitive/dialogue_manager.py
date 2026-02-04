"""Dialogue Manager - 멀티턴 대화 컨텍스트 관리

Phase 1: Cognitive Layer 고도화
Multi-turn 대화 히스토리, 컨텍스트 추적, Clarification 지원
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from backend.app.core.logging import get_logger, LogContext

logger = get_logger(__name__)


# ============================================================
# Dialogue Models
# ============================================================

class DialogueTurnType(str, Enum):
    """대화 턴 타입"""
    USER_INPUT = "user_input"
    AGENT_RESPONSE = "agent_response"
    CLARIFICATION_REQUEST = "clarification_request"
    CONFIRMATION_REQUEST = "confirmation_request"
    ERROR_MESSAGE = "error_message"


class DialogueTurn(BaseModel):
    """단일 대화 턴"""
    turn_id: str
    turn_type: DialogueTurnType
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Intent and entities (if applicable)
    intent: Optional[Dict[str, Any]] = None
    entities: Optional[Dict[str, Any]] = None


class DialogueContext(BaseModel):
    """대화 컨텍스트"""
    session_id: str
    user_id: Optional[str] = None
    turns: List[DialogueTurn] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Accumulated context
    accumulated_entities: Dict[str, Any] = Field(default_factory=dict)
    accumulated_intent: Optional[Dict[str, Any]] = None
    unresolved_entities: List[str] = Field(default_factory=list)

    # Dialogue state
    waiting_for_clarification: bool = False
    clarification_question: Optional[str] = None
    waiting_for_confirmation: bool = False
    confirmation_prompt: Optional[str] = None


class ClarificationQuestion(BaseModel):
    """명확화 질문"""
    question_id: str
    question: str
    entity_type: str
    options: Optional[List[str]] = None
    allow_custom: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Dialogue Manager
# ============================================================

class DialogueManager:
    """멀티턴 대화 컨텍스트 관리자"""

    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.context = DialogueContext(
            session_id=session_id,
            user_id=user_id
        )
        self.log = LogContext(logger, node="DialogueManager", session_id=session_id)

        self.log.info(f"DialogueManager initialized for session: {session_id}")

    def add_user_turn(
        self,
        user_input: str,
        intent: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None
    ) -> DialogueTurn:
        """사용자 입력 턴 추가"""

        turn = DialogueTurn(
            turn_id=f"user_{len(self.context.turns) + 1}",
            turn_type=DialogueTurnType.USER_INPUT,
            content=user_input,
            intent=intent,
            entities=entities
        )

        self.context.turns.append(turn)
        self.context.updated_at = datetime.now().isoformat()

        # Update accumulated context
        if intent:
            self.context.accumulated_intent = self._merge_intent(
                self.context.accumulated_intent,
                intent
            )

        if entities:
            self.context.accumulated_entities = self._merge_entities(
                self.context.accumulated_entities,
                entities
            )

        self.log.debug(f"Added user turn: {user_input[:50]}...")

        return turn

    def add_agent_turn(
        self,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DialogueTurn:
        """에이전트 응답 턴 추가"""

        turn = DialogueTurn(
            turn_id=f"agent_{len(self.context.turns) + 1}",
            turn_type=DialogueTurnType.AGENT_RESPONSE,
            content=agent_response,
            metadata=metadata or {}
        )

        self.context.turns.append(turn)
        self.context.updated_at = datetime.now().isoformat()

        self.log.debug(f"Added agent turn: {agent_response[:50]}...")

        return turn

    def add_clarification_request(
        self,
        question: ClarificationQuestion
    ) -> DialogueTurn:
        """명확화 요청 턴 추가"""

        turn = DialogueTurn(
            turn_id=f"clarify_{len(self.context.turns) + 1}",
            turn_type=DialogueTurnType.CLARIFICATION_REQUEST,
            content=question.question,
            metadata={
                "question_id": question.question_id,
                "entity_type": question.entity_type,
                "options": question.options,
                "allow_custom": question.allow_custom
            }
        )

        self.context.turns.append(turn)
        self.context.waiting_for_clarification = True
        self.context.clarification_question = question.question
        self.context.updated_at = datetime.now().isoformat()

        self.log.info(f"Added clarification request: {question.entity_type}")

        return turn

    def add_confirmation_request(
        self,
        confirmation_prompt: str,
        data_to_confirm: Dict[str, Any]
    ) -> DialogueTurn:
        """확인 요청 턴 추가"""

        turn = DialogueTurn(
            turn_id=f"confirm_{len(self.context.turns) + 1}",
            turn_type=DialogueTurnType.CONFIRMATION_REQUEST,
            content=confirmation_prompt,
            metadata={"data_to_confirm": data_to_confirm}
        )

        self.context.turns.append(turn)
        self.context.waiting_for_confirmation = True
        self.context.confirmation_prompt = confirmation_prompt
        self.context.updated_at = datetime.now().isoformat()

        self.log.info("Added confirmation request")

        return turn

    def resolve_clarification(
        self,
        user_response: str,
        entity_type: str,
        normalized_value: Any
    ):
        """명확화 응답 처리"""

        self.context.waiting_for_clarification = False
        self.context.clarification_question = None

        # Update accumulated entities
        if entity_type not in self.context.accumulated_entities:
            self.context.accumulated_entities[entity_type] = []

        self.context.accumulated_entities[entity_type].append({
            "raw_value": user_response,
            "normalized_value": normalized_value,
            "resolved_at": datetime.now().isoformat()
        })

        # Remove from unresolved
        if entity_type in self.context.unresolved_entities:
            self.context.unresolved_entities.remove(entity_type)

        self.log.info(f"Clarification resolved for: {entity_type}")

    def resolve_confirmation(self, confirmed: bool):
        """확인 응답 처리"""

        self.context.waiting_for_confirmation = False
        self.context.confirmation_prompt = None

        self.log.info(f"Confirmation resolved: {confirmed}")

        return confirmed

    def get_recent_turns(self, n: int = 5) -> List[DialogueTurn]:
        """최근 N개 턴 가져오기"""
        return self.context.turns[-n:] if len(self.context.turns) > n else self.context.turns

    def get_conversation_summary(self) -> str:
        """대화 요약 생성"""

        if not self.context.turns:
            return "No conversation yet."

        summary_parts = []

        # Get last 3 user turns
        user_turns = [
            turn for turn in self.context.turns[-10:]
            if turn.turn_type == DialogueTurnType.USER_INPUT
        ]

        for turn in user_turns[-3:]:
            summary_parts.append(f"User: {turn.content}")

        return "\n".join(summary_parts)

    def check_intent_complete(self) -> tuple[bool, List[str]]:
        """
        Intent가 완전한지 확인

        Returns:
            (is_complete, missing_entities)
        """

        if not self.context.accumulated_intent:
            return False, []

        intent = self.context.accumulated_intent

        # Check required entities based on intent
        required_entities = self._get_required_entities_for_intent(intent)

        missing = []
        for entity_type in required_entities:
            if entity_type not in self.context.accumulated_entities:
                missing.append(entity_type)
            elif not self.context.accumulated_entities[entity_type]:
                missing.append(entity_type)

        is_complete = len(missing) == 0

        self.log.debug(
            f"Intent completeness check: {is_complete}, "
            f"missing: {missing if not is_complete else 'none'}"
        )

        return is_complete, missing

    def generate_clarification_questions(
        self,
        missing_entities: List[str]
    ) -> List[ClarificationQuestion]:
        """누락된 엔티티에 대한 명확화 질문 생성"""

        questions = []

        for entity_type in missing_entities:
            question = self._generate_question_for_entity(entity_type)
            if question:
                questions.append(question)

        return questions

    def _generate_question_for_entity(
        self,
        entity_type: str
    ) -> Optional[ClarificationQuestion]:
        """특정 엔티티에 대한 질문 생성"""

        question_templates = {
            "data_source": {
                "question": "어떤 데이터 소스에서 데이터를 수집할까요?",
                "options": ["Amazon", "Coupang", "Naver", "올리브영"],
                "allow_custom": True
            },
            "time_range": {
                "question": "어떤 기간의 데이터를 분석할까요?",
                "options": ["최근 7일", "최근 30일", "지난달", "직접 입력"],
                "allow_custom": True
            },
            "brand": {
                "question": "어떤 브랜드를 분석할까요?",
                "options": ["설화수", "라네즈", "헤라", "이니스프리"],
                "allow_custom": True
            },
            "output_format": {
                "question": "어떤 형식으로 결과를 받으시겠어요?",
                "options": ["PDF 리포트", "Excel 파일", "대시보드", "이메일"],
                "allow_custom": False
            },
            "metric": {
                "question": "어떤 지표를 분석할까요?",
                "options": ["매출", "조회수", "전환율", "클릭율"],
                "allow_custom": True
            }
        }

        template = question_templates.get(entity_type)
        if not template:
            return None

        return ClarificationQuestion(
            question_id=f"clarify_{entity_type}_{len(self.context.turns) + 1}",
            question=template["question"],
            entity_type=entity_type,
            options=template.get("options"),
            allow_custom=template.get("allow_custom", True)
        )

    def _merge_intent(
        self,
        accumulated: Optional[Dict[str, Any]],
        new_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Intent 병합"""

        if not accumulated:
            return new_intent

        # New intent has higher priority
        merged = accumulated.copy()
        merged.update(new_intent)

        # Increase confidence if consistent
        if accumulated.get("intent_type") == new_intent.get("intent_type"):
            old_confidence = accumulated.get("confidence", 0.5)
            new_confidence = new_intent.get("confidence", 0.5)
            merged["confidence"] = min((old_confidence + new_confidence) / 2 + 0.1, 1.0)

        return merged

    def _merge_entities(
        self,
        accumulated: Dict[str, Any],
        new_entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """엔티티 병합"""

        merged = accumulated.copy()

        for entity_type, entity_list in new_entities.items():
            if entity_type not in merged:
                merged[entity_type] = entity_list
            else:
                # Append new entities
                existing = merged[entity_type]
                if isinstance(existing, list):
                    # Deduplicate
                    existing_values = {
                        e.get("raw_value") if isinstance(e, dict) else e
                        for e in existing
                    }
                    for entity in entity_list:
                        entity_value = (
                            entity.get("raw_value") if isinstance(entity, dict) else entity
                        )
                        if entity_value not in existing_values:
                            existing.append(entity)
                else:
                    merged[entity_type] = entity_list

        return merged

    def _get_required_entities_for_intent(
        self,
        intent: Dict[str, Any]
    ) -> List[str]:
        """Intent에 필요한 필수 엔티티 목록 반환"""

        # Intent type에 따라 필요한 엔티티 결정
        intent_type = intent.get("intent_type", "")

        # Data analysis intents
        if "analysis" in intent_type or "data" in intent_type:
            return ["data_source", "time_range"]

        # Content creation intents
        elif "create" in intent_type or "video" in intent_type or "creative" in intent_type:
            return []  # Usually no required entities

        # Report generation
        elif "report" in intent_type:
            return ["output_format"]

        return []

    def get_context_for_llm(self) -> str:
        """LLM에 전달할 컨텍스트 문자열 생성"""

        parts = []

        # Recent conversation summary
        summary = self.get_conversation_summary()
        if summary and summary != "No conversation yet.":
            parts.append(f"Recent conversation:\n{summary}")

        # Accumulated intent
        if self.context.accumulated_intent:
            intent_str = json.dumps(
                self.context.accumulated_intent,
                ensure_ascii=False,
                indent=2
            )
            parts.append(f"\nAccumulated intent:\n{intent_str}")

        # Accumulated entities
        if self.context.accumulated_entities:
            entities_str = json.dumps(
                self.context.accumulated_entities,
                ensure_ascii=False,
                indent=2
            )
            parts.append(f"\nAccumulated entities:\n{entities_str}")

        # Unresolved entities
        if self.context.unresolved_entities:
            parts.append(f"\nUnresolved entities: {', '.join(self.context.unresolved_entities)}")

        return "\n".join(parts) if parts else ""

    def should_ask_for_clarification(self, intent_confidence: float) -> bool:
        """명확화 질문이 필요한지 판단"""

        # Low confidence - need clarification
        if intent_confidence < 0.7:
            return True

        # Check if essential entities are missing
        is_complete, missing = self.check_intent_complete()
        if not is_complete and len(missing) > 0:
            return True

        return False

    def should_ask_for_confirmation(self, intent_confidence: float) -> bool:
        """확인 요청이 필요한지 판단"""

        # Medium confidence - need confirmation
        if 0.7 <= intent_confidence < 0.85:
            return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """DialogueContext를 딕셔너리로 변환"""
        return self.context.dict()

    def from_dict(self, context_dict: Dict[str, Any]):
        """딕셔너리에서 DialogueContext 복원"""
        self.context = DialogueContext(**context_dict)
        self.log.info(f"DialogueContext restored: {len(self.context.turns)} turns")


# ============================================================
# Helper Functions
# ============================================================

def create_dialogue_manager(
    session_id: str,
    user_id: Optional[str] = None
) -> DialogueManager:
    """DialogueManager 생성 헬퍼"""
    return DialogueManager(session_id=session_id, user_id=user_id)


def format_clarification_for_user(
    question: ClarificationQuestion
) -> Dict[str, Any]:
    """사용자에게 보여줄 명확화 질문 포맷팅"""
    return {
        "type": "clarification",
        "question": question.question,
        "options": question.options,
        "allow_custom": question.allow_custom,
        "metadata": {
            "question_id": question.question_id,
            "entity_type": question.entity_type
        }
    }
