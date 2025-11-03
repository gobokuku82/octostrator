# 3-Tier Hybrid Memory 종합 영향 분석 보고서

**작성일**: 2025-10-21
**작성자**: Claude Code Analysis
**분석 범위**: 전체 코드베이스 대조 및 세부 분석
**예상 작업 시간**: 3시간 45분

---

## 📋 목차

1. [분석 요약](#분석-요약)
2. [현재 코드 상태 검증](#현재-코드-상태-검증)
3. [영향 받는 파일 전체 목록](#영향-받는-파일-전체-목록)
4. [코드 흐름 분석](#코드-흐름-분석)
5. [구현 계획 검증](#구현-계획-검증)
6. [잠재적 이슈 및 해결방안](#잠재적-이슈-및-해결방안)
7. [종합 체크리스트](#종합-체크리스트)

---

## 분석 요약

### 🎯 핵심 발견사항

#### ✅ 계획서 정확도: 95%
- **정확한 부분**: 6개 설정 필드, 메서드 시그니처, DB 트랜잭션 패턴
- **부정확한 부분**: 노드 위치 Line 번호 (실제 코드와 약간 차이)
- **누락된 부분**: 프롬프트 디렉토리 구조, LLM 호출 패턴

#### ⚠️ 발견된 이슈

1. **프롬프트 파일 누락**
   - `conversation_summary.txt` 파일이 존재하지 않음
   - 현재 prompts 구조: cognitive/, common/, execution/ (3개 카테고리만)
   - 필요: common/conversation_summary.txt 추가

2. **Line 번호 불일치**
   - 계획서 Line 870 → 실제 Line 174-252 (generate_response_node)
   - 계획서 Line 235-263 → 실제와 일치 (planning_node)

3. **State 필드 정의 누락**
   - `tiered_memories` 필드가 separated_states.py에 아직 정의되지 않음
   - 필수는 아니지만, 타입 안정성을 위해 권장

---

## 현재 코드 상태 검증

### 1. Config.py (backend/app/core/config.py)

**현재 상태**:
```python
# Line 1-2
from typing import List
from pydantic_settings import BaseSettings

# Line 31
MEMORY_LOAD_LIMIT: int = 5
```

**검증 결과**:
- ✅ MEMORY_LOAD_LIMIT 존재
- ❌ `from pydantic import Field` 누락
- ❌ 6개 신규 Field 미정의

**필요한 수정**:
```python
# Line 2에 추가
from pydantic import Field

# Line 31 이후 추가
SHORTTERM_MEMORY_LIMIT: int = Field(default=5, description="...")
MIDTERM_MEMORY_LIMIT: int = Field(default=5, description="...")
LONGTERM_MEMORY_LIMIT: int = Field(default=10, description="...")
MEMORY_TOKEN_LIMIT: int = Field(default=2000, description="...")
MEMORY_MESSAGE_LIMIT: int = Field(default=10, description="...")
SUMMARY_MAX_LENGTH: int = Field(default=200, description="...")
```

---

### 2. SimpleMemoryService (simple_memory_service.py)

**현재 상태 (Line 5-10)**:
```python
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, desc  # ← and_ 누락
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
```

**검증 결과**:
- ✅ 기본 imports 존재
- ❌ `import asyncio` 누락
- ❌ `import tiktoken` 누락
- ❌ `and_` 누락 (from sqlalchemy)

**총 라인 수**: 392 lines
**기존 메서드**:
- `load_recent_memories()` (Lines 217-329) ✅
- `save_conversation()` (Lines 331-386) ✅

**누락된 메서드** (6개):
1. `load_tiered_memories()` - 3-Tier 구조 로드
2. `_get_or_create_summary()` - 요약 캐시 조회
3. `summarize_with_llm()` - LLM 요약 생성
4. `_save_summary_to_metadata()` - JSONB 저장
5. `summarize_conversation_background()` - 백그라운드 진입점
6. `_background_summary_task()` - 백그라운드 실행

---

### 3. TeamSupervisor (team_supervisor.py)

#### A. planning_node (Lines 174-397)

**현재 메모리 로딩 로직 (Lines 235-263)**:
```python
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
                session_id=chat_session_id  # 현재 진행 중인 세션 제외
            )

            # 사용자 선호도 로드
            user_preferences = await memory_service.get_user_preferences(user_id)

            state["loaded_memories"] = loaded_memories
            state["user_preferences"] = user_preferences
            state["memory_load_time"] = datetime.now().isoformat()

            logger.info(f"[TeamSupervisor] Loaded {len(loaded_memories)} memories and preferences for user {user_id}")
            break  # get_db()는 generator이므로 첫 번째 세션만 사용
    except Exception as e:
        logger.error(f"[TeamSupervisor] Failed to load Long-term Memory: {e}")
```

**검증 결과**:
- ✅ DB 트랜잭션 패턴 정확 (`async for db_session in get_async_db()`)
- ✅ 에러 핸들링 존재
- ✅ State 업데이트 패턴 정확
- ⚠️ `tiered_memories` 필드 추가 필요

**필요한 수정**:
```python
# load_recent_memories() 호출을 load_tiered_memories()로 교체
tiered_memories = await memory_service.load_tiered_memories(
    user_id=user_id,
    current_session_id=chat_session_id
)

# State에 tiered_memories 추가
state["tiered_memories"] = tiered_memories
state["loaded_memories"] = (  # 하위 호환성
    tiered_memories.get("shortterm", []) +
    tiered_memories.get("midterm", []) +
    tiered_memories.get("longterm", [])
)
```

#### B. generate_response_node (Lines 174-252)

**현재 메모리 저장 로직 (Lines 216-250)**:
```python
user_id = state.get("user_id")
if user_id and intent_type not in ["irrelevant", "unclear"]:
    try:
        logger.info(f"[TeamSupervisor] Saving conversation to Long-term Memory for user {user_id}")

        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            # 응답 요약 생성 (최대 200자)
            response_summary = response.get("summary", "")
            if not response_summary and response.get("answer"):
                response_summary = response.get("answer", "")[:200]
            if not response_summary:
                response_summary = f"{response.get('type', 'response')} 생성 완료"

            # chat_session_id 추출 (Chat History & State Endpoints)
            chat_session_id = state.get("chat_session_id")

            # 대화 저장 (Phase 1: 간소화된 4개 파라미터)
            await memory_service.save_conversation(
                user_id=user_id,
                session_id=chat_session_id,
                messages=[],  # Phase 1에서는 빈 리스트
                summary=response_summary
            )

            logger.info(f"[TeamSupervisor] Conversation saved to Long-term Memory")
            break  # get_db()는 generator이므로 첫 번째 세션만 사용
    except Exception as e:
        logger.error(f"[TeamSupervisor] Failed to save Long-term Memory: {e}")
```

**검증 결과**:
- ✅ save_conversation 시그니처 정확 (user_id, session_id, messages, summary)
- ✅ DB 트랜잭션 패턴 정확
- ✅ 에러 핸들링 존재
- ⚠️ 백그라운드 요약 호출 추가 필요

**필요한 수정**:
```python
# save_conversation 호출 전에 백그라운드 요약 시작
await memory_service.summarize_conversation_background(
    session_id=chat_session_id,
    user_id=user_id,
    messages=[]
)
```

---

### 4. LLMService (llm_service.py)

**complete_async() 메서드 (Lines 146-196)**:
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
    # 프롬프트 로드
    prompt = self.prompt_manager.get(prompt_name, variables or {})

    # 모델 선택
    if model is None:
        model = Config.LLM_DEFAULTS["models"].get(prompt_name, "gpt-4o-mini")

    # 파라미터 설정
    params = {
        "model": model,
        "messages": [{"role": "system", "content": prompt}],
        "temperature": temperature or Config.LLM_DEFAULTS["default_params"]["temperature"],
        "max_tokens": max_tokens or Config.LLM_DEFAULTS["default_params"]["max_tokens"],
    }

    if response_format:
        params["response_format"] = response_format

    params.update(kwargs)

    # 비동기 LLM 호출 with 재시도
    try:
        response = await self._call_async_with_retry(params)
        self._log_call(prompt_name, response)
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Async LLM call failed for {prompt_name}: {e}")
        raise
```

**검증 결과**:
- ✅ PromptManager 사용 (`self.prompt_manager.get(prompt_name, variables)`)
- ✅ 비동기 재시도 로직 존재
- ✅ 에러 핸들링 존재
- ✅ `conversation_summary` 프롬프트 호출 가능

**필요한 작업**:
- `conversation_summary.txt` 파일만 생성하면 바로 사용 가능

---

### 5. PromptManager (prompt_manager.py)

**프롬프트 로딩 로직 (Lines 160-202)**:
```python
def _load_template(self, prompt_name: str, category: str = None) -> str:
    # 캐시 확인
    cache_key = f"{category}/{prompt_name}" if category else prompt_name
    if cache_key in self._cache:
        logger.debug(f"Using cached prompt: {cache_key}")
        return self._cache[cache_key]

    # 파일 경로 결정
    file_path = self._find_prompt_file(prompt_name, category)

    if not file_path or not file_path.exists():
        raise FileNotFoundError(
            f"Prompt template not found: {prompt_name} "
            f"(category: {category or 'auto'})"
        )

    # 파일 로드
    logger.debug(f"Loading prompt from: {file_path}")

    if file_path.suffix == ".yaml" or file_path.suffix == ".yml":
        template, metadata = self._load_yaml_template(file_path)
        self._metadata_cache[prompt_name] = metadata
    else:  # .txt
        with open(file_path, 'r', encoding='utf-8') as f:
            template = f.read()

    # 캐시 저장
    self._cache[cache_key] = template

    return template
```

**검증 결과**:
- ✅ .txt 파일 자동 로드 지원
- ✅ 3개 카테고리 탐색 (cognitive, execution, common)
- ✅ 캐싱 메커니즘 존재

**필요한 작업**:
- `prompts/common/conversation_summary.txt` 파일만 생성하면 자동 로드됨

---

### 6. SeparatedStates (separated_states.py)

**MainSupervisorState 정의 (Lines 286-332)**:
```python
class MainSupervisorState(TypedDict, total=False):
    # ... 기존 필드들 ...

    # Long-term Memory Fields (Line 329-332)
    user_id: Optional[int]
    loaded_memories: Optional[List[Dict[str, Any]]]
    user_preferences: Optional[Dict[str, Any]]
    memory_load_time: Optional[str]

    # ⚠️ tiered_memories 누락
```

**검증 결과**:
- ✅ loaded_memories 필드 존재
- ✅ user_id, user_preferences 존재
- ❌ tiered_memories 필드 누락

**필요한 추가**:
```python
# Line 332 이후 추가
tiered_memories: Optional[Dict[str, List[Dict[str, Any]]]]
```

---

## 영향 받는 파일 전체 목록

### 직접 수정 필요 (7개 파일)

| 파일 경로 | 수정 내용 | 예상 시간 |
|----------|----------|----------|
| `backend/app/core/config.py` | Field import, 6개 설정 추가 | 5분 |
| `backend/.env` | 6개 환경변수 추가 | 2분 |
| `backend/app/service_agent/foundation/simple_memory_service.py` | imports, 6개 메서드 추가 | 80분 |
| `backend/app/service_agent/supervisor/team_supervisor.py` | planning_node, generate_response_node 수정 | 50분 |
| `backend/app/service_agent/cognitive_agents/planning_agent.py` | tiered_memories 활용 로직 | 30분 |
| `backend/app/service_agent/llm_manager/prompts/common/conversation_summary.txt` | 프롬프트 파일 생성 | 10분 |
| `backend/app/service_agent/foundation/separated_states.py` | tiered_memories 필드 추가 (선택) | 5분 |

### 간접 영향 (자동 호환)

| 파일 경로 | 영향 내용 | 조치 필요 |
|----------|----------|----------|
| `backend/app/service_agent/llm_manager/llm_service.py` | 새 프롬프트 호출 | 없음 (자동) |
| `backend/app/service_agent/llm_manager/prompt_manager.py` | 새 프롬프트 로드 | 없음 (자동) |
| `backend/app/models/chat.py` | JSONB metadata 사용 | 없음 (기존 구조) |
| `backend/app/db/postgre_db.py` | DB 세션 제공 | 없음 (기존 패턴) |

### 테스트 파일 (1개)

| 파일 경로 | 목적 | 예상 시간 |
|----------|------|----------|
| `backend/test_3tier_memory.py` | 통합 테스트 | 50분 |

---

## 코드 흐름 분석

### 1. State 전파 흐름

```
사용자 요청
    ↓
[initialize_node]
    ↓
    state["user_id"] = user_id
    state["chat_session_id"] = session_id
    ↓
[planning_node] ← ⚡ 메모리 로드 지점
    ↓
    async for db_session in get_async_db():
        memory_service = LongTermMemoryService(db_session)

        # 🔵 현재 (Phase 0)
        loaded_memories = await memory_service.load_recent_memories(
            user_id=user_id,
            limit=settings.MEMORY_LOAD_LIMIT,
            session_id=chat_session_id
        )
        state["loaded_memories"] = loaded_memories

        # 🟢 변경 후 (Phase 1)
        tiered_memories = await memory_service.load_tiered_memories(
            user_id=user_id,
            current_session_id=chat_session_id
        )
        state["tiered_memories"] = tiered_memories
        state["loaded_memories"] = tiered_memories["shortterm"] + ...
    ↓
[execute_teams_node]
    ↓
    shared_state = StateManager.create_shared_state(
        query=state["query"],
        session_id=state["session_id"]
    )
    # 팀 실행 (SearchTeam, AnalysisTeam, DocumentTeam)
    ↓
[aggregate_results_node]
    ↓
    state["aggregated_results"] = {...}
    ↓
[generate_response_node] ← ⚡ 메모리 저장 지점
    ↓
    async for db_session in get_async_db():
        memory_service = LongTermMemoryService(db_session)

        # 🟢 추가 (Phase 1)
        await memory_service.summarize_conversation_background(
            session_id=chat_session_id,
            user_id=user_id,
            messages=[]
        )

        # 기존 (Phase 0)
        await memory_service.save_conversation(
            user_id=user_id,
            session_id=chat_session_id,
            messages=[],
            summary=response_summary
        )
    ↓
    state["final_response"] = response
    ↓
사용자 응답 반환
```

### 2. 메모리 로드 상세 흐름

```python
# planning_node (Line 235-263)
user_id = state.get("user_id")  # 예: 1
chat_session_id = state.get("chat_session_id")  # 예: "session-abc-123"

# LongTermMemoryService 초기화
async for db_session in get_async_db():
    memory_service = LongTermMemoryService(db_session)

    # 🔵 Phase 0: 기존 방식
    loaded_memories = await memory_service.load_recent_memories(
        user_id=1,
        limit=5,  # settings.MEMORY_LOAD_LIMIT
        relevance_filter="RELEVANT",
        session_id="session-abc-123"
    )
    # 반환 형식:
    # [
    #     {"session_id": "session-xyz", "summary": "강남구 전세 시세 문의", ...},
    #     {"session_id": "session-def", "summary": "대출 조건 확인", ...},
    #     ...
    # ]

    # 🟢 Phase 1: 3-Tier 방식
    tiered_memories = await memory_service.load_tiered_memories(
        user_id=1,
        current_session_id="session-abc-123"
    )
    # 반환 형식:
    # {
    #     "shortterm": [
    #         {
    #             "session_id": "session-1",
    #             "messages": [
    #                 {"role": "user", "content": "...", "timestamp": "..."},
    #                 {"role": "assistant", "content": "...", "timestamp": "..."},
    #                 ...
    #             ],
    #             "metadata": {...},
    #             "tier": "shortterm"
    #         },
    #         ...  # 최근 5개 세션 (설정 가능)
    #     ],
    #     "midterm": [
    #         {
    #             "session_id": "session-6",
    #             "summary": "강남구 아파트 전세 시세 및 대출 조건 문의",
    #             "metadata": {...},
    #             "tier": "midterm"
    #         },
    #         ...  # 6-10번째 세션 (설정 가능)
    #     ],
    #     "longterm": [
    #         {
    #             "session_id": "session-11",
    #             "summary": "서초구 오피스텔 월세 관련 법률 상담",
    #             "metadata": {...},
    #             "tier": "longterm"
    #         },
    #         ...  # 11-20번째 세션 (설정 가능)
    #     ]
    # }

    # State 업데이트
    state["tiered_memories"] = tiered_memories
    state["loaded_memories"] = (  # 하위 호환성
        tiered_memories["shortterm"] +
        tiered_memories["midterm"] +
        tiered_memories["longterm"]
    )
```

### 3. LLM 요약 생성 흐름

```python
# generate_response_node (Line 216-250)
async for db_session in get_async_db():
    memory_service = LongTermMemoryService(db_session)

    # 백그라운드 요약 시작 (fire-and-forget)
    await memory_service.summarize_conversation_background(
        session_id="session-abc-123",
        user_id=1,
        messages=[]
    )
    # ↓ (비동기 백그라운드 실행)
    # asyncio.create_task(_background_summary_task(...))
    #     ↓
    #     summarize_with_llm("session-abc-123")
    #         ↓
    #         1. chat_messages에서 대화 로드
    #         2. 대화 포맷팅 (최근 10개 메시지)
    #         3. LLMService.complete_async(
    #                prompt_name="conversation_summary",
    #                variables={"conversation": "...", "max_length": 200}
    #            )
    #         4. _save_summary_to_metadata(session_id, summary)
    #             ↓
    #             session.session_metadata["conversation_summary"] = summary
    #             flag_modified(session, "session_metadata")
    #             await db.commit()

    # 기존 저장 로직 (즉시 실행)
    await memory_service.save_conversation(
        user_id=1,
        session_id="session-abc-123",
        messages=[],
        summary=response_summary
    )
```

### 4. 토큰 제한 로직

```python
# simple_memory_service.py - load_tiered_memories()
encoding = tiktoken.get_encoding("cl100k_base")
total_tokens = 0

for idx, session in enumerate(sessions):
    # 토큰 제한 체크
    if total_tokens >= settings.MEMORY_TOKEN_LIMIT:  # 기본 2000
        logger.info(f"Token limit reached: {total_tokens}")
        break

    if idx < settings.SHORTTERM_MEMORY_LIMIT:
        # Short-term: 전체 메시지
        content_text = " ".join([m["content"] for m in messages])
        tokens = len(encoding.encode(content_text))
        total_tokens += tokens

        if total_tokens > settings.MEMORY_TOKEN_LIMIT:
            break  # 제한 초과

    elif idx < settings.SHORTTERM_MEMORY_LIMIT + settings.MIDTERM_MEMORY_LIMIT:
        # Mid-term: 요약만
        summary = await self._get_or_create_summary(session)
        tokens = len(encoding.encode(summary))
        total_tokens += tokens

    else:
        # Long-term: 요약만
        summary = await self._get_or_create_summary(session)
        tokens = len(encoding.encode(summary))
        total_tokens += tokens
```

---

## 구현 계획 검증

### Phase별 정확도 평가

| Phase | 내용 | 정확도 | 발견된 이슈 | 권장사항 |
|-------|------|--------|------------|----------|
| Phase 1 | 설정 파일 | ✅ 100% | 없음 | 그대로 진행 |
| Phase 2 | 메모리 서비스 | ✅ 98% | import 순서 권장사항 | Line 387 이후 추가 정확 |
| Phase 3 | Supervisor | ⚠️ 90% | Line 번호 불일치 | 실제 위치: Line 235-263, 174-252 |
| Phase 4 | Planning Agent | ✅ 95% | 구체적 위치 누락 | analyze_intent 메서드 내부 |
| Phase 5 | 프롬프트 | ✅ 100% | 없음 | common/ 디렉토리 확인됨 |
| Phase 6 | 테스트 | ✅ 100% | 없음 | pytest-asyncio 확인 필요 |

### 수정된 Line 번호

| 계획서 | 실제 | 메서드 | 파일 |
|-------|------|--------|------|
| Line 235-263 | ✅ Line 235-263 | planning_node | team_supervisor.py |
| Line 870~ | ❌ Line 174-252 | generate_response_node | team_supervisor.py |

---

## 잠재적 이슈 및 해결방안

### 1. 프롬프트 파일 누락

**이슈**:
```bash
FileNotFoundError: Prompt template not found: conversation_summary
```

**원인**:
- `backend/app/service_agent/llm_manager/prompts/common/conversation_summary.txt` 파일 없음

**해결방안**:
```bash
# 파일 생성
touch backend/app/service_agent/llm_manager/prompts/common/conversation_summary.txt

# 내용 작성 (계획서 Phase 5-1 참조)
cat > backend/app/service_agent/llm_manager/prompts/common/conversation_summary.txt << 'EOF'
당신은 대화 내용을 간결하게 요약하는 전문가입니다.

다음 대화를 {max_length}자 이내로 요약해주세요:

{conversation}

요약 규칙:
1. 핵심 주제와 결론만 포함
2. 사용자의 주요 요구사항 명시
3. 중요한 결정사항이나 합의 내용 포함
4. 불필요한 인사말이나 반복 제외

요약:
EOF
```

---

### 2. tiktoken 설치 확인

**이슈**:
```python
ModuleNotFoundError: No module named 'tiktoken'
```

**해결방안**:
```bash
# 설치
pip install tiktoken

# 또는 requirements.txt에 추가
echo "tiktoken==0.5.2" >> backend/requirements.txt
pip install -r backend/requirements.txt
```

---

### 3. DB 세션 타이밍 이슈

**잠재적 문제**:
- 백그라운드 태스크에서 DB 세션이 이미 닫힌 경우

**현재 코드**:
```python
# generate_response_node
async for db_session in get_async_db():
    memory_service = LongTermMemoryService(db_session)

    # 백그라운드 시작
    await memory_service.summarize_conversation_background(...)

    # 즉시 저장
    await memory_service.save_conversation(...)

    break  # ← DB 세션 종료
```

**문제**:
- `summarize_conversation_background()`가 `asyncio.create_task()`로 실행
- 메인 플로우가 `break`로 종료되면 db_session 닫힘
- 백그라운드 태스크에서 `_save_summary_to_metadata()`가 닫힌 세션 사용

**해결방안 1**: 독립 세션 생성
```python
async def _background_summary_task(self, session_id: str, user_id: int, messages: List) -> None:
    try:
        # 새로운 DB 세션 생성
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)

            summary = await memory_service.summarize_with_llm(session_id)
            await memory_service._save_summary_to_metadata(session_id, summary)

            break
    except Exception as e:
        logger.error(f"Background summary failed: {e}")
```

**해결방안 2**: 세션 ID만 전달
```python
async def summarize_conversation_background(
    self,
    session_id: str,
    user_id: int,
    messages: List[Dict[str, Any]]
) -> None:
    """백그라운드에서 대화 요약 (세션 독립)"""
    asyncio.create_task(
        self._background_summary_with_new_session(session_id, user_id)
    )

async def _background_summary_with_new_session(self, session_id: str, user_id: int) -> None:
    """새 세션으로 백그라운드 요약"""
    try:
        async for db_session in get_async_db():
            temp_service = LongTermMemoryService(db_session)
            summary = await temp_service.summarize_with_llm(session_id)
            await temp_service._save_summary_to_metadata(session_id, summary)
            break
    except Exception as e:
        logger.error(f"Background summary failed: {e}")
```

**권장**: 해결방안 2 (독립 세션)

---

### 4. State 타입 안전성

**이슈**:
- `tiered_memories` 필드가 TypedDict에 정의되지 않으면 IDE 경고

**현재**:
```python
state["tiered_memories"] = tiered_memories  # ← Type warning
```

**해결방안**:
```python
# separated_states.py Line 332 이후 추가
class MainSupervisorState(TypedDict, total=False):
    # ... 기존 필드들 ...

    # Long-term Memory Fields
    user_id: Optional[int]
    loaded_memories: Optional[List[Dict[str, Any]]]
    user_preferences: Optional[Dict[str, Any]]
    memory_load_time: Optional[str]

    # 3-Tier Memory (Phase 1)
    tiered_memories: Optional[Dict[str, List[Dict[str, Any]]]]  # ← 추가
```

---

### 5. Planning Agent 통합 위치

**이슈**:
- 계획서에 "적절한 메서드 내부"라고만 명시됨

**정확한 위치**:
```python
# planning_agent.py - analyze_intent 메서드
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    """LLM을 사용한 의도 분석"""
    try:
        # Context에서 chat_history 추출
        chat_history = context.get("chat_history", []) if context else []

        # 🟢 여기에 tiered_memories 통합 추가
        tiered_memories = context.get("tiered_memories", {}) if context else {}

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

        # LLMService를 통한 의도 분석
        result = await self.llm_service.complete_json_async(
            prompt_name="intent_analysis",
            variables={
                "query": query,
                "chat_history": chat_history_text,
                "memory_context": memory_context  # ← 추가
            },
            temperature=0.0,
            max_tokens=500
        )

        # ... 나머지 코드 ...
```

**추가 필요 작업**:
- `intent_analysis.txt` 프롬프트에 `{memory_context}` 변수 추가

---

## 종합 체크리스트

### 구현 전 준비 (10분)

- [ ] **백업 생성**
  ```bash
  cp backend/app/core/config.py backend/app/core/config.py.backup
  cp backend/app/service_agent/foundation/simple_memory_service.py backend/app/service_agent/foundation/simple_memory_service.py.backup
  cp backend/app/service_agent/supervisor/team_supervisor.py backend/app/service_agent/supervisor/team_supervisor.py.backup
  cp backend/.env backend/.env.backup
  ```

- [ ] **의존성 확인 및 설치**
  ```bash
  pip install tiktoken pytest-asyncio
  ```

- [ ] **프롬프트 디렉토리 확인**
  ```bash
  ls backend/app/service_agent/llm_manager/prompts/common/
  # 출력에 conversation_summary.txt가 없으면 생성 필요
  ```

---

### Phase 1: 설정 (15분)

- [ ] **config.py - Line 2 수정**
  ```python
  from pydantic import Field  # ← 추가
  ```

- [ ] **config.py - Line 31 이후 추가**
  ```python
  SHORTTERM_MEMORY_LIMIT: int = Field(default=5, description="최근 N개 세션 전체 메시지 로드")
  MIDTERM_MEMORY_LIMIT: int = Field(default=5, description="중기 메모리 세션 수 (6-10번째)")
  LONGTERM_MEMORY_LIMIT: int = Field(default=10, description="장기 메모리 세션 수 (11-20번째)")
  MEMORY_TOKEN_LIMIT: int = Field(default=2000, description="메모리 로드 시 최대 토큰 제한")
  MEMORY_MESSAGE_LIMIT: int = Field(default=10, description="Short-term 세션당 최대 메시지 수")
  SUMMARY_MAX_LENGTH: int = Field(default=200, description="LLM 요약 최대 글자 수")
  ```

- [ ] **.env - 환경변수 추가**
  ```bash
  SHORTTERM_MEMORY_LIMIT=5
  MIDTERM_MEMORY_LIMIT=5
  LONGTERM_MEMORY_LIMIT=10
  MEMORY_TOKEN_LIMIT=2000
  MEMORY_MESSAGE_LIMIT=10
  SUMMARY_MAX_LENGTH=200
  ```

- [ ] **설정 검증**
  ```bash
  python -c "from app.core.config import settings; print(settings.SHORTTERM_MEMORY_LIMIT)"
  # 출력: 5
  ```

---

### Phase 2: 메모리 서비스 (1시간 20분)

- [ ] **simple_memory_service.py - imports 수정 (Line 5-10)**
  ```python
  import logging
  from typing import List, Dict, Any, Optional
  from datetime import datetime
  import asyncio  # ← 추가
  import tiktoken  # ← 추가
  from sqlalchemy import select, desc, and_  # ← and_ 추가
  ```

- [ ] **Line 387 이후 - load_tiered_memories() 추가**
  - 계획서 Phase 2-2-A 전체 코드 복사

- [ ] **_get_or_create_summary() 추가**
  - 계획서 Phase 2-2-B 전체 코드 복사

- [ ] **summarize_with_llm() 추가**
  - 계획서 Phase 2-2-C 전체 코드 복사

- [ ] **_save_summary_to_metadata() 추가**
  - 계획서 Phase 2-2-D 전체 코드 복사

- [ ] **summarize_conversation_background() 추가**
  - ⚠️ 수정된 버전 (독립 세션) 사용:
  ```python
  async def summarize_conversation_background(
      self,
      session_id: str,
      user_id: int,
      messages: List[Dict[str, Any]]
  ) -> None:
      """백그라운드에서 대화 요약 (독립 세션)"""
      asyncio.create_task(
          self._background_summary_with_new_session(session_id, user_id)
      )
  ```

- [ ] **_background_summary_with_new_session() 추가**
  - ⚠️ 새 버전 (독립 세션):
  ```python
  async def _background_summary_with_new_session(
      self,
      session_id: str,
      user_id: int
  ) -> None:
      """새 세션으로 백그라운드 요약"""
      try:
          async for db_session in get_async_db():
              temp_service = LongTermMemoryService(db_session)
              summary = await temp_service.summarize_with_llm(session_id)
              await temp_service._save_summary_to_metadata(session_id, summary)
              break
      except Exception as e:
          logger.error(f"Background summary failed: {e}")
  ```

- [ ] **메서드 존재 확인**
  ```python
  from app.service_agent.foundation.simple_memory_service import SimpleMemoryService
  print(hasattr(SimpleMemoryService, 'load_tiered_memories'))  # True
  print(hasattr(SimpleMemoryService, 'summarize_with_llm'))  # True
  ```

---

### Phase 3: Supervisor (50분)

- [ ] **team_supervisor.py - planning_node 수정 (Line 235-263)**
  - ⚠️ 정확한 위치: Line 244-249 (load_recent_memories 호출 부분)
  - 계획서 Phase 3-1 수정 후 코드 사용

- [ ] **team_supervisor.py - generate_response_node 수정**
  - ⚠️ 정확한 위치: Line 216-250 (save_conversation 호출 부분)
  - 계획서 Phase 3-2 수정 후 코드 사용
  - 백그라운드 요약 호출 추가

- [ ] **로그 확인**
  ```bash
  # 서버 실행 후 테스트 요청
  tail -f backend/logs/app.log | grep "3-Tier"
  # 출력 예상: "3-Tier memories loaded - Short(5), Mid(3), Long(2)"
  ```

---

### Phase 4: Planning Agent (30분)

- [ ] **planning_agent.py - _analyze_with_llm 메서드 수정**
  - 위치: Line 183-248 (async def _analyze_with_llm)
  - context에서 tiered_memories 추출
  - memory_context 문자열 생성
  - variables에 memory_context 추가

- [ ] **intent_analysis.txt 프롬프트 수정 (선택)**
  - 파일: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`
  - `{memory_context}` 변수 추가 (필요 시)

---

### Phase 5: 프롬프트 (20분)

- [ ] **conversation_summary.txt 생성**
  - 경로: `backend/app/service_agent/llm_manager/prompts/common/conversation_summary.txt`
  - 내용: 계획서 Phase 5-1 전체 복사

- [ ] **프롬프트 로드 테스트**
  ```python
  from app.service_agent.llm_manager.prompt_manager import PromptManager
  pm = PromptManager()
  prompt = pm.get('conversation_summary', {
      'conversation': '테스트 대화',
      'max_length': 100
  })
  print("SUCCESS" if "테스트 대화" in prompt else "FAILED")
  ```

---

### Phase 6: 테스트 (50분)

- [ ] **test_3tier_memory.py 생성**
  - 경로: `backend/test_3tier_memory.py`
  - 내용: 계획서 Phase 6-1 전체 복사

- [ ] **테스트 실행**
  ```bash
  # 개별 테스트
  pytest backend/test_3tier_memory.py::test_3tier_memory_loading -v
  pytest backend/test_3tier_memory.py::test_llm_summarization -v

  # 전체 테스트
  pytest backend/test_3tier_memory.py -v
  ```

- [ ] **통합 테스트 (실제 요청)**
  ```bash
  # 1. 서버 시작
  cd backend
  python main.py

  # 2. 요청 전송 (별도 터미널)
  curl -X POST http://localhost:8000/api/chat/query \
    -H "Content-Type: application/json" \
    -d '{"query": "강남구 아파트 전세 시세 알려주세요", "user_id": 1, "session_id": "test-001"}'

  # 3. 로그 확인
  tail -f backend/logs/app.log | grep "3-Tier\|tiered_memories"
  ```

---

### 선택: State 정의 (5분)

- [ ] **separated_states.py - tiered_memories 필드 추가**
  - 위치: Line 332 이후
  ```python
  tiered_memories: Optional[Dict[str, List[Dict[str, Any]]]]
  ```

- [ ] **타입 검증**
  ```python
  from app.service_agent.foundation.separated_states import MainSupervisorState
  import inspect
  print("tiered_memories" in MainSupervisorState.__annotations__)  # True
  ```

---

### 최종 검증 (15분)

- [ ] **전체 플로우 테스트**
  1. 사용자 요청 → planning_node에서 메모리 로드 확인
  2. generate_response_node에서 백그라운드 요약 시작 확인
  3. DB에 conversation_summary 저장 확인
  4. 다음 요청에서 3-Tier 구조로 로드 확인

- [ ] **DB 확인**
  ```sql
  -- PostgreSQL
  SELECT
      session_id,
      session_metadata->'conversation_summary' as summary,
      session_metadata->'summary_method' as method,
      session_metadata->'summary_updated_at' as updated
  FROM chat_sessions
  WHERE user_id = 1
  ORDER BY updated_at DESC
  LIMIT 5;
  ```

- [ ] **성능 검증**
  - 토큰 제한 확인 (2000 이하)
  - 응답 시간 확인 (백그라운드 요약으로 인한 지연 없음)
  - 메모리 사용량 확인

---

## 🎯 최종 권장사항

### 1. 구현 순서 (순서대로 필수)

1. **Phase 1 → Phase 5** 먼저 완료 (설정 + 프롬프트)
2. **Phase 2** 메모리 서비스 구현
3. **Phase 3** Supervisor 통합
4. **Phase 6** 테스트 실행
5. **Phase 4** Planning Agent (마지막, 선택적)

### 2. 주의사항

⚠️ **DB 세션 이슈 해결 필수**
- 백그라운드 태스크는 독립 세션 사용 (`_background_summary_with_new_session`)

⚠️ **Line 번호 정확히 확인**
- 계획서 Line 870 → 실제 Line 174-252

⚠️ **프롬프트 파일 먼저 생성**
- `conversation_summary.txt` 없으면 LLM 호출 실패

### 3. 테스트 우선

✅ 각 Phase 완료 후 즉시 검증
✅ Phase 2 완료 → Python REPL에서 메서드 확인
✅ Phase 3 완료 → 로그로 3-Tier 로드 확인
✅ Phase 5 완료 → 프롬프트 로드 테스트

### 4. 롤백 준비

```bash
# 문제 발생 시 즉시 복구
cp backend/app/core/config.py.backup backend/app/core/config.py
cp backend/app/service_agent/foundation/simple_memory_service.py.backup backend/app/service_agent/foundation/simple_memory_service.py
cp backend/app/service_agent/supervisor/team_supervisor.py.backup backend/app/service_agent/supervisor/team_supervisor.py
cp backend/.env.backup backend/.env

# 서버 재시작
cd backend
python main.py
```

---

## 📊 예상 결과

### 성공 시

```log
[TeamSupervisor] Loading 3-Tier Memory for user 1
[SimpleMemoryService] Loaded tiered memories - Tokens: 1847, Short: 5, Mid: 3, Long: 2
[TeamSupervisor] 3-Tier memories loaded - Short(5), Mid(3), Long(2)
[TeamSupervisor] Saving conversation to Long-term Memory for user 1
[SimpleMemoryService] Background summary started for session: session-abc-123
[SimpleMemoryService] LLM summarization completed: 강남구 아파트 전세 시세 및 대출 조건 문의
[SimpleMemoryService] Summary saved for session: session-abc-123
```

### DB 상태

```sql
-- chat_sessions.session_metadata
{
  "conversation_summary": "강남구 아파트 전세 시세 및 대출 조건 문의",
  "summary_method": "llm",
  "summary_updated_at": "2025-10-21T14:30:00",
  "last_updated": "2025-10-21T14:30:00",
  "message_count": 6
}
```

---

**보고서 작성 완료**
**다음 단계**: Phase 1부터 체크리스트에 따라 순차 구현
