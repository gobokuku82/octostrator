# 3-Tier Hybrid Memory 구현 계획서 (최종본 v3.0)

**작성일**: 2025-10-20
**최종 수정**: 2025-10-20
**버전**: 3.0 (Final)
**예상 소요시간**: 3시간 20분

---

## 🎯 개요

### 목적
기존 Long-term Memory를 **3-Tier Hybrid Memory** 구조로 개선하여 더 풍부한 맥락 제공

### 현재 상황
- ✅ **Option A 완료**: Chat History를 Intent 분석에 추가 (현재 대화창 최근 6개 메시지)
- ✅ **Long-term Memory 구현됨**: `team_supervisor.py:235-259`에서 다른 대화창 요약 5개 로드
- ⚠️ **개선 필요**: 요약이 단순 잘라내기(`[:200]`)로 되어 있어 맥락 손실

### 3-Tier Hybrid Memory 구조 (확정)

```
┌─────────────────────────────────────────────────────────┐
│ Short-term Memory (1-5 sessions)                        │
│ - 전체 메시지 내용 (요약 없음)                           │
│ - 가장 상세한 맥락 제공                                  │
│ - Intent 분석에 최우선 사용                              │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ Mid-term Memory (6-10 sessions)                         │
│ - LLM 요약본 (GPT-4o-mini, 200자)                       │
│ - 핵심 내용만 압축                                       │
│ - Intent 분석 보조 자료                                  │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ Long-term Memory (11-20 sessions)                       │
│ - LLM 요약본 (GPT-4o-mini, 200자)                       │
│ - 간략한 요약 (참고용)                                   │
│ - 사용자 패턴 파악용                                     │
└─────────────────────────────────────────────────────────┘
```

**설정 가능 항목**:
- 각 Tier의 세션 개수 (SHORTTERM_MEMORY_LIMIT, MIDTERM_MEMORY_LIMIT, LONGTERM_MEMORY_LIMIT)
- 각 Tier의 요약 길이 (SUMMARY_MAX_LENGTH_MIDTERM, SUMMARY_MAX_LENGTH_LONGTERM)
- 각 Tier 활성화 여부 (SHORTTERM_MEMORY_ENABLED, etc.)

---

## 🔧 구현 전 검증 결과

### 코드 검증 완료 ✅
**검증 보고서**: `reports/analysis/HYBRID_MEMORY_PLAN_VALIDATION_251020.md`

### 발견된 주요 이슈 (수정됨)

#### 🔴 Critical Issue 1: Field Import 누락
**문제**: `config.py`에 `from pydantic import Field` 없음
**해결**: Step 1에서 import 추가

#### 🔴 Critical Issue 2: 기존 Long-term Memory 로직과 충돌
**문제**: `team_supervisor.py:235-259`에 기존 Long-term Memory 로직 존재
**해결**: 기존 로직을 **통합(Integration)**하는 방식으로 변경 (교체 X)

#### 🔴 Critical Issue 3: team_supervisor.py Import 중복
**문제**: `settings` import가 이미 존재 (Line 22)
**해결**: Step 3-1 삭제 (import 추가 불필요)

#### ⚠️ High Issue 4-5: Import 누락
**문제**: `simple_memory_service.py`에 필요한 import 누락
**해결**: Step 2에서 import 명시

#### 💡 Low Issue 6: Directory 누락
**문제**: `prompts/memory/` 디렉토리가 없을 수 있음
**해결**: Step 2에서 디렉토리 생성 추가

---

## 📋 구현 단계

### Step 0: 준비 (5분)

#### 0-1. 현재 브랜치 확인 및 백업
```bash
# 현재 상태 확인
git status
git log --oneline -5

# 백업 브랜치 생성
git checkout -b backup-before-3tier-memory

# 작업 브랜치로 전환
git checkout main
git checkout -b feature/3tier-hybrid-memory
```

#### 0-2. 기존 코드 위치 확인
```bash
# 검증된 파일 위치
backend/app/core/config.py                   # Line 31: MEMORY_LOAD_LIMIT
backend/.env                                  # Line 27: MEMORY_LOAD_LIMIT=5
backend/app/service_agent/foundation/simple_memory_service.py  # Line 1-20
backend/app/service_agent/supervisor/team_supervisor.py        # Line 22 (settings import 있음)
backend/app/service_agent/cognitive_agents/planning_agent.py   # Line 183-213
backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt  # Line 203-218
```

---

### Step 1: 설정 파일 수정 (15분)

#### 1-1. `backend/app/core/config.py` 수정

**현재 코드** (Line 1-5):
```python
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...
```

**수정 내용**:
```python
from typing import List
from pydantic import Field  # ✅ 추가: Critical Issue 1 해결
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...
```

**현재 코드** (Line 31 근처):
```python
MEMORY_LOAD_LIMIT: int = 5  # Number of recent memories to load per user
```

**추가할 설정** (Line 31 이후):
```python
    # ========================================
    # 3-Tier Hybrid Memory Settings (NEW)
    # ========================================

    # Short-term Memory: 최근 1-5개 세션 (전체 메시지)
    SHORTTERM_MEMORY_LIMIT: int = Field(
        default=5,
        description="최근 대화 세션 수 (전체 메시지 로드)"
    )
    SHORTTERM_MEMORY_ENABLED: bool = Field(
        default=True,
        description="Short-term Memory 활성화 여부"
    )

    # Mid-term Memory: 6-10개 세션 (LLM 요약)
    MIDTERM_MEMORY_LIMIT: int = Field(
        default=5,
        description="중기 대화 세션 수 (LLM 요약 로드, offset=5)"
    )
    MIDTERM_MEMORY_ENABLED: bool = Field(
        default=True,
        description="Mid-term Memory 활성화 여부"
    )

    # Long-term Memory: 11-20개 세션 (LLM 요약)
    LONGTERM_MEMORY_LIMIT: int = Field(
        default=10,
        description="장기 대화 세션 수 (LLM 요약 로드, offset=10)"
    )
    LONGTERM_MEMORY_ENABLED: bool = Field(
        default=True,
        description="Long-term Memory 활성화 여부"
    )

    # LLM Summarization Settings
    SUMMARY_METHOD: str = Field(
        default="llm",
        description="요약 방식: 'llm' (LLM 요약) 또는 'simple' (단순 잘라내기)"
    )
    SUMMARY_LLM_MODEL: str = Field(
        default="gpt-4o-mini",
        description="요약에 사용할 LLM 모델"
    )

    # 각 Tier별 요약 길이 설정 (Option A: 동일하지만 설정 가능)
    SUMMARY_MAX_LENGTH_MIDTERM: int = Field(
        default=200,
        description="Mid-term Memory 요약 최대 길이 (문자 수)"
    )
    SUMMARY_MAX_LENGTH_LONGTERM: int = Field(
        default=200,
        description="Long-term Memory 요약 최대 길이 (문자 수)"
    )

    SUMMARY_BACKGROUND: bool = Field(
        default=True,
        description="백그라운드에서 요약 생성 여부 (비동기)"
    )

    # Backward Compatibility
    # MEMORY_LOAD_LIMIT는 유지 (기존 코드 호환성)
    MEMORY_LOAD_LIMIT: int = 5  # ← 기존 설정 유지
```

#### 1-2. `backend/.env` 수정

**현재 코드** (Line 27):
```bash
MEMORY_LOAD_LIMIT=5
```

**추가할 설정** (Line 27 이후):
```bash
# ========================================
# 3-Tier Hybrid Memory Settings (NEW)
# ========================================

# Short-term Memory (1-5 sessions, full messages)
SHORTTERM_MEMORY_LIMIT=5
SHORTTERM_MEMORY_ENABLED=true

# Mid-term Memory (6-10 sessions, LLM summary)
MIDTERM_MEMORY_LIMIT=5
MIDTERM_MEMORY_ENABLED=true

# Long-term Memory (11-20 sessions, LLM summary)
LONGTERM_MEMORY_LIMIT=10
LONGTERM_MEMORY_ENABLED=true

# LLM Summarization
SUMMARY_METHOD=llm
SUMMARY_LLM_MODEL=gpt-4o-mini
SUMMARY_MAX_LENGTH_MIDTERM=200
SUMMARY_MAX_LENGTH_LONGTERM=200
SUMMARY_BACKGROUND=true

# Backward Compatibility
MEMORY_LOAD_LIMIT=5
```

**검증**:
```bash
# .env 파일 확인
grep -E "(SHORTTERM_MEMORY|MIDTERM_MEMORY|LONGTERM_MEMORY|SUMMARY_)" backend/.env
```

---

### Step 2: LLM 요약 메서드 추가 (40분)

#### 2-1. 디렉토리 생성
```bash
# prompts/memory 디렉토리가 없을 수 있으므로 생성
mkdir -p backend/app/service_agent/llm_manager/prompts/memory
```

#### 2-2. `prompts/memory/conversation_summary.txt` 생성

**파일**: `backend/app/service_agent/llm_manager/prompts/memory/conversation_summary.txt`

**내용**:
```markdown
# 대화 요약 생성

당신은 부동산 상담 대화를 간결하게 요약하는 AI입니다.

## 📝 요약 대상 대화

{conversation_text}

---

## 🎯 요약 지침

1. **핵심만 추출**: 사용자가 질문한 내용과 AI가 답변한 핵심 정보만 포함
2. **간결하게**: 최대 {max_length}자 이내
3. **맥락 유지**: 나중에 이 요약만 보고도 대화 주제를 파악할 수 있어야 함
4. **키워드 포함**: 지역, 매물 유형, 가격대, 특이사항 등

## 📊 출력 형식

한 문장 또는 두 문장으로 요약하세요. 예시:

- "강남구 아파트 전세 시세 조회 (5억~7억 범위, 대치동/개포동 중심)"
- "송파구 투자 분석 및 리스크 평가 (신축 아파트 선호)"
- "강남구와 송파구 전세 시세 비교 (강남구 평균 6억, 송파구 평균 5억)"

---

**요약을 생성하세요 (최대 {max_length}자):**
```

#### 2-3. `simple_memory_service.py` 수정

**파일**: `backend/app/service_agent/foundation/simple_memory_service.py`

**현재 Import 섹션** (Line 1-14):
```python
"""
SimpleMemoryService - Memory 테이블 없이 chat_messages만 사용
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)
```

**추가할 Import** (✅ High Issue 해결):
```python
"""
SimpleMemoryService - Memory 테이블 없이 chat_messages만 사용
"""

import logging
import asyncio  # ✅ 추가: Background task용
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone  # ✅ timezone 추가
from sqlalchemy import select, desc, and_, or_, func  # ✅ and_ 추가
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.chat import ChatMessage, ChatSession
from app.core.config import settings  # ✅ 추가: settings 사용
from app.service_agent.llm_manager import LLMService  # ✅ 추가: LLM 요약용

logger = logging.getLogger(__name__)
```

**추가할 메서드 1: `summarize_with_llm()` (파일 끝에 추가)**

```python
    async def summarize_with_llm(
        self,
        conversation_text: str,
        max_length: int = None
    ) -> str:
        """
        LLM을 사용하여 대화 요약 생성

        Args:
            conversation_text: 요약할 대화 내용 (포맷된 문자열)
            max_length: 최대 요약 길이 (기본값: settings.SUMMARY_MAX_LENGTH_MIDTERM)

        Returns:
            str: 요약된 텍스트
        """
        if max_length is None:
            max_length = settings.SUMMARY_MAX_LENGTH_MIDTERM

        try:
            # LLM Service 초기화
            llm_service = LLMService()

            # LLM 요약 생성
            logger.info(f"[LLM 요약] 시작: max_length={max_length}")

            summary = await llm_service.complete_async(
                prompt_name="memory/conversation_summary",
                variables={
                    "conversation_text": conversation_text,
                    "max_length": max_length
                },
                model=settings.SUMMARY_LLM_MODEL,
                temperature=0.3,  # 일관된 요약을 위해 낮은 temperature
                max_tokens=100  # 약 200자
            )

            # 요약 결과 정리
            summary = summary.strip()

            # 최대 길이 제한 (LLM이 초과할 경우 대비)
            if len(summary) > max_length:
                summary = summary[:max_length]

            logger.info(f"[LLM 요약] 완료: {len(summary)}자")
            return summary

        except Exception as e:
            logger.error(f"[LLM 요약] 실패: {e}")

            # Fallback: 단순 잘라내기
            logger.warning("[LLM 요약] Fallback to simple truncation")
            return conversation_text[:max_length]
```

**추가할 메서드 2: `summarize_conversation_background()` (파일 끝에 추가)**

```python
    async def summarize_conversation_background(
        self,
        session_id: str,
        user_id: str
    ) -> None:
        """
        백그라운드에서 대화 요약 생성 및 저장

        Args:
            session_id: 채팅 세션 ID
            user_id: 사용자 ID
        """
        try:
            logger.info(f"[백그라운드 요약] 시작: session_id={session_id}")

            # 1. 세션의 모든 메시지 조회
            query = select(ChatMessage).where(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.asc())

            result = await self.db_session.execute(query)
            messages = result.scalars().all()

            if not messages:
                logger.warning(f"[백그라운드 요약] 메시지 없음: session_id={session_id}")
                return

            # 2. 대화 텍스트 포맷팅
            conversation_lines = []
            for msg in messages:
                role = "사용자" if msg.role == "user" else "AI"
                conversation_lines.append(f"{role}: {msg.content}")

            conversation_text = "\n".join(conversation_lines)

            # 3. LLM 요약 생성 (Mid-term/Long-term 동일 길이)
            if settings.SUMMARY_METHOD == "llm":
                summary = await self.summarize_with_llm(
                    conversation_text=conversation_text,
                    max_length=settings.SUMMARY_MAX_LENGTH_MIDTERM  # 200자
                )
            else:
                # 단순 잘라내기
                summary = conversation_text[:settings.SUMMARY_MAX_LENGTH_MIDTERM]

            # 4. chat_sessions.metadata 업데이트
            session_query = select(ChatSession).where(
                and_(
                    ChatSession.session_id == session_id,
                    ChatSession.user_id == user_id
                )
            )

            session_result = await self.db_session.execute(session_query)
            chat_session = session_result.scalar_one_or_none()

            if not chat_session:
                logger.error(f"[백그라운드 요약] 세션 없음: session_id={session_id}")
                return

            # 5. metadata 업데이트
            metadata = chat_session.session_metadata or {}
            metadata["conversation_summary"] = summary
            metadata["summary_method"] = settings.SUMMARY_METHOD
            metadata["summary_updated_at"] = datetime.now(timezone.utc).isoformat()

            chat_session.session_metadata = metadata
            flag_modified(chat_session, "session_metadata")  # JSONB 업데이트 플래그

            await self.db_session.commit()

            logger.info(f"[백그라운드 요약] 완료: {len(summary)}자")

        except Exception as e:
            logger.error(f"[백그라운드 요약] 오류: {e}")
            await self.db_session.rollback()
```

**추가할 메서드 3: `load_tiered_memories()` (파일 끝에 추가)**

```python
    async def load_tiered_memories(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        3-Tier Memory 로드: Short-term (전체) + Mid-term (요약) + Long-term (요약)

        Args:
            user_id: 사용자 ID
            session_id: 현재 세션 ID (제외할 세션)

        Returns:
            {
                "shortterm": [...],   # 1-5 세션 (전체 메시지)
                "midterm": [...],     # 6-10 세션 (요약)
                "longterm": [...]     # 11-20 세션 (요약)
            }
        """
        result = {
            "shortterm": [],
            "midterm": [],
            "longterm": []
        }

        try:
            # 현재 세션 제외 조건
            filter_conditions = [ChatSession.user_id == user_id]
            if session_id:
                filter_conditions.append(ChatSession.session_id != session_id)

            # ============================================================
            # 1. Short-term Memory: 최근 1-5개 세션 (전체 메시지)
            # ============================================================
            if settings.SHORTTERM_MEMORY_ENABLED:
                shortterm_limit = settings.SHORTTERM_MEMORY_LIMIT

                # 최근 세션 조회
                shortterm_query = select(ChatSession).where(
                    and_(*filter_conditions)
                ).order_by(
                    ChatSession.updated_at.desc()
                ).limit(shortterm_limit)

                shortterm_result = await self.db_session.execute(shortterm_query)
                shortterm_sessions = shortterm_result.scalars().all()

                # 각 세션의 메시지 로드
                for session in shortterm_sessions:
                    # 메시지 조회
                    msg_query = select(ChatMessage).where(
                        ChatMessage.session_id == session.session_id
                    ).order_by(ChatMessage.created_at.asc())

                    msg_result = await self.db_session.execute(msg_query)
                    messages = msg_result.scalars().all()

                    # 포맷팅
                    formatted_messages = [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.created_at.isoformat()
                        }
                        for msg in messages
                    ]

                    result["shortterm"].append({
                        "session_id": session.session_id,
                        "messages": formatted_messages,
                        "updated_at": session.updated_at.isoformat()
                    })

                logger.info(f"[3-Tier Memory] Short-term 로드: {len(result['shortterm'])}개 세션")

            # ============================================================
            # 2. Mid-term Memory: 6-10개 세션 (요약)
            # ============================================================
            if settings.MIDTERM_MEMORY_ENABLED:
                midterm_limit = settings.MIDTERM_MEMORY_LIMIT
                shortterm_limit = settings.SHORTTERM_MEMORY_LIMIT if settings.SHORTTERM_MEMORY_ENABLED else 0

                # 중간 범위 세션 조회 (offset 사용)
                midterm_query = select(ChatSession).where(
                    and_(*filter_conditions)
                ).order_by(
                    ChatSession.updated_at.desc()
                ).offset(shortterm_limit).limit(midterm_limit)

                midterm_result = await self.db_session.execute(midterm_query)
                midterm_sessions = midterm_result.scalars().all()

                # 요약 추출
                for session in midterm_sessions:
                    metadata = session.session_metadata or {}
                    summary = metadata.get("conversation_summary", "요약 없음")

                    result["midterm"].append({
                        "session_id": session.session_id,
                        "summary": summary,
                        "updated_at": session.updated_at.isoformat()
                    })

                logger.info(f"[3-Tier Memory] Mid-term 로드: {len(result['midterm'])}개 세션")

            # ============================================================
            # 3. Long-term Memory: 11-20개 세션 (요약)
            # ============================================================
            if settings.LONGTERM_MEMORY_ENABLED:
                longterm_limit = settings.LONGTERM_MEMORY_LIMIT
                shortterm_limit = settings.SHORTTERM_MEMORY_LIMIT if settings.SHORTTERM_MEMORY_ENABLED else 0
                midterm_limit = settings.MIDTERM_MEMORY_LIMIT if settings.MIDTERM_MEMORY_ENABLED else 0
                offset = shortterm_limit + midterm_limit

                # 장기 범위 세션 조회 (offset 사용)
                longterm_query = select(ChatSession).where(
                    and_(*filter_conditions)
                ).order_by(
                    ChatSession.updated_at.desc()
                ).offset(offset).limit(longterm_limit)

                longterm_result = await self.db_session.execute(longterm_query)
                longterm_sessions = longterm_result.scalars().all()

                # 요약 추출
                for session in longterm_sessions:
                    metadata = session.session_metadata or {}
                    summary = metadata.get("conversation_summary", "요약 없음")

                    result["longterm"].append({
                        "session_id": session.session_id,
                        "summary": summary,
                        "updated_at": session.updated_at.isoformat()
                    })

                logger.info(f"[3-Tier Memory] Long-term 로드: {len(result['longterm'])}개 세션")

            return result

        except Exception as e:
            logger.error(f"[3-Tier Memory] 로드 실패: {e}")
            return result
```

---

### Step 3: team_supervisor.py 통합 (35분)

#### 3-1. ~~Import 추가~~ (삭제 - 이미 존재)

**확인됨**: `team_supervisor.py:22`에 이미 `from app.core.config import settings` 존재
**조치**: Import 추가 불필요 ✅

#### 3-2. planning_node 수정 (기존 로직 통합)

**현재 코드** (Line 235-259 근처):
```python
        # Long-term Memory 로드
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

                    # ... user_preferences 로드 ...

                    state["loaded_memories"] = loaded_memories
                    state["user_preferences"] = user_preferences

                    break
```

**수정 코드** (✅ Critical Issue 2 해결: 통합 방식):
```python
        # 3-Tier Memory 로드 (기존 Long-term Memory 로직 통합)
        if user_id:
            try:
                async for db_session in get_async_db():
                    memory_service = LongTermMemoryService(db_session)

                    # ✅ 3-Tier Memory 로드 (새 메서드)
                    tiered_memories = await memory_service.load_tiered_memories(
                        user_id=user_id,
                        session_id=chat_session_id
                    )

                    # User preferences 로드 (기존 로직 유지)
                    user_preferences = {}
                    user_prefs = await memory_service.load_user_preferences(user_id)
                    if user_prefs:
                        user_preferences = user_prefs

                    # ✅ State 저장 (하위 호환성 유지)
                    # 기존 코드와 호환되도록 loaded_memories는 병합된 형태로 저장
                    state["loaded_memories"] = (
                        tiered_memories.get("shortterm", []) +
                        tiered_memories.get("midterm", []) +
                        tiered_memories.get("longterm", [])
                    )

                    # ✅ 새로운 필드: 3-Tier Memory 구분
                    state["tiered_memories"] = tiered_memories

                    # 기존 필드 유지
                    state["user_preferences"] = user_preferences

                    logger.info(
                        f"[3-Tier Memory] 로드 완료: "
                        f"Short={len(tiered_memories.get('shortterm', []))}, "
                        f"Mid={len(tiered_memories.get('midterm', []))}, "
                        f"Long={len(tiered_memories.get('longterm', []))}"
                    )

                    break
```

#### 3-3. generate_response_node 수정 (백그라운드 요약)

**현재 코드** (Line 878-894 근처):
```python
        # 응답 요약 생성 (최대 200자)
        response_summary = response.get("summary", "")
        if not response_summary and response.get("answer"):
            response_summary = response.get("answer", "")[:200]
        if not response_summary:
            response_summary = f"{response.get('type', 'response')} 생성 완료"

        # Long-term Memory 저장
        if user_id and chat_session_id:
            try:
                async for db_session in get_async_db():
                    memory_service = LongTermMemoryService(db_session)

                    await memory_service.save_conversation(
                        user_id=user_id,
                        session_id=chat_session_id,
                        messages=[],
                        summary=response_summary
                    )
```

**수정 코드** (백그라운드 요약 추가 - Option B: 200자):
```python
        # 응답 요약 생성 (Option B: 기존 방식 200자 유지)
        response_summary = response.get("summary", "")
        if not response_summary and response.get("answer"):
            response_summary = response.get("answer", "")[:200]  # ✅ 200자 (Option B)
        if not response_summary:
            response_summary = f"{response.get('type', 'response')} 생성 완료"

        # Long-term Memory 저장
        if user_id and chat_session_id:
            try:
                async for db_session in get_async_db():
                    memory_service = LongTermMemoryService(db_session)

                    # 즉시 저장 (200자 요약)
                    await memory_service.save_conversation(
                        user_id=user_id,
                        session_id=chat_session_id,
                        messages=[],
                        summary=response_summary
                    )

                    # ✅ 백그라운드 LLM 요약 생성 (설정 확인)
                    if settings.SUMMARY_METHOD == "llm" and settings.SUMMARY_BACKGROUND:
                        asyncio.create_task(
                            memory_service.summarize_conversation_background(
                                session_id=chat_session_id,
                                user_id=user_id
                            )
                        )
                        logger.info("[요약] 백그라운드 LLM 요약 태스크 생성")
```

**참고**:
- 즉시 저장: 200자 잘라내기 (기존 방식)
- 백그라운드: LLM 요약으로 업데이트 (몇 초 후)
- Mid-term/Long-term Memory는 백그라운드 완료 후 LLM 요약 사용

---

### Step 4: planning_agent.py 수정 (25분)

#### 4-1. `_analyze_with_llm()` 메서드 수정

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**현재 코드** (Line 183-213):
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

**수정 코드** (3-Tier Memory 추가):
```python
    async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
        # Context에서 데이터 추출
        chat_history = context.get("chat_history", []) if context else []
        tiered_memories = context.get("tiered_memories", {}) if context else {}  # ✅ 추가

        # 1. Chat History 포맷팅 (현재 대화)
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

        # ✅ 2. Short-term Memory 포맷팅 (최근 1-5 세션, 전체 메시지)
        shortterm_memory_text = ""
        shortterm_memories = tiered_memories.get("shortterm", [])
        if shortterm_memories:
            shortterm_lines = []
            for idx, session in enumerate(shortterm_memories, 1):
                session_id = session.get("session_id", "unknown")
                messages = session.get("messages", [])

                # 각 세션의 메시지 (최대 5개만 미리보기)
                msg_preview = []
                for msg in messages[:5]:
                    role = "사용자" if msg.get("role") == "user" else "AI"
                    content = msg.get("content", "")[:150]  # 각 메시지 최대 150자
                    msg_preview.append(f"  {role}: {content}")

                shortterm_lines.append(
                    f"[대화 {idx}]\n" + "\n".join(msg_preview)
                )

            shortterm_memory_text = "\n\n".join(shortterm_lines)

        # ✅ 3. Mid-term Memory 포맷팅 (6-10 세션, 요약)
        midterm_memory_text = ""
        midterm_memories = tiered_memories.get("midterm", [])
        if midterm_memories:
            midterm_lines = []
            for idx, session in enumerate(midterm_memories, 1):
                summary = session.get("summary", "요약 없음")
                midterm_lines.append(f"[대화 {idx}] {summary}")

            midterm_memory_text = "\n".join(midterm_lines)

        # ✅ 4. Long-term Memory 포맷팅 (11-20 세션, 요약)
        longterm_memory_text = ""
        longterm_memories = tiered_memories.get("longterm", [])
        if longterm_memories:
            longterm_lines = []
            for idx, session in enumerate(longterm_memories, 1):
                summary = session.get("summary", "요약 없음")
                longterm_lines.append(f"[대화 {idx}] {summary}")

            longterm_memory_text = "\n".join(longterm_lines)

        # ✅ LLM 호출 (모든 메모리 전달)
        result = await self.llm_service.complete_json_async(
            prompt_name="intent_analysis",
            variables={
                "query": query,
                "chat_history": chat_history_text,
                "shortterm_memory": shortterm_memory_text,   # ✅ 추가
                "midterm_memory": midterm_memory_text,       # ✅ 추가
                "longterm_memory": longterm_memory_text      # ✅ 추가
            },
            temperature=0.0,
            max_tokens=500
        )
```

#### 4-2. team_supervisor에서 Context 전달 수정

**team_supervisor.py** (Line 200-210 근처) 수정:
```python
        # 의도 분석
        query = state.get("query", "")
        chat_session_id = state.get("chat_session_id")

        # Chat History 조회 (현재 대화창)
        chat_history = await self._get_chat_history(
            session_id=chat_session_id,
            limit=3  # 최근 3쌍 (6개 메시지)
        )

        # ✅ Context 구성 (3-Tier Memory 추가)
        context = {
            "chat_history": chat_history,
            "tiered_memories": state.get("tiered_memories", {})  # ✅ 추가
        } if chat_history or state.get("tiered_memories") else None

        intent_result = await self.planning_agent.analyze_intent(query, context)
```

---

### Step 5: intent_analysis.txt 프롬프트 수정 (25분)

#### 5-1. `intent_analysis.txt` 수정

**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`

**현재 코드** (Line 203-218):
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
```

**수정 코드** (3-Tier Memory 섹션 추가):
```markdown
## 🔹 현재 대화창 (Chat History)

현재 대화창의 최근 대화 내용입니다.

{chat_history}

---

## 🔹 최근 다른 대화 (Short-term Memory: 1-5 sessions)

사용자가 최근에 진행한 다른 대화의 **전체 내용**입니다.
현재 질문이 이전 대화와 관련이 있는지 확인하세요.

{shortterm_memory}

---

## 🔹 중기 대화 요약 (Mid-term Memory: 6-10 sessions)

사용자가 최근에 진행한 대화의 **요약**입니다.
사용자의 관심사와 패턴을 파악하는 데 활용하세요.

{midterm_memory}

---

## 🔹 장기 대화 요약 (Long-term Memory: 11-20 sessions)

사용자가 과거에 진행한 대화의 **요약**입니다.
사용자의 장기적인 관심사와 패턴을 파악하는 데 활용하세요.

{longterm_memory}

---

**현재 질문**: {query}

**분석 지침**:

1. **현재 대화창 (Chat History)**: 질문의 직접적인 맥락 파악 ⭐ 최우선
   - "그럼", "그거", "그건", "아까" 등의 지시어가 있으면 Chat History에서 언급된 내용을 찾으세요
   - 이전 대화와 연결되는 질문이면 부동산 관련 질문으로 처리하세요

2. **최근 다른 대화 (Short-term Memory)**: 사용자의 최근 관심사 파악 ⭐⭐
   - 현재 질문이 다른 대화창에서 논의한 주제와 관련이 있는지 확인
   - 예: "아까 본 강남 아파트" → Short-term Memory에서 강남 관련 대화 찾기
   - 전체 메시지가 제공되므로 상세한 맥락 파악 가능

3. **중기 대화 요약 (Mid-term Memory)**: 사용자의 중기적 관심 패턴 ⭐
   - 사용자가 최근 몇 주 동안 자주 질문하는 지역, 매물 유형, 가격대 등을 파악
   - 현재 질문의 배경을 이해하는 데 활용

4. **장기 대화 요약 (Long-term Memory)**: 사용자의 장기적 관심 패턴 (참고용)
   - 사용자의 전반적인 부동산 관심사 파악
   - 과도하게 의존하지 마세요 (최신 정보 우선)

5. **우선순위**: Chat History > Short-term > Mid-term > Long-term
   - 가장 최근 대화가 가장 중요
   - 오래된 대화는 참고만 하고, 과도하게 의존하지 마세요
```

**변수 확인**:
- `{chat_history}`: 현재 대화 (기존)
- `{shortterm_memory}`: Short-term Memory (새로 추가)
- `{midterm_memory}`: Mid-term Memory (새로 추가)
- `{longterm_memory}`: Long-term Memory (새로 추가)

---

### Step 6: 테스트 (35분)

#### 6-1. 설정 확인
```bash
# .env 파일 확인
grep -E "(SHORTTERM_MEMORY|MIDTERM_MEMORY|LONGTERM_MEMORY|SUMMARY_)" backend/.env

# 예상 출력:
# SHORTTERM_MEMORY_LIMIT=5
# SHORTTERM_MEMORY_ENABLED=true
# MIDTERM_MEMORY_LIMIT=5
# MIDTERM_MEMORY_ENABLED=true
# LONGTERM_MEMORY_LIMIT=10
# LONGTERM_MEMORY_ENABLED=true
# SUMMARY_METHOD=llm
# SUMMARY_LLM_MODEL=gpt-4o-mini
# SUMMARY_MAX_LENGTH_MIDTERM=200
# SUMMARY_MAX_LENGTH_LONGTERM=200
# SUMMARY_BACKGROUND=true
```

#### 6-2. 서버 재시작
```bash
# 백엔드 재시작 (Windows)
cd backend
# venv 활성화 후
uvicorn app.main:app --reload
```

#### 6-3. 테스트 시나리오

**테스트 1: Short-term Memory (전체 메시지)**

```
[대화 1 - Session A]
User: "강남구 아파트 전세 시세 알려줘"
AI: "5억~7억입니다..."

[대화 2 - Session B]
User: "송파구는?"
AI: "4억~6억입니다..."

[대화 3 - Session C (새로운 대화창)]
User: "아까 본 강남하고 송파 비교해줘"

✅ 예상 결과:
- Intent: MARKET_INQUIRY
- Short-term Memory에서 Session A, B 로드 (전체 메시지)
- "아까 본" 지시어를 Short-term Memory와 연결
- 로그: "[3-Tier Memory] 로드 완료: Short=2, Mid=0, Long=0"
```

**테스트 2: Mid-term Memory (요약)**

```
[대화 1-5: Short-term Memory]
...

[대화 6 - Session F]
User: "강남구 투자 분석해줘"
AI: "강남구는 안정적인 투자처입니다..."
→ 요약: "강남구 투자 분석 및 리스크 평가"

[대화 7 - 현재]
User: "투자 분석 다시 해줘"

✅ 예상 결과:
- Intent: MARKET_INQUIRY
- Mid-term Memory에서 Session F 요약 로드
- "투자 분석" 키워드를 Mid-term Memory와 연결
- 로그: "[3-Tier Memory] 로드 완료: Short=5, Mid=1, Long=0"
```

**테스트 3: Long-term Memory (요약)**

```
[대화 1-10: Short + Mid-term]
...

[대화 15 - Session O (2개월 전)]
User: "송파구 신축 아파트 관심 있어"
AI: "송파구 신축 단지 추천..."
→ 요약: "송파구 신축 아파트 선호 (투자 목적)"

[대화 16 - 현재]
User: "신축 아파트 어디 좋아?"

✅ 예상 결과:
- Intent: MARKET_INQUIRY
- Long-term Memory에서 Session O 요약 로드
- 사용자 선호도 파악: "신축 아파트 선호"
- 로그: "[3-Tier Memory] 로드 완료: Short=5, Mid=5, Long=5"
```

**테스트 4: 백그라운드 LLM 요약**

```
[대화 1]
User: "강남구 아파트 전세 시세 알려줘"
AI: "강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 개포동 래미안, 대치동 은마아파트 등이 있으며..."

✅ 확인 사항:
1. 응답 즉시 반환 (200자 잘라내기로 저장)
2. 로그: "[요약] 백그라운드 LLM 요약 태스크 생성"
3. 몇 초 후 로그: "[백그라운드 요약] 완료: 50자"
4. DB 확인:
   psql -U postgres -d real_estate -c "
   SELECT session_id, session_metadata->'conversation_summary'
   FROM chat_sessions
   WHERE session_id = 'session-xxx';
   "
   → conversation_summary가 LLM 요약으로 업데이트됨
   → "강남구 아파트 전세 시세 조회 (5억~7억, 대치동/개포동 중심)"
```

#### 6-4. 로그 확인

**예상 로그**:
```
[3-Tier Memory] 로드 완료: Short=5, Mid=5, Long=10
[요약] 백그라운드 LLM 요약 태스크 생성
[LLM 요약] 시작: max_length=200
[LLM 요약] 완료: 65자
[백그라운드 요약] 완료: 65자
```

#### 6-5. DB 확인

```bash
# chat_sessions.session_metadata 확인
psql -U postgres -d real_estate -c "
SELECT
    session_id,
    session_metadata->'conversation_summary' as summary,
    session_metadata->'summary_method' as method,
    session_metadata->'summary_updated_at' as updated_at
FROM chat_sessions
WHERE user_id = 'test-user-001'
ORDER BY updated_at DESC
LIMIT 10;
"
```

**예상 출력**:
```
 session_id       | summary                                  | method | updated_at
------------------+------------------------------------------+--------+-------------------------
 session-xxx      | "강남구 아파트 전세 시세 (5억~7억)"       | "llm"  | "2025-10-20T18:30:00"
 session-yyy      | "송파구 투자 분석 및 리스크 평가"         | "llm"  | "2025-10-20T17:15:00"
```

#### 6-6. 3-Tier 경계 테스트

**테스트 5: 정확히 5, 10, 20개 세션 경계**

```bash
# 15개 세션 생성 후 테스트
# 예상 결과:
# Short-term: 1-5 세션 (5개)
# Mid-term: 6-10 세션 (5개)
# Long-term: 11-15 세션 (5개)

# 로그 확인
[3-Tier Memory] Short-term 로드: 5개 세션
[3-Tier Memory] Mid-term 로드: 5개 세션
[3-Tier Memory] Long-term 로드: 5개 세션
```

---

## 📊 예상 소요시간

| Step | 작업 | 예상 시간 | 비고 |
|------|------|----------|------|
| 0 | 준비 (백업, 브랜치) | 5분 | |
| 1 | 설정 파일 (config.py, .env) | 15분 | Field import + 3-Tier 설정 |
| 2 | LLM 요약 메서드 (3개) | 40분 | 디렉토리 생성 + 3-Tier 로직 |
| 3 | team_supervisor 통합 | 35분 | 3-Tier 통합 + 백그라운드 요약 |
| 4 | planning_agent 수정 | 25분 | 3-Tier 포맷팅 |
| 5 | intent_analysis.txt | 25분 | 3개 섹션 추가 |
| 6 | 테스트 | 35분 | 5가지 시나리오 |
| **합계** | | **3시간 20분** | |

---

## 🎯 핵심 변경사항 요약

### ✅ v3.0 주요 변경사항

1. **3-Tier 구조 확정**:
   - Short-term: 1-5 세션 (전체 메시지)
   - Mid-term: 6-10 세션 (LLM 요약)
   - Long-term: 11-20 세션 (LLM 요약)

2. **Option A 적용**: Mid-term/Long-term 요약 길이 동일 (200자)
   - 단, 설정 가능 (`SUMMARY_MAX_LENGTH_MIDTERM`, `SUMMARY_MAX_LENGTH_LONGTERM`)

3. **Option B 적용**: 임시 요약 200자 (기존 방식)
   - 백그라운드 완료 후 LLM 요약으로 업데이트

4. **Critical Issue 해결**:
   - Field import 추가 ✅
   - 기존 로직 통합 (교체 X) ✅
   - team_supervisor settings import 중복 제거 ✅

5. **메서드명 변경**:
   - `load_hybrid_memories()` → `load_tiered_memories()`
   - State 필드: `tiered_memories` (shortterm/midterm/longterm)

---

## 📋 구현 체크리스트

- [ ] Step 0: 백업 및 브랜치 생성
- [ ] Step 1: config.py에 Field import 추가 ✅
- [ ] Step 1: config.py에 3-Tier 설정 추가
- [ ] Step 1: .env에 3-Tier 설정 추가
- [ ] Step 2: prompts/memory/ 디렉토리 생성 ✅
- [ ] Step 2: conversation_summary.txt 생성
- [ ] Step 2: simple_memory_service.py에 import 추가 ✅
- [ ] Step 2: summarize_with_llm() 추가
- [ ] Step 2: summarize_conversation_background() 추가
- [ ] Step 2: load_tiered_memories() 추가 (3-Tier)
- [ ] Step 3: planning_node에서 기존 로직 통합 ✅
- [ ] Step 3: generate_response_node에 백그라운드 요약 추가
- [ ] Step 4: planning_agent.py에 3-Tier 포맷팅 추가
- [ ] Step 4: team_supervisor.py에서 Context에 tiered_memories 추가
- [ ] Step 5: intent_analysis.txt에 3개 섹션 추가
- [ ] Step 6: 테스트 5가지 시나리오
- [ ] Step 6: 로그 및 DB 확인

---

## 🚀 시작 준비

**구현을 시작하려면 다음 명령어를 실행하세요**:

```bash
# 1. 백업 브랜치 생성
git checkout -b backup-before-3tier-memory

# 2. 작업 브랜치 생성
git checkout main
git checkout -b feature/3tier-hybrid-memory

# 3. 계획서 확인
cat reports/long_term_memory/HYBRID_MEMORY_IMPLEMENTATION_PLAN_FINAL_v3.md

# 4. Step 1부터 시작
# (각 Step은 개별적으로 커밋 권장)
```

---

**작성 완료**: 2025-10-20
**최종 수정**: 2025-10-20 (v3.0 Final)
**검증 기반**: HYBRID_MEMORY_PLAN_VALIDATION_251020.md + 사용자 피드백
**확정 사항**:
- 3-Tier 구조: Short(1-5) + Mid(6-10) + Long(11-20)
- 요약 길이: Mid/Long 동일 200자 (설정 가능)
- 임시 요약: 200자 (기존 방식)
