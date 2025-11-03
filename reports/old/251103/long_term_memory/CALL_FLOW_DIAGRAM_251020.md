# Chat History vs Long-term Memory 호출 흐름

**작성일**: 2025-10-20
**목적**: 두 메커니즘이 언제, 어떻게 호출되는지 시각화

---

## 📊 전체 호출 흐름

```
사용자 질문: "2개 비교해줘"
        ↓
┌───────────────────────────────────────────────────────────┐
│ 1. planning_node (Line 174-385)                           │
│    - Intent 분석 단계                                      │
└───────────────────────────────────────────────────────────┘
        ↓
        │
        ├─────────────────────────────────────────┐
        ↓                                         ↓
┌──────────────────────┐              ┌──────────────────────┐
│ 2a. Chat History     │              │ 2b. Long-term Memory │
│    (Line 200-210)    │              │    (Line 235-259)    │
└──────────────────────┘              └──────────────────────┘
        │                                         │
        │ _get_chat_history()                    │ load_recent_memories()
        │                                         │
        │ 현재 대화창                             │ 다른 대화창들
        │ 최근 6개 메시지                         │ 5개 요약
        │ (요약 없음)                             │ (200자 요약)
        ↓                                         ↓
┌──────────────────────┐              ┌──────────────────────┐
│ 3a. Intent 분석      │              │ 3b. State 저장       │
│    analyze_intent()  │              │    state["loaded..."]│
└──────────────────────┘              └──────────────────────┘
        ↓                                         │
        │ Intent: MARKET_INQUIRY                  │
        └─────────────┬───────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ 4. execute_node         │
        │    - 팀 실행            │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ 5. generate_response    │
        │    - 답변 생성          │
        │    (여기서 Long-term    │
        │     Memory 사용 가능)   │
        └─────────────────────────┘
                      ↓
        ┌─────────────────────────┐
        │ 6. save_conversation    │
        │    - 200자 요약 저장    │
        │    (다음 Long-term      │
        │     Memory로 사용)      │
        └─────────────────────────┘
                      ↓
              최종 응답 반환
```

---

## 🔍 상세 호출 순서

### Step 1: planning_node 시작
**파일**: `team_supervisor.py:174-385`
**시점**: 사용자 질문이 들어온 직후

```python
async def planning_node(self, state: OverallState) -> OverallState:
    """Planning 단계"""
    query = state.get("query", "")

    # ↓ 여기서 두 메커니즘 호출 시작
```

---

### Step 2a: Chat History 조회 (먼저)
**파일**: `team_supervisor.py:196-210`
**시점**: Intent 분석 직전

```python
# 의도 분석
query = state.get("query", "")
chat_session_id = state.get("chat_session_id")

# ✅ Chat History 조회 (현재 대화창)
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3  # 최근 3쌍 (6개 메시지)
)

# Context 생성
context = {"chat_history": chat_history}

# ✅ Intent 분석 (Chat History 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)
```

**로드하는 데이터**:
```python
[
    {"role": "user", "content": "강남구 시세 알려줘"},
    {"role": "assistant", "content": "5억~7억입니다..."},
    {"role": "user", "content": "송파구는?"},
    {"role": "assistant", "content": "4억~6억입니다..."},
    {"role": "user", "content": "2개 비교해줘"}
]
```

---

### Step 2b: Long-term Memory 조회 (다음)
**파일**: `team_supervisor.py:235-259`
**시점**: Intent 분석 완료 직후

```python
# Intent 분석 완료 ↑

# ✅ Long-term Memory 로드 (다른 대화창들)
user_id = state.get("user_id")
chat_session_id = state.get("chat_session_id")

if user_id:
    loaded_memories = await memory_service.load_recent_memories(
        user_id=user_id,
        limit=settings.MEMORY_LOAD_LIMIT,  # 기본값: 5
        relevance_filter="RELEVANT",
        session_id=chat_session_id  # 현재 세션 제외
    )

    # State에 저장 (나중에 사용)
    state["loaded_memories"] = loaded_memories
    state["user_preferences"] = user_preferences
```

**로드하는 데이터**:
```python
[
    {
        "session_id": "session-xxx",
        "summary": "강남구 아파트 전세 시세 조회 (5억~7억)",
        "created_at": "2025-10-18T14:20:00"
    },
    {
        "session_id": "session-yyy",
        "summary": "송파구 투자 분석 및 리스크 평가",
        "created_at": "2025-10-19T09:15:00"
    }
]
```

---

### Step 3: Intent 분석 (Chat History 사용)
**파일**: `planning_agent.py:183-213`
**시점**: Chat History를 받아서 LLM 호출

```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    # ✅ Chat History 추출
    chat_history = context.get("chat_history", [])

    # 포맷팅
    chat_history_text = "\n".join([
        f"사용자: {msg['content']}" if msg["role"] == "user"
        else f"AI: {msg['content']}"
        for msg in chat_history
    ])

    # ✅ LLM에 전달
    result = await self.llm_service.complete_json_async(
        prompt_name="intent_analysis",
        variables={
            "query": query,
            "chat_history": chat_history_text  # ← 여기서 사용
        }
    )
```

**LLM이 보는 Prompt**:
```
## 🔹 최근 대화 기록 (Chat History)

사용자: 강남구 시세 알려줘
AI: 5억~7억입니다...
사용자: 송파구는?
AI: 4억~6억입니다...

**현재 질문**: 2개 비교해줘

**분석 지침**:
1. 위 대화 기록을 참고하여 현재 질문의 맥락을 이해하세요
...
```

**결과**:
- Intent: MARKET_INQUIRY
- Keywords: ["비교", "강남구", "송파구"]

---

### Step 4: 팀 실행
**파일**: `team_supervisor.py:387-590`
**시점**: Intent 분석 완료 후

```python
# execute_node에서 search_team, analysis_team 실행
# (Long-term Memory는 여기서 직접 사용 안 함)
```

---

### Step 5: Response 생성 (Long-term Memory 사용 가능)
**파일**: `team_supervisor.py:592-901`
**시점**: 팀 실행 완료 후

```python
async def generate_response_node(self, state: OverallState) -> OverallState:
    """응답 생성"""

    # ✅ Long-term Memory 사용 가능
    loaded_memories = state.get("loaded_memories", [])

    # LLM에 전달 (현재는 명시적으로 전달 안 함, Phase 2에서 추가 예정)
    # 하지만 state에 있으므로 필요하면 사용 가능

    response = await self.llm_service.complete_async(
        prompt_name="response_synthesis",
        variables={
            "query": query,
            "search_results": search_results,
            # "long_term_memory": loaded_memories  # ← Phase 2
        }
    )
```

**현재 상태**:
- Long-term Memory는 로드되어 state에 저장됨
- Response 생성 시 명시적으로 사용하지는 않음 (Phase 2에서 개선 예정)
- 하지만 필요하면 언제든 접근 가능

---

### Step 6: 대화 저장 (Long-term Memory 업데이트)
**파일**: `team_supervisor.py:846-900`
**시점**: Response 생성 완료 후

```python
# ✅ 응답 요약 생성
response_summary = response.get("answer", "")[:200]

# ✅ Long-term Memory 저장
await memory_service.save_conversation(
    user_id=user_id,
    session_id=chat_session_id,
    messages=[],
    summary=response_summary  # ← 200자 요약
)
```

**저장되는 내용**:
```python
{
    "conversation_summary": "강남구와 송파구 전세 시세 비교 (강남구 5억~7억, 송파구 4억~6억)",
    "last_updated": "2025-10-20T17:30:00",
    "message_count": 3
}
```

**저장 위치**: `chat_sessions.metadata` (JSONB)

**다음 사용**:
- 다른 대화창에서 Long-term Memory로 로드됨
- 또는 같은 대화창을 나중에 다시 열었을 때 참조 가능

---

## ⏱️ 타임라인 요약

```
시간 ──────────────────────────────────────────────▶

0ms    사용자 질문: "2개 비교해줘"
       ↓
10ms   planning_node 시작
       ↓
20ms   ✅ Chat History 조회 (현재 대화창, 6개 메시지)
       ↓
50ms   ✅ Intent 분석 (Chat History 사용)
       ↓
2000ms Intent 분석 완료: MARKET_INQUIRY
       ↓
2010ms ✅ Long-term Memory 조회 (다른 대화창, 5개 요약)
       ↓
2100ms execute_node 시작 (search_team, analysis_team)
       ↓
8000ms 팀 실행 완료
       ↓
8010ms generate_response_node 시작
       ↓
       (Long-term Memory 사용 가능, 현재는 미사용)
       ↓
10000ms Response 생성 완료
       ↓
10010ms ✅ save_conversation (200자 요약 저장)
       ↓
10050ms 최종 응답 반환
```

---

## 🎯 핵심 요약

### Chat History (먼저 호출)
```
언제: Intent 분석 직전 (20ms)
어디: team_supervisor.py:200-210
무엇: 현재 대화창 최근 6개 메시지 (요약 없음)
목적: Intent 분석 (질문 이해)
다음: LLM에 전달 → Intent 분류
```

### Long-term Memory (나중 호출)
```
언제: Intent 분석 직후 (2010ms)
어디: team_supervisor.py:235-259
무엇: 다른 대화창 5개 요약 (200자)
목적: Response 생성 시 참고 (현재는 미사용)
저장: 대화 종료 시 (10010ms)
```

---

## 📝 코드 위치 정리

| 기능 | 파일 | 라인 | 설명 |
|------|------|------|------|
| Chat History 조회 | `team_supervisor.py` | 200-210 | `_get_chat_history()` 호출 |
| Chat History 구현 | `team_supervisor.py` | 1008-1070 | DB 조회 및 포맷팅 |
| Intent 분석 | `planning_agent.py` | 183-213 | Chat History 사용 |
| Long-term Memory 조회 | `team_supervisor.py` | 235-259 | `load_recent_memories()` 호출 |
| Long-term Memory 구현 | `simple_memory_service.py` | 217-275 | DB 조회 및 반환 |
| Long-term Memory 저장 | `team_supervisor.py` | 846-900 | `save_conversation()` 호출 |
| Long-term Memory 구현 | `simple_memory_service.py` | 277-332 | DB 저장 |

---

**작성 완료**: 2025-10-20
