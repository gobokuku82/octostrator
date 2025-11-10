# 버그 수정 체크리스트
**작성일**: 2025-11-10
**프로젝트**: AI PT Manager beta_v001

---

## 🔴 Critical Bugs (즉시 수정 필요)

### [ ] BUG-001: Missing Import (`uuid`)
**파일**: `backend/app/octostrator/agents/frontdesk/frontdesk_tools.py:178`
**수정 내용**:
```python
# 파일 상단에 추가
import uuid
```
**예상 시간**: 5분

---

### [ ] BUG-002: Incorrect Import Path
**파일**: `backend/app/octostrator/agents/frontdesk/frontdesk_tools.py:12-13`
**수정 내용**:
```python
# Before
from database import frontdesk_crud
from database.session import get_db

# After
from backend.database import frontdesk_crud
from backend.database.session import get_db
```
**예상 시간**: 5분

---

### [ ] BUG-003: Incorrect Async Context Manager Usage
**파일**: `backend/app/octostrator/agents/frontdesk/frontdesk_tools.py` (5곳)
- Line 28 (`create_lead_record`)
- Line 104 (`get_available_appointment_slots`)
- Line 135 (`create_appointment`)
- Line 221 (`update_lead_status`)
- Line 274 (`get_lead_history`)

**수정 내용** (권장 방법):
```python
# Before
async with await get_db() as session:
    ...

# After (방법 1 - 권장)
async with get_db_session() as session:
    ...

# After (방법 2)
session = await get_db()
try:
    ...
finally:
    await session.close()
```

**추가 수정**: `backend/database/session.py:39`
```python
# Before
async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# After
from typing import AsyncGenerator

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```
**예상 시간**: 20분

---

### [ ] BUG-004: Agent Registry Missing or Incomplete
**파일**: `backend/app/octostrator/agents/__init__.py`

**확인 사항**:
1. `agent_registry` 딕셔너리가 정의되어 있는가?
2. 모든 에이전트가 등록되어 있는가?

**예상 구조**:
```python
# backend/app/octostrator/agents/__init__.py
from .frontdesk.frontdesk_agent import FrontdeskAgent
from .assessor.assessor_agent import AssessorAgent
from .nutrition.nutrition_agent import NutritionAgent
from .program_designer.program_designer_agent import ProgramDesignerAgent
from .manager.manager_agent import ManagerAgent
from .marketing.marketing_agent import MarketingAgent
from .owner_assistant.owner_assistant_agent import OwnerAssistantAgent

agent_registry = {
    "frontdesk_agent": FrontdeskAgent,
    "assessor_agent": AssessorAgent,
    "nutrition_agent": NutritionAgent,
    "program_designer_agent": ProgramDesignerAgent,
    "manager_agent": ManagerAgent,
    "marketing_agent": MarketingAgent,
    "owner_assistant_agent": OwnerAssistantAgent,
}

__all__ = ["agent_registry"]
```
**예상 시간**: 20분

---

## 🟡 High Priority Issues (1-2일 내 수정)

### [ ] ISSUE-001: Assessor Agent Nodes Not Implemented
**파일**: `backend/app/octostrator/agents/assessor/assessor_nodes.py`

**구현 필요 노드**:
1. [ ] `inbody_analyzer_node`
   - DB에서 InBodyData 조회 (`assessor_crud.get_latest_inbody_data`)
   - LLM으로 체성분 분석
   - 분석 결과 State 업데이트

2. [ ] `posture_evaluator_node`
   - DB에서 PostureAnalysis 조회 (`assessor_crud.get_latest_posture_analysis`)
   - LLM으로 자세 평가
   - 불균형 및 교정 권장사항 생성

3. [ ] `goal_assessor_node`
   - 사용자 목표 및 동기 평가
   - 목표 설정 지원

4. [ ] `report_generator_node`
   - 종합 평가 보고서 생성
   - PDF 또는 HTML 형식

**예상 시간**: 4시간

---

### [ ] ISSUE-002: Cognitive Layer Nodes Not Implemented
**파일**: `backend/app/octostrator/supervisors/cognitive/cognitive_nodes.py`

**구현 필요 노드**:
1. [ ] `intent_understanding_node`
   - LLM으로 사용자 의도 분류
   - 카테고리: diet_query, workout_query, schedule_query, member_report, etc.
   - OpenAI Structured Output 사용 권장

2. [ ] `planning_node`
   - 동적 계획 수립 (Agent Registry 기반)
   - 의존성 그래프 생성
   - Todo 생성

3. [ ] `validator_node`
   - 계획 검증 (순환 참조, 리소스 체크)
   - Agent 가용성 확인

**예상 시간**: 6시간

---

### [ ] ISSUE-003: JSON Parsing Error Handling Weak
**파일**: `backend/app/octostrator/agents/frontdesk/frontdesk_nodes.py` (3곳)
- Line 74-84 (`inquiry_handler_node`)
- Line 144-153 (`lead_scorer_node`)
- Line 248-254 (`appointment_scheduler_node`)

**수정 방법 1: 로깅 강화**
```python
try:
    result = json.loads(response.content)
except json.JSONDecodeError:
    logger.warning(
        f"[FrontdeskAgent] Failed to parse LLM response as JSON. "
        f"Raw response: {response.content[:200]}"
    )
    result = {
        "intent": "general_question",
        "response": response.content,  # 원본 보존
        ...
    }
```

**수정 방법 2: OpenAI Structured Output (권장)**
```python
from pydantic import BaseModel
from typing import List

class InquiryResponse(BaseModel):
    intent: str
    customer_needs: List[str]
    response: str
    next_action: str
    urgency: str

llm = ChatOpenAI(
    model=system_config.openai_model,
    temperature=0.7
).with_structured_output(InquiryResponse)

response = await llm.ainvoke([SystemMessage(content=prompt)])
# response는 자동으로 InquiryResponse 객체
```
**예상 시간**: 2시간

---

## 🟢 Medium Priority Improvements (1주일 내)

### [ ] IMPROVE-001: Database Session Typing
**파일**: `backend/database/session.py:39`
**수정**: BUG-003에 포함됨
**예상 시간**: 포함됨

---

### [ ] IMPROVE-002: Hard-coded LLM Settings
**파일**:
- `backend/app/octostrator/agents/frontdesk/frontdesk_nodes.py` (4곳)
- `backend/app/octostrator/supervisors/cognitive/cognitive_nodes.py`
- 기타 노드 파일들

**수정 내용**: Context API 사용
```python
from langgraph.types import RuntimeValue

context = RuntimeValue.runtime.context
llm = ChatOpenAI(
    model=context.llm_settings.intent_model,
    temperature=context.llm_settings.intent_temperature,
    max_tokens=context.llm_settings.intent_max_tokens,
    api_key=system_config.openai_api_key
)
```
**예상 시간**: 4시간

---

### [ ] IMPROVE-003: Missing Logging in CRUD Operations
**파일**: `backend/database/frontdesk_crud.py`, `backend/database/assessor_crud.py`

**수정 내용**:
```python
try:
    # ... CRUD 작업
except SQLAlchemyError as e:
    logger.error(
        f"[FrontdeskCRUD] Failed to create lead: {e}",
        exc_info=True,  # 스택 트레이스 추가
        extra={"lead_data": lead_data}  # 컨텍스트 추가
    )
```
**예상 시간**: 3시간

---

### [ ] IMPROVE-004: TODO Comments Accumulation
**파일**: 전체 프로젝트

**작업**:
1. [ ] 모든 TODO 주석 수집
2. [ ] GitHub Issues로 이동
3. [ ] 우선순위 라벨 추가
4. [ ] TODO 주석 제거 또는 이슈 번호로 대체

**예상 시간**: 2시간

---

## 📊 진행 상황 요약

### Critical Bugs
- [ ] 0 / 4 완료

### High Priority Issues
- [ ] 0 / 3 완료

### Medium Priority Improvements
- [ ] 0 / 4 완료

### 전체 진행률
**0% 완료** (0 / 11)

---

## 🎯 다음 단계

### 1단계: Critical Bugs 수정 (목표: 1일)
1. BUG-001: uuid import 추가
2. BUG-002: import 경로 수정
3. BUG-003: async context manager 수정 (5곳)
4. BUG-004: agent_registry 확인 및 수정

**완료 조건**: 시스템이 오류 없이 실행됨

---

### 2단계: Core Features 구현 (목표: 2일)
1. ISSUE-001: Assessor Agent 노드 4개 구현
2. ISSUE-002: Cognitive Layer 노드 3개 구현
3. ISSUE-003: JSON 파싱 개선

**완료 조건**: Frontdesk + Assessor 워크플로우가 정상 작동

---

### 3단계: 코드 품질 개선 (목표: 1-2일)
1. IMPROVE-002: Context API 통합
2. IMPROVE-003: 로깅 강화
3. IMPROVE-004: TODO 정리

**완료 조건**: 코드 리뷰 통과

---

## 📝 수정 이력

| 날짜 | 완료 항목 | 담당자 | 비고 |
|------|-----------|--------|------|
| 2025-11-10 | - | - | 체크리스트 작성 |
|  |  |  |  |

---

**작성자**: Claude Code
**최종 업데이트**: 2025-11-10
