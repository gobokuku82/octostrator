# 3-Tier Hybrid Memory 구현 계획서 (최종)

**작성일**: 2025-10-21
**버전**: FINAL IMPLEMENTATION PLAN
**예상 소요 시간**: 3시간 45분

---

## 📋 구현 개요

### 목표
- 3-Tier 메모리 시스템 구축 (Short/Mid/Long-term)
- LLM 기반 자동 요약 생성
- 토큰 효율적인 메모리 로드

### 현재 상태
- ✅ user_id Integer 타입 통일 완료
- ✅ chat_sessions.session_metadata (JSONB) 사용 중
- ✅ 기본 메모리 로드/저장 구현됨

---

## Phase 1: 설정 파일 수정 (15분)

### 1-1. config.py 수정

**파일**: `backend/app/core/config.py`

**현재 Line 1-2**:
```python
from typing import List
from pydantic_settings import BaseSettings
```

**수정 후 Line 1-3**:
```python
from typing import List
from pydantic import Field  # ← 추가
from pydantic_settings import BaseSettings
```

**현재 Line 31**:
```python
MEMORY_LOAD_LIMIT: int = 5  # Number of recent memories to load per user
```

**수정: Line 31 이후 추가**:
```python
MEMORY_LOAD_LIMIT: int = 5  # 기존 유지

# === 3-Tier Memory Configuration ===
SHORTTERM_MEMORY_LIMIT: int = Field(
    default=5,
    description="최근 N개 세션 전체 메시지 로드"
)

MIDTERM_MEMORY_LIMIT: int = Field(
    default=5,
    description="중기 메모리 세션 수 (6-10번째)"
)

LONGTERM_MEMORY_LIMIT: int = Field(
    default=10,
    description="장기 메모리 세션 수 (11-20번째)"
)

MEMORY_TOKEN_LIMIT: int = Field(
    default=2000,
    description="메모리 로드 시 최대 토큰 제한"
)

MEMORY_MESSAGE_LIMIT: int = Field(
    default=10,
    description="Short-term 세션당 최대 메시지 수"
)

SUMMARY_MAX_LENGTH: int = Field(
    default=200,
    description="LLM 요약 최대 글자 수"
)
```

### 1-2. .env 파일 수정

**파일**: `backend/.env`

**현재**:
```bash
# === Long-term Memory Configuration ===
MEMORY_LOAD_LIMIT=5
```

**추가**:
```bash
# === Long-term Memory Configuration ===
MEMORY_LOAD_LIMIT=5

# === 3-Tier Memory Configuration ===
SHORTTERM_MEMORY_LIMIT=5
MIDTERM_MEMORY_LIMIT=5
LONGTERM_MEMORY_LIMIT=10
MEMORY_TOKEN_LIMIT=2000
MEMORY_MESSAGE_LIMIT=10
SUMMARY_MAX_LENGTH=200
```

### 1-3. 검증
```bash
# 서버 재시작 후
python -c "from app.core.config import settings; print(settings.SHORTTERM_MEMORY_LIMIT)"
# 출력: 5
```

---

## Phase 2: 메모리 서비스 확장 (1시간 20분)

### 2-1. import 추가

**파일**: `backend/app/service_agent/foundation/simple_memory_service.py`

**현재 Line 5-8**:
```python
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, desc
```

**수정 후 Line 5-10**:
```python
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio  # ← 추가
import tiktoken  # ← 추가
from sqlalchemy import select, desc, and_  # ← and_ 추가
```

### 2-2. 메서드 추가 (Line 387 이후)

#### A. load_tiered_memories() 메서드

```python
async def load_tiered_memories(
    self,
    user_id: int,
    current_session_id: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    3-Tier 구조의 메모리 로드

    Returns:
        {
            "shortterm": [...],  # 1-5 세션 전체
            "midterm": [...],    # 6-10 세션 요약
            "longterm": [...]    # 11-20 세션 요약
        }
    """
    from app.core.config import settings

    try:
        # 토큰 카운터 초기화
        encoding = tiktoken.get_encoding("cl100k_base")
        total_tokens = 0

        # 최근 20개 세션 조회 (현재 세션 제외)
        query = select(ChatSession).where(
            and_(
                ChatSession.user_id == user_id,
                ChatSession.session_id != current_session_id if current_session_id else True
            )
        ).order_by(
            ChatSession.updated_at.desc()
        ).limit(20)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        tiered_memories = {
            "shortterm": [],
            "midterm": [],
            "longterm": []
        }

        for idx, session in enumerate(sessions):
            # 토큰 제한 체크
            if total_tokens >= settings.MEMORY_TOKEN_LIMIT:
                logger.info(f"Token limit reached: {total_tokens}")
                break

            if idx < settings.SHORTTERM_MEMORY_LIMIT:
                # Short-term: 전체 메시지 (1-5번째)
                messages_query = select(ChatMessage).where(
                    ChatMessage.session_id == session.session_id
                ).order_by(
                    ChatMessage.created_at.desc()
                ).limit(settings.MEMORY_MESSAGE_LIMIT)

                messages_result = await self.db.execute(messages_query)
                messages = messages_result.scalars().all()

                memory_content = {
                    "session_id": session.session_id,
                    "messages": [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.created_at.isoformat()
                        }
                        for msg in reversed(messages)
                    ],
                    "metadata": session.session_metadata or {},
                    "tier": "shortterm"
                }

                # 토큰 계산
                content_text = " ".join([m["content"] for m in memory_content["messages"]])
                tokens = len(encoding.encode(content_text))
                total_tokens += tokens

                tiered_memories["shortterm"].append(memory_content)

            elif idx < settings.SHORTTERM_MEMORY_LIMIT + settings.MIDTERM_MEMORY_LIMIT:
                # Mid-term: LLM 요약 (6-10번째)
                summary = await self._get_or_create_summary(session)

                memory_content = {
                    "session_id": session.session_id,
                    "summary": summary[:settings.SUMMARY_MAX_LENGTH],
                    "metadata": session.session_metadata or {},
                    "tier": "midterm"
                }

                # 토큰 계산
                tokens = len(encoding.encode(summary))
                total_tokens += tokens

                tiered_memories["midterm"].append(memory_content)

            else:
                # Long-term: LLM 요약 (11-20번째)
                summary = await self._get_or_create_summary(session)

                memory_content = {
                    "session_id": session.session_id,
                    "summary": summary[:settings.SUMMARY_MAX_LENGTH],
                    "metadata": session.session_metadata or {},
                    "tier": "longterm"
                }

                # 토큰 계산
                tokens = len(encoding.encode(summary))
                total_tokens += tokens

                tiered_memories["longterm"].append(memory_content)

        logger.info(f"Loaded tiered memories - Tokens: {total_tokens}, "
                   f"Short: {len(tiered_memories['shortterm'])}, "
                   f"Mid: {len(tiered_memories['midterm'])}, "
                   f"Long: {len(tiered_memories['longterm'])}")

        return tiered_memories

    except Exception as e:
        logger.error(f"Error loading tiered memories: {e}")
        return {"shortterm": [], "midterm": [], "longterm": []}
```

#### B. _get_or_create_summary() 메서드

```python
async def _get_or_create_summary(self, session: ChatSession) -> str:
    """세션 요약 가져오기 또는 생성"""
    # JSONB metadata에서 요약 확인
    metadata = session.session_metadata or {}

    if metadata.get("conversation_summary"):
        return metadata["conversation_summary"]

    # 요약이 없으면 생성
    return await self.summarize_with_llm(session.session_id)
```

#### C. summarize_with_llm() 메서드

```python
async def summarize_with_llm(
    self,
    session_id: str,
    max_length: int = 200
) -> str:
    """LLM을 사용한 대화 요약 생성"""
    from app.service_agent.llm_manager.llm_service import LLMService
    from app.core.config import settings

    try:
        # 메시지 로드
        messages_query = select(ChatMessage).where(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at)

        result = await self.db.execute(messages_query)
        messages = result.scalars().all()

        if not messages:
            return "대화 내용 없음"

        # 대화 내용 포맷팅
        conversation = "\n".join([
            f"{msg.role}: {msg.content[:500]}"
            for msg in messages[-10:]  # 최근 10개만
        ])

        # LLM 서비스 초기화
        llm_service = LLMService()

        # 프롬프트 변수
        variables = {
            "conversation": conversation,
            "max_length": max_length
        }

        # LLM 호출
        summary = await llm_service.complete_async(
            prompt_name="conversation_summary",
            variables=variables,
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=100
        )

        # 요약 저장 (백그라운드)
        asyncio.create_task(
            self._save_summary_to_metadata(session_id, summary)
        )

        return summary[:max_length]

    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        return "요약 생성 실패"
```

#### D. _save_summary_to_metadata() 메서드

```python
async def _save_summary_to_metadata(
    self,
    session_id: str,
    summary: str
) -> None:
    """요약을 metadata에 저장 (백그라운드)"""
    try:
        # 세션 조회
        query = select(ChatSession).where(
            ChatSession.session_id == session_id
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return

        # metadata 업데이트
        if session.session_metadata is None:
            session.session_metadata = {}

        session.session_metadata["conversation_summary"] = summary
        session.session_metadata["summary_method"] = "llm"
        session.session_metadata["summary_updated_at"] = datetime.now().isoformat()

        # JSONB 변경 플래그
        flag_modified(session, "session_metadata")

        # DB 업데이트
        await self.db.commit()

        logger.info(f"Summary saved for session: {session_id}")

    except Exception as e:
        logger.error(f"Failed to save summary: {e}")
        # 에러는 로깅만 (fire-and-forget)
```

#### E. summarize_conversation_background() 메서드

```python
async def summarize_conversation_background(
    self,
    session_id: str,
    user_id: int,
    messages: List[Dict[str, Any]]
) -> None:
    """백그라운드에서 대화 요약"""
    # 백그라운드 태스크로 실행
    asyncio.create_task(
        self._background_summary_task(session_id, user_id, messages)
    )
```

#### F. _background_summary_task() 메서드

```python
async def _background_summary_task(
    self,
    session_id: str,
    user_id: int,
    messages: List[Dict[str, Any]]
) -> None:
    """백그라운드 요약 태스크"""
    try:
        # LLM 요약 생성
        summary = await self.summarize_with_llm(session_id)

        # metadata 저장
        await self._save_summary_to_metadata(session_id, summary)

        logger.info(f"Background summary completed: {session_id}")

    except Exception as e:
        logger.error(f"Background summary failed: {e}")
        # 에러는 로깅만
```

### 2-3. 검증

```python
# Python REPL에서 확인
from app.service_agent.foundation.simple_memory_service import SimpleMemoryService
import inspect

# 메서드 존재 확인
print(hasattr(SimpleMemoryService, 'load_tiered_memories'))  # True
print(hasattr(SimpleMemoryService, 'summarize_with_llm'))  # True
```

---

## Phase 3: Supervisor 통합 (50분)

### 3-1. planning_node 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**위치**: Line 235-263 (planning_node 메서드 내부)

**현재 코드**:
```python
user_id = state.get("user_id")
chat_session_id = state.get("chat_session_id")
if user_id:
    try:
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            loaded_memories = await memory_service.load_recent_memories(
                user_id=user_id,
                limit=settings.MEMORY_LOAD_LIMIT,
                relevance_filter="RELEVANT",
                session_id=chat_session_id
            )

            user_preferences = await memory_service.get_user_preferences(user_id)

            state["loaded_memories"] = loaded_memories
            state["user_preferences"] = user_preferences
            state["memory_load_time"] = datetime.now().isoformat()

            logger.info(f"Loaded {len(loaded_memories)} memories")
            break
    except Exception as e:
        logger.error(f"Failed to load Long-term Memory: {e}")
```

**수정 후**:
```python
user_id = state.get("user_id")
chat_session_id = state.get("chat_session_id")
if user_id:
    try:
        logger.info(f"Loading 3-Tier Memory for user {user_id}")
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            # 3-Tier 메모리 로드
            tiered_memories = await memory_service.load_tiered_memories(
                user_id=user_id,
                current_session_id=chat_session_id
            )

            # 하위 호환성: loaded_memories 유지
            loaded_memories = (
                tiered_memories.get("shortterm", []) +
                tiered_memories.get("midterm", []) +
                tiered_memories.get("longterm", [])
            )

            # State 업데이트
            state["loaded_memories"] = loaded_memories
            state["tiered_memories"] = tiered_memories  # 신규 필드

            # 사용자 선호도 로드 (기존 유지)
            user_preferences = await memory_service.get_user_preferences(user_id)
            state["user_preferences"] = user_preferences
            state["memory_load_time"] = datetime.now().isoformat()

            # 로깅
            logger.info(
                f"3-Tier memories loaded - "
                f"Short({len(tiered_memories.get('shortterm', []))}), "
                f"Mid({len(tiered_memories.get('midterm', []))}), "
                f"Long({len(tiered_memories.get('longterm', []))})"
            )

            break
    except Exception as e:
        logger.error(f"Failed to load tiered memories: {e}")
        state["loaded_memories"] = []
        state["tiered_memories"] = {
            "shortterm": [],
            "midterm": [],
            "longterm": []
        }
```

### 3-2. generate_response_node 수정

**위치**: Line 870 근처 (generate_response_node 메서드 내부)

**현재 코드**:
```python
user_id = state.get("user_id")
if user_id and intent_type not in ["irrelevant", "unclear"]:
    try:
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            response_summary = response.get("summary", "")
            if not response_summary and response.get("answer"):
                response_summary = response.get("answer", "")[:200]
            if not response_summary:
                response_summary = f"{response.get('type', 'response')} 생성 완료"

            chat_session_id = state.get("chat_session_id")

            await memory_service.save_conversation(
                user_id=user_id,
                session_id=chat_session_id,
                messages=[],
                summary=response_summary
            )

            logger.info("Conversation saved to Long-term Memory")
            break
    except Exception as e:
        logger.error(f"Failed to save Long-term Memory: {e}")
```

**수정 후 (백그라운드 요약 추가)**:
```python
user_id = state.get("user_id")
if user_id and intent_type not in ["irrelevant", "unclear"]:
    try:
        logger.info(f"Saving conversation to Long-term Memory for user {user_id}")
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            chat_session_id = state.get("chat_session_id")

            # 백그라운드 요약 시작 (fire-and-forget)
            await memory_service.summarize_conversation_background(
                session_id=chat_session_id,
                user_id=user_id,
                messages=[]
            )

            # 응답 요약 생성 (기존 로직 유지)
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

            logger.info("Conversation saved to Long-term Memory")
            break
    except Exception as e:
        logger.error(f"Failed to save Long-term Memory: {e}")
```

---

## Phase 4: Planning Agent 수정 (30분)

### 4-1. planning_agent.py 수정

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**위치**: PlanningAgent 클래스의 적절한 메서드 내부

**추가할 코드**:
```python
# State에서 3-Tier 메모리 가져오기
tiered_memories = state.get("tiered_memories", {})

memory_context = ""
if tiered_memories:
    # Short-term: 전체 대화
    if tiered_memories.get("shortterm"):
        memory_context += "=== 최근 대화 (전체) ===\n"
        for mem in tiered_memories["shortterm"]:
            for msg in mem.get("messages", []):
                memory_context += f"{msg['role']}: {msg['content'][:100]}...\n"
            memory_context += "\n"

    # Mid-term: 요약
    if tiered_memories.get("midterm"):
        memory_context += "=== 중기 대화 (요약) ===\n"
        for mem in tiered_memories["midterm"]:
            memory_context += f"- {mem.get('summary', '')}\n"
        memory_context += "\n"

    # Long-term: 요약
    if tiered_memories.get("longterm"):
        memory_context += "=== 장기 대화 (요약) ===\n"
        for mem in tiered_memories["longterm"]:
            memory_context += f"- {mem.get('summary', '')}\n"

# 프롬프트 변수에 추가
variables["memory_context"] = memory_context
```

---

## Phase 5: 프롬프트 파일 생성 (20분)

### 5-1. conversation_summary.txt 생성

**파일**: `backend/app/service_agent/llm_manager/prompts/common/conversation_summary.txt`

**내용**:
```text
당신은 대화 내용을 간결하게 요약하는 전문가입니다.

다음 대화를 {max_length}자 이내로 요약해주세요:

{conversation}

요약 규칙:
1. 핵심 주제와 결론만 포함
2. 사용자의 주요 요구사항 명시
3. 중요한 결정사항이나 합의 내용 포함
4. 불필요한 인사말이나 반복 제외

요약:
```

### 5-2. 검증

```python
# Python REPL에서 확인
from app.service_agent.llm_manager.prompt_manager import PromptManager

pm = PromptManager()
prompt = pm.get('conversation_summary', {
    'conversation': '테스트 대화',
    'max_length': 100
})
print("SUCCESS" if prompt else "FAILED")
```

---

## Phase 6: 테스트 (50분)

### 6-1. 테스트 파일 생성

**파일**: `backend/test_3tier_memory.py`

**내용**:
```python
import pytest
import pytest_asyncio
from app.db.postgre_db import get_async_db
from app.service_agent.foundation.simple_memory_service import SimpleMemoryService
from app.core.config import settings

@pytest_asyncio.fixture
async def db_session():
    """비동기 DB 세션 fixture"""
    async for session in get_async_db():
        yield session
        break

@pytest.mark.asyncio
async def test_3tier_memory_loading(db_session):
    """3-Tier 메모리 로드 테스트"""
    memory_service = SimpleMemoryService(db_session)

    tiered = await memory_service.load_tiered_memories(
        user_id=1,
        current_session_id="test-session"
    )

    assert "shortterm" in tiered
    assert "midterm" in tiered
    assert "longterm" in tiered

    # 각 티어가 리스트인지 확인
    assert isinstance(tiered["shortterm"], list)
    assert isinstance(tiered["midterm"], list)
    assert isinstance(tiered["longterm"], list)

@pytest.mark.asyncio
async def test_llm_summarization(db_session):
    """LLM 요약 생성 테스트"""
    memory_service = SimpleMemoryService(db_session)

    summary = await memory_service.summarize_with_llm(
        session_id="test-session",
        max_length=200
    )

    assert isinstance(summary, str)
    assert len(summary) <= 200
```

### 6-2. 테스트 실행

```bash
# 특정 테스트만 실행
pytest backend/test_3tier_memory.py::test_3tier_memory_loading -v

# 전체 테스트
pytest backend/test_3tier_memory.py -v
```

---

## 추가: separated_states.py 수정 (선택)

### tiered_memories 필드 추가

**파일**: `backend/app/service_agent/foundation/separated_states.py`

**위치**: Line 332 이후 (MainSupervisorState 클래스)

**추가**:
```python
# Long-term Memory Fields
user_id: Optional[int]
loaded_memories: Optional[List[Dict[str, Any]]]
user_preferences: Optional[Dict[str, Any]]
memory_load_time: Optional[str]

# 3-Tier Memory (신규)
tiered_memories: Optional[Dict[str, List[Dict[str, Any]]]]  # ← 추가
```

---

## 📋 구현 체크리스트

### Phase 1: 설정 (15분)
- [ ] config.py - Line 2에 `from pydantic import Field` 추가
- [ ] config.py - Line 31 이후 6개 Field 추가
- [ ] .env - 6개 환경변수 추가
- [ ] 서버 재시작 후 설정 로드 확인

### Phase 2: 메모리 서비스 (1시간 20분)
- [ ] simple_memory_service.py - Line 5에 `import asyncio` 추가
- [ ] simple_memory_service.py - Line 6에 `import tiktoken` 추가
- [ ] simple_memory_service.py - Line 8에 `and_` 추가
- [ ] `load_tiered_memories()` 메서드 추가
- [ ] `_get_or_create_summary()` 메서드 추가
- [ ] `summarize_with_llm()` 메서드 추가
- [ ] `_save_summary_to_metadata()` 메서드 추가
- [ ] `summarize_conversation_background()` 메서드 추가
- [ ] `_background_summary_task()` 메서드 추가

### Phase 3: Supervisor (50분)
- [ ] team_supervisor.py - planning_node (Line 235-263) 수정
- [ ] team_supervisor.py - generate_response_node (Line 870~) 수정
- [ ] 로그로 3-Tier 로드 확인

### Phase 4: Planning Agent (30분)
- [ ] planning_agent.py - tiered_memories 활용 로직 추가

### Phase 5: 프롬프트 (20분)
- [ ] conversation_summary.txt 생성
- [ ] 프롬프트 로드 테스트

### Phase 6: 테스트 (50분)
- [ ] test_3tier_memory.py 생성
- [ ] db_session fixture 추가
- [ ] 테스트 실행 및 통과 확인

### 선택: State 정의 (5분)
- [ ] separated_states.py - tiered_memories 필드 추가

---

## ⚠️ 주의사항

### 1. import 반드시 추가
```python
# simple_memory_service.py 상단
import asyncio
import tiktoken
from sqlalchemy import select, desc, and_
```

### 2. 정확한 수정 위치
- ❌ explore_node (존재하지 않음)
- ✅ planning_node (Line 235-263)
- ❌ execute_node (존재하지 않음)
- ✅ generate_response_node (Line 870~)

### 3. 메서드 시그니처
```python
# 정확한 파라미터 순서
await memory_service.save_conversation(
    user_id=user_id,          # 첫 번째
    session_id=chat_session_id,  # 두 번째
    messages=[],              # 세 번째 (conversation_history 아님!)
    summary=response_summary  # 네 번째
)
```

### 4. tiktoken 설치
```bash
pip install tiktoken
```

---

## 📊 예상 소요 시간

| Phase | 작업 | 시간 |
|-------|------|------|
| Phase 1 | 설정 파일 | 15분 |
| Phase 2 | 메모리 서비스 | 1시간 20분 |
| Phase 3 | Supervisor 통합 | 50분 |
| Phase 4 | Planning Agent | 30분 |
| Phase 5 | 프롬프트 | 20분 |
| Phase 6 | 테스트 | 50분 |
| **총합** | | **3시간 45분** |

---

## 🚀 시작하기

### 사전 준비
```bash
# 1. 백업 생성
cp backend/app/core/config.py backend/app/core/config.py.backup
cp backend/app/service_agent/foundation/simple_memory_service.py backend/app/service_agent/foundation/simple_memory_service.py.backup
cp backend/app/service_agent/supervisor/team_supervisor.py backend/app/service_agent/supervisor/team_supervisor.py.backup
cp backend/.env backend/.env.backup

# 2. 의존성 설치
pip install tiktoken pytest-asyncio
```

### 구현 순서
1. Phase 1부터 순차적으로 진행
2. 각 Phase 완료 후 체크리스트 확인
3. Phase 3, 6에서 테스트 실행
4. 문제 발생 시 백업 파일로 복구

---

**작성 완료**: 2025-10-21
**다음 단계**: Phase 1부터 구현 시작
