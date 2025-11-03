# Hybrid Memory 구현 계획서

**작성일**: 2025-10-20
**목표**: Recent Memory (전체) + Mid-term Memory (요약) 구현
**우선순위**: 높음 (즉시 구현)
**예상 소요**: 2-3시간

---

## 📋 목차

1. [현재 상황](#1-현재-상황)
2. [목표 및 요구사항](#2-목표-및-요구사항)
3. [구현 계획](#3-구현-계획)
4. [설정 파일 구조](#4-설정-파일-구조)
5. [구현 상세](#5-구현-상세)
6. [테스트 시나리오](#6-테스트-시나리오)
7. [롤백 계획](#7-롤백-계획)

---

## 1. 현재 상황

### 1.1 구현 완료 사항

#### ✅ Option A: Chat History (현재 세션)
**파일**: `team_supervisor.py:196-210`

```python
# Chat History 조회 (현재 세션 내 최근 6개 메시지)
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3  # 3쌍 = 6개 메시지
)

context = {"chat_history": chat_history}
intent_result = await self.planning_agent.analyze_intent(query, context)
```

**특징**:
- 범위: 현재 세션만
- 개수: 6개 메시지 (3쌍)
- 요약: 없음 (원본 그대로)
- 사용: Intent 분석

---

#### ✅ Phase 1: Long-term Memory (다른 세션)
**파일**: `team_supervisor.py:235-259`

```python
# Long-term Memory 조회 (다른 세션들)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,  # 기본값: 5
    relevance_filter="RELEVANT",
    session_id=chat_session_id  # 현재 세션 제외
)

state["loaded_memories"] = loaded_memories
```

**특징**:
- 범위: 다른 세션들
- 개수: 5개 세션
- 요약: 있음 (200자 요약)
- 사용: State에만 저장 (명시적 사용 안 함)

---

#### ✅ 요약 생성
**파일**: `team_supervisor.py:878-883`

```python
# 현재: 단순 잘라내기
response_summary = response.get("answer", "")[:200]

await memory_service.save_conversation(
    user_id=user_id,
    session_id=chat_session_id,
    messages=[],
    summary=response_summary
)
```

**특징**:
- 방식: 단순 잘라내기 (`[:200]`)
- LLM: 사용 안 함
- 백그라운드: 아니요 (동기)

---

### 1.2 현재 구조의 한계

| 한계 | 설명 | 영향도 |
|------|------|--------|
| **Long-term Memory 미사용** | State에만 저장, Intent/Response에 미사용 | 높음 |
| **단순 요약** | 문자열 잘라내기 ([:200]), 문장 중간에서 잘림 | 중간 |
| **범위 제한** | 5개 세션만, 설정 불가능 | 중간 |
| **계층 없음** | 최근/과거 구분 없음, 모두 요약 | 높음 |

---

### 1.3 현재 파일 구조

```
backend/
├── app/
│   ├── core/
│   │   └── config.py                    # 설정 파일 (MEMORY_LOAD_LIMIT)
│   ├── service_agent/
│   │   ├── supervisor/
│   │   │   └── team_supervisor.py       # Intent 분석, Memory 로드
│   │   ├── foundation/
│   │   │   └── simple_memory_service.py # Memory 서비스
│   │   ├── cognitive_agents/
│   │   │   └── planning_agent.py        # Intent 분석 LLM
│   │   └── llm_manager/
│   │       └── prompts/cognitive/
│   │           └── intent_analysis.txt  # Intent Prompt
│   └── models/
│       └── chat.py                      # ChatMessage, ChatSession
└── .env                                 # 환경 변수
```

---

## 2. 목표 및 요구사항

### 2.1 핵심 목표

**Hybrid Memory 구현**:
```
┌──────────────────────────────────────────┐
│ Recent Memory (최근 N개)                  │
│ - 전체 대화 내용 (요약 없음)              │
│ - 높은 상세도                            │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│ Mid-term Memory (N+1 ~ M개)              │
│ - LLM 요약                               │
│ - 중간 상세도                            │
└──────────────────────────────────────────┘
```

---

### 2.2 요구사항

#### 기능 요구사항

1. ✅ **Recent Memory 로드**
   - 최근 N개 세션의 전체 대화
   - 요약 없음 (원본 그대로)

2. ✅ **Mid-term Memory 로드**
   - N+1 ~ M개 세션의 요약
   - LLM 요약 사용

3. ✅ **Intent 분석에 통합**
   - Context에 Recent/Mid-term Memory 추가
   - Prompt 수정

4. ✅ **LLM 요약 생성**
   - GPT-4o-mini 사용
   - 백그라운드 처리

5. ✅ **설정 가능**
   - Recent 범위 (개수)
   - Mid-term 범위 (개수)
   - 요약 방식 (LLM/단순)
   - LLM 모델 선택

---

#### 비기능 요구사항

1. ✅ **성능**
   - Intent 분석 응답 시간: +500ms 이내
   - 백그라운드 요약: 사용자 응답 영향 없음

2. ✅ **비용**
   - LLM 요약: 백그라운드로 비용 최소화
   - 토큰 증가: 3,800 토큰 이내

3. ✅ **호환성**
   - 기존 코드 동작 유지
   - 설정으로 활성화/비활성화 가능

4. ✅ **유지보수성**
   - 설정 파일로 쉽게 조정
   - 로그 상세 기록

---

## 3. 구현 계획

### 3.1 구현 단계

```
┌─────────────────────────────────────────────────────┐
│ Step 1: 설정 파일 추가 (10분)                        │
│ - config.py에 Hybrid Memory 설정 추가                │
│ - .env에 환경 변수 추가                              │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ Step 2: LLM 요약 기능 구현 (30분)                    │
│ - simple_memory_service.py에 summarize_with_llm()    │
│ - Prompt 템플릿 생성                                 │
│ - 백그라운드 처리 로직                               │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ Step 3: Hybrid Memory 로더 구현 (30분)               │
│ - simple_memory_service.py에 load_hybrid_memories()  │
│ - Recent: 전체 메시지 조회                           │
│ - Mid-term: 요약만 조회                              │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ Step 4: Intent 분석 통합 (20분)                      │
│ - team_supervisor.py 수정                            │
│ - Context에 Recent/Mid-term 추가                     │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ Step 5: Prompt 수정 (20분)                           │
│ - intent_analysis.txt 수정                           │
│ - Recent/Mid-term 섹션 추가                          │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ Step 6: planning_agent.py 수정 (20분)                │
│ - Context에서 Recent/Mid-term 추출                   │
│ - 포맷팅 및 LLM 전달                                 │
└─────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────┐
│ Step 7: 테스트 및 검증 (30분)                        │
│ - 기본 시나리오 테스트                               │
│ - 로그 확인                                          │
└─────────────────────────────────────────────────────┘

총 소요 시간: 2.5시간
```

---

### 3.2 파일 수정 목록

| 파일 | 작업 | 예상 시간 |
|------|------|-----------|
| `.env` | 환경 변수 추가 | 2분 |
| `config.py` | 설정 클래스 추가 | 5분 |
| `simple_memory_service.py` | LLM 요약 + Hybrid 로더 | 60분 |
| `team_supervisor.py` | Hybrid Memory 통합 | 20분 |
| `planning_agent.py` | Context 처리 | 20분 |
| `intent_analysis.txt` | Prompt 수정 | 20분 |
| `prompts/memory/` | 요약 Prompt 생성 | 10분 |

---

## 4. 설정 파일 구조

### 4.1 .env 파일

**파일**: `backend/.env`

```bash
# ============================================================================
# Hybrid Memory Configuration
# ============================================================================

# Recent Memory (전체 대화)
RECENT_MEMORY_LIMIT=5            # 최근 5개 세션 (전체 대화)
RECENT_MEMORY_ENABLED=true       # Recent Memory 활성화

# Mid-term Memory (요약)
MIDTERM_MEMORY_LIMIT=10          # 6~15개 세션 (요약)
MIDTERM_MEMORY_ENABLED=true      # Mid-term Memory 활성화

# 요약 설정
SUMMARY_METHOD=llm               # llm | simple (llm: LLM 요약, simple: 단순 잘라내기)
SUMMARY_LLM_MODEL=gpt-4o-mini    # LLM 모델 (요약용)
SUMMARY_MAX_LENGTH=200           # 요약 최대 길이
SUMMARY_BACKGROUND=true          # 백그라운드 요약 활성화

# 기존 설정 (호환성)
MEMORY_LOAD_LIMIT=5              # Long-term Memory (기존, 사용 안 함)
```

---

### 4.2 config.py 설정 클래스

**파일**: `backend/app/core/config.py`

```python
class Settings(BaseSettings):
    # ... 기존 설정 ...

    # ============================================================================
    # Hybrid Memory Configuration
    # ============================================================================

    # Recent Memory (전체 대화)
    RECENT_MEMORY_LIMIT: int = Field(
        default=5,
        description="Recent Memory 로드 개수 (최근 N개 세션, 전체 대화)"
    )
    RECENT_MEMORY_ENABLED: bool = Field(
        default=True,
        description="Recent Memory 활성화 여부"
    )

    # Mid-term Memory (요약)
    MIDTERM_MEMORY_LIMIT: int = Field(
        default=10,
        description="Mid-term Memory 로드 개수 (N+1 ~ M개 세션, 요약)"
    )
    MIDTERM_MEMORY_ENABLED: bool = Field(
        default=True,
        description="Mid-term Memory 활성화 여부"
    )

    # 요약 설정
    SUMMARY_METHOD: str = Field(
        default="llm",
        description="요약 방식 (llm: LLM 요약, simple: 단순 잘라내기)"
    )
    SUMMARY_LLM_MODEL: str = Field(
        default="gpt-4o-mini",
        description="요약에 사용할 LLM 모델"
    )
    SUMMARY_MAX_LENGTH: int = Field(
        default=200,
        description="요약 최대 길이 (문자 수)"
    )
    SUMMARY_BACKGROUND: bool = Field(
        default=True,
        description="백그라운드 요약 활성화 여부"
    )

    # 기존 설정 (호환성, Deprecated)
    MEMORY_LOAD_LIMIT: int = Field(
        default=5,
        description="[Deprecated] Long-term Memory 로드 개수 (Hybrid Memory로 대체)"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True
```

---

### 4.3 설정 예시

#### 예시 1: 기본 설정 (권장)
```bash
RECENT_MEMORY_LIMIT=5
MIDTERM_MEMORY_LIMIT=10
SUMMARY_METHOD=llm
SUMMARY_BACKGROUND=true
```

**효과**:
- 최근 5개: 전체 대화
- 6~15개: LLM 요약
- 백그라운드 요약

---

#### 예시 2: 성능 최적화 (빠른 응답)
```bash
RECENT_MEMORY_LIMIT=3
MIDTERM_MEMORY_LIMIT=7
SUMMARY_METHOD=llm
SUMMARY_BACKGROUND=true
```

**효과**:
- 토큰 감소 (빠른 응답)
- 비용 절감

---

#### 예시 3: 긴 기억 (높은 정확도)
```bash
RECENT_MEMORY_LIMIT=10
MIDTERM_MEMORY_LIMIT=20
SUMMARY_METHOD=llm
SUMMARY_BACKGROUND=true
```

**효과**:
- 긴 기억 (20개 세션)
- 높은 정확도

---

#### 예시 4: 비용 절감 (단순 요약)
```bash
RECENT_MEMORY_LIMIT=5
MIDTERM_MEMORY_LIMIT=10
SUMMARY_METHOD=simple  # ← LLM 사용 안 함
SUMMARY_BACKGROUND=false
```

**효과**:
- LLM 비용 없음
- 단순 잘라내기

---

#### 예시 5: Hybrid Memory 비활성화
```bash
RECENT_MEMORY_ENABLED=false
MIDTERM_MEMORY_ENABLED=false
```

**효과**:
- 기존 방식 유지 (Chat History만)
- 롤백 가능

---

## 5. 구현 상세

### 5.1 Step 1: 설정 파일 추가

#### 파일 1: `.env`

**위치**: `backend/.env`

**추가할 내용**:
```bash
# ============================================================================
# Hybrid Memory Configuration (추가됨: 2025-10-20)
# ============================================================================

# Recent Memory (전체 대화)
RECENT_MEMORY_LIMIT=5
RECENT_MEMORY_ENABLED=true

# Mid-term Memory (요약)
MIDTERM_MEMORY_LIMIT=10
MIDTERM_MEMORY_ENABLED=true

# 요약 설정
SUMMARY_METHOD=llm
SUMMARY_LLM_MODEL=gpt-4o-mini
SUMMARY_MAX_LENGTH=200
SUMMARY_BACKGROUND=true
```

---

#### 파일 2: `config.py`

**위치**: `backend/app/core/config.py`

**수정 위치**: Settings 클래스 내부

**추가할 코드**:
```python
# Line ~70 (MEMORY_LOAD_LIMIT 아래)

# ============================================================================
# Hybrid Memory Configuration
# ============================================================================

# Recent Memory (전체 대화)
RECENT_MEMORY_LIMIT: int = Field(
    default=5,
    description="Recent Memory 로드 개수 (최근 N개 세션, 전체 대화)"
)
RECENT_MEMORY_ENABLED: bool = Field(
    default=True,
    description="Recent Memory 활성화 여부"
)

# Mid-term Memory (요약)
MIDTERM_MEMORY_LIMIT: int = Field(
    default=10,
    description="Mid-term Memory 로드 개수 (N+1 ~ M개 세션, 요약)"
)
MIDTERM_MEMORY_ENABLED: bool = Field(
    default=True,
    description="Mid-term Memory 활성화 여부"
)

# 요약 설정
SUMMARY_METHOD: str = Field(
    default="llm",
    description="요약 방식 (llm: LLM 요약, simple: 단순 잘라내기)"
)
SUMMARY_LLM_MODEL: str = Field(
    default="gpt-4o-mini",
    description="요약에 사용할 LLM 모델"
)
SUMMARY_MAX_LENGTH: int = Field(
    default=200,
    description="요약 최대 길이 (문자 수)"
)
SUMMARY_BACKGROUND: bool = Field(
    default=True,
    description="백그라운드 요약 활성화 여부"
)
```

---

### 5.2 Step 2: LLM 요약 기능 구현

#### 파일 1: Prompt 템플릿 생성

**위치**: `backend/app/service_agent/llm_manager/prompts/memory/conversation_summary.txt` (새 파일)

**내용**:
```markdown
# Conversation Summary Prompt

다음 대화를 간결하게 요약해주세요.

## 요약 지침

1. **핵심만 추출**: 주요 주제와 결과만 포함
2. **간결성**: {max_length}자 이내로 작성
3. **완전한 문장**: 문장이 중간에서 끊기지 않도록
4. **구체적**: 지역명, 금액, 핵심 키워드 포함

## 대화 내용

{conversation}

## 요약 ({max_length}자 이내)

```

---

#### 파일 2: `simple_memory_service.py` - LLM 요약 메서드

**위치**: `backend/app/service_agent/foundation/simple_memory_service.py`

**추가 위치**: 클래스 내부, 기존 메서드 아래

**추가할 코드**:
```python
# Line ~390 (기존 메서드 아래)

async def summarize_with_llm(
    self,
    messages: List[Dict[str, Any]],
    max_length: int = 200
) -> str:
    """
    LLM을 사용한 대화 요약

    Args:
        messages: 대화 메시지 리스트
            [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        max_length: 최대 요약 길이

    Returns:
        요약 문자열
    """
    try:
        from app.service_agent.llm_manager import LLMService
        from app.core.config import settings

        # 대화 내용을 문자열로 변환
        conversation_lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                conversation_lines.append(f"사용자: {content}")
            elif role == "assistant":
                conversation_lines.append(f"AI: {content}")

        conversation_text = "\n".join(conversation_lines)

        # LLM Service 초기화
        llm_service = LLMService()

        # LLM 요약 요청
        summary = await llm_service.complete_async(
            prompt_name="conversation_summary",
            variables={
                "conversation": conversation_text,
                "max_length": max_length
            },
            model=settings.SUMMARY_LLM_MODEL,
            temperature=0.3,
            max_tokens=100
        )

        # 길이 제한
        summary = summary.strip()[:max_length]

        logger.info(f"[LLM Summary] Generated summary: {len(summary)} chars")
        return summary

    except Exception as e:
        logger.error(f"[LLM Summary] Failed to generate summary: {e}")
        # Fallback: 단순 잘라내기
        if messages:
            last_msg = messages[-1].get("content", "")
            return last_msg[:max_length]
        return "대화 요약 실패"


async def summarize_conversation_background(
    self,
    session_id: str,
    user_id: str
):
    """
    백그라운드로 대화 요약 생성 및 업데이트

    Args:
        session_id: 세션 ID
        user_id: 사용자 ID
    """
    try:
        from app.core.config import settings

        # 설정 확인
        if not settings.SUMMARY_BACKGROUND:
            logger.debug("[Summary] Background summary disabled")
            return

        if settings.SUMMARY_METHOD != "llm":
            logger.debug("[Summary] LLM summary disabled")
            return

        # 메시지 조회
        messages = await self.load_recent_messages(
            session_id=session_id,
            limit=50  # 전체 대화
        )

        if not messages:
            logger.warning(f"[Summary] No messages found for session {session_id}")
            return

        # LLM 요약 생성
        summary = await self.summarize_with_llm(
            messages=messages,
            max_length=settings.SUMMARY_MAX_LENGTH
        )

        # 세션 조회
        from sqlalchemy import select
        query = select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            logger.error(f"[Summary] Session not found: {session_id}")
            return

        # Metadata 업데이트
        if session.session_metadata is None:
            session.session_metadata = {}

        session.session_metadata["conversation_summary"] = summary
        session.session_metadata["summary_method"] = "llm"
        session.session_metadata["last_updated"] = datetime.now().isoformat()

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(session, "session_metadata")

        await self.db.commit()

        logger.info(f"[Summary] Background summary updated for session {session_id}")

    except Exception as e:
        logger.error(f"[Summary] Background summary failed: {e}")
        # 실패해도 에러 전파 안 함 (백그라운드 작업)
```

---

### 5.3 Step 3: Hybrid Memory 로더 구현

**파일**: `simple_memory_service.py`

**추가 위치**: 클래스 내부

**추가할 코드**:
```python
# Line ~500 (summarize_conversation_background 아래)

async def load_hybrid_memories(
    self,
    user_id: str,
    session_id: Optional[str] = None,
    recent_limit: Optional[int] = None,
    midterm_limit: Optional[int] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Hybrid Memory 로드 (Recent + Mid-term)

    Args:
        user_id: 사용자 ID
        session_id: 현재 세션 ID (제외할 세션)
        recent_limit: Recent Memory 개수 (None이면 설정값 사용)
        midterm_limit: Mid-term Memory 개수 (None이면 설정값 사용)

    Returns:
        {
            "recent": [
                {
                    "session_id": "...",
                    "title": "...",
                    "messages": [{"role": "user", "content": "..."}],
                    "timestamp": "..."
                }
            ],
            "midterm": [
                {
                    "session_id": "...",
                    "title": "...",
                    "summary": "...",
                    "timestamp": "..."
                }
            ]
        }
    """
    try:
        from app.core.config import settings
        from sqlalchemy import select, desc

        # 설정값 사용
        if recent_limit is None:
            recent_limit = settings.RECENT_MEMORY_LIMIT
        if midterm_limit is None:
            midterm_limit = settings.MIDTERM_MEMORY_LIMIT

        # 활성화 확인
        recent_enabled = settings.RECENT_MEMORY_ENABLED
        midterm_enabled = settings.MIDTERM_MEMORY_ENABLED

        # 전체 세션 조회 (최신순)
        total_limit = recent_limit + midterm_limit if midterm_enabled else recent_limit

        query = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.session_metadata.isnot(None)
        )

        # 현재 세션 제외
        if session_id:
            query = query.where(ChatSession.session_id != session_id)

        query = query.order_by(desc(ChatSession.updated_at)).limit(total_limit)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        # 분리: Recent vs Mid-term
        recent_sessions = sessions[:recent_limit] if recent_enabled else []
        midterm_sessions = sessions[recent_limit:total_limit] if midterm_enabled else []

        logger.info(
            f"[Hybrid Memory] Loaded {len(recent_sessions)} recent, "
            f"{len(midterm_sessions)} midterm sessions for user {user_id}"
        )

        # ===== Recent Memory: 전체 대화 로드 =====
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
                "title": session.title or "Untitled",
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content[:500],  # 길이 제한
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ],
                "timestamp": session.updated_at.isoformat()
            })

        # ===== Mid-term Memory: 요약만 로드 =====
        midterm_memories = []

        for session in midterm_sessions:
            metadata = session.session_metadata
            if metadata and "conversation_summary" in metadata:
                midterm_memories.append({
                    "session_id": session.session_id,
                    "title": session.title or "Untitled",
                    "summary": metadata["conversation_summary"],
                    "timestamp": session.updated_at.isoformat()
                })

        return {
            "recent": recent_memories,
            "midterm": midterm_memories
        }

    except Exception as e:
        logger.error(f"[Hybrid Memory] Failed to load: {e}")
        return {
            "recent": [],
            "midterm": []
        }
```

---

### 5.4 Step 4: team_supervisor.py 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**수정 위치**: `planning_node` 메서드 (Line 196-259)

**기존 코드**:
```python
# Line 196-210
# 의도 분석
query = state.get("query", "")
chat_session_id = state.get("chat_session_id")

# Chat history 조회 (문맥 이해를 위해)
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3  # 최근 3개 대화 쌍 (6개 메시지)
)

# Context 생성
context = {"chat_history": chat_history} if chat_history else None

# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)
```

**수정 후**:
```python
# Line 196-230 (확장)
# 의도 분석
query = state.get("query", "")
chat_session_id = state.get("chat_session_id")
user_id = state.get("user_id")

# Chat history 조회 (문맥 이해를 위해)
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3  # 최근 3개 대화 쌍 (6개 메시지)
)

# ✅ Hybrid Memory 조회 (Recent + Mid-term)
hybrid_memories = {"recent": [], "midterm": []}

if user_id:
    try:
        async for db_session in get_async_db():
            from app.service_agent.foundation.simple_memory_service import SimpleMemoryService as LongTermMemoryService

            memory_service = LongTermMemoryService(db_session)

            hybrid_memories = await memory_service.load_hybrid_memories(
                user_id=user_id,
                session_id=chat_session_id
            )

            logger.info(
                f"[Hybrid Memory] Loaded {len(hybrid_memories['recent'])} recent, "
                f"{len(hybrid_memories['midterm'])} midterm memories"
            )
            break
    except Exception as e:
        logger.warning(f"[Hybrid Memory] Failed to load: {e}")

# ✅ Context 생성 (Chat History + Hybrid Memory)
context = {
    "chat_history": chat_history,
    "recent_memory": hybrid_memories["recent"],
    "midterm_memory": hybrid_memories["midterm"]
}

# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)
```

**수정 위치 2**: `generate_response_node` - 저장 시 백그라운드 요약

**기존 코드** (Line 878-894):
```python
# 응답 요약 생성 (최대 200자)
response_summary = response.get("summary", "")
if not response_summary and response.get("answer"):
    response_summary = response.get("answer", "")[:200]
if not response_summary:
    response_summary = f"{response.get('type', 'response')} 생성 완료"

# 대화 저장
await memory_service.save_conversation(
    user_id=user_id,
    session_id=chat_session_id,
    messages=[],
    summary=response_summary
)
```

**수정 후**:
```python
from app.core.config import settings
import asyncio

# 응답 요약 생성 (임시)
response_summary = response.get("summary", "")
if not response_summary and response.get("answer"):
    if settings.SUMMARY_METHOD == "llm":
        # LLM 요약은 백그라운드로
        response_summary = response.get("answer", "")[:200]  # 임시 요약
    else:
        # 단순 잘라내기
        response_summary = response.get("answer", "")[:settings.SUMMARY_MAX_LENGTH]

if not response_summary:
    response_summary = f"{response.get('type', 'response')} 생성 완료"

# 대화 저장 (임시 요약 사용)
await memory_service.save_conversation(
    user_id=user_id,
    session_id=chat_session_id,
    messages=[],
    summary=response_summary
)

# ✅ 백그라운드 LLM 요약 (비동기)
if settings.SUMMARY_METHOD == "llm" and settings.SUMMARY_BACKGROUND:
    asyncio.create_task(
        memory_service.summarize_conversation_background(
            session_id=chat_session_id,
            user_id=user_id
        )
    )
    logger.info(f"[Summary] Background LLM summary task created for session {chat_session_id}")
```

---

### 5.5 Step 5: planning_agent.py 수정

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**수정 위치**: `_analyze_with_llm` 메서드 (Line 183-213)

**기존 코드**:
```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    # Context에서 chat_history 추출
    chat_history = context.get("chat_history", []) if context else []

    # Chat history를 문자열로 포맷팅
    chat_history_text = ""
    if chat_history:
        formatted_history = []
        for msg in chat_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                formatted_history.append(f"사용자: {content}")
            elif role == "assistant":
                formatted_history.append(f"AI: {content}")

        if formatted_history:
            chat_history_text = "\n".join(formatted_history)

    # LLMService를 통한 의도 분석
    result = await self.llm_service.complete_json_async(
        prompt_name="intent_analysis",
        variables={
            "query": query,
            "chat_history": chat_history_text
        },
        temperature=0.0,
        max_tokens=500
    )
```

**수정 후**:
```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    # Context에서 chat_history 추출
    chat_history = context.get("chat_history", []) if context else []

    # Chat history를 문자열로 포맷팅
    chat_history_text = ""
    if chat_history:
        formatted_history = []
        for msg in chat_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                formatted_history.append(f"사용자: {content}")
            elif role == "assistant":
                formatted_history.append(f"AI: {content}")

        if formatted_history:
            chat_history_text = "\n".join(formatted_history)

    # ✅ Recent Memory 추출 및 포맷팅
    recent_memory = context.get("recent_memory", []) if context else []
    recent_memory_text = ""

    if recent_memory:
        formatted_recent = []
        for mem in recent_memory:
            title = mem.get("title", "Untitled")
            timestamp = mem.get("timestamp", "")[:10]  # YYYY-MM-DD
            messages = mem.get("messages", [])

            # 각 세션의 메시지 포맷팅
            session_lines = [f"[{timestamp}] {title}:"]
            for msg in messages[:10]:  # 최대 10개 메시지만
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    session_lines.append(f"  사용자: {content}")
                elif role == "assistant":
                    session_lines.append(f"  AI: {content}")

            formatted_recent.append("\n".join(session_lines))

        if formatted_recent:
            recent_memory_text = "\n\n".join(formatted_recent)

    # ✅ Mid-term Memory 추출 및 포맷팅
    midterm_memory = context.get("midterm_memory", []) if context else []
    midterm_memory_text = ""

    if midterm_memory:
        formatted_midterm = []
        for mem in midterm_memory:
            title = mem.get("title", "Untitled")
            timestamp = mem.get("timestamp", "")[:10]
            summary = mem.get("summary", "")

            formatted_midterm.append(f"- [{timestamp}] {title}: {summary}")

        if formatted_midterm:
            midterm_memory_text = "\n".join(formatted_midterm)

    # LLMService를 통한 의도 분석
    result = await self.llm_service.complete_json_async(
        prompt_name="intent_analysis",
        variables={
            "query": query,
            "chat_history": chat_history_text,
            "recent_memory": recent_memory_text,      # ← 추가
            "midterm_memory": midterm_memory_text     # ← 추가
        },
        temperature=0.0,
        max_tokens=500
    )
```

---

### 5.6 Step 6: intent_analysis.txt Prompt 수정

**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`

**수정 위치**: Line 203-218 (기존 Chat History 섹션 아래)

**기존 코드**:
```markdown
## 🔹 최근 대화 기록 (Chat History)

이전 대화 맥락을 참고하여 의도를 더 정확히 파악하세요.

{chat_history}

---

**현재 질문**: {query}

**분석 지침**:
1. 위 대화 기록을 참고하여 현재 질문의 맥락을 이해하세요
2. "그럼", "그거", "그건", "아까" 등의 지시어가 있으면 이전 대화에서 언급된 내용을 찾으세요
3. 이전 대화와 연결되는 질문이면 부동산 관련 질문으로 처리하세요

---
```

**수정 후**:
```markdown
## 🔹 현재 세션 대화 (Chat History)

현재 대화창의 최근 대화입니다.

{chat_history}

---

## 🔹 최근 대화 전체 (Recent Memory)

과거 대화창들의 전체 대화 내용입니다. 높은 우선순위로 참조하세요.

{recent_memory}

---

## 🔹 과거 대화 요약 (Mid-term Memory)

오래된 대화창들의 요약입니다. 주제 파악에 참고하세요.

{midterm_memory}

---

**현재 질문**: {query}

**분석 지침 (우선순위 순)**:
1. **Chat History**: 현재 대화창에서 직접 참조 확인 (최우선)
2. **Recent Memory**: 과거 대화창의 전체 내용에서 관련 대화 확인 (높은 우선순위)
3. **Mid-term Memory**: 오래된 대화의 요약에서 주제 확인 (보조)
4. **지시어 처리**: "그럼", "그거", "그건", "아까" 등이 있으면 위 3가지 메모리에서 찾기
5. **판단**: 셋 중 하나라도 관련 있으면 부동산 관련 질문으로 처리

---
```

---

## 6. 테스트 시나리오

### 6.1 테스트 1: Recent Memory 동작 확인

**시나리오**:
```
[2일 전 대화창 A]
사용자: "강남구 아파트 전세 시세 알려줘"
AI: "5억~7억 범위입니다..."

[1일 전 대화창 B]
사용자: "송파구는?"
AI: "4억~6억 범위입니다..."

[오늘 새 대화창 C]
사용자: "그럼 서초구는?"
```

**기대 결과**:
```
Recent Memory 로드:
- 대화창 A 전체
- 대화창 B 전체

Intent 분석:
- Intent: MARKET_INQUIRY (confidence: 0.9+)
- Keywords: ["서초구", "시세", "아파트", "전세"]
- Reasoning: "Recent Memory에서 강남구, 송파구 시세 조회 확인.
             서초구도 같은 맥락의 시세 조회"
```

---

### 6.2 테스트 2: Mid-term Memory 동작 확인

**시나리오**:
```
[10일 전 대화창들 (6~15번째)]
- 대화창 6: "전세자금대출 한도 조회"
- 대화창 7: "LTV/DTI 계산"
- ...
- 대화창 15: "금리 비교"

[오늘 새 대화창]
사용자: "대출 한도가 어떻게 됐지?"
```

**기대 결과**:
```
Mid-term Memory 로드:
- 대화창 6 요약: "전세자금대출 한도 조회 및 LTV 계산"
- 대화창 7 요약: "DTI 한도 계산 및 금리 비교"
- ...

Intent 분석:
- Intent: LOAN_CONSULT (confidence: 0.85+)
- Keywords: ["대출", "한도"]
- Reasoning: "Mid-term Memory에서 대출 관련 대화 확인"
```

---

### 6.3 테스트 3: LLM 요약 확인

**시나리오**:
```
[대화 완료]
사용자: "강남구 아파트 전세 시세 알려줘"
AI: "강남구 아파트 전세 시세는 5억~7억 범위입니다.
    주요 단지로는 대치동 은마아파트(6억), 개포동 개포주공(5.5억)이 있으며,
    최근 1년간 약 10% 상승했습니다..."
```

**기대 결과**:
```
임시 요약 (즉시):
"강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 대치동 은마아파트(6억),
개포동 개포주공(5.5억)이 있으며, 최근 1년간 약 10% 상승했습니다. 전세금 상승의 주요
원인은 매매가 상승과 전세 수요 증가입니다. 향후 6개월 동안에도 꾸준한 상승이..."

백그라운드 LLM 요약 (1~2초 후):
"강남구 아파트 전세 시세 조회 (5억~7억 범위, 최근 1년간 10% 상승)"
```

---

### 6.4 테스트 4: 설정 변경 테스트

**시나리오 A**: Recent Memory 비활성화
```bash
# .env
RECENT_MEMORY_ENABLED=false
```

**기대 결과**:
- Recent Memory 로드 안 됨
- Chat History + Mid-term Memory만 사용

---

**시나리오 B**: 단순 요약
```bash
# .env
SUMMARY_METHOD=simple
```

**기대 결과**:
- LLM 요약 안 함
- 단순 잘라내기 ([:200])

---

## 7. 롤백 계획

### 7.1 문제 발생 시 즉시 롤백

**방법 1**: 환경 변수로 비활성화
```bash
# .env
RECENT_MEMORY_ENABLED=false
MIDTERM_MEMORY_ENABLED=false
```

**효과**:
- Hybrid Memory 완전 비활성화
- 기존 방식 (Chat History만) 유지
- 코드 수정 없음

---

**방법 2**: 단순 요약으로 전환
```bash
# .env
SUMMARY_METHOD=simple
SUMMARY_BACKGROUND=false
```

**효과**:
- LLM 요약 비활성화
- 비용 절감
- 응답 시간 빠름

---

### 7.2 Git 롤백

**명령어**:
```bash
# 커밋 전이라면
git checkout .

# 커밋 후라면
git revert HEAD
```

---

## 📋 체크리스트

### 구현 전 체크리스트

- [ ] `.env` 파일 백업
- [ ] `config.py` 백업
- [ ] 현재 코드 커밋 (`git commit`)
- [ ] 테스트 환경 준비

---

### 구현 중 체크리스트

**Step 1: 설정**
- [ ] `.env` 파일 수정
- [ ] `config.py` 수정
- [ ] 서버 재시작하여 설정 로드 확인

**Step 2: LLM 요약**
- [ ] Prompt 템플릿 생성 (`conversation_summary.txt`)
- [ ] `summarize_with_llm()` 메서드 추가
- [ ] `summarize_conversation_background()` 메서드 추가
- [ ] 로그 확인

**Step 3: Hybrid Memory 로더**
- [ ] `load_hybrid_memories()` 메서드 추가
- [ ] Recent Memory 로드 확인
- [ ] Mid-term Memory 로드 확인
- [ ] 로그 확인

**Step 4: team_supervisor.py**
- [ ] Hybrid Memory 조회 코드 추가
- [ ] Context 생성 수정
- [ ] 백그라운드 요약 추가
- [ ] 로그 확인

**Step 5: planning_agent.py**
- [ ] Recent Memory 포맷팅 추가
- [ ] Mid-term Memory 포맷팅 추가
- [ ] Variables에 추가
- [ ] 로그 확인

**Step 6: Prompt**
- [ ] `intent_analysis.txt` 수정
- [ ] Recent Memory 섹션 추가
- [ ] Mid-term Memory 섹션 추가
- [ ] 분석 지침 업데이트

---

### 구현 후 체크리스트

- [ ] 서버 재시작
- [ ] 테스트 1: Recent Memory 동작 확인
- [ ] 테스트 2: Mid-term Memory 동작 확인
- [ ] 테스트 3: LLM 요약 확인
- [ ] 테스트 4: 설정 변경 테스트
- [ ] 로그 확인 (에러 없음)
- [ ] 응답 시간 측정
- [ ] Git 커밋
- [ ] 문서 업데이트

---

**작성 완료**: 2025-10-20
**구현 시작**: 지금 바로!
