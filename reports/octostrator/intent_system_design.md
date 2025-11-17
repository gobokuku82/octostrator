# Intent System Design for Multi-turn Conversations

## 1. Intent 분류 체계

### Primary Intents (주요 의도)
```python
class PrimaryIntent(Enum):
    CREATE = "create"        # 새로운 작업 생성 (코드, 문서, 설계 등)
    MODIFY = "modify"        # 기존 작업 수정
    QUERY = "query"          # 정보 조회/질문
    EXECUTE = "execute"      # 작업 실행
    CANCEL = "cancel"        # 작업 취소
    CLARIFY = "clarify"      # 이전 대화 명확화
    CONTINUE = "continue"    # 이전 작업 계속
    REVIEW = "review"        # 결과 검토
```

### Secondary Intents (세부 의도)
```python
class SecondaryIntent(Enum):
    # CREATE 하위
    CREATE_CODE = "create_code"
    CREATE_DOC = "create_doc"
    CREATE_TEST = "create_test"

    # MODIFY 하위
    MODIFY_TODO = "modify_todo"
    MODIFY_PRIORITY = "modify_priority"
    MODIFY_APPROACH = "modify_approach"

    # QUERY 하위
    QUERY_STATUS = "query_status"
    QUERY_PROGRESS = "query_progress"
    QUERY_HISTORY = "query_history"
```

## 2. Intent Detection System

```python
# backend/app/octostrator/services/intent_service.py
from typing import Dict, List, Optional, Tuple
from enum import Enum
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
import numpy as np

class IntentContext(BaseModel):
    """대화 컨텍스트 정보"""
    previous_intent: Optional[str] = None
    active_todos: List[str] = []
    conversation_turns: int = 0
    last_user_message: Optional[str] = None
    last_assistant_response: Optional[str] = None
    current_graph_state: Optional[Dict] = None

class DetectedIntent(BaseModel):
    """감지된 의도"""
    primary: str
    secondary: Optional[str] = None
    confidence: float
    entities: Dict[str, any] = {}
    requires_context: bool = False
    suggested_action: str

class IntentDetector:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.intent_history: List[DetectedIntent] = []

    async def detect_intent(
        self,
        user_message: str,
        context: IntentContext
    ) -> DetectedIntent:
        """사용자 메시지에서 의도 감지"""

        # 1. 컨텍스트 기반 의도 추론
        if self._is_continuation(user_message, context):
            return self._handle_continuation(context)

        # 2. LLM 기반 의도 분류
        prompt = f"""
        Analyze the user's intent from their message in a multi-turn conversation.

        Current Context:
        - Previous Intent: {context.previous_intent}
        - Active TODOs: {context.active_todos}
        - Conversation Turn: {context.conversation_turns}
        - Last Exchange:
          User: {context.last_user_message}
          Assistant: {context.last_assistant_response}

        New User Message: "{user_message}"

        Classify the intent as:
        1. Primary Intent: {[e.value for e in PrimaryIntent]}
        2. Secondary Intent (if applicable)
        3. Confidence (0-1)
        4. Entities (key information extracted)
        5. Whether this requires previous context
        6. Suggested action

        Return as JSON.
        """

        response = await self.llm.ainvoke(prompt)
        intent_data = self._parse_llm_response(response)

        # 3. 컨텍스트 보정
        intent = self._adjust_for_context(intent_data, context)

        # 4. 히스토리 업데이트
        self.intent_history.append(intent)

        return intent

    def _is_continuation(self, message: str, context: IntentContext) -> bool:
        """이전 대화의 연속인지 판단"""
        continuation_phrases = [
            "그리고", "또한", "추가로", "그 다음",
            "아니", "잠깐", "수정해서", "다시",
            "그런데", "그보다", "그것 말고"
        ]

        # 짧은 메시지 + 이전 대화 존재
        if len(message.split()) < 5 and context.previous_intent:
            return True

        # 연속성 표현 포함
        return any(phrase in message for phrase in continuation_phrases)

    def _handle_continuation(self, context: IntentContext) -> DetectedIntent:
        """연속 대화 처리"""
        if "수정" in context.last_user_message or "변경" in context.last_user_message:
            return DetectedIntent(
                primary=PrimaryIntent.MODIFY.value,
                confidence=0.9,
                requires_context=True,
                suggested_action="modify_previous"
            )

        return DetectedIntent(
            primary=PrimaryIntent.CONTINUE.value,
            confidence=0.85,
            requires_context=True,
            suggested_action="continue_previous"
        )

    def _adjust_for_context(
        self,
        intent: DetectedIntent,
        context: IntentContext
    ) -> DetectedIntent:
        """컨텍스트 기반 의도 보정"""

        # Active TODOs가 있고 수정 관련 키워드가 있으면 MODIFY로 변경
        if context.active_todos and self._has_modification_keywords(intent.entities):
            intent.primary = PrimaryIntent.MODIFY.value
            intent.secondary = "modify_todo"
            intent.confidence = min(intent.confidence * 1.2, 1.0)

        # 이전 의도가 CREATE였고 추가 정보를 제공하면 CLARIFY
        if context.previous_intent == "create" and intent.confidence < 0.7:
            intent.primary = PrimaryIntent.CLARIFY.value
            intent.requires_context = True

        return intent
```

## 3. Intent Router (의도 기반 라우팅)

```python
# backend/app/octostrator/graphs/intent_router.py
from langgraph.types import Command
from typing import Dict, Literal

class IntentRouter:
    """Intent 기반 그래프 라우팅"""

    def __init__(self):
        self.intent_detector = IntentDetector()
        self.route_map = {
            PrimaryIntent.CREATE: "planner_node",
            PrimaryIntent.MODIFY: "modifier_node",
            PrimaryIntent.QUERY: "query_handler_node",
            PrimaryIntent.EXECUTE: "executor_node",
            PrimaryIntent.CANCEL: "cancel_handler_node",
            PrimaryIntent.CLARIFY: "clarification_node",
            PrimaryIntent.CONTINUE: "continuation_node",
            PrimaryIntent.REVIEW: "review_node"
        }

    async def route(self, state: GraphState) -> Command:
        """Intent 기반 다음 노드 결정"""

        # 컨텍스트 구성
        context = IntentContext(
            previous_intent=state.get("previous_intent"),
            active_todos=[t.id for t in state.get("todos", [])],
            conversation_turns=len(state.get("messages", [])) // 2,
            last_user_message=state.get("messages", [])[-2].content if len(state.get("messages", [])) > 1 else None,
            last_assistant_response=state.get("messages", [])[-1].content if state.get("messages", []) else None,
            current_graph_state=state
        )

        # Intent 감지
        user_message = state["messages"][-1].content
        intent = await self.intent_detector.detect_intent(user_message, context)

        # State 업데이트 및 라우팅
        next_node = self.route_map.get(
            PrimaryIntent(intent.primary),
            "planner_node"
        )

        return Command(
            update={
                "detected_intent": intent.dict(),
                "previous_intent": intent.primary,
                "intent_confidence": intent.confidence
            },
            goto=next_node
        )
```

## 4. Context-Aware Nodes (컨텍스트 인식 노드)

```python
# backend/app/octostrator/graphs/context_nodes.py

class ContextAwareNodes:
    """멀티턴 대화를 위한 컨텍스트 인식 노드"""

    async def clarification_node(self, state: GraphState) -> GraphState:
        """명확화 요청 처리"""
        intent = state.get("detected_intent", {})

        # 이전 대화 컨텍스트 로드
        previous_context = await self._load_context(state["thread_id"])

        # 명확화된 정보로 이전 작업 업데이트
        if intent.get("entities", {}).get("clarification_type") == "additional_requirements":
            # 기존 TODO에 요구사항 추가
            updated_todos = self._update_todos_with_clarification(
                state["todos"],
                intent["entities"]["clarified_info"]
            )
            state["todos"] = updated_todos

        return state

    async def continuation_node(self, state: GraphState) -> GraphState:
        """이전 작업 계속 진행"""
        # 중단된 지점 찾기
        checkpoint = await self._get_last_checkpoint(state["thread_id"])

        # 중단 지점부터 재개
        state["resume_from"] = checkpoint.get("last_completed_todo_id")
        state["continuation_mode"] = True

        return state

    async def modifier_node(self, state: GraphState) -> GraphState:
        """TODO 수정 처리"""
        intent = state.get("detected_intent", {})
        modification_target = intent.get("entities", {}).get("target")

        if modification_target == "last_todo":
            # 마지막 TODO 수정
            if state["todos"]:
                state["todos"][-1] = await self._apply_modification(
                    state["todos"][-1],
                    intent["entities"].get("modification")
                )
        elif modification_target == "all_todos":
            # 모든 TODO 수정 (예: 우선순위 일괄 변경)
            state["todos"] = [
                await self._apply_modification(todo, intent["entities"].get("modification"))
                for todo in state["todos"]
            ]

        return state
```

## 5. Conversation State Management

```python
# backend/app/octostrator/managers/conversation_manager.py

class ConversationManager:
    """멀티턴 대화 상태 관리"""

    def __init__(self):
        self.redis_client = None
        self.context_window = 10  # 최근 10턴 유지

    async def save_turn(self, thread_id: str, turn_data: Dict):
        """대화 턴 저장"""
        key = f"conversation:{thread_id}:turns"

        # Redis List에 추가 (최근 N개만 유지)
        await self.redis_client.lpush(key, json.dumps(turn_data))
        await self.redis_client.ltrim(key, 0, self.context_window - 1)

        # Intent 히스토리 업데이트
        intent_key = f"conversation:{thread_id}:intents"
        await self.redis_client.lpush(
            intent_key,
            turn_data.get("detected_intent", {}).get("primary", "unknown")
        )

    async def get_conversation_context(self, thread_id: str) -> Dict:
        """대화 컨텍스트 조회"""
        turns_key = f"conversation:{thread_id}:turns"
        intents_key = f"conversation:{thread_id}:intents"

        # 최근 대화 턴
        turns = await self.redis_client.lrange(turns_key, 0, -1)
        turns = [json.loads(turn) for turn in turns]

        # Intent 패턴 분석
        intents = await self.redis_client.lrange(intents_key, 0, 4)
        intent_pattern = self._analyze_intent_pattern(intents)

        return {
            "recent_turns": turns,
            "intent_pattern": intent_pattern,
            "conversation_length": len(turns),
            "dominant_intent": self._get_dominant_intent(intents),
            "context_switches": self._count_context_switches(intents)
        }

    def _analyze_intent_pattern(self, intents: List[str]) -> str:
        """Intent 패턴 분석"""
        if len(intents) < 2:
            return "single_turn"

        # 패턴 감지
        if all(i == intents[0] for i in intents):
            return "repetitive"  # 같은 의도 반복
        elif intents == ["create", "clarify", "execute"]:
            return "standard_workflow"  # 표준 워크플로우
        elif "modify" in intents and "cancel" in intents:
            return "iterative_refinement"  # 반복적 수정

        return "mixed"
```

## 6. Intent-based Graph State

```python
# backend/app/octostrator/graphs/intent_state.py

class IntentAwareGraphState(TypedDict):
    """Intent 인식 그래프 상태"""
    # 기본 상태
    messages: Annotated[List[BaseMessage], add_messages]
    todos: List[TodoItem]

    # Intent 관련
    detected_intent: Optional[DetectedIntent]
    previous_intent: Optional[str]
    intent_history: List[str]
    intent_confidence: float

    # 멀티턴 컨텍스트
    conversation_turns: int
    context_switches: int
    requires_clarification: bool
    clarification_attempts: int

    # 대화 상태
    conversation_mode: Literal["new", "continuation", "clarification", "modification"]
    conversation_context: Dict[str, any]

    # 작업 컨텍스트
    active_task_context: Optional[Dict]
    suspended_tasks: List[Dict]

    # 메타데이터
    thread_id: str
    session_id: str
    user_id: str
```