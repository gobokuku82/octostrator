# AI PT Manager 에이전트 재구조화 계획서

**작성일**: 2025-11-06
**대상 시스템**: AI PT Manager - Octostrator Agents v2.0
**작업 범위**: 기존 에이전트 구조를 비즈니스 중심 에이전트로 재편

---

## 📋 Executive Summary

### 현재 상황
시스템의 에이전트가 **기능 중심 구조**에서 **비즈니스 역할 중심 구조**로 재편됩니다.

**기존 구조** (기능 중심):
```
backend/app/octostrator/agents/
├── diet/             # 식단 관리
├── workout/          # 운동 관리
├── schedule/         # 일정 관리
├── member_care/      # 회원 케어
├── coaching/         # 코칭
└── base/            # 기본 프레임워크
```

**새로운 구조** (비즈니스 역할 중심):
```
backend/app/octostrator/agents/
├── frontdesk/                # AI 프로틱데스크 - 신규 회원 응대 및 리드 관리
├── assessor/                 # AI 어시션 - 회원 평가 및 자세 분석
├── program_designer/         # AI 프로그램 디자이너 - 맞춤형 프로그램 설계
├── manager/                  # AI 매니저 - 회원 관리 및 이탈 방지
├── marketing/                # AI 마케팅/콘텐츠 - 신규 고객 유치
├── owner_assistant/          # AI 오너 어시스턴트 - 비즈니스 데이터 분석
├── trainer_education/        # AI 트레이너 교육 - 내부 교육 및 역량 강화
└── base/                    # 기본 프레임워크 (유지)
```

### 핵심 변경사항
✅ **기능 중심** → **비즈니스 역할 중심** 재편
✅ **5개 에이전트** → **7개 에이전트** 확장
✅ **PT 센터 실무 워크플로우** 반영
✅ **각 에이전트별 State 독립 관리**

### 목표
1. **비즈니스 가치 중심 에이전트 설계**
2. **PT 센터 운영 전 과정 커버**
3. **확장 가능하고 유지보수 쉬운 구조**
4. **각 역할별 명확한 책임 분리**

---

## 🎯 신규 에이전트 정의

### 1. AI 프로틱데스크 (AI Frontdesk)

**에이전트 명칭**: Frontdesk Agent
**핵심 역할**: 24/7 신규 회원 응대 및 리드 관리
**주요 대상**: 트레이너, 원장
**해결하는 Pain Point**: "수업/영업 외 시간에 상담 문의가 와도 고객을 놓치고 싶지 않다."

**주요 기능**:
- 신규 문의 자동 응대 (챗봇/메시징)
- 리드 정보 수집 및 관리
- 초기 상담 일정 예약
- 리드 스코어링 및 우선순위화
- 트레이너/원장에게 알림 전달

**폴더 구조**:
```
agents/frontdesk/
├── __init__.py
├── frontdesk_agent.py       # 메인 에이전트 클래스
├── frontdesk_nodes.py       # 워크플로우 노드들
├── frontdesk_graph.py       # LangGraph 워크플로우
├── frontdesk_prompts.py     # LLM 프롬프트 템플릿
└── frontdesk_tools.py       # 도구 함수들
```

**State**: `states/frontdesk_state.py`

---

### 2. AI 어시션 (AI Assessor)

**에이전트 명칭**: Assessor Agent
**핵심 역할**: 회원 초기 평가 및 자세 분석 전문
**주요 대상**: 트레이너
**해결하는 Pain Point**: "회원 체형과 자세를 '감'이 아닌 '데이터'로 정확하게 분석하고 싶다."

**주요 기능**:
- 신규 회원 InBody 데이터 분석
- 자세 평가 및 불균형 분석
- 부상 이력 및 제한사항 파악
- 회원 목표 및 동기 평가
- 종합 평가 보고서 생성

**폴더 구조**:
```
agents/assessor/
├── __init__.py
├── assessor_agent.py
├── assessor_nodes.py
├── assessor_graph.py
├── assessor_prompts.py
└── assessor_tools.py
```

**State**: `states/assessor_state.py`

---

### 3. AI 프로그램 디자이너 (AI Program Designer)

**에이전트 명칭**: Program Designer Agent
**핵심 역할**: 맞춤형 운동 및 식단 프로그램 설계
**주요 대상**: 트레이너
**해결하는 Pain Point**: "회원마다 다른 목표와 특이사항을 반영해 프로그램을 짜는 시간이 오래 걸린다."

**주요 기능**:
- 평가 결과 기반 운동 프로그램 설계
- 목표별 식단 계획 수립
- 운동 난이도 및 진행 단계 설정
- 프로그램 템플릿 관리 및 커스터마이징
- 회원별 프로그램 히스토리 관리

**폴더 구조**:
```
agents/program_designer/
├── __init__.py
├── program_designer_agent.py
├── program_designer_nodes.py
├── program_designer_graph.py
├── program_designer_prompts.py
└── program_designer_tools.py
```

**State**: `states/program_designer_state.py`

---

### 4. AI 매니저 (AI Manager)

**에이전트 명칭**: Manager Agent
**핵심 역할**: 기존 회원 관리 및 이탈 방지
**주요 대상**: 트레이너, 원장
**해결하는 Pain Point**: "회원 스케줄 관리, 재등록률 유지가 번거롭고 힘들다."

**주요 기능**:
- 회원 출석 및 진행도 모니터링
- 이탈 위험 회원 자동 감지
- 재등록 알림 및 리마인더
- 회원 만족도 조사 및 피드백 수집
- PT 세션 일정 관리

**폴더 구조**:
```
agents/manager/
├── __init__.py
├── manager_agent.py
├── manager_nodes.py
├── manager_graph.py
├── manager_prompts.py
└── manager_tools.py
```

**State**: `states/manager_state.py`

---

### 5. AI 마케팅/콘텐츠 (AI Marketing)

**에이전트 명칭**: Marketing Agent
**핵심 역할**: 신규 고객 유치 (블로그, SNS 홍보)
**주요 대상**: 원장, 트레이너
**해결하는 Pain Point**: "수업만으로도 바쁜데 언제 블로그 글 쓰고 인스타그램 관리까지 하나."

**주요 기능**:
- 블로그 콘텐츠 자동 생성
- SNS 포스팅 스케줄링
- 회원 성공 사례 스토리텔링
- 프로모션 및 이벤트 기획
- SEO 최적화된 콘텐츠 생성

**폴더 구조**:
```
agents/marketing/
├── __init__.py
├── marketing_agent.py
├── marketing_nodes.py
├── marketing_graph.py
├── marketing_prompts.py
└── marketing_tools.py
```

**State**: `states/marketing_state.py`

---

### 6. AI 오너 어시스턴트 (AI Owner Assistant)

**에이전트 명칭**: Owner Assistant Agent
**핵심 역할**: 비즈니스/매출 데이터 분석 및 경영 보조
**주요 대상**: 원장 (대표)
**해결하는 Pain Point**: "매출, 트레이너별 성과, 프로그램 수익성을 한눈에 파악하고 싶다."

**주요 기능**:
- 매출 및 수익성 분석
- 트레이너별 성과 리포트
- 프로그램별 ROI 분석
- 경영 지표 대시보드
- 비즈니스 인사이트 및 제안

**폴더 구조**:
```
agents/owner_assistant/
├── __init__.py
├── owner_assistant_agent.py
├── owner_assistant_nodes.py
├── owner_assistant_graph.py
├── owner_assistant_prompts.py
└── owner_assistant_tools.py
```

**State**: `states/owner_assistant_state.py`

---

### 7. AI 트레이너 교육 (AI Trainer Education)

**에이전트 명칭**: Trainer Education Agent
**핵심 역할**: 내부 직원 온보딩 및 역량 강화
**주요 대상**: 원장, 트레이너
**해결하는 Pain Point**: "신입 트레이너 교육이 번거롭고, 최신 피트니스 지식을 계속 공부하고 싶다."

**주요 기능**:
- 신입 트레이너 온보딩 가이드
- 운동 기법 및 프로그램 설계 교육
- 최신 피트니스 트렌드 큐레이션
- 트레이너 역량 평가 및 피드백
- 내부 교육 자료 관리

**폴더 구조**:
```
agents/trainer_education/
├── __init__.py
├── trainer_education_agent.py
├── trainer_education_nodes.py
├── trainer_education_graph.py
├── trainer_education_prompts.py
└── trainer_education_tools.py
```

**State**: `states/trainer_education_state.py`

---

## 🏗️ 상세 파일 구조

### 전체 디렉토리 구조

```
backend/app/octostrator/
│
├── agents/                           # 에이전트 모듈
│   │
│   ├── base/                        # ✅ 기본 프레임워크 (유지)
│   │   ├── __init__.py
│   │   ├── base_agent.py           # BaseAgent 추상 클래스
│   │   ├── agent_registry.py       # 에이전트 레지스트리
│   │   ├── capabilities.py         # 공통 Capability
│   │   ├── checkpoint_strategy.py  # Checkpoint 전략
│   │   └── dependency_resolver.py  # 의존성 해결
│   │
│   ├── frontdesk/                  # 🆕 AI 프로틱데스크
│   │   ├── __init__.py
│   │   ├── frontdesk_agent.py
│   │   ├── frontdesk_nodes.py
│   │   ├── frontdesk_graph.py
│   │   ├── frontdesk_prompts.py
│   │   └── frontdesk_tools.py
│   │
│   ├── assessor/                   # 🆕 AI 어시션
│   │   ├── __init__.py
│   │   ├── assessor_agent.py
│   │   ├── assessor_nodes.py
│   │   ├── assessor_graph.py
│   │   ├── assessor_prompts.py
│   │   └── assessor_tools.py
│   │
│   ├── program_designer/           # 🆕 AI 프로그램 디자이너
│   │   ├── __init__.py
│   │   ├── program_designer_agent.py
│   │   ├── program_designer_nodes.py
│   │   ├── program_designer_graph.py
│   │   ├── program_designer_prompts.py
│   │   └── program_designer_tools.py
│   │
│   ├── manager/                    # 🆕 AI 매니저
│   │   ├── __init__.py
│   │   ├── manager_agent.py
│   │   ├── manager_nodes.py
│   │   ├── manager_graph.py
│   │   ├── manager_prompts.py
│   │   └── manager_tools.py
│   │
│   ├── marketing/                  # 🆕 AI 마케팅/콘텐츠
│   │   ├── __init__.py
│   │   ├── marketing_agent.py
│   │   ├── marketing_nodes.py
│   │   ├── marketing_graph.py
│   │   ├── marketing_prompts.py
│   │   └── marketing_tools.py
│   │
│   ├── owner_assistant/            # 🆕 AI 오너 어시스턴트
│   │   ├── __init__.py
│   │   ├── owner_assistant_agent.py
│   │   ├── owner_assistant_nodes.py
│   │   ├── owner_assistant_graph.py
│   │   ├── owner_assistant_prompts.py
│   │   └── owner_assistant_tools.py
│   │
│   └── trainer_education/          # 🆕 AI 트레이너 교육
│       ├── __init__.py
│       ├── trainer_education_agent.py
│       ├── trainer_education_nodes.py
│       ├── trainer_education_graph.py
│       ├── trainer_education_prompts.py
│       └── trainer_education_tools.py
│
└── states/                          # 상태 정의
    │
    ├── base.py                     # ✅ BaseState, BaseAgentState (수정 금지)
    ├── supervisors.py              # ✅ Supervisor States (수정 금지)
    ├── cognitive_state.py          # ✅ Cognitive Layer (수정 금지)
    ├── execute_state.py            # ✅ Execute Layer (수정 금지)
    ├── response_state.py           # ✅ Response Layer (수정 금지)
    ├── todo_state.py               # ✅ TODO Layer (수정 금지)
    │
    ├── frontdesk_state.py          # 🆕 Frontdesk Agent State
    ├── assessor_state.py           # 🆕 Assessor Agent State
    ├── program_designer_state.py   # 🆕 Program Designer Agent State
    ├── manager_state.py            # 🆕 Manager Agent State
    ├── marketing_state.py          # 🆕 Marketing Agent State
    ├── owner_assistant_state.py    # 🆕 Owner Assistant Agent State
    └── trainer_education_state.py  # 🆕 Trainer Education Agent State
```

---

## 📝 각 에이전트 파일 템플릿

### 1. {agent}_agent.py (메인 에이전트 클래스)

```python
"""
{Agent Name} Agent

{Agent Description}
"""

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from backend.app.octostrator.agents.base.base_agent import BaseAgent, AgentPriority
from backend.app.octostrator.states.{agent}_state import {Agent}State
from .{agent}_graph import build_{agent}_graph
import logging

logger = logging.getLogger(__name__)


class {Agent}Agent(BaseAgent):
    """{Agent Name} Agent

    핵심 역할: {Role}
    주요 대상: {Target}
    해결하는 Pain Point: {Pain Point}
    """

    def __init__(
        self,
        agent_id: str = "{agent}_agent",
        agent_name: str = "{Agent Name} Agent",
        description: str = "{Description}",
        enable_checkpoint: bool = True,
        priority: AgentPriority = AgentPriority.NORMAL,
        dependencies: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_name=agent_name,
            description=description,
            enable_checkpoint=enable_checkpoint,
            priority=priority,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )

    def build_graph(self, llm=None):
        """{Agent Name} Workflow Graph 구축"""
        if llm is None:
            from backend.app.config.system import config
            llm = ChatOpenAI(
                model=config.openai_model,
                api_key=config.openai_api_key,
                temperature=0.7
            )

        return build_{agent}_graph(llm=llm, state_class={Agent}State)

    async def process_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """{Agent Name} 작업 처리"""
        try:
            logger.info(f"[{Agent}Agent] Processing task: {task.get('task_type')}")

            # Graph 실행
            result = await self.execute(
                task=task,
                context=context,
                thread_id=context.get("session_id")
            )

            return result

        except Exception as e:
            logger.error(f"[{Agent}Agent] Task processing failed: {e}")
            raise
```

### 2. {agent}_nodes.py (워크플로우 노드)

```python
"""
{Agent Name} Agent Workflow Nodes
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def {node_name}_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """{Node Description}

    Args:
        state: Current state

    Returns:
        Updated state
    """
    try:
        logger.info(f"[{Agent}Agent] {Node Name} node executing")

        # TODO: Implement node logic

        return {
            "status": "completed",
            # Add other state updates
        }

    except Exception as e:
        logger.error(f"[{Agent}Agent] {Node Name} node failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


# Additional nodes...
```

### 3. {agent}_graph.py (LangGraph 워크플로우)

```python
"""
{Agent Name} Agent LangGraph Workflow
"""

from langgraph.graph import StateGraph, END, START
from typing import Dict, Any, Optional
from .{agent}_nodes import {node_1}_node, {node_2}_node
import logging

logger = logging.getLogger(__name__)


def build_{agent}_graph(
    llm=None,
    state_class=None
):
    """Build {Agent Name} workflow graph

    Args:
        llm: Language Model instance
        state_class: State schema class

    Returns:
        StateGraph workflow
    """
    if state_class is None:
        state_class = dict

    # Create graph
    graph = StateGraph(state_class)

    # Add nodes
    graph.add_node("{node_1}", {node_1}_node)
    graph.add_node("{node_2}", {node_2}_node)
    # Add more nodes...

    # Add edges
    graph.add_edge(START, "{node_1}")
    graph.add_edge("{node_1}", "{node_2}")
    # Add more edges...
    graph.add_edge("{last_node}", END)

    logger.info(f"[{Agent}Agent] Graph built successfully")

    return graph
```

### 4. {agent}_prompts.py (LLM 프롬프트)

```python
"""
{Agent Name} Agent Prompts
"""


def create_{prompt_name}_prompt(**kwargs) -> str:
    """{Prompt Description}

    Args:
        **kwargs: Prompt variables

    Returns:
        Formatted prompt string
    """
    return f"""
당신은 PT 센터의 {Agent Role}입니다.

{Specific instructions based on agent role}

입력 정보:
{Format input variables}

출력 형식:
{Specify output format}
    """.strip()


# Additional prompts...
```

### 5. {agent}_tools.py (도구 함수)

```python
"""
{Agent Name} Agent Tools
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


async def {tool_name}(params: Dict[str, Any]) -> Dict[str, Any]:
    """{Tool Description}

    Args:
        params: Tool parameters

    Returns:
        Tool execution result
    """
    try:
        logger.info(f"[{Agent}Agent] Executing {tool_name}")

        # TODO: Implement tool logic

        return {
            "status": "success",
            "result": {}
        }

    except Exception as e:
        logger.error(f"[{Agent}Agent] {tool_name} failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


# Additional tools...
```

### 6. {agent}_state.py (State 정의)

```python
"""
{Agent Name} Agent State
"""

from typing import TypedDict, Optional, List, Dict, Any
from backend.app.octostrator.states.base import BaseAgentState


class {Agent}State(BaseAgentState):
    """{Agent Name} Agent State Schema

    Extends BaseAgentState with agent-specific fields
    """

    # Agent-specific fields
    {field_1}: Optional[str]
    {field_2}: Optional[Dict[str, Any]]
    {field_3}: Optional[List[str]]

    # Add more fields as needed
```

---

## 🔄 마이그레이션 작업 순서

### Phase 1: 준비 및 Base 검증 (Week 1)

**목표**: 기존 구조 백업 및 Base 프레임워크 검증

#### Task 1.1: 기존 구조 백업
- [ ] 현재 agents 폴더 전체 백업
- [ ] 현재 states의 agent 관련 파일 백업
- [ ] Git branch 생성: `feature/agent-restructure`

**예상 시간**: 1시간

#### Task 1.2: Base 프레임워크 검증
- [ ] `base/base_agent.py` 검증 및 테스트
- [ ] `base/agent_registry.py` 검증
- [ ] `base/capabilities.py` 검증
- [ ] BaseAgentState 검증

**예상 시간**: 2-3시간

---

### Phase 2: 핵심 에이전트 구현 (Week 1-2)

**목표**: 비즈니스 핵심 3개 에이전트 구현

#### Task 2.1: Frontdesk Agent 구현 (P0 - 최우선)
- [ ] `frontdesk/frontdesk_agent.py` 작성
- [ ] `frontdesk/frontdesk_nodes.py` 작성
- [ ] `frontdesk/frontdesk_graph.py` 작성
- [ ] `frontdesk/frontdesk_prompts.py` 작성
- [ ] `frontdesk/frontdesk_tools.py` 작성
- [ ] `states/frontdesk_state.py` 작성
- [ ] 단위 테스트 작성

**주요 노드**:
1. `inquiry_handler_node` - 신규 문의 처리
2. `lead_scorer_node` - 리드 스코어링
3. `appointment_scheduler_node` - 상담 일정 예약
4. `notification_node` - 트레이너/원장 알림

**예상 시간**: 8-10시간

#### Task 2.2: Assessor Agent 구현 (P0)
- [ ] `assessor/assessor_agent.py` 작성
- [ ] `assessor/assessor_nodes.py` 작성
- [ ] `assessor/assessor_graph.py` 작성
- [ ] `assessor/assessor_prompts.py` 작성
- [ ] `assessor/assessor_tools.py` 작성
- [ ] `states/assessor_state.py` 작성
- [ ] 단위 테스트 작성

**주요 노드**:
1. `inbody_analyzer_node` - InBody 데이터 분석
2. `posture_evaluator_node` - 자세 평가
3. `goal_assessor_node` - 목표 및 동기 평가
4. `report_generator_node` - 종합 평가 보고서

**예상 시간**: 8-10시간

#### Task 2.3: Program Designer Agent 구현 (P0)
- [ ] `program_designer/program_designer_agent.py` 작성
- [ ] `program_designer/program_designer_nodes.py` 작성
- [ ] `program_designer/program_designer_graph.py` 작성
- [ ] `program_designer/program_designer_prompts.py` 작성
- [ ] `program_designer/program_designer_tools.py` 작성
- [ ] `states/program_designer_state.py` 작성
- [ ] 단위 테스트 작성

**주요 노드**:
1. `workout_planner_node` - 운동 프로그램 설계
2. `diet_planner_node` - 식단 계획 수립
3. `program_customizer_node` - 커스터마이징
4. `template_manager_node` - 템플릿 관리

**예상 시간**: 10-12시간

---

### Phase 3: 운영 지원 에이전트 구현 (Week 2-3)

**목표**: 운영 효율화 에이전트 구현

#### Task 3.1: Manager Agent 구현 (P1)
- [ ] `manager/manager_agent.py` 작성
- [ ] `manager/manager_nodes.py` 작성
- [ ] `manager/manager_graph.py` 작성
- [ ] `manager/manager_prompts.py` 작성
- [ ] `manager/manager_tools.py` 작성
- [ ] `states/manager_state.py` 작성
- [ ] 단위 테스트 작성

**주요 노드**:
1. `attendance_monitor_node` - 출석 모니터링
2. `churn_predictor_node` - 이탈 위험 감지
3. `renewal_reminder_node` - 재등록 알림
4. `feedback_collector_node` - 피드백 수집

**예상 시간**: 8-10시간

#### Task 3.2: Marketing Agent 구현 (P1)
- [ ] `marketing/marketing_agent.py` 작성
- [ ] `marketing/marketing_nodes.py` 작성
- [ ] `marketing/marketing_graph.py` 작성
- [ ] `marketing/marketing_prompts.py` 작성
- [ ] `marketing/marketing_tools.py` 작성
- [ ] `states/marketing_state.py` 작성
- [ ] 단위 테스트 작성

**주요 노드**:
1. `content_generator_node` - 콘텐츠 생성
2. `sns_scheduler_node` - SNS 스케줄링
3. `story_creator_node` - 성공 사례 스토리텔링
4. `seo_optimizer_node` - SEO 최적화

**예상 시간**: 8-10시간

---

### Phase 4: 경영 지원 에이전트 구현 (Week 3-4)

**목표**: 경영 및 교육 에이전트 구현

#### Task 4.1: Owner Assistant Agent 구현 (P1)
- [ ] `owner_assistant/owner_assistant_agent.py` 작성
- [ ] `owner_assistant/owner_assistant_nodes.py` 작성
- [ ] `owner_assistant/owner_assistant_graph.py` 작성
- [ ] `owner_assistant/owner_assistant_prompts.py` 작성
- [ ] `owner_assistant/owner_assistant_tools.py` 작성
- [ ] `states/owner_assistant_state.py` 작성
- [ ] 단위 테스트 작성

**주요 노드**:
1. `revenue_analyzer_node` - 매출 분석
2. `performance_reporter_node` - 트레이너 성과 리포트
3. `roi_calculator_node` - 프로그램 ROI 분석
4. `insight_generator_node` - 경영 인사이트 생성

**예상 시간**: 8-10시간

#### Task 4.2: Trainer Education Agent 구현 (P2)
- [ ] `trainer_education/trainer_education_agent.py` 작성
- [ ] `trainer_education/trainer_education_nodes.py` 작성
- [ ] `trainer_education/trainer_education_graph.py` 작성
- [ ] `trainer_education/trainer_education_prompts.py` 작성
- [ ] `trainer_education/trainer_education_tools.py` 작성
- [ ] `states/trainer_education_state.py` 작성
- [ ] 단위 테스트 작성

**주요 노드**:
1. `onboarding_guide_node` - 신입 온보딩
2. `skill_trainer_node` - 기법 교육
3. `trend_curator_node` - 트렌드 큐레이션
4. `assessment_node` - 역량 평가

**예상 시간**: 6-8시간

---

### Phase 5: 통합 및 테스트 (Week 4)

**목표**: 전체 시스템 통합 및 검증

#### Task 5.1: Agent Registry 업데이트
- [ ] `base/agent_registry.py` 7개 에이전트 등록
- [ ] 에이전트 간 의존성 설정
- [ ] 우선순위 설정

**예상 시간**: 2-3시간

#### Task 5.2: 통합 테스트
- [ ] 각 에이전트 단독 실행 테스트
- [ ] 에이전트 간 의존성 테스트
- [ ] Execute Layer에서 에이전트 호출 테스트
- [ ] End-to-end 워크플로우 테스트

**예상 시간**: 8-10시간

#### Task 5.3: 기존 코드 정리
- [ ] 기존 diet, workout, schedule, member_care, coaching 폴더 삭제
- [ ] 기존 state 파일 삭제 (diet_agent_state.py, workout_agent_state.py)
- [ ] import 경로 업데이트

**예상 시간**: 2-3시간

---

### Phase 6: 문서화 및 최적화 (Week 4)

**목표**: 문서화 및 최종 점검

#### Task 6.1: 문서화
- [ ] 각 에이전트 README 작성
- [ ] API 문서 업데이트
- [ ] 사용 가이드 작성
- [ ] 예제 코드 작성

**예상 시간**: 6-8시간

#### Task 6.2: 최적화
- [ ] 프롬프트 최적화
- [ ] 성능 프로파일링
- [ ] 로깅 강화

**예상 시간**: 4-6시간

---

## 📋 전체 작업 로드맵

### 작업 요약

| Phase | 주요 작업 | 예상 시간 | 우선순위 | 완료 기준 |
|-------|----------|----------|---------|----------|
| **Phase 1** | 준비 및 검증 | 3-4시간 | P0 | Base 검증 완료 |
| **Phase 2** | 핵심 에이전트 (3개) | 26-32시간 | P0 | Frontdesk/Assessor/Designer 동작 |
| **Phase 3** | 운영 에이전트 (2개) | 16-20시간 | P1 | Manager/Marketing 동작 |
| **Phase 4** | 경영 에이전트 (2개) | 14-18시간 | P1-P2 | Owner/Education 동작 |
| **Phase 5** | 통합 및 테스트 | 12-16시간 | P0 | E2E 테스트 통과 |
| **Phase 6** | 문서화 및 최적화 | 10-14시간 | P1 | 문서 완료 |

**총 예상 시간**: 81-104시간 (약 2-3주, 1인 기준)

### 우선순위별 분류

**P0 (Critical) - 2주 내 완료**:
- Phase 1: 준비 및 검증
- Phase 2: Frontdesk, Assessor, Program Designer
- Phase 5: 통합 및 테스트

**P1 (High) - 3주 내 완료**:
- Phase 3: Manager, Marketing
- Phase 4: Owner Assistant
- Phase 6: 문서화

**P2 (Medium) - 4주 내 완료**:
- Phase 4: Trainer Education
- Phase 6: 최적화

---

## ⚠️ 주의사항

### 1. State 관리

**수정 금지 파일**:
- `states/base.py` - BaseState, BaseAgentState
- `states/supervisors.py` - Supervisor 관련 State
- `states/cognitive_state.py` - Cognitive Layer State
- `states/execute_state.py` - Execute Layer State
- `states/response_state.py` - Response Layer State
- `states/todo_state.py` - TODO Layer State

**새로 생성할 파일**:
- `states/frontdesk_state.py`
- `states/assessor_state.py`
- `states/program_designer_state.py`
- `states/manager_state.py`
- `states/marketing_state.py`
- `states/owner_assistant_state.py`
- `states/trainer_education_state.py`

**State 작성 규칙**:
```python
from backend.app.octostrator.states.base import BaseAgentState

class NewAgentState(BaseAgentState):
    """반드시 BaseAgentState를 상속받을 것"""

    # 에이전트 고유 필드만 추가
    custom_field: Optional[str]
```

### 2. BaseAgent 상속

모든 에이전트는 `BaseAgent`를 상속받아야 합니다:

```python
from backend.app.octostrator.agents.base.base_agent import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self, ...):
        super().__init__(
            agent_id="new_agent",
            agent_name="New Agent",
            enable_checkpoint=True,  # 필요시
            priority=AgentPriority.NORMAL
        )

    def build_graph(self, llm=None):
        # LangGraph 구축
        pass

    async def process_task(self, task, context):
        # 작업 처리
        pass
```

### 3. Import 경로

**올바른 import**:
```python
# Base 프레임워크
from backend.app.octostrator.agents.base.base_agent import BaseAgent

# State
from backend.app.octostrator.states.frontdesk_state import FrontdeskState

# Config
from backend.app.config.system import config
```

### 4. Context API 적용

각 에이전트도 Context API를 사용해야 합니다:

```python
from langgraph.types import Runtime
from backend.app.octostrator.contexts.app_context import AppContext

async def node_function(state: Dict[str, Any], runtime: Runtime):
    context: AppContext = runtime.context
    settings = context.llm_settings

    # LLM 사용
    llm = ChatOpenAI(
        model=settings.agent_model,
        temperature=settings.agent_temperature,
        max_tokens=settings.agent_max_tokens
    )
```

### 5. 에이전트 등록

구현 후 반드시 Registry에 등록:

```python
# base/agent_registry.py
from backend.app.octostrator.agents.frontdesk.frontdesk_agent import FrontdeskAgent

class AgentRegistry:
    def __init__(self):
        self._agents = {
            "frontdesk": FrontdeskAgent(),
            "assessor": AssessorAgent(),
            # ... 모든 에이전트 등록
        }
```

### 6. 테스트 필수

각 에이전트는 단위 테스트를 반드시 작성:

```python
# tests/agents/test_frontdesk_agent.py
import pytest
from backend.app.octostrator.agents.frontdesk.frontdesk_agent import FrontdeskAgent

@pytest.mark.asyncio
async def test_frontdesk_agent_initialization():
    agent = FrontdeskAgent()
    assert agent.agent_id == "frontdesk_agent"
    assert agent.agent_name == "Frontdesk Agent"

@pytest.mark.asyncio
async def test_frontdesk_agent_process_task():
    agent = FrontdeskAgent()
    await agent.initialize()

    result = await agent.process_task(
        task={"task_type": "new_inquiry"},
        context={"user_id": "test", "session_id": "test_session"}
    )

    assert result["status"] == "completed"
```

---

## 🎯 완료 기준

### Phase 2 완료 (핵심 에이전트)
- ✅ Frontdesk Agent가 신규 문의를 처리하고 리드를 관리함
- ✅ Assessor Agent가 회원 평가 보고서를 생성함
- ✅ Program Designer Agent가 맞춤형 프로그램을 설계함
- ✅ 각 에이전트의 단위 테스트 통과

### Phase 3-4 완료 (전체 에이전트)
- ✅ 7개 에이전트 모두 구현 완료
- ✅ 각 에이전트가 독립적으로 동작
- ✅ 에이전트 간 의존성 정상 작동

### Phase 5 완료 (통합)
- ✅ Agent Registry에 모든 에이전트 등록
- ✅ Execute Layer에서 에이전트 호출 가능
- ✅ End-to-end 워크플로우 테스트 통과
- ✅ 기존 diet/workout 등 폴더 제거 완료

### 최종 완료
- ✅ 모든 테스트 통과 (단위 + 통합)
- ✅ 문서화 완료 (README, API, 가이드)
- ✅ Production 환경 배포 준비 완료

---

## 📚 참고 자료

### 관련 문서
- [Context API 마이그레이션 계획](../contextAPI/CONTEXT_API_MIGRATION_TO_HIERARCHICAL_SUPERVISORS_251106.md)
- [Base Agent 구현](../../backend/app/octostrator/agents/base/base_agent.py)
- [BaseAgentState 정의](../../backend/app/octostrator/states/base.py)

### LangGraph 공식 문서
- [StateGraph](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.StateGraph)
- [Agents 패턴](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)

---

## ✅ 체크리스트

### Phase 1: 준비
- [ ] 기존 코드 백업
- [ ] Git branch 생성
- [ ] Base 프레임워크 검증

### Phase 2: 핵심 에이전트
- [ ] Frontdesk Agent 구현 및 테스트
- [ ] Assessor Agent 구현 및 테스트
- [ ] Program Designer Agent 구현 및 테스트

### Phase 3: 운영 에이전트
- [ ] Manager Agent 구현 및 테스트
- [ ] Marketing Agent 구현 및 테스트

### Phase 4: 경영 에이전트
- [ ] Owner Assistant Agent 구현 및 테스트
- [ ] Trainer Education Agent 구현 및 테스트

### Phase 5: 통합
- [ ] Agent Registry 업데이트
- [ ] 통합 테스트 통과
- [ ] 기존 코드 정리

### Phase 6: 문서화
- [ ] 각 에이전트 README
- [ ] API 문서 업데이트
- [ ] 사용 가이드 작성

---

**작성자**: Claude (Anthropic)
**검토 필요**: 시스템 아키텍처 팀, 개발 팀
**승인 대기**: 재구조화 계획 승인 후 작업 시작

---

**END OF RESTRUCTURE PLAN**
