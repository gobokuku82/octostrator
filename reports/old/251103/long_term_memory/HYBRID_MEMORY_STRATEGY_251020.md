# Hybrid Memory 전략 - 최근 대화 전체 + 과거 대화 요약

**작성일**: 2025-10-20
**제안**: "최근 5~10개는 전체, 11~20개는 요약"
**평가**: ✅ **매우 좋은 아이디어!**

---

## 🎯 제안 내용 분석

### 제안: 계층적 메모리 구조

```
┌─────────────────────────────────────────────────┐
│  Recent Memory (최근 5~10개)                     │
│  - 전체 대화 내용 (요약 없음)                     │
│  - 높은 상세도                                   │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  Mid-term Memory (11~20개)                      │
│  - 요약본                                        │
│  - 중간 상세도                                   │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  Long-term Memory (21개 이상)                   │
│  - 삭제 또는 압축 요약                           │
│  - 낮은 상세도                                   │
└─────────────────────────────────────────────────┘
```

---

## 📛 용어 정의

### "이전 대화를 전부 가져오기"를 뭐라고 부를까?

**업계 표준 용어**:

1. **Chat History** (채팅 히스토리)
   - 가장 일반적
   - 원본 메시지 전체

2. **Conversation Buffer** (대화 버퍼)
   - LangChain 용어
   - 최근 N개 메시지 버퍼링

3. **Recent Context** (최근 맥락)
   - 설명적
   - 최근 대화 맥락

4. **Short-term Memory** (단기 메모리)
   - 심리학/AI 용어
   - 최근 정보 저장

**권장**: ✅ **"Recent Memory" 또는 "Short-term Memory"**

---

### 계층별 명칭

```
1~10개:   Recent Memory / Short-term Memory (단기 메모리)
          → 원본 전체

11~20개:  Mid-term Memory (중기 메모리)
          → 요약본

21개 이상: Long-term Memory (장기 메모리)
          → 압축 요약 또는 삭제
```

---

## ✅ 구현 가능성 검토

### 질문 1: "지금 구조에서 이렇게 설정해도 되는가?"

**답변**: ✅ **완전히 가능합니다!**

**현재 구조**:
- Chat History: 현재 세션 내 최근 6개 (전체)
- Long-term Memory: 다른 세션 5개 (요약)

**개선 후**:
- Short-term Memory: 최근 5~10개 세션 (전체)
- Mid-term Memory: 11~20개 세션 (요약)
- Long-term Memory: 21개 이상 (압축 요약)

---

### 질문 2: "요약은 LLM이나 요약 모델 사용하기?"

**답변**: ✅ **LLM 사용 권장**

**3가지 옵션 비교**:

| 옵션 | 방법 | 장점 | 단점 |
|------|------|------|------|
| **A. 단순 잘라내기** | `[:200]` | 빠름, 무료 | 품질 낮음 |
| **B. LLM 요약** | GPT-4o-mini | 품질 좋음 | 비용, 느림 |
| **C. 요약 모델** | BART, T5 | 빠름, 저렴 | 품질 중간 |

**권장**: ✅ **Option B (LLM 요약)**

**이유**:
1. 최근 대화는 전체 저장 → 요약 빈도 낮음
2. 11~20개만 요약 → 비용 부담 적음
3. GPT-4o-mini 저렴 (~$0.0001/요청)
4. 품질이 중요함 (맥락 이해 필요)

---

## 🏗️ 구현 설계

### 아키텍처

```
┌─────────────────────────────────────────────────────┐
│            Hybrid Memory System                      │
└─────────────────────────────────────────────────────┘

[사용자 질문]
      ↓
┌─────────────────────────────────────────────────────┐
│ 1. Memory Loader (메모리 로더)                       │
└─────────────────────────────────────────────────────┘
      ↓
      ├─────────────────────────────────────────┐
      ↓                                         ↓
┌──────────────────────┐              ┌──────────────────────┐
│ Short-term Memory    │              │ Mid-term Memory      │
│ (최근 5~10개)         │              │ (11~20개)            │
│ - 전체 대화          │              │ - 요약본             │
└──────────────────────┘              └──────────────────────┘
      ↓                                         ↓
┌─────────────────────────────────────────────────────┐
│ 2. Memory Formatter (메모리 포맷터)                  │
│    - Short-term: 원본 그대로                         │
│    - Mid-term: "요약: ..." 형식                      │
└─────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────┐
│ 3. Context Builder (컨텍스트 빌더)                   │
│    - Chat History (현재 세션)                        │
│    - Short-term Memory (1~10)                       │
│    - Mid-term Memory (11~20)                        │
└─────────────────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────┐
│ 4. Intent Analysis / Response Generation            │
└─────────────────────────────────────────────────────┘
```

---

## 💻 구현 코드

### Step 1: Hybrid Memory 로더

**파일**: `simple_memory_service.py` (새 메서드 추가)

```python
async def load_hybrid_memories(
    self,
    user_id: str,
    session_id: Optional[str] = None,
    recent_limit: int = 10,      # Short-term: 최근 10개
    midterm_limit: int = 20      # Mid-term: 11~20개
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Hybrid Memory 로드

    Returns:
        {
            "recent": [세션1, 세션2, ..., 세션10],  # 전체 대화
            "midterm": [세션11, ..., 세션20]        # 요약
        }
    """

    # 모든 세션 조회 (최신순)
    query = select(ChatSession).where(
        ChatSession.user_id == user_id,
        ChatSession.session_metadata.isnot(None)
    )

    # 현재 세션 제외
    if session_id:
        query = query.where(ChatSession.session_id != session_id)

    query = query.order_by(ChatSession.updated_at.desc()).limit(midterm_limit)

    result = await self.db.execute(query)
    sessions = result.scalars().all()

    # 분리: Recent vs Mid-term
    recent_sessions = sessions[:recent_limit]
    midterm_sessions = sessions[recent_limit:midterm_limit]

    # Recent: 전체 대화 로드
    recent_memories = []
    for session in recent_sessions:
        # 전체 메시지 조회
        msg_query = select(ChatMessage).where(
            ChatMessage.session_id == session.session_id
        ).order_by(ChatMessage.created_at)

        msg_result = await self.db.execute(msg_query)
        messages = msg_result.scalars().all()

        recent_memories.append({
            "session_id": session.session_id,
            "title": session.title,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ],
            "timestamp": session.updated_at.isoformat()
        })

    # Mid-term: 요약만
    midterm_memories = []
    for session in midterm_sessions:
        metadata = session.session_metadata
        if metadata and "conversation_summary" in metadata:
            midterm_memories.append({
                "session_id": session.session_id,
                "title": session.title,
                "summary": metadata["conversation_summary"],
                "timestamp": session.updated_at.isoformat()
            })

    return {
        "recent": recent_memories,
        "midterm": midterm_memories
    }
```

---

### Step 2: 요약 생성 (LLM 사용)

**파일**: `simple_memory_service.py` (새 메서드 추가)

```python
async def summarize_conversation(
    self,
    messages: List[Dict[str, Any]],
    max_length: int = 200
) -> str:
    """
    LLM을 사용한 대화 요약

    Args:
        messages: 대화 메시지 리스트
        max_length: 최대 요약 길이

    Returns:
        요약 문자열
    """
    from app.service_agent.llm_manager import LLMService

    # LLM Service 초기화
    llm_service = LLMService()

    # 대화 내용을 문자열로 변환
    conversation_text = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in messages
    ])

    # LLM 요약 요청
    prompt = f"""다음 대화를 {max_length}자 이내로 요약해주세요.

대화 내용:
{conversation_text}

요약 (핵심만, {max_length}자 이내):"""

    summary = await llm_service.complete_async(
        prompt=prompt,
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=100
    )

    return summary[:max_length]
```

**대안 (Prompt Template 사용)**:

```python
# prompts/memory/conversation_summary.txt 생성

summary = await llm_service.complete_async(
    prompt_name="conversation_summary",
    variables={
        "conversation": conversation_text,
        "max_length": max_length
    }
)
```

---

### Step 3: 저장 시 요약 생성

**파일**: `team_supervisor.py:878-894` (수정)

```python
# 현재
response_summary = response.get("answer", "")[:200]

# 개선 (LLM 요약)
if user_id:
    async for db_session in get_async_db():
        memory_service = LongTermMemoryService(db_session)

        # ✅ 메시지 조회
        messages = await memory_service.load_recent_messages(
            session_id=chat_session_id,
            limit=50  # 전체 대화
        )

        # ✅ LLM 요약 생성
        response_summary = await memory_service.summarize_conversation(
            messages=messages,
            max_length=200
        )

        # 저장
        await memory_service.save_conversation(
            user_id=user_id,
            session_id=chat_session_id,
            messages=[],
            summary=response_summary
        )
```

---

### Step 4: Intent 분석에 Hybrid Memory 사용

**파일**: `team_supervisor.py:196-259` (수정)

```python
# 현재
chat_history = await self._get_chat_history(session_id, limit=3)
context = {"chat_history": chat_history}

# 개선 (Hybrid Memory)
chat_history = await self._get_chat_history(session_id, limit=3)

# ✅ Hybrid Memory 로드
hybrid_memories = await memory_service.load_hybrid_memories(
    user_id=user_id,
    session_id=chat_session_id,
    recent_limit=10,   # 최근 10개 전체
    midterm_limit=20   # 11~20개 요약
)

context = {
    "chat_history": chat_history,              # 현재 세션
    "recent_memory": hybrid_memories["recent"],   # 1~10개 전체
    "midterm_memory": hybrid_memories["midterm"]  # 11~20개 요약
}

intent_result = await self.planning_agent.analyze_intent(query, context)
```

---

### Step 5: Prompt 수정

**파일**: `prompts/cognitive/intent_analysis.txt`

```markdown
## 🔹 현재 세션 대화 (Chat History)

{chat_history}

---

## 🔹 최근 대화 전체 (Short-term Memory, 1~10개 세션)

과거 대화창들의 전체 내용입니다.

{recent_memory}

---

## 🔹 과거 대화 요약 (Mid-term Memory, 11~20개 세션)

오래된 대화창들의 요약입니다.

{midterm_memory}

---

**현재 질문**: {query}

**분석 지침**:
1. Chat History에서 직접 참조 확인 (최우선)
2. Recent Memory에서 관련 대화 확인 (높은 우선순위)
3. Mid-term Memory에서 주제 확인 (보조)
4. 셋 중 하나라도 관련 있으면 RELEVANT로 분류
```

---

## 📊 성능 분석

### 토큰 사용량 비교

#### 현재 구현
```
Chat History: 6개 메시지 × 평균 100자 = 600자 (~300 토큰)
Long-term Memory: 5개 요약 × 200자 = 1000자 (~500 토큰)
───────────────────────────────────────────────────────
합계: ~800 토큰
```

#### Hybrid Memory (제안)
```
Chat History: 6개 메시지 × 100자 = 600자 (~300 토큰)
Recent Memory: 10개 세션 × 10개 메시지 × 100자 = 10,000자 (~5,000 토큰)
Mid-term Memory: 10개 요약 × 200자 = 2,000자 (~1,000 토큰)
───────────────────────────────────────────────────────
합계: ~6,300 토큰
```

**증가량**: +5,500 토큰 (~8배)

**비용 영향** (GPT-4o-mini):
- 현재: $0.00012/요청 (800 토큰)
- 개선: $0.00095/요청 (6,300 토큰)
- **증가: +$0.00083/요청**

---

### 응답 시간 영향

#### 추가 시간
```
1. Hybrid Memory 로드:
   - Recent (10개 세션, 전체 메시지): ~200ms
   - Mid-term (10개 세션, 요약만): ~50ms

2. LLM 요약 생성 (저장 시):
   - GPT-4o-mini: ~1,000ms

3. LLM Intent 분석 (토큰 증가):
   - 800 토큰 → 6,300 토큰: ~300ms 추가
───────────────────────────────────────────────────────
총 증가: ~550ms (Intent 분석 시)
         ~1,250ms (저장 시)
```

**허용 가능?**
- Intent 분석: 2s → 2.55s (+27%) ⚠️
- 저장: 0.1s → 1.35s (+1250%) ⚠️

---

## ⚖️ 장단점 분석

### ✅ 장점

1. **높은 정확도**
   - Recent Memory: 전체 대화 → 정확한 맥락
   - Mid-term Memory: 요약 → 주제 파악

2. **긴 기억**
   - 20개 세션까지 기억
   - 현재 5개 대비 4배

3. **균형 잡힌 설계**
   - 최근은 상세히, 과거는 요약
   - 토큰/비용 최적화

4. **품질 좋은 요약**
   - LLM 요약 → 의미 보존
   - 단순 잘라내기 대비 우수

---

### ❌ 단점

1. **응답 시간 증가**
   - +550ms (Intent 분석)
   - +1,250ms (저장 시)

2. **비용 증가**
   - 토큰: 8배 증가
   - 요약 LLM 호출 추가

3. **복잡도 증가**
   - 코드 복잡도 상승
   - 디버깅 어려움

4. **DB 부하**
   - Recent Memory 로드 시 메시지 대량 조회

---

## 💡 최적화 방안

### 1. Recent Memory 개수 조정

**제안**: 10개 → **5개**

```python
# 최적화
hybrid_memories = await memory_service.load_hybrid_memories(
    recent_limit=5,    # 10 → 5 (토큰 절반)
    midterm_limit=15   # 20 → 15
)
```

**효과**:
- 토큰: 6,300 → 3,650 (-42%)
- 응답 시간: +550ms → +300ms

---

### 2. 요약을 백그라운드로

**문제**: 저장 시 LLM 요약 → +1,250ms

**해결**: 비동기 백그라운드 작업

```python
# 저장 (동기)
await memory_service.save_conversation(
    summary=response.get("answer", "")[:200]  # 임시 요약
)

# 요약 (비동기 백그라운드)
asyncio.create_task(
    memory_service.update_summary_with_llm(
        session_id=chat_session_id
    )
)
```

**효과**:
- 사용자 응답 시간 증가 없음
- 요약은 나중에 백그라운드로

---

### 3. Lazy Loading (필요할 때만)

**아이디어**: Recent Memory는 필요할 때만 로드

```python
# Intent 분석 1차 (Chat History만)
intent_result = await self.planning_agent.analyze_intent(query, {
    "chat_history": chat_history
})

# IRRELEVANT이면 Recent Memory 로드 후 재분석
if intent_result.intent_type == IntentType.IRRELEVANT:
    hybrid_memories = await memory_service.load_hybrid_memories(...)

    intent_result = await self.planning_agent.analyze_intent(query, {
        "chat_history": chat_history,
        "recent_memory": hybrid_memories["recent"]
    })
```

**효과**:
- 대부분 케이스는 빠름 (Chat History만)
- IRRELEVANT일 때만 추가 로드

---

### 4. 캐싱

**아이디어**: Recent/Mid-term Memory 캐싱

```python
# Redis 캐싱
cache_key = f"hybrid_memory:{user_id}"
cached = await redis.get(cache_key)

if cached:
    return json.loads(cached)
else:
    memories = await load_hybrid_memories(...)
    await redis.setex(cache_key, 300, json.dumps(memories))  # 5분 캐시
    return memories
```

**효과**:
- DB 부하 감소
- 응답 시간 -200ms

---

## 🎯 권장 구현 순서

### Phase 1: 기본 구현 (2-3일)

1. ✅ `load_hybrid_memories()` 구현 (0.5일)
2. ✅ LLM 요약 기능 추가 (0.5일)
3. ✅ Intent 분석에 통합 (0.5일)
4. ✅ Prompt 수정 (0.5일)
5. ✅ 테스트 (1일)

---

### Phase 2: 최적화 (1-2일)

1. ✅ Recent Memory 개수 조정 (5개로)
2. ✅ 백그라운드 요약 (asyncio)
3. ✅ 성능 모니터링

---

### Phase 3: 고도화 (선택, 2-3일)

1. ✅ Lazy Loading
2. ✅ Redis 캐싱
3. ✅ A/B 테스트

---

## 📋 최종 권장사항

### ✅ 구현 추천

**이유**:
1. 매우 좋은 아이디어
2. 균형 잡힌 설계
3. 실용적

**단, 최적화 필요**:
- Recent Memory: 10 → **5개**
- 요약: **백그라운드 처리**
- Lazy Loading 또는 캐싱

---

### 📊 최종 설정 권장

```python
# 권장 설정
RECENT_MEMORY_LIMIT = 5     # 최근 5개 세션 (전체 대화)
MIDTERM_MEMORY_LIMIT = 15   # 6~15개 세션 (요약)
LONGTERM_MEMORY_LIMIT = 50  # 16~50개 세션 (압축 요약, Phase 2)

# 요약 방식
SUMMARY_METHOD = "llm"      # LLM 요약 (GPT-4o-mini)
SUMMARY_BACKGROUND = True   # 백그라운드 처리
```

---

## 🎯 결론

### 질문 1: "지금 구조에서 이렇게 설정해도 되는가?"

**답변**: ✅ **완전히 가능합니다**
- 현재 구조를 확장하면 됨
- 새 테이블 불필요

---

### 질문 2: "이걸 뭐라고 부르면 좋지?"

**답변**: ✅ **Hybrid Memory** 또는 **Tiered Memory**
- Recent Memory (1~5개, 전체)
- Mid-term Memory (6~15개, 요약)
- Long-term Memory (16개 이상, 압축)

---

### 질문 3: "요약은 LLM이나 요약 모델 사용하기?"

**답변**: ✅ **LLM 사용 권장** (GPT-4o-mini)
- 품질 우수
- 비용 저렴 (~$0.0001/요청)
- 백그라운드 처리로 속도 영향 없음

---

**작성 완료**: 2025-10-20
**구현 우선순위**: 중간 (프로덕션 배포 후 고려)
