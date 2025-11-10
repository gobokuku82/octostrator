# 재설계 순서 명확화
**작성일**: 2025-11-10
**질문**: DB schema를 정의하고 에이전트를 재구성하는 순서가 맞는가?

---

## 🎯 핵심 질문: "DB schema"의 의미

### Schema 종류 구분

#### 1. Database Schema (ORM 모델) ✅ 이미 완성
**위치**: `backend/app/models/`

```python
# backend/app/models/frontdesk.py
class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    phone = Column(String(20))
    email = Column(String(255))
    score = Column(Integer)  # 0-100
    status = Column(String(20))
    # ... (총 23개 테이블)
```

**상태**: ✅ 완성됨 (11개 파일, 23개 테이블)
**작업 필요**: ❌ 없음 (그대로 사용)

---

#### 2. Agent State Schema (TypedDict) ⚠️ 재정리 필요
**위치**: `backend/app/octostrator/states/`

```python
# backend/app/octostrator/states/frontdesk_state.py
class LeadInfo(TypedDict):
    """Agent가 사용하는 리드 정보 (메모리 상)"""
    lead_id: int
    name: Optional[str]
    phone: Optional[str]
    inquiry_type: Optional[str]
    lead_score: Optional[float]  # 0.0-1.0
    # ...

class FrontdeskState(BaseAgentState):
    """Frontdesk Agent의 상태"""
    lead_info: Optional[LeadInfo]
    inquiry_text: Optional[str]
    response_text: Optional[str]
    # ...
```

**상태**: ⚠️ 존재하지만 재정리 필요
**작업 필요**: ✅ 깔끔하게 재정의

---

#### 3. API Schema (Pydantic Models) ❓ 정의 필요 여부
**위치**: `backend/app/schemas/` (비어있을 수 있음)

```python
# backend/app/schemas/frontdesk.py (존재 여부 확인 필요)
from pydantic import BaseModel, Field

class LeadCreateRequest(BaseModel):
    """API 요청 스키마"""
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r"^\d{10,11}$")
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    inquiry_content: str
    source: str = "web"

class LeadResponse(BaseModel):
    """API 응답 스키마"""
    lead_id: int
    name: str
    score: float  # 0.0-1.0
    status: str
    created_at: str
```

**상태**: ❓ 확인 필요
**작업 필요**: ✅ 필요하다면 정의

---

## 📋 올바른 재설계 순서

### 옵션 A: Schema 우선 설계 (권장) ⭐

#### Step 1: 에이전트 삭제
```bash
# Agent 구현 파일 삭제
rm -rf backend/app/octostrator/agents/frontdesk/*.py
rm -rf backend/app/octostrator/agents/assessor/*.py
# ...
```

#### Step 2: 데이터 스키마 정의 (중요!)
각 에이전트가 **무엇을 다룰지** 먼저 정의

**2-1. State Schema 재정의**
```python
# backend/app/octostrator/states/frontdesk_state.py (깔끔하게 재작성)

from typing import TypedDict, Optional, List, Dict, Any
from backend.app.octostrator.states.base import BaseAgentState

# ===== 하위 타입 정의 =====

class LeadInfo(TypedDict, total=False):
    """리드 정보 (DB Lead 모델과 매핑)"""
    lead_id: int                    # DB: leads.id
    name: str                       # DB: leads.name
    phone: str                      # DB: leads.phone
    email: str                      # DB: leads.email
    source: str                     # DB: leads.source
    interest: str                   # DB: leads.interest
    score: float                    # DB: leads.score (0-100) → 0.0-1.0 변환
    status: str                     # DB: leads.status
    notes: Optional[str]            # DB: leads.notes
    created_at: str                 # DB: leads.created_at (ISO format)

class InquiryInfo(TypedDict, total=False):
    """문의 정보 (DB Inquiry 모델과 매핑)"""
    inquiry_id: int                 # DB: inquiries.id
    lead_id: int                    # DB: inquiries.lead_id (FK)
    inquiry_text: str               # DB: inquiries.inquiry_text
    response_text: Optional[str]    # DB: inquiries.response_text
    inquiry_type: str               # DB: inquiries.inquiry_type
    handled_by: str                 # DB: inquiries.handled_by
    created_at: str                 # DB: inquiries.created_at

class AppointmentInfo(TypedDict, total=False):
    """예약 정보 (DB Appointment 모델과 매핑)"""
    appointment_id: int             # DB: appointments.id
    lead_id: int                    # DB: appointments.lead_id (FK)
    appointment_date: str           # DB: appointments.appointment_date (ISO)
    scheduled_date: str             # 날짜만 (YYYY-MM-DD)
    scheduled_time: str             # 시간만 (HH:MM)
    appointment_type: str           # DB: appointments.appointment_type
    status: str                     # DB: appointments.status
    notes: Optional[str]            # DB: appointments.notes

# ===== 메인 State 정의 =====

class FrontdeskState(BaseAgentState):
    """
    Frontdesk Agent State

    Workflow:
    1. inquiry_handler → inquiry_text 분석
    2. lead_scorer → lead_info 생성 (DB 저장)
    3. appointment_scheduler → appointment_info 생성 (DB 저장)
    4. notification_sender → 알림 전송
    """

    # Input
    inquiry_text: Optional[str]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    customer_email: Optional[str]
    source: Optional[str]  # "web", "phone", "sns"

    # Processing
    intent_classification: Optional[str]  # LLM 분류 결과
    urgency_level: Optional[str]  # "high", "medium", "low"
    customer_needs: Optional[List[str]]  # LLM 추출 needs

    # Output (DB 저장된 데이터)
    lead_info: Optional[LeadInfo]
    inquiry_info: Optional[InquiryInfo]
    appointment_info: Optional[AppointmentInfo]

    # 응답
    response_text: Optional[str]
    available_slots: Optional[List[Dict[str, str]]]
    notification_sent: Optional[bool]

    # 메타
    conversation_history: Optional[List[Dict[str, str]]]
```

**2-2. LLM Response Schema 정의 (Pydantic)**
```python
# backend/app/octostrator/agents/frontdesk/schemas.py (새로 생성)

from pydantic import BaseModel, Field
from typing import List, Optional

class InquiryAnalysisResponse(BaseModel):
    """Inquiry Handler LLM 응답 스키마"""
    intent: str = Field(..., description="Customer intent category")
    customer_needs: List[str] = Field(
        default_factory=list,
        description="Extracted customer needs"
    )
    response: str = Field(..., description="Response to customer")
    next_action: str = Field(
        ...,
        description="Recommended action: schedule_appointment, send_info, follow_up"
    )
    urgency: str = Field(
        ...,
        description="Urgency level: high, medium, low"
    )

class LeadScoringResponse(BaseModel):
    """Lead Scorer LLM 응답 스키마"""
    lead_score: float = Field(..., ge=0.0, le=1.0, description="Score 0.0-1.0")
    priority: str = Field(..., description="Priority: high, medium, low")
    scoring_factors: dict = Field(
        default_factory=dict,
        description="Scoring breakdown"
    )
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Recommended follow-up actions"
    )
    reasoning: str = Field(..., description="Scoring reasoning")

class AppointmentSchedulingResponse(BaseModel):
    """Appointment Scheduler LLM 응답 스키마"""
    message: str = Field(..., description="Scheduling message to customer")
    recommended_slots: List[str] = Field(
        default_factory=list,
        description="Recommended time slots"
    )
    confirmation_message: str = Field(
        ...,
        description="Confirmation message template"
    )
```

#### Step 3: CRUD ↔ State 매핑 함수 정의
```python
# backend/database/frontdesk_crud.py 에 추가

def lead_to_state(lead: Lead) -> LeadInfo:
    """ORM Lead → State LeadInfo 변환"""
    return LeadInfo(
        lead_id=lead.id,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        source=lead.source,
        interest=lead.interest,
        score=lead.score / 100.0,  # 0-100 → 0.0-1.0
        status=lead.status,
        notes=lead.notes,
        created_at=lead.created_at.isoformat() if lead.created_at else None
    )

def state_to_lead_data(lead_info: Dict[str, Any]) -> Dict[str, Any]:
    """State LeadInfo → CRUD create_lead 입력 변환"""
    return {
        "name": lead_info.get("name"),
        "phone": lead_info.get("phone"),
        "email": lead_info.get("email"),
        "source": lead_info.get("source", "web"),
        "interest": lead_info.get("interest"),
        "lead_score": lead_info.get("score", 0.5),  # 0.0-1.0 (CRUD가 0-100 변환)
        "status": lead_info.get("status", "new"),
        "notes": lead_info.get("notes")
    }
```

#### Step 4: 에이전트 구현 (Schema 기반)
이제 State와 LLM Response Schema가 명확하므로, 노드 구현이 쉬워짐

```python
# backend/app/octostrator/agents/frontdesk/frontdesk_nodes.py

from langchain_openai import ChatOpenAI
from .schemas import InquiryAnalysisResponse

async def inquiry_handler_node(state: FrontdeskState) -> Dict[str, Any]:
    """문의 분석 노드 (Schema 기반)"""

    # LLM with Structured Output
    llm = ChatOpenAI(...).with_structured_output(InquiryAnalysisResponse)

    response: InquiryAnalysisResponse = await llm.ainvoke([...])

    # State 업데이트 (타입 안전)
    return {
        "intent_classification": response.intent,
        "customer_needs": response.customer_needs,
        "response_text": response.response,
        "urgency_level": response.urgency,
        # ... Annotated Reducers 자동 적용
    }
```

---

### 옵션 B: 기존 순서 (Schema 없이)

#### Step 1: 에이전트 삭제
#### Step 2: 에이전트 구현 시작
#### Step 3: 구현 중 Schema가 필요할 때마다 정의 ❌

**문제점**:
- Schema가 중구난방으로 정의됨
- 타입 불일치 발생
- 나중에 리팩토링 필요

---

## ✅ 권장 순서 (옵션 A)

### Phase 1: 정리 및 삭제
1. **백업 생성**
2. **Agent 파일 삭제**
3. **Cognitive/Todo 삭제**

### Phase 2: Schema 정의 (중요!) ⭐
1. **각 Agent State 재정의**
   - `frontdesk_state.py` 깔끔하게 재작성
   - `assessor_state.py` 깔끔하게 재작성
   - 나머지 State 파일들

2. **LLM Response Schema 정의 (Pydantic)**
   - `agents/frontdesk/schemas.py` 생성
   - `agents/assessor/schemas.py` 생성
   - Structured Output용

3. **CRUD ↔ State 매핑 함수 추가**
   - `database/frontdesk_crud.py`에 `lead_to_state()` 추가
   - `database/assessor_crud.py`에 `inbody_to_state()` 추가

### Phase 3: Reference Agent 구현
1. Template 생성
2. Frontdesk Agent 구현 (Schema 기반)
3. 테스트

### Phase 4: 나머지 Agent 복제
1. Assessor Agent
2. Nutrition Agent
3. ... (5개 더)

---

## 📊 Schema 우선 설계의 장점

### ✅ 장점
1. **타입 안전성**: TypedDict, Pydantic으로 타입 보장
2. **명확성**: 각 Agent가 무엇을 다루는지 명확
3. **일관성**: DB ↔ State ↔ LLM Response 매핑이 체계적
4. **유지보수**: Schema 변경 시 영향 범위 명확
5. **자동완성**: IDE에서 필드 자동완성
6. **검증**: Pydantic이 자동 검증

### ❌ Schema 없이 구현 시 문제
1. 타입 불일치 (str vs int, 0-1 vs 0-100)
2. 필드명 오타 (`lead_score` vs `leadScore`)
3. 누락된 필드
4. 중복 정의
5. 리팩토링 어려움

---

## 🎯 결론

### 질문: "DB schema를 정의하고 에이전트를 재구성하면 되는가?"

**답변**: ✅ **네, 맞습니다!** 하지만 "DB schema"를 명확히 해야 합니다.

### 올바른 이해
1. **Database Schema (ORM)**: ✅ 이미 완성 (건드리지 않음)
2. **Agent State Schema**: ⚠️ 재정의 필요 (깔끔하게)
3. **LLM Response Schema**: ✅ 새로 정의 (Pydantic)
4. **CRUD ↔ State 매핑**: ✅ 명확히 정의

### 권장 순서
```
1. 에이전트 삭제
2. State Schema 재정의 ⭐ (중요!)
3. LLM Response Schema 정의 ⭐ (중요!)
4. CRUD ↔ State 매핑 함수 ⭐ (중요!)
5. 에이전트 구현 (Schema 기반으로 쉬워짐)
```

---

## 📝 다음 질문

**사용자께 확인이 필요합니다**:

1. **"DB schema"는 어떤 의미였나요?**
   - A) Database ORM 모델 (이미 완성)
   - B) Agent State 스키마 (재정의 필요)
   - C) 둘 다

2. **Schema 우선 설계로 진행하시겠습니까?**
   - ✅ Yes → State Schema 재정의부터 시작
   - ❌ No → 바로 Agent 구현 시작

3. **어떤 방식으로 진행하시겠습니까?**
   - 옵션 1: 제가 Schema 재정의부터 시작
   - 옵션 2: 가이드만 제공, 직접 진행

---

**작성자**: Claude Code
**최종 업데이트**: 2025-11-10
**중요**: Schema 우선 설계 강력 권장!
