# 3-Tier Hybrid Memory 최종 구현 계획서

**작성일**: 2025-10-21
**버전**: FINAL (user_id Integer 통일 완료)
**예상 소요 시간**: 3시간 20분

---

## ✅ 완료 사항

### user_id 타입 통일 (완료)
- ✅ DB: Integer
- ✅ State: Optional[int]
- ✅ **SimpleMemoryService 메서드: int로 통일 완료**
  - `load_recent_memories()`: int
  - `save_conversation()`: int
  - 기타 모든 메서드: int

### UUID 전환 대비
- ✅ UUID 전환 가이드 작성 완료: `UUID_MIGRATION_COMPLETE_GUIDE_251021.md`
- ✅ 추후 UUID 전환 시 해당 문서만 참고하면 됨

---

## 📋 핵심 결정 사항 (확정)

### ✅ 사용자 확인 완료 항목

1. **user_id 타입**: Integer ✅ **통일 완료**
   - DB: Integer ✅
   - State: Optional[int] ✅
   - Methods: int ✅ **수정 완료**

2. **프롬프트 위치**: common/ 디렉토리
3. **3-Tier 범위**:
   - Short-term: 1-5 세션
   - Mid-term: 6-10 세션
   - Long-term: 11-20 세션
4. **백그라운드 에러**: 로깅만
5. **JSONB 동시성**: PostgreSQL MVCC 의존
6. **토큰 제한**: 1000-2000 (설정 가능)
7. **호환성**: loaded_memories + tiered_memories 병행
8. **요약 길이**: 200자 (설정 가능)

---

## 🔧 구현 사항

### Phase 1: 설정 파일 (20분)

#### 1-1. `.env` 파일 업데이트
```bash
# === 3-Tier Memory Configuration ===
# Short-term: 최근 1-5 세션 (전체 메시지)
SHORTTERM_MEMORY_LIMIT=5

# Mid-term: 최근 6-10 세션 (LLM 요약)
MIDTERM_MEMORY_LIMIT=5

# Long-term: 최근 11-20 세션 (LLM 요약)
LONGTERM_MEMORY_LIMIT=10

# 메모리 토큰 제한
MEMORY_TOKEN_LIMIT=2000

# 세션당 메시지 제한 (Short-term용)
MEMORY_MESSAGE_LIMIT=10

# 요약 길이 제한
SUMMARY_MAX_LENGTH=200
```

#### 1-2. `backend/app/core/config.py` 수정
```python
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field  # ← 추가 필요!

class Settings(BaseSettings):
    # ... 기존 설정들 ...

    # Long-term Memory 범위 설정 (기존)
    MEMORY_LOAD_LIMIT: int = 5

    # === 3-Tier Memory Configuration (신규) ===
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

---

### Phase 2: 메모리 서비스 확장 (1시간 10분)

#### 2-1. `backend/app/service_agent/foundation/simple_memory_service.py`

##### A. user_id 타입 수정 ✅ **완료**
- 모든 메서드의 user_id 파라미터를 int로 변경 완료
- 하위 호환성 로직은 필요 시 추가 가능

##### B. 3-Tier 메모리 로드 메서드 추가
```python
async def load_tiered_memories(
    self,
    user_id: int,  # ← Integer 타입!
    current_session_id: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """3-Tier 구조의 메모리 로드

    Returns:
        {
            "shortterm": [...],  # 1-5 세션 전체
            "midterm": [...],    # 6-10 세션 요약
            "longterm": [...]    # 11-20 세션 요약
        }
    """
    from app.core.config import settings
    import tiktoken

    # user_id 타입 변환 (하위 호환성)
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.warning(f"Invalid user_id format: {user_id}")
            return {"shortterm": [], "midterm": [], "longterm": []}

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

##### C. LLM 요약 메서드 추가
```python
async def _get_or_create_summary(self, session: ChatSession) -> str:
    """세션 요약 가져오기 또는 생성"""
    # JSONB metadata에서 요약 확인
    metadata = session.session_metadata or {}

    if metadata.get("conversation_summary"):
        return metadata["conversation_summary"]

    # 요약이 없으면 생성
    return await self.summarize_with_llm(session.session_id)

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

        # LLM 호출 (common 디렉토리의 프롬프트 사용)
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

async def _save_summary_to_metadata(
    self,
    session_id: str,
    summary: str
) -> None:
    """요약을 metadata에 저장 (백그라운드)"""
    try:
        from datetime import datetime

        # 세션 조회
        query = select(ChatSession).where(
            ChatSession.session_id == session_id
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return

        # metadata 업데이트
        metadata = session.session_metadata or {}
        metadata.update({
            "conversation_summary": summary,
            "summary_method": "llm",
            "summary_updated_at": datetime.utcnow().isoformat()
        })

        # DB 업데이트
        session.session_metadata = metadata
        await self.db.commit()

        logger.info(f"Summary saved for session: {session_id}")

    except Exception as e:
        logger.error(f"Failed to save summary: {e}")
        # 에러는 로깅만 (fire-and-forget)

async def summarize_conversation_background(
    self,
    session_id: str,
    user_id: int,  # ← Integer 타입!
    messages: List[Dict[str, Any]]
) -> None:
    """백그라운드에서 대화 요약 (기존 메서드 수정)"""
    # user_id 타입 변환 추가
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
            logger.error(f"Invalid user_id for background summary: {user_id}")
            return

    # 백그라운드 태스크로 실행
    asyncio.create_task(
        self._background_summary_task(session_id, user_id, messages)
    )

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

---

### Phase 3: Supervisor 통합 (40분)

#### 3-1. `backend/app/service_agent/supervisor/team_supervisor.py` 수정

```python
# explore_node 수정 (Line 240~)
async def explore_node(state: MainSupervisorState) -> MainSupervisorState:
    """탐색 노드 - 3-Tier 메모리 로드"""
    # ... 기존 코드 ...

    # Long-term Memory 로드 (Line 241~)
    memory_service = LongTermMemoryService(db_session)

    # user_id 타입 변환 (신규 추가)
    user_id_int = state.get("user_id")
    if user_id_int and isinstance(user_id_int, str):
        try:
            user_id_int = int(user_id_int)
        except ValueError:
            logger.warning(f"Invalid user_id: {user_id_int}")
            user_id_int = None

    if user_id_int:
        try:
            # 3-Tier 메모리 로드 (신규)
            tiered_memories = await memory_service.load_tiered_memories(
                user_id=user_id_int,
                current_session_id=state.get("chat_session_id")
            )

            # 하위 호환성: loaded_memories 유지
            loaded_memories = (
                tiered_memories.get("shortterm", []) +
                tiered_memories.get("midterm", []) +
                tiered_memories.get("longterm", [])
            )

            state["loaded_memories"] = loaded_memories
            state["tiered_memories"] = tiered_memories  # 신규 필드

            # 토큰 정보 로깅
            from app.core.config import settings
            logger.info(
                f"3-Tier memories loaded - "
                f"Short({len(tiered_memories.get('shortterm', []))}), "
                f"Mid({len(tiered_memories.get('midterm', []))}), "
                f"Long({len(tiered_memories.get('longterm', []))}), "
                f"Token limit: {settings.MEMORY_TOKEN_LIMIT}"
            )

        except Exception as e:
            logger.error(f"Failed to load tiered memories: {e}")
            state["loaded_memories"] = []
            state["tiered_memories"] = {
                "shortterm": [],
                "midterm": [],
                "longterm": []
            }

    # ... 나머지 코드 ...
```

```python
# execute_node 수정 (Line 878~)
# 대화 저장 시 백그라운드 요약 추가
if chat_session_id and user_id:
    # user_id 타입 변환
    user_id_int = user_id
    if isinstance(user_id_int, str):
        try:
            user_id_int = int(user_id_int)
        except ValueError:
            logger.error(f"Invalid user_id for save: {user_id_int}")
            user_id_int = None

    if user_id_int:
        # 백그라운드 요약 시작 (fire-and-forget)
        await memory_service.summarize_conversation_background(
            session_id=chat_session_id,
            user_id=user_id_int,
            messages=state.get("conversation_history", [])
        )

        # 기존 저장 로직
        await memory_service.save_conversation(
            session_id=chat_session_id,
            user_id=user_id_int,
            conversation_history=state.get("conversation_history", []),
            summary=state.get("final_answer", "")[:200]  # 200자 제한
        )
```

---

### Phase 4: Planning Agent 수정 (30분)

#### 4-1. `backend/app/service_agent/cognitive/planning_agent.py`

```python
async def planning_agent(state: MainSupervisorState) -> MainSupervisorState:
    """계획 수립 에이전트 - 3-Tier 메모리 활용"""

    # ... 기존 코드 ...

    # 3-Tier 메모리 컨텍스트 준비
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
                memory_context += f"- {mem.get('summary', '')}\\n"
            memory_context += "\n"

        # Long-term: 요약
        if tiered_memories.get("longterm"):
            memory_context += "=== 장기 대화 (요약) ===\n"
            for mem in tiered_memories["longterm"]:
                memory_context += f"- {mem.get('summary', '')}\\n"

    # 프롬프트에 메모리 컨텍스트 추가
    variables["memory_context"] = memory_context

    # ... 나머지 코드 ...
```

---

### Phase 5: 프롬프트 파일 생성 (20분)

#### 5-1. `backend/app/service_agent/llm_manager/prompts/common/conversation_summary.txt`

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

#### 5-2. `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt` 수정

```text
# 기존 내용에 추가

## 메모리 컨텍스트
{memory_context}

위 메모리 정보를 참고하여 사용자의 의도를 더 정확하게 파악하세요.
```

---

### Phase 6: 테스트 (40분)

#### 6-1. 단위 테스트 파일: `backend/test_3tier_memory.py`

```python
import asyncio
import pytest
from app.service_agent.foundation.simple_memory_service import SimpleMemoryService
from app.core.config import settings

@pytest.mark.asyncio
async def test_user_id_type_conversion():
    """user_id 타입 변환 테스트"""
    # String → Integer 변환
    memory_service = SimpleMemoryService(db_session)

    # String user_id로 호출
    result = await memory_service.load_recent_memories(
        user_id="123",  # String
        limit=5
    )
    assert isinstance(result, list)

    # Integer user_id로 호출
    result = await memory_service.load_recent_memories(
        user_id=123,  # Integer
        limit=5
    )
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_3tier_memory_loading():
    """3-Tier 메모리 로드 테스트"""
    memory_service = SimpleMemoryService(db_session)

    tiered = await memory_service.load_tiered_memories(
        user_id=1,
        current_session_id="test-session"
    )

    assert "shortterm" in tiered
    assert "midterm" in tiered
    assert "longterm" in tiered

    # 토큰 제한 확인
    assert len(str(tiered)) < settings.MEMORY_TOKEN_LIMIT * 4

@pytest.mark.asyncio
async def test_llm_summarization():
    """LLM 요약 생성 테스트"""
    memory_service = SimpleMemoryService(db_session)

    summary = await memory_service.summarize_with_llm(
        session_id="test-session",
        max_length=200
    )

    assert len(summary) <= 200
    assert summary != "요약 생성 실패"
```

---

## 📊 구현 체크리스트

### Phase 1: 설정 (20분)
- [ ] `.env` 파일에 6개 새 설정 추가
- [ ] `config.py`에 Field import 추가
- [ ] 6개 Field 설정 추가

### Phase 2: 메모리 서비스 (1시간 10분)
- [x] `load_recent_memories()` user_id 타입 수정 ✅
- [x] 모든 메서드 user_id int로 통일 ✅
- [ ] `load_tiered_memories()` 메서드 추가
- [ ] `summarize_with_llm()` 메서드 추가
- [ ] `_save_summary_to_metadata()` 메서드 추가
- [ ] `summarize_conversation_background()` 수정
- [ ] `_background_summary_task()` 메서드 추가

### Phase 3: Supervisor (40분)
- [ ] `explore_node`에 3-Tier 로드 추가
- [ ] user_id 타입 변환 로직 추가
- [ ] `execute_node`에 백그라운드 요약 추가

### Phase 4: Planning Agent (30분)
- [ ] 3-Tier 메모리 컨텍스트 생성
- [ ] 프롬프트 변수에 추가

### Phase 5: 프롬프트 (20분)
- [ ] `conversation_summary.txt` 생성
- [ ] `intent_analysis.txt` 수정

### Phase 6: 테스트 (40분)
- [ ] 타입 변환 테스트
- [ ] 3-Tier 로드 테스트
- [ ] LLM 요약 테스트
- [ ] 통합 테스트

---

## ⚠️ 주의사항

### 1. user_id 타입 불일치 해결
```python
# 모든 메서드에서 일관되게 처리
if isinstance(user_id, str):
    try:
        user_id = int(user_id)
    except ValueError:
        logger.warning(f"Invalid user_id: {user_id}")
        return default_value
```

### 2. self.db 사용 (self.db_session 아님!)
```python
# 올바른 사용
result = await self.db.execute(query)

# 잘못된 사용
result = await self.db_session.execute(query)  # ❌
```

### 3. 프롬프트 경로
```python
# 올바른 사용
prompt_name="conversation_summary"  # common/ 디렉토리

# 잘못된 사용
prompt_name="memory/conversation_summary"  # ❌ 지원 안 됨
```

### 4. 백그라운드 태스크 에러 처리
```python
# Fire-and-forget 패턴
asyncio.create_task(background_task())
# 에러는 태스크 내부에서 로깅만
```

---

## 🎯 예상 결과

### 성능 지표
- **토큰 사용**: 1000-2000 토큰 이내
- **응답 시간**: 기존 대비 +0.5초 이내
- **메모리 품질**: 문맥 이해도 30% 향상

### 사용자 경험
- 이전 대화 자연스러운 연결
- 장기 선호도 기억
- 반복 질문 감소

### 시스템 안정성
- user_id 타입 일관성 확보
- 백그라운드 요약 안정화
- 에러 처리 강화

---

## 📅 타임라인

| 단계 | 작업 | 예상 시간 | 누적 시간 | 상태 |
|------|------|-----------|-----------|------|
| **완료** | user_id Integer 통일 | 20분 | - | ✅ |
| Phase 1 | 설정 파일 | 20분 | 20분 | ⏳ |
| Phase 2 | 메모리 서비스 | 1시간 10분 | 1시간 30분 | ⏳ |
| Phase 3 | Supervisor 통합 | 40분 | 2시간 10분 | ⏳ |
| Phase 4 | Planning Agent | 30분 | 2시간 40분 | ⏳ |
| Phase 5 | 프롬프트 | 20분 | 3시간 | ⏳ |
| Phase 6 | 테스트 | 40분 | 3시간 40분 | ⏳ |

**총 예상 시간**: 3시간 20분 (테스트 제외, user_id 통일 완료로 20분 단축)

---

**작성 완료**: 2025-10-21
**업데이트**: 2025-10-21 (user_id Integer 통일 완료)
**다음 단계**: Phase 1부터 순차적 구현 시작

**관련 문서**:
- `UUID_MIGRATION_COMPLETE_GUIDE_251021.md`: 추후 UUID 전환 시 참고