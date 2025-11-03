# Long-term Memory 구현 분석 및 활용 가이드

**작성일**: 2025-10-20
**목적**: Long-term Memory 구현 방식 이해 및 활용 방안 제시

---

## 🔍 질문 1: "Long-term Memory가 어떤 식으로 구현되어있는거지? LangChain/LangGraph 컴포넌트인가?"

### 답변: ❌ **LangChain/LangGraph 컴포넌트 아님**

**실제 구현**: ✅ **자체 구현 (PostgreSQL JSONB 기반)**

---

## 📦 구현 방식

### 핵심: PostgreSQL의 `chat_sessions.metadata` 컬럼 활용

**파일**: `backend/app/service_agent/foundation/simple_memory_service.py`

```python
class SimpleMemoryService:
    """
    간단한 메모리 서비스 (chat_messages 기반)

    Note:
        - ConversationMemory/EntityMemory/UserPreference 제거됨
        - chat_sessions.metadata (JSONB) 사용
        - LangChain/LangGraph 컴포넌트 아님 (자체 구현)
    """
```

---

## 🗄️ 데이터베이스 구조

### chat_sessions 테이블 (기존 테이블 활용)

```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(200),

    -- ✅ 여기에 Long-term Memory 저장
    session_metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,

    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**session_metadata 예시**:
```json
{
  "conversation_summary": "강남구 아파트 전세 시세 조회 (5억~7억 범위)",
  "last_updated": "2025-10-20T16:58:31+00:00",
  "message_count": 2
}
```

---

## 🔧 핵심 메서드 2개

### 1️⃣ `load_recent_memories()` - 메모리 로드

**파일**: `simple_memory_service.py:217-329`

```python
async def load_recent_memories(
    self,
    user_id: str,
    limit: int = 5,
    relevance_filter: str = "ALL",
    session_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    최근 세션의 메모리 로드 (chat_sessions.metadata 기반)
    """

    # ✅ PostgreSQL 쿼리 (LangChain 사용 안 함)
    query = select(ChatSession).where(
        ChatSession.user_id == user_id,
        ChatSession.session_metadata.isnot(None)  # JSONB가 있는 세션만
    )

    # 현재 세션 제외
    if session_id:
        query = query.where(ChatSession.session_id != session_id)

    # 최신순 정렬 및 개수 제한
    query = query.order_by(ChatSession.updated_at.desc()).limit(limit)

    result = await self.db.execute(query)
    sessions = result.scalars().all()

    # conversation_summary 추출
    memories = []
    for session in sessions:
        metadata = session.session_metadata
        if metadata and "conversation_summary" in metadata:
            memories.append({
                "session_id": session.session_id,
                "summary": metadata["conversation_summary"],
                "timestamp": session.updated_at.isoformat(),
                "title": session.title
            })

    return memories
```

**특징**:
- ✅ 순수 SQLAlchemy 쿼리
- ✅ LangChain/LangGraph 의존성 없음
- ✅ PostgreSQL JSONB 네이티브 기능 활용

---

### 2️⃣ `save_conversation()` - 메모리 저장

**파일**: `simple_memory_service.py:331-386`

```python
async def save_conversation(
    self,
    user_id: str,
    session_id: str,
    messages: List[dict],
    summary: str
) -> None:
    """
    대화 요약을 chat_sessions.metadata에 저장
    """

    # 세션 조회
    query = select(ChatSession).where(
        ChatSession.session_id == session_id,
        ChatSession.user_id == user_id
    )
    result = await self.db.execute(query)
    session = result.scalar_one_or_none()

    # metadata 초기화 (없는 경우)
    if session.session_metadata is None:
        session.session_metadata = {}

    # ✅ conversation_summary 저장 (JSONB에 직접 저장)
    session.session_metadata["conversation_summary"] = summary
    session.session_metadata["last_updated"] = datetime.now().isoformat()
    session.session_metadata["message_count"] = len(messages)

    # ✅ JSONB 변경 플래그 설정 (SQLAlchemy가 변경 감지하도록)
    flag_modified(session, "session_metadata")

    await self.db.commit()
```

**특징**:
- ✅ `flag_modified()` 사용 (SQLAlchemy JSONB 변경 추적)
- ✅ 트랜잭션 관리 (commit/rollback)
- ✅ LangChain 메모리 클래스 사용 안 함

---

## 🆚 LangChain Memory vs 현재 구현

### LangChain의 Memory (사용 안 함)

LangChain에는 다음과 같은 메모리 컴포넌트가 있지만, **우리는 사용하지 않음**:

```python
# ❌ 우리가 사용하지 않는 LangChain 컴포넌트들

from langchain.memory import (
    ConversationBufferMemory,      # 전체 대화 저장
    ConversationSummaryMemory,     # 대화 요약 저장
    ConversationBufferWindowMemory, # 최근 N개만 저장
    ConversationKGMemory,          # Knowledge Graph 기반
    VectorStoreRetrieverMemory     # Vector DB 기반
)

# 사용 예시 (우리는 안 함)
memory = ConversationSummaryMemory(llm=llm)
memory.save_context({"input": "..."}, {"output": "..."})
```

**우리가 사용 안 하는 이유**:
1. **커스텀 요구사항**: 세션별, 유저별 메모리 격리 필요
2. **PostgreSQL 활용**: 이미 있는 DB 스키마 활용
3. **유연성**: 자체 구현이 더 커스터마이징 쉬움
4. **성능**: 불필요한 추상화 제거

---

### 현재 구현 (자체 구현)

```python
# ✅ 우리의 구현 (simple_memory_service.py)

class SimpleMemoryService:
    """자체 구현 메모리 서비스"""

    async def load_recent_memories(self, user_id, limit=5):
        # PostgreSQL 직접 쿼리
        query = select(ChatSession).where(...)
        return memories

    async def save_conversation(self, user_id, session_id, summary):
        # JSONB에 직접 저장
        session.session_metadata["conversation_summary"] = summary
        flag_modified(session, "session_metadata")
```

**장점**:
- ✅ 간단하고 명확
- ✅ PostgreSQL JSONB 최적화
- ✅ 외부 의존성 없음
- ✅ 커스터마이징 쉬움

---

## 🎯 질문 2: "이걸 어떻게 활용하는 게 좋지?"

### 현재 활용 방식 (Option A 구현 후)

```
┌─────────────────────────────────────────────────────┐
│            현재 구현 상태 (2025-10-20)               │
└─────────────────────────────────────────────────────┘

1. Chat History (현재 세션)
   ↓
   Intent 분석 ✅ (방금 구현 완료)

2. Long-term Memory (다른 세션들)
   ↓
   State에만 저장 ⚠️ (명시적으로 사용 안 함)
```

**문제점**:
- Long-term Memory를 로드는 하지만, **명시적으로 활용 안 함**
- Response 생성 시 LLM에 전달하지 않음
- State에만 있고 실제로는 사용 안 됨

---

## 💡 활용 방안 (우선순위별)

### 🔥 우선순위 1: Intent 분석에 Long-term Memory 추가 (권장)

**목적**: 새 대화창에서도 이전 주제 참조 가능

**시나리오**:
```
[2일 전 대화창]
사용자: "강남구 시세 알려줘"
→ Long-term Memory 저장: "강남구 아파트 전세 시세 조회"

[오늘 새 대화창]
사용자: "그럼 송파구는?"
→ 현재: IRRELEVANT (Chat History 없음) ❌
→ 개선: MARKET_INQUIRY (Long-term Memory 참조) ✅
```

**구현 방법**:

#### Step 1: Context에 Long-term Memory 추가
**파일**: `team_supervisor.py:196-210`

```python
# 현재
chat_history = await self._get_chat_history(session_id, limit=3)
context = {"chat_history": chat_history}

# 개선 후
chat_history = await self._get_chat_history(session_id, limit=3)
long_term_memory = state.get("loaded_memories", [])  # 이미 로드됨

context = {
    "chat_history": chat_history,
    "long_term_memory": long_term_memory  # ← 추가
}

intent_result = await self.planning_agent.analyze_intent(query, context)
```

#### Step 2: Prompt에 Long-term Memory 섹션 추가
**파일**: `prompts/cognitive/intent_analysis.txt`

```markdown
## 🔹 최근 대화 기록 (Chat History)

{chat_history}

---

## 🔹 이전 대화 요약 (Long-term Memory)

과거 다른 대화창에서 나눈 대화 요약입니다.

{long_term_memory}

---

**현재 질문**: {query}

**분석 지침**:
1. Chat History에서 직접 참조 확인 (우선순위 높음)
2. Long-term Memory에서 관련 주제 확인 (보조)
3. 둘 중 하나라도 관련 있으면 RELEVANT로 분류
```

#### Step 3: planning_agent.py 수정
**파일**: `planning_agent.py:183-213`

```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    # Chat History 추출 (기존)
    chat_history = context.get("chat_history", []) if context else []
    chat_history_text = ...

    # ✅ Long-term Memory 추출 (추가)
    long_term_memory = context.get("long_term_memory", []) if context else []

    # 포맷팅
    ltm_text = ""
    if long_term_memory:
        formatted_ltm = []
        for mem in long_term_memory:
            summary = mem.get("summary", "")
            timestamp = mem.get("timestamp", "")
            formatted_ltm.append(f"- [{timestamp[:10]}] {summary}")

        if formatted_ltm:
            ltm_text = "\n".join(formatted_ltm)

    # LLM에 전달
    result = await self.llm_service.complete_json_async(
        prompt_name="intent_analysis",
        variables={
            "query": query,
            "chat_history": chat_history_text,
            "long_term_memory": ltm_text  # ← 추가
        }
    )
```

**예상 효과**:
- ✅ 새 대화창에서도 이전 주제 참조 가능
- ✅ 크로스 세션 문맥 이해
- ✅ IRRELEVANT 오분류 추가 감소

**예상 시간**: 1-2시간

---

### ⭐ 우선순위 2: Response 생성에 Long-term Memory 명시적 사용

**목적**: 더 맥락 있는 답변 생성

**시나리오**:
```
[이전 대화창]
사용자: "강남구 아파트 투자 분석해줘"
→ Long-term Memory: "강남구 아파트 투자 분석 및 리스크 평가"

[현재 대화창]
사용자: "송파구는 어때?"
→ 답변: "이전에 강남구 투자 분석을 하셨는데, 송파구는 강남구 대비..." ✅
```

**구현 방법**:

#### Step 1: Response Synthesis Prompt 수정
**파일**: `prompts/response/response_synthesis.txt`

```markdown
## 사용자 컨텍스트

### 이전 대화 요약
{long_term_memory}

### 현재 질문
{query}

**답변 작성 지침**:
1. 이전 대화와 연관성이 있으면 언급하세요
2. 예: "이전에 강남구에 대해 문의하셨는데..."
```

#### Step 2: generate_response_node 수정
**파일**: `team_supervisor.py:592-901`

```python
async def generate_response_node(self, state: OverallState) -> OverallState:
    # Long-term Memory 추출
    loaded_memories = state.get("loaded_memories", [])

    # 포맷팅
    ltm_text = "\n".join([
        f"- {mem['summary']}"
        for mem in loaded_memories
    ])

    # LLM에 전달
    response = await self.llm_service.complete_async(
        prompt_name="response_synthesis",
        variables={
            "query": query,
            "search_results": search_results,
            "long_term_memory": ltm_text  # ← 추가
        }
    )
```

**예상 효과**:
- ✅ 맥락 있는 답변
- ✅ 사용자 경험 향상
- ✅ 대화 연속성 강화

**예상 시간**: 1-2시간

---

### 📊 우선순위 3: Long-term Memory 검색 기능 (Phase 2)

**목적**: 특정 주제 관련 과거 대화 찾기

**시나리오**:
```
사용자: "강남구에 대해 뭐 물어봤었지?"
→ Long-term Memory 검색: "강남구" 키워드
→ 답변: "2일 전에 강남구 아파트 전세 시세를 문의하셨습니다 (5억~7억)"
```

**구현 방법** (Phase 2):

#### Step 1: Vector Embedding 추가
```sql
-- conversation_memories 테이블 (새로 생성)
CREATE TABLE conversation_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_id VARCHAR(100),
    summary TEXT,

    -- ✅ Vector Embedding 추가
    summary_embedding VECTOR(384),  -- KURE_v1 모델

    created_at TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Vector 인덱스
CREATE INDEX idx_summary_embedding
ON conversation_memories
USING ivfflat (summary_embedding vector_cosine_ops);
```

#### Step 2: 의미 검색 구현
```python
async def search_similar_memories(
    self,
    user_id: str,
    query: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Vector 유사도 검색"""

    # Query Embedding 생성
    query_embedding = self.embedding_model.encode(query)

    # PostgreSQL pgvector 검색
    sql = """
        SELECT summary,
               1 - (summary_embedding <=> :query_embedding) AS similarity
        FROM conversation_memories
        WHERE user_id = :user_id
        ORDER BY summary_embedding <=> :query_embedding
        LIMIT :limit
    """

    result = await self.db.execute(
        text(sql),
        {
            "query_embedding": query_embedding,
            "user_id": user_id,
            "limit": limit
        }
    )

    return result.all()
```

**예상 효과**:
- ✅ 의미 기반 검색
- ✅ "강남구" vs "강남" 같은 변형도 검색
- ✅ 주제별 대화 이력 조회

**예상 시간**: 3-4일 (Phase 2)

---

### 🔧 우선순위 4: 사용자 선호도 학습 (장기)

**목적**: 사용자 패턴 학습 및 맞춤 서비스

**시나리오**:
```
[여러 대화 분석]
사용자가 자주 묻는 주제:
- 강남구 시세 (5회)
- 전세자금대출 (3회)
- 계약서 검토 (2회)

→ 자동으로 관련 정보 추천
→ 답변 스타일 조정
```

**구현 방법** (장기):
```python
async def analyze_user_preferences(self, user_id: str) -> Dict[str, Any]:
    """사용자 선호도 분석"""

    memories = await self.load_recent_memories(user_id, limit=20)

    # 주제 빈도 분석
    topics = {}
    for mem in memories:
        # NLP 분석 또는 단순 키워드 추출
        ...

    return {
        "frequent_topics": ["시세조회", "대출상담"],
        "preferred_regions": ["강남구", "송파구"],
        "interaction_style": "간결한 답변 선호"
    }
```

---

## 📋 추천 순서

### 즉시 구현 (오늘)
1. ✅ **Intent 분석에 Long-term Memory 추가** (1-2시간)
   - 크로스 세션 참조 가능
   - IRRELEVANT 오분류 추가 감소

### 단기 (1주일 내)
2. ✅ **Response 생성에 Long-term Memory 사용** (1-2시간)
   - 맥락 있는 답변
   - 사용자 경험 향상

### 중기 (1개월 내)
3. ✅ **Vector 검색 기능 추가** (3-4일)
   - 의미 기반 검색
   - Phase 2 준비

### 장기 (3개월 내)
4. ✅ **사용자 선호도 학습** (2주)
   - 맞춤형 서비스
   - 추천 기능

---

## 🎯 즉시 실행 가능한 개선

### Option A 확장: Long-term Memory를 Intent 분석에 추가

**필요한 수정**:
1. `team_supervisor.py:196-210` - Context에 long_term_memory 추가 (5줄)
2. `planning_agent.py:183-213` - LTM 포맷팅 및 전달 (15줄)
3. `intent_analysis.txt` - LTM 섹션 추가 (10줄)

**총 소요 시간**: 1-2시간

**예상 효과**:
- 새 대화창에서도 이전 주제 참조 가능
- Intent 분류 정확도 추가 +5%p 향상

---

## 🔍 현재 구현의 장단점

### ✅ 장점

1. **간단함**: LangChain 없이 PostgreSQL만 사용
2. **빠름**: 추가 의존성 없음, 네이티브 JSONB 쿼리
3. **유연함**: 커스터마이징 쉬움
4. **비용 절감**: 외부 Vector DB 불필요 (Phase 1)
5. **기존 인프라 활용**: 새 테이블 불필요 (chat_sessions 재활용)

### ⚠️ 단점

1. **검색 제한**: 키워드 검색 불가 (시간순만 가능)
2. **의미 검색 없음**: Vector Embedding 미지원
3. **상세 정보 부족**: 요약만 저장 (200자)
4. **크로스 세션 참조 제한**: Intent 분석에 미사용 (개선 필요)

---

## 📊 LangChain Memory와 비교

| 항목 | LangChain Memory | 현재 구현 (자체) |
|------|------------------|------------------|
| **구현 방식** | LangChain 클래스 | PostgreSQL JSONB |
| **저장소** | Memory/Vector DB | chat_sessions.metadata |
| **의존성** | LangChain 필요 | SQLAlchemy만 |
| **커스터마이징** | 제한적 | 자유로움 |
| **검색** | Vector 지원 | 시간순만 (Phase 1) |
| **비용** | 추가 인프라 | 기존 DB 활용 |
| **성능** | 추상화 오버헤드 | 네이티브 쿼리 |

---

## 🎯 결론

### Long-term Memory 구현 방식
- ❌ LangChain/LangGraph 컴포넌트 아님
- ✅ 자체 구현 (PostgreSQL JSONB 기반)
- ✅ 간단하고 효율적

### 활용 방안
1. **즉시**: Intent 분석에 Long-term Memory 추가 (1-2시간)
2. **단기**: Response 생성에 명시적 사용 (1-2시간)
3. **중기**: Vector 검색 추가 (Phase 2, 3-4일)
4. **장기**: 사용자 선호도 학습 (2주)

### 권장 사항
- ✅ **지금**: Intent 분석에 Long-term Memory 추가 구현
- ✅ **다음**: 실사용 데이터 수집 후 개선 방향 결정

---

**작성 완료**: 2025-10-20
