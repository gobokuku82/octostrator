# Complete System Architecture with Intent & Memory

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: Intent, Memory를 포함한 전체 시스템 아키텍처 종합

---

## 1. 전체 시스템 구성도

```
┌───────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                     (React + WebSocket)                         │
└───────────────────────────────────────────────────────────────┘
                                │
                          WebSocket
                                │
┌───────────────────────────────────────────────────────────────┐
│                        FastAPI Server                           │
│                    /ws/chat/{session_id}                        │
└───────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    INTENT CLASSIFIER (NEW)                      │
│         - Pattern Matching                                      │
│         - Context Analysis                                      │
│         - Reference Resolution                                  │
└───────────────────────────────────────────────────────────────┘
                                │
                    ┌──────────┴──────────┐
                    ▼                     ▼
┌─────────────────────────┐    ┌────────────────────────────────┐
│   MEMORY MANAGER (NEW)  │◄──►│    ENHANCED SUPERVISOR         │
│  - User Profile         │    │  - Intent Routing              │
│  - Conversation History │    │  - Context Building            │
│  - Task History        │    │  - Agent Orchestration         │
│  - Vector Embeddings   │    │  - State Management            │
└─────────────────────────┘    └────────────────────────────────┘
            │                                │
            │                   ┌────────────┼────────────┐
            │                   ▼            ▼            ▼
            │         ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │         │  DietAgent   │ │ WorkoutAgent │ │ScheduleAgent │
            │         │ (LangGraph)  │ │ (LangGraph)  │ │ (LangGraph)  │
            │         │ +Checkpoint  │ │ +Checkpoint  │ │ -Checkpoint  │
            │         └──────────────┘ └──────────────┘ └──────────────┘
            │                   │            │            │
            ▼                   ▼            ▼            ▼
┌───────────────────────────────────────────────────────────────┐
│                      PostgreSQL Database                        │
│  ┌─────────────┬──────────────┬────────────┬──────────────┐  │
│  │ Checkpoints │ User Profile │ Task History│ Embeddings   │  │
│  │ (LangGraph) │ (Memory)     │ (Memory)    │ (pgvector)   │  │
│  └─────────────┴──────────────┴────────────┴──────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. 데이터 플로우 상세

### 2.1 초기 요청 처리

```
Step 1: User Input
"지난번 다이어트 계획 수정해줘"
         │
         ▼
Step 2: Intent Classification
┌─────────────────────────────┐
│ Intent Classifier           │
├─────────────────────────────┤
│ Input: "지난번...수정해줘"  │
│                             │
│ Process:                    │
│ - Detect: "지난번" (ref)    │
│ - Detect: "수정" (modify)   │
│ - Detect: "다이어트" (diet) │
│                             │
│ Output:                     │
│ - Primary: MODIFY           │
│ - Sub: MODIFY_EXISTING      │
│ - Ref: LAST_DIET_PLAN      │
└─────────────────────────────┘
         │
         ▼
Step 3: Memory Retrieval
┌─────────────────────────────┐
│ Memory Manager              │
├─────────────────────────────┤
│ Query: LAST_DIET_PLAN       │
│                             │
│ SQL:                        │
│ SELECT * FROM task_history  │
│ WHERE user_id = ?           │
│   AND agent = 'diet_agent'  │
│ ORDER BY created_at DESC    │
│ LIMIT 1                     │
│                             │
│ Result: {plan_id: "abc123"} │
└─────────────────────────────┘
         │
         ▼
Step 4: Enhanced Supervisor
┌─────────────────────────────┐
│ Supervisor State            │
├─────────────────────────────┤
│ messages: [user_msg]        │
│ intent: {                   │
│   type: MODIFY,             │
│   sub: MODIFY_EXISTING,     │
│   target: "abc123"          │
│ }                           │
│ context: {                  │
│   previous_plan: {...},     │
│   user_profile: {...}       │
│ }                           │
│ plan: [{                    │
│   agent: "diet_agent",      │
│   task: "modify",           │
│   params: {...}             │
│ }]                          │
└─────────────────────────────┘
         │
         ▼
Step 5: Agent Execution
┌─────────────────────────────┐
│ DietAgent.modify()          │
├─────────────────────────────┤
│ Load previous plan          │
│ Apply modifications         │
│ Validate nutrition          │
│ Return updated plan         │
└─────────────────────────────┘
```

---

## 3. 핵심 컴포넌트 연결

### 3.1 컴포넌트 의존성

```
                    ┌─────────────────┐
                    │ WebSocket Handler│
                    └────────┬────────┘
                             │ uses
                             ▼
                    ┌─────────────────┐
                    │ Intent Classifier│
                    └────────┬────────┘
                             │ provides intent
                             ▼
                ┌────────────────────────┐
                │  Enhanced Supervisor    │
                └──┬──────────────────┬──┘
    uses memory    │                  │ orchestrates
                   ▼                  ▼
         ┌──────────────┐    ┌──────────────┐
         │Memory Manager│    │Agent Registry │
         └──────────────┘    └───────┬──────┘
                provides context      │ manages
                                     ▼
                            ┌──────────────┐
                            │ Agent Pool   │
                            │ - DietAgent  │
                            │ - WorkoutAgent│
                            │ - ...        │
                            └──────────────┘
```

### 3.2 State 계층 구조

```
Global Session State
├── session_id: "session_123"
├── user_id: "user_456"
├── thread_id: "thread_789"
│
├── Intent Context
│   ├── primary_intent: MODIFY
│   ├── sub_intent: MODIFY_EXISTING
│   └── entities: {target: "plan_abc"}
│
├── Memory Context
│   ├── user_profile: {...}
│   ├── recent_history: [...]
│   └── relevant_tasks: [...]
│
├── Supervisor State
│   ├── messages: [...]
│   ├── plan: [...]
│   ├── current_step: 2
│   └── aggregated_data: {...}
│
└── Agent States
    ├── diet_agent_state
    │   ├── thread_id: "thread_789_diet"
    │   └── checkpoint: {...}
    └── workout_agent_state
        ├── thread_id: "thread_789_workout"
        └── checkpoint: {...}
```

---

## 4. 시스템 초기화 순서

```python
# backend/app/main.py

async def initialize_system():
    """시스템 초기화 순서"""

    # 1. Database 연결
    db = await connect_database()

    # 2. Memory Manager 초기화
    memory_manager = MemoryManager(db)
    await memory_manager.initialize_schema()

    # 3. Intent Classifier 초기화
    intent_classifier = IntentClassifier(memory_manager)
    await intent_classifier.load_patterns()

    # 4. Agent Registry 초기화
    agent_registry = AgentRegistry()
    agent_registry.discover_agents("app/octostrator/agents")

    # 5. Checkpoint Strategy 초기화
    checkpoint_strategy = CheckpointStrategy()

    # 6. Dependency Resolver 초기화
    dependency_resolver = DependencyResolver()
    for agent_id in agent_registry.list_agents():
        agent = agent_registry.get_agent_instance(agent_id)
        dependency_resolver.add_agent(agent_id, agent.dependencies)

    # 7. Supervisor 초기화
    supervisor = EnhancedSupervisor(
        intent_classifier=intent_classifier,
        memory_manager=memory_manager,
        agent_registry=agent_registry,
        checkpoint_strategy=checkpoint_strategy,
        dependency_resolver=dependency_resolver
    )

    return supervisor
```

---

## 5. 실행 시나리오별 플로우

### 5.1 신규 사용자 첫 요청

```
[NEW USER] → "다이어트 계획 만들어줘"
    │
    ├─ Intent: CREATE / CREATE_DIET_PLAN
    ├─ Memory: Empty (new user)
    ├─ Context: Default profile created
    │
    └─ Flow:
        1. Create user profile in memory
        2. Execute DietAgent.create_plan()
        3. Save plan to memory
        4. Save checkpoint
        5. Return response
```

### 5.2 기존 사용자 연속 대화

```
[EXISTING USER] → "어제 만든 계획 어때?"
    │
    ├─ Intent: QUERY / QUERY_HISTORY
    ├─ Memory: Load user profile & history
    ├─ Context: "어제" → resolve to date
    │
    └─ Flow:
        1. Search task_history for yesterday
        2. No agent execution needed
        3. Format and return directly

[SAME USER] → "거기에 간식 추가해줘"
    │
    ├─ Intent: MODIFY / ADD_ITEM
    ├─ Reference: "거기" → last queried plan
    ├─ Context: Maintain conversation state
    │
    └─ Flow:
        1. Resolve "거기" to plan_id
        2. Execute DietAgent.add_snacks()
        3. Update memory with modification
        4. Update checkpoint
```

### 5.3 복잡한 멀티 Agent 시나리오

```
[USER] → "다이어트랑 운동 계획 같이 만들고 일정에 넣어줘"
    │
    ├─ Intent: CREATE / CREATE_MULTIPLE
    ├─ Entities: [diet, workout, schedule]
    │
    └─ Execution Plan:
        Level 0: [DietAgent]       (먼저 실행)
            ↓
        Level 1: [WorkoutAgent]    (diet 결과 참조)
            ↓
        Level 2: [ScheduleAgent]   (통합 일정)
```

---

## 6. 에러 처리 및 복구

### 6.1 Intent 분류 실패

```python
async def handle_intent_failure(message: str, error: Exception):
    """Intent 분류 실패 처리"""

    # Fallback to basic pattern matching
    basic_intent = await basic_pattern_match(message)

    if not basic_intent:
        # Ask for clarification
        return {
            "response": "무엇을 도와드릴까요? 좀 더 구체적으로 말씀해주세요.",
            "suggestions": [
                "다이어트 계획 만들기",
                "운동 계획 만들기",
                "이전 계획 확인하기"
            ]
        }
```

### 6.2 Memory 조회 실패

```python
async def handle_memory_failure(reference: str):
    """메모리 조회 실패 처리"""

    # Try fuzzy search
    similar_items = await memory_manager.fuzzy_search(reference)

    if similar_items:
        return {
            "clarification_needed": True,
            "message": "다음 중 어떤 것을 말씀하시는 건가요?",
            "options": similar_items[:3]
        }
    else:
        return {
            "not_found": True,
            "message": "관련된 이전 작업을 찾을 수 없습니다."
        }
```

---

## 7. 모니터링 및 분석

### 7.1 메트릭 수집 포인트

```python
class SystemMetrics:
    """시스템 메트릭 수집"""

    # Intent Classification Metrics
    intent_classification_time: float
    intent_accuracy_score: float
    unknown_intent_count: int

    # Memory Access Metrics
    memory_query_time: float
    memory_hit_rate: float
    embedding_search_time: float

    # Agent Execution Metrics
    agent_execution_times: Dict[str, float]
    agent_success_rates: Dict[str, float]
    checkpoint_save_times: Dict[str, float]

    # User Experience Metrics
    total_response_time: float
    conversation_turns: int
    task_completion_rate: float
```

### 7.2 분석 대시보드

```
┌──────────────────────────────────────────────────────┐
│              System Analytics Dashboard                │
├──────────────────────────────────────────────────────┤
│                                                        │
│ Intent Classification                                  │
│ ├─ Accuracy: 92%                                      │
│ ├─ Avg Time: 120ms                                    │
│ └─ Unknown: 8%                                        │
│                                                        │
│ Memory Performance                                     │
│ ├─ Query Time: 45ms avg                               │
│ ├─ Hit Rate: 78%                                      │
│ └─ DB Size: 2.3GB                                     │
│                                                        │
│ Agent Performance                                      │
│ ├─ DietAgent: 1.2s avg, 95% success                  │
│ ├─ WorkoutAgent: 0.8s avg, 97% success               │
│ └─ ScheduleAgent: 0.5s avg, 99% success              │
│                                                        │
│ User Satisfaction                                      │
│ ├─ Completion Rate: 87%                               │
│ ├─ Avg Turns: 3.2                                     │
│ └─ Response Time: 2.1s                                │
│                                                        │
└──────────────────────────────────────────────────────┘
```

---

## 8. 구현 우선순위

### Priority 1: Core Foundation (필수)
1. **Enhanced Supervisor** - Intent routing 추가
2. **Intent Classifier** - 기본 패턴 매칭
3. **Basic Memory** - 세션 내 기억

### Priority 2: Advanced Features (중요)
4. **Context Resolution** - 참조 해결
5. **Memory Persistence** - PostgreSQL 저장
6. **Agent Integration** - BaseAgent 적용

### Priority 3: Optimization (선택)
7. **Embedding Search** - 유사도 검색
8. **Caching Layer** - 성능 최적화
9. **Analytics** - 모니터링 대시보드

---

## 9. 코드 구조

```
backend/app/
├── octostrator/
│   ├── supervisor/
│   │   ├── enhanced_supervisor.py  # NEW: Intent-aware
│   │   ├── intent_router.py       # NEW: Intent routing
│   │   └── context_builder.py     # NEW: Context building
│   │
│   ├── intent/                    # NEW MODULE
│   │   ├── __init__.py
│   │   ├── classifier.py          # Intent classifier
│   │   ├── patterns.py           # Pattern definitions
│   │   └── resolver.py           # Reference resolver
│   │
│   ├── memory/                    # NEW MODULE
│   │   ├── __init__.py
│   │   ├── manager.py            # Memory manager
│   │   ├── embeddings.py         # Vector embeddings
│   │   └── schemas.py            # DB schemas
│   │
│   └── agents/
│       ├── base/                 # Foundation
│       │   ├── base_agent.py
│       │   ├── agent_registry.py
│       │   └── checkpoint_strategy.py
│       │
│       └── [specific agents]/    # Implementations
```

---

## 10. 최종 점검 사항

### ✅ 필수 구현
- [ ] Intent Classifier 기본 구현
- [ ] Memory Manager 기본 구현
- [ ] Enhanced Supervisor 구현
- [ ] Agent Wrapper 구현

### ✅ 통합 테스트
- [ ] Intent → Supervisor 연동
- [ ] Memory → Context 연동
- [ ] Supervisor → Agent 연동
- [ ] End-to-end 시나리오

### ✅ 문서화
- [ ] API 문서
- [ ] 아키텍처 문서
- [ ] 운영 가이드
- [ ] 트러블슈팅 가이드

---

## 결론

이 아키텍처는 다음을 제공합니다:

1. **Intent Classification**: 사용자 의도 정확한 파악
2. **Memory Integration**: 컨텍스트 기반 개인화
3. **Enhanced Supervisor**: 지능적인 작업 조율
4. **Scalable Agents**: 10+ 복잡한 Agent 관리
5. **Robust Error Handling**: 안정적인 서비스

모든 컴포넌트가 유기적으로 연결되어 자연스럽고 지능적인 대화형 AI 서비스를 구현합니다.

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/COMPLETE_ARCHITECTURE_DIAGRAM_251105.md`