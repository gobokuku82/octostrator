# Intent Classification & Memory Architecture

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: Intent 분류 시스템과 메모리 기능 통합 설계

---

## 1. 문제 인식

### 1.1 현재 시스템의 한계

```python
# 현재: 단순 메시지 처리
async def planner_node(state: SupervisorState):
    messages = state["messages"]
    # 단순히 마지막 메시지만 보고 계획 수립
    last_message = messages[-1].content
    plan = create_plan(last_message)  # Context 없이 판단
```

**문제점:**
- "그거 좀 수정해줘" → 무엇을 수정?
- "지난번처럼 해줘" → 지난번이 뭐지?
- "취소해줘" → 무엇을 취소?
- "다시 해줘" → 어떤 작업을?

### 1.2 메모리 기능 추가 시 필수 요구사항

```
User: "다이어트 계획 만들어줘"
AI: "다이어트 계획을 생성했습니다..."

(1주일 후)
User: "지난번 계획 어땠지?"  ← Intent: RECALL_PREVIOUS
User: "그거 수정해줘"         ← Intent: MODIFY_EXISTING
User: "새로 만들어줘"         ← Intent: CREATE_NEW
```

---

## 2. Intent Classification System

### 2.1 Intent 계층 구조

```
Primary Intent (대분류)
├── CREATE (새로 생성)
│   ├── CREATE_DIET_PLAN
│   ├── CREATE_WORKOUT_PLAN
│   └── CREATE_SCHEDULE
├── MODIFY (수정)
│   ├── MODIFY_EXISTING_PLAN
│   ├── ADJUST_PARAMETERS
│   └── UPDATE_PREFERENCES
├── QUERY (조회)
│   ├── QUERY_CURRENT_STATUS
│   ├── QUERY_HISTORY
│   └── QUERY_PROGRESS
├── EXECUTE (실행)
│   ├── EXECUTE_ACTION
│   ├── CONTINUE_TASK
│   └── RETRY_FAILED
├── MANAGE (관리)
│   ├── CANCEL_TASK
│   ├── PAUSE_EXECUTION
│   └── RESET_SESSION
└── SOCIAL (대화)
    ├── GREETING
    ├── THANKS
    └── FEEDBACK
```

### 2.2 Intent Classifier 구현

```python
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re

class IntentType(Enum):
    # Primary Intents
    CREATE = "create"
    MODIFY = "modify"
    QUERY = "query"
    EXECUTE = "execute"
    MANAGE = "manage"
    SOCIAL = "social"
    UNKNOWN = "unknown"

class SubIntent(Enum):
    # CREATE sub-intents
    CREATE_DIET_PLAN = "create_diet_plan"
    CREATE_WORKOUT_PLAN = "create_workout_plan"
    CREATE_SCHEDULE = "create_schedule"

    # MODIFY sub-intents
    MODIFY_EXISTING = "modify_existing"
    ADJUST_PARAMETERS = "adjust_parameters"

    # QUERY sub-intents
    QUERY_STATUS = "query_status"
    QUERY_HISTORY = "query_history"
    QUERY_PROGRESS = "query_progress"

    # Context-dependent
    CONTINUE_PREVIOUS = "continue_previous"
    REFER_TO_CONTEXT = "refer_to_context"

class IntentClassifier:
    """사용자 의도 분류기"""

    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self.intent_patterns = self._build_patterns()

    def _build_patterns(self) -> Dict[IntentType, List[re.Pattern]]:
        """Intent 패턴 정의"""
        return {
            IntentType.CREATE: [
                re.compile(r"(만들|생성|작성|새로|신규)", re.IGNORECASE),
                re.compile(r"(create|make|new|generate)", re.IGNORECASE),
            ],
            IntentType.MODIFY: [
                re.compile(r"(수정|변경|바꿔|고쳐|조정)", re.IGNORECASE),
                re.compile(r"(modify|change|update|adjust|edit)", re.IGNORECASE),
            ],
            IntentType.QUERY: [
                re.compile(r"(보여|알려|확인|조회|어떻|뭐야|어디)", re.IGNORECASE),
                re.compile(r"(show|tell|check|what|where|how)", re.IGNORECASE),
            ],
            IntentType.MANAGE: [
                re.compile(r"(취소|중단|멈춰|그만|리셋)", re.IGNORECASE),
                re.compile(r"(cancel|stop|pause|reset|abort)", re.IGNORECASE),
            ],
        }

    async def classify(
        self,
        message: str,
        context: Optional[Dict] = None,
        history: Optional[List[BaseMessage]] = None
    ) -> Tuple[IntentType, SubIntent, Dict[str, Any]]:
        """
        사용자 메시지의 의도를 분류

        Returns:
            (Primary Intent, Sub Intent, Extracted Entities)
        """

        # 1. Context-aware classification
        if self._is_contextual_message(message):
            return await self._classify_with_context(message, context, history)

        # 2. Pattern-based classification
        primary_intent = self._classify_primary_intent(message)

        # 3. Sub-intent classification
        sub_intent = self._classify_sub_intent(message, primary_intent)

        # 4. Entity extraction
        entities = self._extract_entities(message, primary_intent)

        return primary_intent, sub_intent, entities

    def _is_contextual_message(self, message: str) -> bool:
        """문맥 의존적 메시지인지 확인"""
        contextual_keywords = [
            "그거", "그것", "이거", "이것", "저거", "저것",
            "그", "이", "저", "같은", "비슷한", "그대로",
            "다시", "또", "역시", "마저", "나머지",
            "it", "that", "this", "same", "again", "continue"
        ]
        return any(keyword in message.lower() for keyword in contextual_keywords)

    async def _classify_with_context(
        self,
        message: str,
        context: Dict,
        history: List[BaseMessage]
    ) -> Tuple[IntentType, SubIntent, Dict]:
        """컨텍스트를 활용한 의도 분류"""

        # Memory에서 이전 작업 조회
        if self.memory_manager:
            previous_task = await self.memory_manager.get_last_task()

            # "그거 수정해줘" → 이전 작업을 수정
            if "수정" in message or "modify" in message.lower():
                return (
                    IntentType.MODIFY,
                    SubIntent.MODIFY_EXISTING,
                    {"target": previous_task}
                )

            # "다시 해줘" → 이전 작업을 재실행
            elif "다시" in message or "again" in message.lower():
                return (
                    IntentType.EXECUTE,
                    SubIntent.CONTINUE_PREVIOUS,
                    {"target": previous_task}
                )

        return IntentType.UNKNOWN, None, {}
```

---

## 3. Memory Integration

### 3.1 Memory 구조

```python
class MemoryManager:
    """대화 및 작업 기록 관리"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.short_term_memory = []  # 현재 세션
        self.long_term_memory = {}   # 영구 저장
        self.working_memory = {}     # 작업 중 상태

    async def store_interaction(self, interaction: Dict):
        """상호작용 저장"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "user_message": interaction["user_message"],
            "intent": interaction["intent"],
            "agents_executed": interaction["agents"],
            "result": interaction["result"],
            "session_id": self.session_id
        }

        # Short-term memory (현재 세션)
        self.short_term_memory.append(record)

        # Long-term memory (PostgreSQL)
        await self._save_to_database(record)

    async def get_context(self, window_size: int = 5) -> List[Dict]:
        """최근 대화 컨텍스트 조회"""
        return self.short_term_memory[-window_size:]

    async def search_similar_tasks(self, query: str) -> List[Dict]:
        """유사한 이전 작업 검색"""
        # Vector similarity search in PostgreSQL
        # pgvector extension 활용
        pass
```

### 3.2 Memory-Aware Supervisor

```python
class EnhancedSupervisorState(TypedDict):
    # 기존 State
    messages: Sequence[BaseMessage]
    plan: List[dict]
    current_step: int

    # Intent & Memory 추가
    intent: Dict[str, Any]  # 분류된 의도
    context: Dict[str, Any]  # 대화 컨텍스트
    memory_refs: List[str]  # 참조 메모리 ID
    user_profile: Dict  # 사용자 프로필 (from memory)
```

---

## 4. 통합 아키텍처

### 4.1 전체 흐름

```
User Message
    │
    ▼
[Intent Classifier]
    │ ← Memory Context
    ├─ Primary Intent
    ├─ Sub Intent
    └─ Entities
    │
    ▼
[Context Builder]
    │ ← User Profile (from Memory)
    │ ← Previous Tasks (from Memory)
    │ ← Preferences (from Memory)
    │
    ▼
[Enhanced Supervisor]
    │
    ├─[Intent Router Node] ← NEW
    │   ├─ CREATE → Planner Node
    │   ├─ MODIFY → Modifier Node
    │   ├─ QUERY → Query Node
    │   └─ MANAGE → Manager Node
    │
    ├─[Memory Update Node] ← NEW
    │   └─ Store interaction
    │
    └─[Agent Execution]
        └─ With context & memory
```

### 4.2 Enhanced Supervisor Graph

```python
def build_enhanced_supervisor_graph(checkpointer, memory_manager):
    workflow = StateGraph(EnhancedSupervisorState)

    # Intent 분류 노드 (NEW)
    workflow.add_node("intent_classifier", intent_classifier_node)

    # Context 구축 노드 (NEW)
    workflow.add_node("context_builder", context_builder_node)

    # Intent별 처리 노드
    workflow.add_node("create_planner", create_planner_node)
    workflow.add_node("modify_planner", modify_planner_node)
    workflow.add_node("query_handler", query_handler_node)
    workflow.add_node("manage_handler", manage_handler_node)

    # 기존 노드
    workflow.add_node("agent_executor", agent_executor_node)
    workflow.add_node("aggregator", aggregator_node)

    # Memory 저장 노드 (NEW)
    workflow.add_node("memory_saver", memory_saver_node)

    # 엣지 정의
    workflow.add_edge(START, "intent_classifier")
    workflow.add_edge("intent_classifier", "context_builder")

    # Intent 기반 라우팅
    workflow.add_conditional_edges(
        "context_builder",
        route_by_intent,
        {
            "create": "create_planner",
            "modify": "modify_planner",
            "query": "query_handler",
            "manage": "manage_handler",
        }
    )

    # 실행 후 메모리 저장
    workflow.add_edge("aggregator", "memory_saver")
    workflow.add_edge("memory_saver", END)

    return workflow.compile(checkpointer=checkpointer)
```

---

## 5. Intent별 처리 예시

### 5.1 CREATE Intent

```python
async def create_planner_node(state: EnhancedSupervisorState):
    """새로운 작업 생성"""
    intent = state["intent"]

    # Sub-intent에 따른 처리
    if intent["sub_intent"] == SubIntent.CREATE_DIET_PLAN:
        # 이전 다이어트 계획 참조
        previous_plans = await memory_manager.search_similar_tasks("diet plan")

        plan = [
            {
                "agent": "diet_agent",
                "task": "create_plan",
                "context": {
                    "previous_plans": previous_plans,
                    "user_preferences": state["user_profile"]["preferences"]
                }
            }
        ]

    return {"plan": plan}
```

### 5.2 MODIFY Intent

```python
async def modify_planner_node(state: EnhancedSupervisorState):
    """기존 작업 수정"""
    intent = state["intent"]
    target = intent["entities"].get("target")

    if not target:
        # Memory에서 최근 작업 조회
        target = await memory_manager.get_last_task()

    # 수정할 Agent와 작업 결정
    if target["agent"] == "diet_agent":
        plan = [
            {
                "agent": "diet_agent",
                "task": "modify_plan",
                "context": {
                    "original_plan": target["result"],
                    "modification_request": state["messages"][-1].content
                }
            }
        ]

    return {"plan": plan}
```

### 5.3 QUERY Intent

```python
async def query_handler_node(state: EnhancedSupervisorState):
    """정보 조회"""
    intent = state["intent"]

    if intent["sub_intent"] == SubIntent.QUERY_HISTORY:
        # Memory에서 이력 조회
        history = await memory_manager.get_task_history(
            user_id=state["user_id"],
            limit=10
        )

        # 결과 직접 반환 (Agent 실행 불필요)
        return {
            "final_result": format_history(history),
            "skip_execution": True
        }

    elif intent["sub_intent"] == SubIntent.QUERY_PROGRESS:
        # 진행 상황 조회
        progress = await memory_manager.get_progress(
            task_id=intent["entities"].get("task_id")
        )

        return {
            "final_result": format_progress(progress),
            "skip_execution": True
        }
```

---

## 6. Context Resolution

### 6.1 대명사 해결 (Pronoun Resolution)

```python
class ContextResolver:
    """문맥 해결기"""

    async def resolve_references(
        self,
        message: str,
        history: List[BaseMessage],
        memory: MemoryManager
    ) -> str:
        """
        "그거", "이전 것" 등의 참조를 실제 대상으로 변환
        """

        # 대명사 매핑
        pronouns = {
            "그거": await self._find_last_mentioned_object(history),
            "이전": await memory.get_last_task(),
            "지난번": await memory.get_previous_session_task(),
        }

        # 메시지에서 대명사 치환
        resolved_message = message
        for pronoun, reference in pronouns.items():
            if pronoun in message and reference:
                resolved_message = resolved_message.replace(
                    pronoun,
                    f"[REF:{reference['id']}]"
                )

        return resolved_message
```

### 6.2 Implicit Intent Detection

```python
async def detect_implicit_intent(
    message: str,
    context: Dict
) -> Optional[IntentType]:
    """
    명시적이지 않은 의도 감지

    예: "배고파" → CREATE_DIET_PLAN
        "힘들어" → CREATE_WORKOUT_PLAN (easier)
        "좋았어" → POSITIVE_FEEDBACK
    """

    implicit_patterns = {
        "배고": IntentType.CREATE,  # 식단 관련
        "운동": IntentType.CREATE,  # 운동 관련
        "피곤": IntentType.MODIFY,  # 강도 조절
        "좋": IntentType.SOCIAL,    # 긍정 피드백
        "별로": IntentType.MODIFY,  # 부정 피드백
    }

    for pattern, intent in implicit_patterns.items():
        if pattern in message:
            return intent

    return None
```

---

## 7. Memory Schema

### 7.1 PostgreSQL Schema

```sql
-- 사용자 프로필
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,
    preferences JSONB,
    demographics JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 대화 기록
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255),
    user_id UUID REFERENCES user_profiles(user_id),
    timestamp TIMESTAMP,
    message_type VARCHAR(50),  -- user/assistant
    content TEXT,
    intent JSONB,
    metadata JSONB
);

-- 작업 기록
CREATE TABLE task_history (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255),
    user_id UUID REFERENCES user_profiles(user_id),
    agent_name VARCHAR(100),
    task_type VARCHAR(100),
    input JSONB,
    output JSONB,
    status VARCHAR(50),
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 벡터 임베딩 (유사도 검색용)
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    source_id UUID,  -- task_id or conversation_id
    source_type VARCHAR(50),
    embedding vector(1536),  -- OpenAI embedding size
    metadata JSONB
);

-- pgvector extension for similarity search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

### 7.2 Memory Access Patterns

```python
class MemoryAccessLayer:
    """메모리 접근 계층"""

    async def get_relevant_context(
        self,
        current_message: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        현재 메시지와 관련된 컨텍스트 조회
        """

        # 1. 임베딩 생성
        embedding = await self.create_embedding(current_message)

        # 2. 유사 작업 검색
        similar_tasks = await self.search_similar_embeddings(
            embedding,
            source_type="task",
            limit=limit
        )

        # 3. 최근 대화 조회
        recent_conversations = await self.get_recent_conversations(
            limit=limit
        )

        # 4. 사용자 프로필
        user_profile = await self.get_user_profile()

        return {
            "similar_tasks": similar_tasks,
            "recent_conversations": recent_conversations,
            "user_profile": user_profile,
            "timestamp": datetime.now().isoformat()
        }
```

---

## 8. 실제 적용 예시

### 8.1 첫 대화

```
User: "다이어트 계획 만들어줘"
System:
  1. Intent: CREATE / CREATE_DIET_PLAN
  2. Memory: No previous diet plans
  3. Execute: DietAgent.create_plan()
  4. Save: Task to memory
Response: "다이어트 계획을 생성했습니다..."
```

### 8.2 후속 대화 (컨텍스트 활용)

```
User: "운동도 추가해줘"
System:
  1. Intent: CREATE / CREATE_WORKOUT_PLAN
  2. Context: Previous diet plan exists
  3. Execute: WorkoutAgent.create_plan(diet_context)
  4. Save: Linked to diet plan
Response: "다이어트 계획에 맞는 운동을 추가했습니다..."

User: "그거 좀 쉽게 바꿔줘"
System:
  1. Intent: MODIFY / ADJUST_PARAMETERS
  2. Reference: "그거" → Last workout plan
  3. Execute: WorkoutAgent.modify_intensity(lower)
  4. Update: Memory with modification
Response: "운동 강도를 낮췄습니다..."

User: "지난주 계획 보여줘"
System:
  1. Intent: QUERY / QUERY_HISTORY
  2. Memory: Fetch last week's plans
  3. No agent execution needed
  4. Direct response from memory
Response: "지난주 계획입니다: ..."
```

---

## 9. 성능 고려사항

### 9.1 캐싱 전략

```python
class IntentCache:
    """Intent 분류 캐싱"""

    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl

    def get_cached_intent(self, message_hash: str):
        """캐시된 Intent 조회"""
        if message_hash in self.cache:
            entry = self.cache[message_hash]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["intent"]
        return None
```

### 9.2 Memory 최적화

```python
class MemoryOptimizer:
    """메모리 사용 최적화"""

    async def cleanup_old_sessions(self, days: int = 30):
        """오래된 세션 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        # Archive old sessions to cold storage
        # Delete from hot storage

    async def compact_embeddings(self):
        """임베딩 압축"""
        # Use dimensionality reduction
        # PCA or other techniques
```

---

## 10. 구현 로드맵

### Phase 1: Intent Classification (Day 1-3)
- [ ] IntentClassifier 구현
- [ ] Pattern-based classification
- [ ] Context-aware classification
- [ ] 테스트 케이스 작성

### Phase 2: Memory Integration (Day 4-7)
- [ ] MemoryManager 구현
- [ ] PostgreSQL schema 생성
- [ ] Embedding 시스템 구축
- [ ] Memory access layer

### Phase 3: Supervisor Enhancement (Day 8-10)
- [ ] Enhanced Supervisor State
- [ ] Intent routing 구현
- [ ] Context builder 구현
- [ ] Memory saver 구현

### Phase 4: Testing & Optimization (Day 11-14)
- [ ] End-to-end 테스트
- [ ] 성능 최적화
- [ ] 캐싱 구현
- [ ] 문서화

---

## 11. 결론

### 핵심 개선사항

1. **Intent Classification**: 사용자 의도를 정확히 파악
2. **Context Awareness**: 대화 맥락 이해
3. **Memory Integration**: 이전 상호작용 기억
4. **Reference Resolution**: "그거", "이전" 등 해결
5. **Personalization**: 사용자별 맞춤 응답

### 기대 효과

- **정확성 향상**: 의도 파악으로 정확한 작업 실행
- **자연스러운 대화**: 컨텍스트 이해로 자연스러운 흐름
- **개인화**: 사용자 이력 기반 맞춤 서비스
- **효율성**: 반복 작업 감소, 빠른 참조

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/INTENT_MEMORY_ARCHITECTURE_251105.md`