# 🤖 Agent Implementation Plan

**작성일**: 2025-11-05
**버전**: 1.0
**목적**: 필요한 Agent 정의 및 구현 계획

---

## 📊 현재 Agent 상태

### ✅ 구현 완료 (BaseAgent 기반)
1. **TodoAgent** - TODO 관리 및 HITL (553 lines)
2. **DietAgentV2** - 식단 관리 (414 lines)

### ⚠️ 구현 필요 (Legacy → BaseAgent)
1. **WorkoutAgent** - 운동 관리 (80 lines, legacy)
2. **ScheduleAgent** - 일정 관리 (77 lines, legacy)
3. **MemberCareAgent** - 회원 관리 (98 lines, legacy)
4. **CoachingAgent** - 코칭 (82 lines, legacy)

### 🆕 신규 구현 필요
5. **AnalysisAgent** - 데이터 분석
6. **ReportAgent** - 리포트 생성
7. **NotificationAgent** - 알림 관리
8. **IntegrationAgent** - 외부 서비스 연동

---

## 🎯 필수 Agent 목록 (우선순위 순)

### Priority 1: Core Fitness (즉시 필요)

#### 1. WorkoutAgentV2
**목적**: 운동 계획 수립 및 추적
**주요 기능**:
- 개인별 운동 프로그램 생성
- 운동 강도 조절
- 진행도 추적
- 자세 피드백
- 1RM 계산 및 예측

**State 필드**:
```python
class WorkoutAgentState(BaseAgentState):
    workout_plan: WorkoutPlan
    exercises: List[Exercise]
    current_session: WorkoutSession
    progress_metrics: Dict[str, float]
    injury_prevention: List[str]
```

**예상 개발 시간**: 3일

---

#### 2. ScheduleAgentV2
**목적**: PT 세션 및 일정 관리
**주요 기능**:
- 세션 예약/변경/취소
- 충돌 감지
- 리마인더 발송
- 일정 최적화
- 트레이너-회원 매칭

**State 필드**:
```python
class ScheduleAgentState(BaseAgentState):
    sessions: List[Session]
    conflicts: List[Conflict]
    available_slots: List[TimeSlot]
    reminders: List[Reminder]
```

**예상 개발 시간**: 2일

---

### Priority 2: Member Management (1주 내)

#### 3. MemberCareAgentV2
**목적**: 회원 관리 및 케어
**주요 기능**:
- 회원 프로필 관리
- 출석 체크
- 목표 설정 및 추적
- 만족도 관리
- 이탈 방지

**State 필드**:
```python
class MemberCareAgentState(BaseAgentState):
    member_profile: MemberProfile
    attendance: List[Attendance]
    goals: List[Goal]
    satisfaction_score: float
    churn_risk: float
```

**예상 개발 시간**: 2일

---

#### 4. CoachingAgentV2
**목적**: 개인 맞춤 코칭
**주요 기능**:
- 동기부여 메시지
- 진행도 피드백
- 목표 조정 제안
- 행동 변화 유도
- 성과 칭찬

**State 필드**:
```python
class CoachingAgentState(BaseAgentState):
    coaching_style: str
    motivational_messages: List[str]
    progress_feedback: str
    behavioral_insights: Dict
```

**예상 개발 시간**: 2일

---

### Priority 3: Analytics & Reporting (2주 내)

#### 5. AnalysisAgent
**목적**: 데이터 분석 및 인사이트
**주요 기능**:
- 운동 패턴 분석
- 영양 패턴 분석
- 진행도 트렌드
- 예측 분석
- 이상 징후 감지

**State 필드**:
```python
class AnalysisAgentState(BaseAgentState):
    data_sources: List[str]
    metrics: Dict[str, float]
    trends: List[Trend]
    predictions: Dict[str, Any]
    anomalies: List[Anomaly]
```

**예상 개발 시간**: 3일

---

#### 6. ReportAgent
**목적**: 보고서 생성
**주요 기능**:
- 주간/월간 리포트
- 진행도 차트
- 목표 달성률
- 비교 분석
- PDF/Excel 출력

**State 필드**:
```python
class ReportAgentState(BaseAgentState):
    report_type: str
    period: DateRange
    data: Dict[str, Any]
    charts: List[Chart]
    export_format: str
```

**예상 개발 시간**: 2일

---

### Priority 4: Advanced Features (1개월 내)

#### 7. NotificationAgent
**목적**: 알림 및 커뮤니케이션
**주요 기능**:
- 푸시 알림
- 이메일 발송
- 카카오톡 연동
- 알림 스케줄링
- 개인화 메시지

**State 필드**:
```python
class NotificationAgentState(BaseAgentState):
    notifications: List[Notification]
    channels: List[str]
    schedule: NotificationSchedule
    templates: Dict[str, Template]
```

**예상 개발 시간**: 3일

---

#### 8. IntegrationAgent
**목적**: 외부 서비스 연동
**주요 기능**:
- 피트니스 앱 연동
- 웨어러블 데이터
- 음식 DB 연동
- 지도 서비스
- 결제 시스템

**State 필드**:
```python
class IntegrationAgentState(BaseAgentState):
    services: List[Service]
    credentials: Dict[str, Credential]
    sync_status: Dict[str, bool]
    data_mappings: Dict[str, Mapping]
```

**예상 개발 시간**: 4일

---

## 📋 구현 로드맵

### Week 1 (Core Fitness)
- [ ] Day 1-3: WorkoutAgentV2
- [ ] Day 4-5: ScheduleAgentV2

### Week 2 (Member Management)
- [ ] Day 1-2: MemberCareAgentV2
- [ ] Day 3-4: CoachingAgentV2
- [ ] Day 5: 통합 테스트

### Week 3 (Analytics)
- [ ] Day 1-3: AnalysisAgent
- [ ] Day 4-5: ReportAgent

### Week 4 (Advanced)
- [ ] Day 1-3: NotificationAgent
- [ ] Day 4-5: IntegrationAgent

---

## 🛠️ Agent 구현 템플릿

```python
"""
{Agent Name} Agent V2

{Agent 설명}
BaseAgent를 상속받은 LangGraph 기반 구현
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from backend.app.octostrator.agents.base.base_agent import BaseAgent
from backend.app.octostrator.agents.base.agent_registry import register_agent
from backend.app.octostrator.agents.base.capabilities import Capability
from backend.app.octostrator.states.{agent}_agent_state import {Agent}AgentState

@register_agent("{agent}_agent_v2")
class {Agent}AgentV2(BaseAgent):
    """{Agent} Management Agent

    주요 기능:
    1. {기능1}
    2. {기능2}
    3. {기능3}
    """

    def __init__(self):
        super().__init__(
            agent_id="{agent}_agent_v2",
            agent_name="{Agent} Agent V2",
            description="{설명}",
            enable_checkpoint=True,  # HITL 필요시 True
            metadata={"version": "2.0"}
        )

        self.capabilities = [
            Capability.{CAPABILITY1}.value,
            Capability.{CAPABILITY2}.value
        ]

    def build_graph(self, llm=None) -> StateGraph:
        """LangGraph workflow 구축"""
        workflow = StateGraph({Agent}AgentState)

        # 노드 추가
        workflow.add_node("analyze", self.analyze_node)
        workflow.add_node("process", self.process_node)
        workflow.add_node("validate", self.validate_node)

        # 엣지 연결
        workflow.add_edge(START, "analyze")
        workflow.add_edge("analyze", "process")
        workflow.add_edge("process", "validate")
        workflow.add_edge("validate", END)

        return workflow

    async def analyze_node(self, state):
        """분석 노드"""
        # 구현
        return {"analyzed": True}

    async def process_node(self, state):
        """처리 노드"""
        # 구현
        return {"processed": True}

    async def validate_node(self, state):
        """검증 노드"""
        # 구현
        return {"result": {...}}

    async def process_task(self, task, context):
        """BaseAgent 추상 메서드"""
        pass
```

---

## 🔍 Agent 간 협업 예시

### 1. 신규 회원 온보딩
```
CognitiveSupervisor (계획)
    └─> MemberCareAgent (프로필 생성)
    └─> AnalysisAgent (체형 분석)
    └─> DietAgent (초기 식단)
    └─> WorkoutAgent (초기 운동)
    └─> ScheduleAgent (첫 세션 예약)
    └─> NotificationAgent (환영 메시지)
```

### 2. 주간 리포트 생성
```
CognitiveSupervisor (계획)
    └─> AnalysisAgent (데이터 수집)
    └─> ReportAgent (리포트 생성)
    └─> CoachingAgent (피드백 작성)
    └─> NotificationAgent (발송)
```

### 3. 운동 프로그램 조정
```
CognitiveSupervisor (계획)
    └─> AnalysisAgent (진행도 분석)
    └─> WorkoutAgent (프로그램 수정)
    └─> CoachingAgent (설명 생성)
    └─> ScheduleAgent (일정 조정)
```

---

## 📈 성공 지표

### Agent별 KPI
1. **WorkoutAgent**: 운동 완료율, 부상 예방율
2. **DietAgent**: 영양 목표 달성률, 식단 준수율
3. **ScheduleAgent**: 예약 정확도, 충돌 해결률
4. **MemberCareAgent**: 회원 만족도, 이탈률
5. **CoachingAgent**: 동기부여 효과, 목표 달성률
6. **AnalysisAgent**: 예측 정확도, 인사이트 품질
7. **ReportAgent**: 리포트 완성도, 생성 속도
8. **NotificationAgent**: 전달률, 응답률
9. **IntegrationAgent**: 연동 성공률, 데이터 정확도

---

## 💡 개발 팁

1. **State First**: State 설계를 먼저 완성
2. **Simple Start**: 최소 기능부터 구현
3. **Test Early**: 각 노드별 단위 테스트
4. **Capability Focus**: 명확한 능력 정의
5. **Checkpoint Strategy**: 필요한 경우만 활성화

---

## ⚠️ 주의사항

1. **의존성 관리**: Agent 간 순환 의존 방지
2. **성능 고려**: Checkpoint는 성능 영향
3. **에러 처리**: 각 노드에 try-catch
4. **로깅 필수**: 디버깅을 위한 상세 로그
5. **문서화**: State와 노드 설명 필수

---

## 🚀 다음 단계

1. **즉시**: WorkoutAgentV2 State 설계
2. **이번 주**: Priority 1 Agent 구현
3. **다음 주**: Priority 2 Agent 구현
4. **이번 달**: 전체 Agent 완성
5. **다음 달**: 최적화 및 고도화

---

**작성일**: 2025-11-05
**다음 리뷰**: 2025-11-12