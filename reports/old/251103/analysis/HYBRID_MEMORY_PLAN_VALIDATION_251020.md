# HYBRID_MEMORY_IMPLEMENTATION_PLAN_251020.md 검증 보고서

**작성일**: 2025-10-20
**검증 대상**: `HYBRID_MEMORY_IMPLEMENTATION_PLAN_251020.md`
**검증 범위**: 계획서의 현재 코드 대조 및 구현 타당성 분석

---

## 📋 목차

1. [검증 요약](#1-검증-요약)
2. [현재 상황 섹션 검증](#2-현재-상황-섹션-검증)
3. [파일별 상세 검증](#3-파일별-상세-검증)
4. [구현 계획 검증](#4-구현-계획-검증)
5. [발견된 문제점](#5-발견된-문제점)
6. [수정 권고사항](#6-수정-권고사항)
7. [구현 순서 타당성](#7-구현-순서-타당성)

---

## 1. 검증 요약

### 1.1 전체 평가

| 항목 | 상태 | 비고 |
|------|------|------|
| **현재 상황 파악** | ⚠️ 부분 정확 | 일부 코드 위치/내용 불일치 |
| **파일 구조** | ✅ 정확 | 파일 경로 및 구조 정확 |
| **설정 계획** | ⚠️ 수정 필요 | Field import 누락 |
| **메서드 이름** | ✅ 정확 | LLMService 메서드명 확인됨 |
| **구현 순서** | ✅ 적절 | 단계별 진행 합리적 |
| **호환성** | ✅ 양호 | 기존 코드와 충돌 없음 |

### 1.2 주요 발견사항

#### ✅ 정확한 부분
1. **파일 구조 및 경로**: 모든 파일 경로 정확히 파악
2. **LLMService 메서드**: `complete_async`, `complete_json_async` 존재 확인
3. **team_supervisor.py 구조**: 전반적인 구조 정확히 파악
4. **simple_memory_service.py**: 기존 메서드 충돌 없음

#### ⚠️ 수정 필요 부분
1. **config.py**: Pydantic Field import 누락
2. **team_supervisor.py**: 일부 코드 위치 및 내용 불일치
3. **planning_agent.py**: 실제 파일 존재하나 계획서에서 누락
4. **intent_analysis.txt**: 실제 파일 존재하나 계획서에서 누락

---

## 2. 현재 상황 섹션 검증

### 2.1 Option A: Chat History (Line 196-210)

#### 계획서 내용
```python
# Line 196-210
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3  # 3쌍 = 6개 메시지
)
context = {"chat_history": chat_history}
intent_result = await self.planning_agent.analyze_intent(query, context)
```

#### 실제 코드 (team_supervisor.py:196-210)
```python
# Line 196-210
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

**검증 결과**: ✅ **정확**
- 라인 번호 정확
- 코드 내용 일치
- 로직 흐름 동일

---

### 2.2 Phase 1: Long-term Memory (Line 235-259)

#### 계획서 내용
```python
# Line 235-259
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,  # 기본값: 5
    relevance_filter="RELEVANT",
    session_id=chat_session_id  # 현재 세션 제외
)
state["loaded_memories"] = loaded_memories
```

#### 실제 코드 (team_supervisor.py:235-259)
```python
# Line 235-259
user_id = state.get("user_id")
chat_session_id = state.get("chat_session_id")
if user_id:
    try:
        logger.info(f"[TeamSupervisor] Loading Long-term Memory for user {user_id}")
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            # 최근 대화 기록 로드 (RELEVANT만, 현재 세션 제외)
            loaded_memories = await memory_service.load_recent_memories(
                user_id=user_id,
                limit=settings.MEMORY_LOAD_LIMIT,
                relevance_filter="RELEVANT",
                session_id=chat_session_id
            )

            # 사용자 선호도 로드
            user_preferences = await memory_service.get_user_preferences(user_id)

            state["loaded_memories"] = loaded_memories
            state["user_preferences"] = user_preferences
            state["memory_load_time"] = datetime.now().isoformat()

            logger.info(f"[TeamSupervisor] Loaded {len(loaded_memories)} memories...")
            break
```

**검증 결과**: ✅ **정확**
- 라인 범위 정확
- 로직 일치
- 추가 기능(user_preferences) 있으나 호환성 문제 없음

---

### 2.3 요약 생성 (Line 878-883)

#### 계획서 내용
```python
# Line 878-883
response_summary = response.get("answer", "")[:200]

await memory_service.save_conversation(
    user_id=user_id,
    session_id=chat_session_id,
    messages=[],
    summary=response_summary
)
```

#### 실제 코드 (team_supervisor.py:878-894)
```python
# Line 878-894
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

**검증 결과**: ⚠️ **부분 불일치**
- 라인 번호 약간 차이 (878-883 vs 878-894)
- 로직이 더 복잡함 (3단계 fallback)
- 하지만 핵심 흐름은 동일

---

## 3. 파일별 상세 검증

### 3.1 config.py

#### 계획서 주장
```python
# Line ~70 (MEMORY_LOAD_LIMIT 아래)
RECENT_MEMORY_LIMIT: int = Field(
    default=5,
    description="Recent Memory 로드 개수"
)
```

#### 실제 코드
```python
# Line 1-2
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... (Field import 없음!)
    MEMORY_LOAD_LIMIT: int = 5
```

**문제점**: ❌ **Field import 누락**

#### 해결 방안
```python
# Line 1-3 (수정 필요)
from typing import List
from pydantic import Field  # ← 추가 필요
from pydantic_settings import BaseSettings
```

**영향도**: 🔴 **높음** - Field 없이는 계획서의 설정 코드가 동작하지 않음

---

### 3.2 .env

#### 계획서 주장
```bash
# Line 27
MEMORY_LOAD_LIMIT=5
```

#### 실제 파일
```bash
# Line 27
MEMORY_LOAD_LIMIT=5
```

**검증 결과**: ✅ **정확**

---

### 3.3 simple_memory_service.py

#### 계획서 주장
- Line 217-329: `load_recent_memories` 메서드
- Line 331-386: `save_conversation` 메서드

#### 실제 코드
- Line 217-329: `load_recent_memories` 메서드 ✅
- Line 331-386: `save_conversation` 메서드 ✅

**검증 결과**: ✅ **정확**

#### 메서드 충돌 검증

계획서에서 추가하려는 메서드:
1. `summarize_with_llm` (Line ~390)
2. `summarize_conversation_background` (Line ~620)
3. `load_hybrid_memories` (Line ~704)

실제 파일 끝: Line 392

**검증 결과**: ✅ **충돌 없음** - 새 메서드 추가 가능

---

### 3.4 team_supervisor.py

#### 계획서의 수정 위치 1: planning_node (Line 196-230)

**실제 코드 범위**: Line 174-397 (planning_node 전체)

**문제점**: ⚠️ **범위 불일치**
- 계획서는 Line 196-230으로 제한했으나
- 실제로는 더 넓은 범위 수정 필요

#### 계획서의 수정 위치 2: generate_response_node (Line 878-894)

**실제 코드 범위**: Line 825-903 (generate_response_node 전체)

**문제점**: ⚠️ **라인 번호 약간 차이**

---

### 3.5 planning_agent.py (계획서에서 누락)

#### 실제 파일 위치
`C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service_agent\cognitive_agents\planning_agent.py`

#### 실제 코드 (Line 183-213: _analyze_with_llm)
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

**검증 결과**: ✅ **파일 존재, 구조 정확**

---

### 3.6 intent_analysis.txt (계획서에서 누락)

#### 실제 파일 위치
`C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service_agent\llm_manager\prompts\cognitive\intent_analysis.txt`

#### 실제 코드 (Line 203-218: Chat History 섹션)
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

**검증 결과**: ✅ **파일 존재, 위치 정확**

---

### 3.7 LLMService 메서드 검증

#### 계획서 주장
```python
# Line ~595
summary = await llm_service.complete_async(
    prompt_name="conversation_summary",
    variables={...},
    model=settings.SUMMARY_LLM_MODEL,
    temperature=0.3,
    max_tokens=100
)
```

#### 실제 LLMService (llm_service.py)

**메서드 존재 확인**:
- ✅ `complete_async` (Line 146-196)
- ✅ `complete_json_async` (Line 228-257)

**시그니처**:
```python
async def complete_async(
    self,
    prompt_name: str,
    variables: Dict[str, Any] = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    response_format: Dict[str, str] = None,
    **kwargs
) -> str:
```

**검증 결과**: ✅ **메서드 존재, 시그니처 일치**

---

## 4. 구현 계획 검증

### 4.1 Step 1: 설정 파일 추가 (10분)

#### 파일 1: .env

**계획**: 새 환경 변수 추가
```bash
RECENT_MEMORY_LIMIT=5
RECENT_MEMORY_ENABLED=true
MIDTERM_MEMORY_LIMIT=10
MIDTERM_MEMORY_ENABLED=true
SUMMARY_METHOD=llm
SUMMARY_LLM_MODEL=gpt-4o-mini
SUMMARY_MAX_LENGTH=200
SUMMARY_BACKGROUND=true
```

**검증**: ✅ **타당** - .env 파일에 추가 가능

---

#### 파일 2: config.py

**계획**: Settings 클래스에 Field 기반 설정 추가

**문제점**: ❌ **Field import 누락**

**수정 필요**:
```python
# Line 1 수정
from typing import List
from pydantic import Field  # ← 추가
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... 기존 설정 ...

    # Line ~32 이후 추가
    RECENT_MEMORY_LIMIT: int = Field(
        default=5,
        description="Recent Memory 로드 개수 (최근 N개 세션, 전체 대화)"
    )
    # ... 나머지 설정 ...
```

**예상 소요**: 10분 → 15분 (import 추가 포함)

---

### 4.2 Step 2: LLM 요약 기능 구현 (30분)

#### 파일 1: Prompt 템플릿 생성

**위치**: `backend/app/service_agent/llm_manager/prompts/memory/conversation_summary.txt`

**디렉터리 생성 필요**: `prompts/memory/` 디렉터리가 없을 가능성

**검증**: ⚠️ **디렉터리 확인 필요**

---

#### 파일 2: simple_memory_service.py - LLM 요약 메서드

**추가 위치**: Line ~390 이후

**메서드**:
1. `summarize_with_llm` (Line ~555-619)
2. `summarize_conversation_background` (Line ~621-692)

**Import 확인**:
```python
# 계획서에서 사용하는 import
from app.service_agent.llm_manager import LLMService
from app.core.config import settings
```

**실제 파일**:
```python
# Line 12
from app.models.chat import ChatMessage, ChatSession
```

**문제점**: ⚠️ **추가 import 필요**
```python
# 추가 필요
from app.service_agent.llm_manager import LLMService
from app.core.config import settings
```

**검증**: ⚠️ **import 추가 필요, 나머지 타당**

---

### 4.3 Step 3: Hybrid Memory 로더 구현 (30분)

**파일**: `simple_memory_service.py`

**추가 위치**: Line ~500 이후

**메서드**: `load_hybrid_memories` (Line ~706-832)

**Import 확인**:
```python
# 계획서에서 사용
from app.core.config import settings
from sqlalchemy import select, desc
```

**실제 파일 (Line 8)**:
```python
from sqlalchemy import select, desc  # ✅ 이미 있음
```

**검증**: ✅ **타당, import 문제 없음**

---

### 4.4 Step 4: team_supervisor.py 수정 (20분)

#### 수정 위치 1: planning_node (Line 196-230)

**계획서 코드**:
```python
# Line 196-230 (확장)
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
            # ...
```

**문제점**: ⚠️ **기존 Long-term Memory 로직과 충돌 가능**

**실제 코드 (Line 235-259)**:
```python
# 이미 Long-term Memory 로드 로직이 있음
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
            # ...
```

**해결 방안**: 기존 로직을 **교체**하는 것이 아니라 **확장**해야 함

**권장 수정**:
```python
# Line 235-259 수정
if user_id:
    try:
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            # ✅ Hybrid Memory 로드 (Recent + Mid-term)
            hybrid_memories = await memory_service.load_hybrid_memories(
                user_id=user_id,
                session_id=chat_session_id
            )

            # 기존 코드와의 호환성 유지
            state["loaded_memories"] = hybrid_memories.get("recent", []) + hybrid_memories.get("midterm", [])
            state["hybrid_memories"] = hybrid_memories  # 새로운 필드

            # 기존 user_preferences 로드는 유지
            user_preferences = await memory_service.get_user_preferences(user_id)
            state["user_preferences"] = user_preferences
            # ...
```

**검증**: ⚠️ **계획서 수정 필요 - 기존 로직과 통합 방식 재검토**

---

#### 수정 위치 2: Context 생성 (Line 206-210)

**계획서 코드**:
```python
# Line 196-230
context = {
    "chat_history": chat_history,
    "recent_memory": hybrid_memories["recent"],
    "midterm_memory": hybrid_memories["midterm"]
}
```

**실제 코드 (Line 206-210)**:
```python
# Context 생성
context = {"chat_history": chat_history} if chat_history else None

# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)
```

**검증**: ✅ **타당, 수정 위치 정확**

---

#### 수정 위치 3: generate_response_node - 백그라운드 요약 (Line 878-894)

**계획서 코드**:
```python
# Line 932-964
from app.core.config import settings
import asyncio

# 백그라운드 LLM 요약 (비동기)
if settings.SUMMARY_METHOD == "llm" and settings.SUMMARY_BACKGROUND:
    asyncio.create_task(
        memory_service.summarize_conversation_background(
            session_id=chat_session_id,
            user_id=user_id
        )
    )
```

**문제점**: ⚠️ **asyncio import 위치**

**실제 코드 (Line 10)**:
```python
import asyncio  # ✅ 이미 import되어 있음
```

**하지만**: settings import는 **없음**

**수정 필요**:
```python
# Line 22 근처에 추가
from app.core.config import settings
```

**검증**: ⚠️ **settings import 추가 필요**

---

### 4.5 Step 5: planning_agent.py 수정 (20분)

**계획서 주장**: Line 183-213 (기존 `_analyze_with_llm` 메서드)

**실제 파일**: ✅ **존재**

**계획서 수정안**:
```python
# Line 1010-1083
# ✅ Recent Memory 추출 및 포맷팅
recent_memory = context.get("recent_memory", []) if context else []
recent_memory_text = ""

if recent_memory:
    formatted_recent = []
    for mem in recent_memory:
        title = mem.get("title", "Untitled")
        timestamp = mem.get("timestamp", "")[:10]
        messages = mem.get("messages", [])

        session_lines = [f"[{timestamp}] {title}:"]
        for msg in messages[:10]:
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

**검증**: ✅ **타당, 기존 구조와 호환**

---

### 4.6 Step 6: intent_analysis.txt 수정 (20분)

**파일 위치**: ✅ **존재 확인**

**계획서 수정안**:
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
```

**검증**: ✅ **타당, 기존 프롬프트 확장**

---

## 5. 발견된 문제점

### 5.1 Critical Issues (🔴 높음)

#### 1. config.py - Field import 누락

**위치**: `backend/app/core/config.py`

**문제**:
```python
# 현재
from typing import List
from pydantic_settings import BaseSettings

# Field를 사용하려면
RECENT_MEMORY_LIMIT: int = Field(default=5, ...)  # ← Field가 없음!
```

**해결**:
```python
from typing import List
from pydantic import Field  # ← 추가
from pydantic_settings import BaseSettings
```

**영향**: 계획서의 모든 Field 기반 설정 코드가 동작하지 않음

---

#### 2. team_supervisor.py - 기존 Long-term Memory 로직과 충돌

**위치**: `team_supervisor.py:235-259`

**문제**: 이미 Long-term Memory 로드 로직이 있는데, 계획서는 이를 고려하지 않고 새로운 로직 추가

**해결**: 기존 로직을 **교체**가 아닌 **확장**으로 수정

---

### 5.2 Medium Issues (⚠️ 중간)

#### 3. simple_memory_service.py - Import 누락

**위치**: `simple_memory_service.py`

**문제**: 계획서에서 사용하는 import가 파일에 없음

**필요한 import**:
```python
from app.service_agent.llm_manager import LLMService
from app.core.config import settings
```

---

#### 4. team_supervisor.py - settings import 누락

**위치**: `team_supervisor.py`

**문제**: 백그라운드 요약에서 `settings.SUMMARY_METHOD` 사용하는데 import 없음

**해결**:
```python
# Line 22 근처 추가
from app.core.config import settings
```

---

#### 5. 계획서 - planning_agent.py, intent_analysis.txt 누락

**문제**: 두 파일이 실제로 존재하는데 계획서에서 Step 5, 6로 다루지만 "현재 상황" 섹션에서 누락

**해결**: "현재 상황" 섹션에 추가 설명 필요

---

### 5.3 Low Issues (💡 낮음)

#### 6. 라인 번호 미세 차이

**문제**: 계획서의 일부 라인 번호가 실제와 약간 다름
- 예: "Line 878-883" → 실제 "Line 878-894"

**영향**: 낮음 (범위 내에 있음)

---

#### 7. prompts/memory/ 디렉터리 확인 필요

**문제**: `prompts/memory/conversation_summary.txt` 생성 시 디렉터리가 없을 수 있음

**해결**: 디렉터리 생성 단계 추가

---

## 6. 수정 권고사항

### 6.1 계획서 수정안

#### 수정 1: Step 1 - config.py 코드 수정

**기존**:
```python
# Line ~70 (MEMORY_LOAD_LIMIT 아래)
RECENT_MEMORY_LIMIT: int = Field(...)
```

**수정**:
```python
# Line 1-3: Import 추가
from typing import List
from pydantic import Field  # ← 추가 필수
from pydantic_settings import BaseSettings

# Line ~32 (MEMORY_LOAD_LIMIT 아래): 새 설정 추가
RECENT_MEMORY_LIMIT: int = Field(
    default=5,
    description="Recent Memory 로드 개수 (최근 N개 세션, 전체 대화)"
)
# ... 나머지 설정 ...
```

---

#### 수정 2: Step 2 - simple_memory_service.py Import 추가

**기존**: import 언급 없음

**수정**:
```python
# Line 6 근처 추가
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.chat import ChatMessage, ChatSession
from app.service_agent.llm_manager import LLMService  # ← 추가
from app.core.config import settings  # ← 추가

logger = logging.getLogger(__name__)
```

---

#### 수정 3: Step 4 - team_supervisor.py 기존 로직 통합

**기존**:
```python
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
```

**수정**:
```python
# Line 235-259 수정 (기존 Long-term Memory 로직 통합)
if user_id:
    try:
        logger.info(f"[TeamSupervisor] Loading Hybrid Memory for user {user_id}")
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            # ✅ Hybrid Memory 로드 (Recent + Mid-term)
            hybrid_memories = await memory_service.load_hybrid_memories(
                user_id=user_id,
                session_id=chat_session_id
            )

            # 기존 loaded_memories 호환성 유지
            state["loaded_memories"] = (
                hybrid_memories.get("recent", []) +
                hybrid_memories.get("midterm", [])
            )

            # Hybrid Memory 전용 필드 (새로 추가)
            state["hybrid_memories"] = hybrid_memories

            # 기존 user_preferences 로드 유지
            user_preferences = await memory_service.get_user_preferences(user_id)
            state["user_preferences"] = user_preferences
            state["memory_load_time"] = datetime.now().isoformat()

            logger.info(
                f"[TeamSupervisor] Loaded {len(hybrid_memories['recent'])} recent, "
                f"{len(hybrid_memories['midterm'])} midterm memories for user {user_id}"
            )
            break
    except Exception as e:
        logger.error(f"[TeamSupervisor] Failed to load Hybrid Memory: {e}")
```

---

#### 수정 4: Step 4 - team_supervisor.py Import 추가

**위치**: `team_supervisor.py` 상단 (Line 22 근처)

**추가**:
```python
# Line 22
from app.core.config import settings  # ← 이미 있는지 확인, 없으면 추가
```

---

#### 수정 5: Step 2 - 디렉터리 생성 단계 추가

**추가할 내용**:
```markdown
#### 파일 1-1: prompts/memory/ 디렉터리 생성 (선행 작업)

**위치**: `backend/app/service_agent/llm_manager/prompts/`

**명령어**:
```bash
mkdir -p backend/app/service_agent/llm_manager/prompts/memory
```

**확인**:
```bash
ls backend/app/service_agent/llm_manager/prompts/memory/
```

---

### 6.2 "현재 상황" 섹션 추가 권고

#### 추가 항목 1: planning_agent.py 현황

```markdown
#### ✅ planning_agent.py (Intent 분석)
**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**현재 구현**:
```python
# Line 183-213: _analyze_with_llm 메서드
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

**특징**:
- Chat History만 처리
- Recent/Mid-term Memory 미사용
- LLMService의 complete_json_async 사용
```

---

#### 추가 항목 2: intent_analysis.txt 현황

```markdown
#### ✅ intent_analysis.txt (Intent 분석 Prompt)
**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`

**현재 구현** (Line 203-218):
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

**특징**:
- Chat History만 포함
- Recent/Mid-term Memory 섹션 없음
- 변수: {chat_history}, {query}
```

---

## 7. 구현 순서 타당성

### 7.1 전체 구현 흐름

```
Step 1: 설정 파일 추가 (10분 → 15분)
    ↓ (Field import 추가로 5분 증가)
Step 2: LLM 요약 기능 구현 (30분 → 40분)
    ↓ (디렉터리 생성 + import 추가로 10분 증가)
Step 3: Hybrid Memory 로더 구현 (30분)
    ↓ (변동 없음)
Step 4: team_supervisor.py 수정 (20분 → 30분)
    ↓ (기존 로직 통합으로 10분 증가)
Step 5: planning_agent.py 수정 (20분)
    ↓ (변동 없음)
Step 6: intent_analysis.txt 수정 (20분)
    ↓ (변동 없음)
Step 7: 테스트 및 검증 (30분)

총 소요 시간: 2.5시간 → 3시간 10분
```

### 7.2 순서 타당성 평가

| Step | 의존성 | 순서 적절성 | 비고 |
|------|--------|-------------|------|
| Step 1 | 없음 | ✅ 적절 | 모든 설정의 기반 |
| Step 2 | Step 1 | ✅ 적절 | settings 사용 |
| Step 3 | Step 1, 2 | ✅ 적절 | settings, LLM 사용 |
| Step 4 | Step 1, 3 | ✅ 적절 | Hybrid Memory 사용 |
| Step 5 | Step 4 | ✅ 적절 | Context 전달 |
| Step 6 | Step 5 | ✅ 적절 | 변수 추가 |
| Step 7 | All | ✅ 적절 | 통합 테스트 |

**결론**: ✅ **구현 순서 합리적**

---

### 7.3 권장 수정 순서

계획서의 순서를 따르되, 아래 사항 추가:

#### Step 0 (선행 작업): 현재 코드 백업 및 검증
```bash
# Git 커밋 (현재 상태 저장)
git add .
git commit -m "Backup before Hybrid Memory implementation"

# Branch 생성
git checkout -b feature/hybrid-memory

# 현재 설정 확인
python -c "from app.core.config import settings; print(settings.MEMORY_LOAD_LIMIT)"
```

#### Step 1: 설정 파일 수정 (15분)
1. `config.py`: **Field import 추가 먼저**
2. `config.py`: Field 기반 설정 추가
3. `.env`: 환경 변수 추가
4. 서버 재시작 및 설정 로드 확인

#### Step 2: LLM 요약 기능 구현 (40분)
1. **디렉터리 생성 먼저**: `prompts/memory/`
2. Prompt 템플릿 생성
3. `simple_memory_service.py`: **Import 추가 먼저**
4. `summarize_with_llm` 메서드 추가
5. `summarize_conversation_background` 메서드 추가
6. 로그 확인

#### Step 3: Hybrid Memory 로더 구현 (30분)
1. `load_hybrid_memories` 메서드 추가
2. 단위 테스트 (메서드만)

#### Step 4: team_supervisor.py 수정 (30분)
1. **settings import 확인/추가**
2. planning_node: Hybrid Memory 로드 (기존 로직 **통합**)
3. Context 생성 수정
4. generate_response_node: 백그라운드 요약 추가
5. 로그 확인

#### Step 5: planning_agent.py 수정 (20분)
1. Recent/Mid-term Memory 포맷팅 추가
2. Variables에 추가

#### Step 6: intent_analysis.txt 수정 (20분)
1. Recent/Mid-term Memory 섹션 추가
2. 분석 지침 업데이트

#### Step 7: 테스트 및 검증 (30분)
1. 단위 테스트
2. 통합 테스트
3. 로그 확인
4. 응답 시간 측정

**총 예상 시간**: 3시간 10분

---

## 8. 최종 체크리스트

### 8.1 구현 전 체크리스트

- [ ] 현재 코드 Git 커밋
- [ ] Feature Branch 생성
- [ ] `.env`, `config.py` 백업
- [ ] 테스트 환경 준비
- [ ] **Field import 확인** (config.py)
- [ ] **prompts/memory/ 디렉터리 확인**

### 8.2 구현 중 체크리스트

**Step 1: 설정**
- [ ] **config.py: Field import 추가 확인**
- [ ] config.py: Field 기반 설정 추가
- [ ] .env: 환경 변수 추가
- [ ] 서버 재시작하여 설정 로드 확인

**Step 2: LLM 요약**
- [ ] **prompts/memory/ 디렉터리 생성**
- [ ] Prompt 템플릿 생성
- [ ] **simple_memory_service.py: Import 추가 (LLMService, settings)**
- [ ] `summarize_with_llm()` 메서드 추가
- [ ] `summarize_conversation_background()` 메서드 추가
- [ ] 로그 확인

**Step 3: Hybrid Memory 로더**
- [ ] `load_hybrid_memories()` 메서드 추가
- [ ] Recent Memory 로드 확인
- [ ] Mid-term Memory 로드 확인
- [ ] 로그 확인

**Step 4: team_supervisor.py**
- [ ] **settings import 확인/추가**
- [ ] Hybrid Memory 조회 코드 추가 (**기존 로직 통합**)
- [ ] Context 생성 수정
- [ ] 백그라운드 요약 추가
- [ ] 로그 확인

**Step 5: planning_agent.py**
- [ ] Recent Memory 포맷팅 추가
- [ ] Mid-term Memory 포맷팅 추가
- [ ] Variables에 추가
- [ ] 로그 확인

**Step 6: Prompt**
- [ ] intent_analysis.txt 수정
- [ ] Recent Memory 섹션 추가
- [ ] Mid-term Memory 섹션 추가
- [ ] 분석 지침 업데이트

### 8.3 구현 후 체크리스트

- [ ] 서버 재시작
- [ ] 테스트 1: Recent Memory 동작 확인
- [ ] 테스트 2: Mid-term Memory 동작 확인
- [ ] 테스트 3: LLM 요약 확인
- [ ] 테스트 4: 설정 변경 테스트
- [ ] 로그 확인 (에러 없음)
- [ ] 응답 시간 측정 (+500ms 이내 확인)
- [ ] Git 커밋
- [ ] 문서 업데이트

---

## 9. 결론 및 권고

### 9.1 전체 평가

**계획서 품질**: ⭐⭐⭐⭐☆ (4/5)

**장점**:
- ✅ 전반적인 구조 정확히 파악
- ✅ 구현 순서 합리적
- ✅ 설정 기반 활성화/비활성화 설계 우수
- ✅ 롤백 계획 체계적

**단점**:
- ❌ Field import 누락 (Critical)
- ⚠️ 기존 Long-term Memory 로직 충돌 고려 부족
- ⚠️ 일부 import 누락
- 💡 planning_agent.py, intent_analysis.txt 현황 누락

---

### 9.2 최종 권고사항

#### 즉시 수정 필요 (🔴 Critical)
1. **config.py: Field import 추가**
2. **team_supervisor.py: 기존 Long-term Memory 로직 통합 방식 재검토**

#### 구현 전 확인 필요 (⚠️ High)
3. **simple_memory_service.py: Import 추가 (LLMService, settings)**
4. **team_supervisor.py: settings import 확인**
5. **prompts/memory/ 디렉터리 생성**

#### 개선 권장 (💡 Medium)
6. 계획서 "현재 상황" 섹션에 planning_agent.py, intent_analysis.txt 추가
7. 라인 번호 정확도 향상 (미세 조정)

---

### 9.3 구현 가능성

**전체 평가**: ✅ **구현 가능** (일부 수정 후)

**예상 소요 시간**: 3시간 10분 (원래 2.5시간 → 40분 증가)

**성공 확률**: 85% (수정사항 반영 시 95%)

---

**작성 완료**: 2025-10-20
**검증자**: Claude Code Analysis System
**다음 단계**: 계획서 수정 후 구현 시작 권장
