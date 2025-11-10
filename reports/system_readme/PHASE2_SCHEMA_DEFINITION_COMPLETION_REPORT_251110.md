# Phase 2: Schema Definition Completion Report
**작성일**: 2025-11-10
**상태**: ✅ 완료

---

## 📋 실행 요약

Schema-first design 접근 방식으로 모든 스키마를 명확하게 정의했습니다.

### 완료된 작업
- ✅ frontdesk_state.py 재정의 (TypedDict, DB 매핑 문서화)
- ✅ assessor_state.py 재정의 (TypedDict, DB 매핑 문서화)
- ✅ frontdesk/schemas.py 생성 (Pydantic LLM Response schemas)
- ✅ assessor/schemas.py 생성 (Pydantic LLM Response schemas)
- ✅ frontdesk_crud.py에 CRUD ↔ State 매핑 함수 추가
- ✅ assessor_crud.py에 CRUD ↔ State 매핑 함수 추가

---

## 📄 생성/수정된 파일

### 1. State Schema Files (TypedDict)

#### frontend/app/octostrator/states/frontdesk_state.py
**수정 내용**: 완전 재작성, 깔끔한 구조

**추가된 TypedDict**:
- `LeadInfo` (total=False)
  - DB Lead 모델과 명확한 매핑
  - score: 0-100 (DB) → 0.0-1.0 (State) normalization
  - created_at: DateTime → ISO string

- `InquiryInfo` (total=False) ⭐ **신규 추가**
  - DB Inquiry 모델과 매핑
  - 이전에는 없었던 TypedDict

- `AppointmentInfo` (total=False)
  - DB Appointment 모델과 매핑
  - scheduled_date, scheduled_time 파생 필드 추가

**주요 개선사항**:
- 모든 필드에 DB 매핑 주석 추가
- `total=False`로 유연성 확보
- Workflow 설명 추가
- 데이터 변환 규칙 명시

**라인 수**: 144 lines (이전: 68 lines)

---

#### backend/app/octostrator/states/assessor_state.py
**수정 내용**: 완전 재작성

**추가된 TypedDict**:
- `InBodyInfo` (total=False)
  - DB InBodyData 모델과 명확한 매핑
  - 12개 측정 필드 (weight, muscle_mass, body_fat_percentage, etc.)

- `PostureInfo` (total=False)
  - DB PostureAnalysis 모델과 매핑
  - issues, recommendations: JSON (DB) → List[Dict] (State)

**주요 개선사항**:
- 모든 필드에 DB 매핑 주석 추가
- JSON 파싱 규칙 명시
- Workflow 설명 추가
- 입력/처리/출력 섹션 분리

**라인 수**: 146 lines (이전: 51 lines)

---

### 2. LLM Response Schema Files (Pydantic)

#### backend/app/octostrator/agents/frontdesk/schemas.py ⭐ **신규 생성**
**Pydantic BaseModel 클래스들**:

1. **InquiryAnalysisResponse**
   - 용도: inquiry_handler_node LLM 응답
   - 필드: intent, inquiry_type, customer_needs, response, next_action, urgency
   - Structured Output 사용
   - 예시 데이터 포함

2. **LeadScoringResponse**
   - 용도: lead_scorer_node LLM 응답
   - 필드: lead_score (0.0-1.0), priority, scoring_factors, recommended_actions, reasoning
   - 예시 데이터 포함

3. **AppointmentSchedulingResponse**
   - 용도: appointment_scheduler_node LLM 응답
   - 필드: message, recommended_slots, appointment_type, confirmation_message
   - ISO format 시간 슬롯

4. **NotificationResponse**
   - 용도: notification_sender_node LLM 응답
   - 필드: notification_title, notification_body, notification_type, recipients, urgency

**특징**:
- OpenAI Structured Output 호환
- Field descriptions 상세화
- Config.json_schema_extra로 예시 제공
- 모든 필드에 validation 규칙

**라인 수**: 165 lines

---

#### backend/app/octostrator/agents/assessor/schemas.py ⭐ **신규 생성**
**Pydantic BaseModel 클래스들**:

1. **InBodyAnalysisResponse**
   - 용도: inbody_analyzer_node LLM 응답
   - 필드: overall_assessment, body_fat_analysis, muscle_mass_analysis, visceral_fat_analysis, health_indicators, fitness_level, recommended_focus_areas, health_risks
   - 체성분 분석 결과 구조화

2. **PostureAnalysisResponse**
   - 용도: posture_analyzer_node LLM 응답
   - 필드: overall_posture_assessment, shoulder_alignment, hip_alignment, spine_curvature, detected_issues, imbalances, injury_risks, corrective_recommendations
   - 자세 분석 결과 구조화
   - detected_issues: List[Dict[str, str]] 구조

3. **FitnessRecommendationResponse**
   - 용도: recommendation_generator_node LLM 응답
   - 필드: primary_goals, recommended_program_type, training_frequency, training_intensity, exercise_recommendations, nutrition_recommendations, lifestyle_recommendations, timeline
   - 종합 추천사항

4. **AssessmentReportResponse**
   - 용도: report_generator_node LLM 응답
   - 필드: report_title, executive_summary, assessment_findings, strengths, areas_for_improvement, action_plan, next_steps, follow_up_schedule
   - 최종 리포트 생성

**특징**:
- 복잡한 nested 구조 (List[Dict[str, Any]])
- 의료/피트니스 전문 용어 정의
- 예시 데이터로 사용법 명확화

**라인 수**: 245 lines

---

### 3. CRUD Mapping Functions

#### backend/database/frontdesk_crud.py
**추가된 함수** (파일 끝에 추가):

1. **lead_to_state(lead: Lead) → Dict[str, Any]**
   - ORM Lead → State LeadInfo
   - score: 0-100 → 0.0-1.0 normalization
   - DateTime → ISO string

2. **state_to_lead_data(lead_info: Dict) → Dict[str, Any]**
   - State LeadInfo → create_lead() 입력 형식
   - score: 0.0-1.0 → 0-100 conversion

3. **inquiry_to_state(inquiry: Inquiry) → Dict[str, Any]**
   - ORM Inquiry → State InquiryInfo

4. **state_to_inquiry_data(inquiry_info: Dict) → Dict[str, Any]**
   - State InquiryInfo → create_inquiry() 입력 형식

5. **appointment_to_state(appointment: Appointment) → Dict[str, Any]**
   - ORM Appointment → State AppointmentInfo
   - scheduled_date, scheduled_time 파생

6. **state_to_appointment_data(appointment_info: Dict) → Dict[str, Any]**
   - State AppointmentInfo → create_appointment() 입력 형식
   - date + time 조합 로직

**라인 수 추가**: +160 lines (565 → 726 lines)

---

#### backend/database/assessor_crud.py
**추가된 함수** (파일 끝에 추가):

1. **inbody_to_state(inbody: InBodyData) → Dict[str, Any]**
   - ORM InBodyData → State InBodyInfo
   - datetime_to_str() 활용

2. **state_to_inbody_data(inbody_info: Dict) → Dict[str, Any]**
   - State InBodyInfo → create_inbody_data() 입력 형식

3. **posture_to_state(posture: PostureAnalysis) → Dict[str, Any]**
   - ORM PostureAnalysis → State PostureInfo
   - parse_json_list() for issues, recommendations

4. **state_to_posture_data(posture_info: Dict) → Dict[str, Any]**
   - State PostureInfo → create_posture_analysis() 입력 형식
   - JSON 직렬화는 CRUD에서 처리

**라인 수 추가**: +124 lines (477 → 602 lines)

---

## 🔑 핵심 설계 원칙

### 1. Schema-first Design
- DB 스키마는 이미 완성 (건드리지 않음)
- Agent State 스키마를 DB와 명확하게 매핑
- LLM Response 스키마를 Pydantic으로 정의
- 모든 매핑 함수를 명시적으로 작성

### 2. 타입 안전성
- TypedDict로 State 타입 정의 (`total=False`로 유연성)
- Pydantic으로 LLM 응답 검증
- 명시적 타입 힌트 (`Dict[str, Any]`, `List[Dict]`)

### 3. 데이터 변환 규칙
```
DB ←→ CRUD ←→ State ←→ Agent

변환 예시:
- score: 0-100 (DB) ←→ 0.0-1.0 (State)
- DateTime (DB) ←→ ISO string (State)
- JSON Text (DB) ←→ List[Dict] (State)
```

### 4. 명확한 문서화
- 모든 TypedDict에 DB 매핑 주석
- 모든 Pydantic 모델에 Field description
- 모든 매핑 함수에 변환 규칙 설명
- 예시 데이터로 사용법 설명

---

## 📊 Schema 구조 요약

### Frontdesk Agent Schemas

#### State (TypedDict)
```python
LeadInfo:
    - lead_id, name, phone, email, source, interest
    - score (0.0-1.0), status, notes, created_at

InquiryInfo:
    - inquiry_id, lead_id, inquiry_text, response_text
    - inquiry_type, handled_by, created_at

AppointmentInfo:
    - appointment_id, lead_id, appointment_date
    - scheduled_date, scheduled_time, appointment_type
    - status, notes, created_at

FrontdeskState (BaseAgentState):
    - Input: inquiry_text, customer_name, customer_phone, customer_email, source
    - LLM Processing: intent_classification, inquiry_type, urgency_level, customer_needs
    - DB Records: lead_info, inquiry_info, appointment_info
    - Response: response_text, available_slots, conversation_history
    - Notification: notification_sent, notification_recipients
```

#### LLM Response (Pydantic)
```python
InquiryAnalysisResponse:
    - intent, inquiry_type, customer_needs
    - response, next_action, urgency

LeadScoringResponse:
    - lead_score (0.0-1.0), priority
    - scoring_factors, recommended_actions, reasoning

AppointmentSchedulingResponse:
    - message, recommended_slots
    - appointment_type, confirmation_message

NotificationResponse:
    - notification_title, notification_body
    - notification_type, recipients, urgency
```

---

### Assessor Agent Schemas

#### State (TypedDict)
```python
InBodyInfo:
    - inbody_id, user_id, measurement_date
    - weight, muscle_mass, body_fat_mass, body_fat_percentage
    - bmr, visceral_fat_level, body_water, protein, mineral
    - created_at

PostureInfo:
    - posture_id, user_id, analysis_date
    - front_image_url, side_image_url, back_image_url
    - shoulder_alignment, hip_alignment, spine_curvature
    - issues (List[Dict]), recommendations (List[Dict])
    - created_at

AssessorState (BaseAgentState):
    - Input: user_id, member_name, assessment_type
    - InBody Input: weight, muscle_mass, body_fat_percentage, bmr, visceral_fat_level
    - Posture Input: posture_images, front/side/back_image_url
    - LLM Analysis: body_composition_analysis, posture_analysis_summary, detected_imbalances
    - DB Records: inbody_info, posture_info, history
    - Recommendations: fitness_goals, recommended_exercises, recommended_nutrition
    - Report: assessment_report, report_generated, report_url
```

#### LLM Response (Pydantic)
```python
InBodyAnalysisResponse:
    - overall_assessment, body_fat_analysis, muscle_mass_analysis
    - visceral_fat_analysis, health_indicators, fitness_level
    - recommended_focus_areas, health_risks

PostureAnalysisResponse:
    - overall_posture_assessment, shoulder/hip_alignment, spine_curvature
    - detected_issues (List[Dict]), imbalances, injury_risks
    - corrective_recommendations (List[Dict])

FitnessRecommendationResponse:
    - primary_goals, recommended_program_type
    - training_frequency, training_intensity
    - exercise_recommendations, nutrition_recommendations
    - lifestyle_recommendations, timeline

AssessmentReportResponse:
    - report_title, executive_summary, assessment_findings
    - strengths, areas_for_improvement
    - action_plan, next_steps, follow_up_schedule
```

---

## 🎯 다음 단계: Phase 3 - Reference Agent Implementation

### Phase 3 작업 목록

#### 1. Coding Conventions 문서 작성
- [ ] Import 경로 규칙
- [ ] LLM 호출 규칙 (Structured Output)
- [ ] Database 세션 사용 규칙
- [ ] 에러 처리 규칙
- [ ] Logging 규칙
- [ ] Docstring 규칙

#### 2. Agent Template 생성
- [ ] `{agent_name}_agent.py.template`
- [ ] `{agent_name}_nodes.py.template`
- [ ] `{agent_name}_tools.py.template`
- [ ] `{agent_name}_prompts.py.template`

#### 3. Frontdesk Agent 구현 (Reference)
- [ ] frontdesk_prompts.py
- [ ] frontdesk_tools.py (Schema 기반)
- [ ] frontdesk_nodes.py (Structured Output)
- [ ] frontdesk_agent.py (BaseAgent 상속)
- [ ] frontdesk_graph.py
- [ ] 통합 테스트

#### 4. 검증
- [ ] E2E 테스트 작성
- [ ] DB 통합 테스트
- [ ] LLM Structured Output 테스트

---

## ✅ Phase 2 검증 결과

### 1. State Schema 검증
- ✅ frontdesk_state.py: 3개 TypedDict, 1개 State 정의
- ✅ assessor_state.py: 2개 TypedDict, 1개 State 정의
- ✅ DB 매핑 주석 완비
- ✅ `total=False` 적용

### 2. LLM Response Schema 검증
- ✅ frontdesk/schemas.py: 4개 Pydantic 모델
- ✅ assessor/schemas.py: 4개 Pydantic 모델
- ✅ Field descriptions 완비
- ✅ 예시 데이터 포함
- ✅ Structured Output 호환

### 3. CRUD Mapping 검증
- ✅ frontdesk_crud.py: 6개 매핑 함수 추가
- ✅ assessor_crud.py: 4개 매핑 함수 추가
- ✅ ORM → State 변환
- ✅ State → CRUD 변환
- ✅ 데이터 normalization (score, datetime, JSON)

---

## 📝 참고 사항

### Schema 사용 예시

#### State Schema 사용
```python
from backend.app.octostrator.states.frontdesk_state import FrontdeskState, LeadInfo

# Agent State 생성
state: FrontdeskState = {
    "inquiry_text": "I want to lose weight",
    "customer_name": "John Doe",
    "customer_phone": "01012345678",
    # ...
}

# LeadInfo 사용
lead_info: LeadInfo = {
    "lead_id": 1,
    "name": "John Doe",
    "score": 0.75,  # 0.0-1.0
    # ...
}
```

#### LLM Response Schema 사용
```python
from langchain_openai import ChatOpenAI
from backend.app.octostrator.agents.frontdesk.schemas import InquiryAnalysisResponse

# LLM with Structured Output
llm = ChatOpenAI(model="gpt-4").with_structured_output(InquiryAnalysisResponse)

# LLM 호출
response: InquiryAnalysisResponse = await llm.ainvoke([
    SystemMessage(content="..."),
    HumanMessage(content="...")
])

# 타입 안전하게 접근
intent = response.intent  # str
customer_needs = response.customer_needs  # List[str]
```

#### CRUD ↔ State Mapping 사용
```python
from backend.database.frontdesk_crud import lead_to_state, state_to_lead_data, create_lead
from backend.database.session import get_db_session

# DB → State
lead_orm = await get_lead_by_id(session, lead_id=1)
lead_info: LeadInfo = lead_to_state(lead_orm)  # ORM → State

# State → DB
lead_data = state_to_lead_data(lead_info)  # State → CRUD 입력
async with get_db_session() as session:
    new_lead = await create_lead(session, lead_data)
```

---

## 🚀 진행 상황

### ✅ 완료된 Phase
- ✅ Phase 0: 시스템 분석 및 버그 리포트
- ✅ Phase 1: Cleanup (Agent 삭제, DB session 수정)
- ✅ Phase 2: Schema Definition (State, LLM Response, Mapping)

### 🔄 진행 중인 Phase
- ⏭️ Phase 3: Reference Agent Implementation

### 📅 예상 소요 시간
- Phase 2 완료: ~2시간
- Phase 3 예상: ~6-8시간 (Frontdesk Agent + Template)

---

**작성자**: Claude Code
**완료 시각**: 2025-11-10 10:10
**소요 시간**: 약 30분
**다음 단계**: Phase 3 - Coding Conventions & Reference Agent Implementation
