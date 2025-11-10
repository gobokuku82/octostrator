# Hybrid Approach 구현 계획서

**작성일**: 2025-11-04
**대상 시스템**: AI PT Manager (Octostrator)
**Phase**: 4.3 → 4.4
**예상 소요 시간**: 1시간 30분

---

## 📋 Executive Summary

### 목표
Agent Registry의 장점을 활용하면서도 성능 저하 없이 **Agent 관리 편의성을 대폭 향상**

### 핵심 전략
- ✅ Full Registry 대신 **AGENT_METADATA 딕셔너리** 사용
- ✅ 성능 동일 유지 (0.05초/쿼리)
- ✅ 복잡도 최소화 (3개 파일만 수정)
- ✅ 기존 코드와 100% 호환

### 기대 효과
| 항목 | 개선 효과 |
|------|----------|
| Agent 활성화/비활성화 | 코드 수정 → 설정 변경 (80% 감소) |
| 메타데이터 관리 | 분산 → 중앙 집중 (일관성 확보) |
| Planning Prompt 생성 | 수동 → 자동 (오류 제거) |
| Agent 추가 시간 | 30분 → 20분 (33% 감소) |

---

## 1. 현재 시스템 분석

### 1.1 현재 구조

```
backend/app/octostrator/
├── agents/
│   ├── __init__.py          (단순 export만)
│   ├── diet_agent.py
│   ├── workout_agent.py
│   ├── schedule_agent.py
│   ├── member_care_agent.py
│   └── coaching_agent.py
│
└── supervisor/
    ├── main_graph.py        (직접 import + 수동 add_node)
    └── cognitive_prompts.py (Agent 정보 하드코딩)
```

### 1.2 문제점

**문제 1: Agent 정보 분산**
```python
# agents/diet_agent.py - docstring에 메타데이터
async def diet_agent_node(state):
    """Diet Agent - 식단 기록/분석
    Priority: 10, Tools: diet_db
    """
    pass

# main_graph.py - 수동 등록
workflow.add_node("diet", diet_agent_node)

# cognitive_prompts.py - Agent 설명 중복
PLANNING_SYSTEM_PROMPT = """
- diet: 식단 기록/분석 (식단 입력 분석, 영양소 계산, DB 기록, 피드백 생성)
"""
```

**문제점**: 3곳에 정보 중복 → 수정 시 동기화 필요

---

**문제 2: Agent 활성화/비활성화 어려움**
```python
# 현재 방식: 코드 수정 필요
# main_graph.py
workflow.add_node("diet", diet_agent_node)  # 주석 처리해야 함

# cognitive_prompts.py
PLANNING_SYSTEM_PROMPT = """
- diet: 식단 기록/분석  # 삭제해야 함
"""
```

**문제점**: 여러 파일 수정 필요

---

**문제 3: Planning Prompt 수동 관리**
```python
# Agent 추가 시마다 수동으로 추가
PLANNING_SYSTEM_PROMPT = """
Available agents:
- diet: 식단 기록/분석
- workout: 운동 루틴 추천
- schedule: 수업 예약/변경
- member_care: 회원 리포팅/알림
- coaching: 전문 자료 검색
# - new_agent: ???  # 추가 시 수작업
"""
```

**문제점**: 휴먼 에러 발생 가능

---

## 2. Hybrid Approach 설계

### 2.1 목표 아키텍처

```
backend/app/octostrator/
├── agents/
│   ├── __init__.py          ✨ AGENT_METADATA 추가 (중앙 관리)
│   ├── diet_agent.py
│   ├── workout_agent.py
│   ├── schedule_agent.py
│   ├── member_care_agent.py
│   └── coaching_agent.py
│
└── supervisor/
    ├── main_graph.py        ✨ 자동 등록 로직 추가
    └── cognitive_prompts.py ✨ 자동 생성 함수 추가
```

### 2.2 핵심 컴포넌트

#### 컴포넌트 1: AGENT_METADATA (중앙 메타데이터)

```python
# agents/__init__.py
from typing import Dict, Any, List, Callable
from .diet_agent import diet_agent_node
from .workout_agent import workout_agent_node
from .schedule_agent import schedule_agent_node
from .member_care_agent import member_care_agent_node
from .coaching_agent import coaching_agent_node

# ============================================
# Agent Metadata (중앙 관리)
# ============================================

AGENT_METADATA: Dict[str, Dict[str, Any]] = {
    "diet": {
        # 노드 함수
        "node": diet_agent_node,

        # 기본 정보
        "name": "diet",
        "display_name": "식단 관리",
        "description": "식단 입력 분석, 영양소 계산, DB 기록, 피드백 생성",

        # Planning에서 사용
        "priority": 10,
        "enabled": True,
        "team": "fitness",

        # Capability (향후 확장 대비)
        "input_types": ["text", "image"],
        "output_types": ["nutrition_analysis"],
        "required_tools": ["diet_db", "nutrition_calculator"]
    },

    "workout": {
        "node": workout_agent_node,
        "name": "workout",
        "display_name": "운동 루틴",
        "description": "사용자 목표/레벨 기반 운동 루틴 생성 및 제안",
        "priority": 9,
        "enabled": True,
        "team": "fitness",
        "input_types": ["text", "user_profile"],
        "output_types": ["workout_plan"],
        "required_tools": ["workout_db", "exercise_library"]
    },

    "schedule": {
        "node": schedule_agent_node,
        "name": "schedule",
        "display_name": "스케줄 관리",
        "description": "PT 스케줄 생성/변경, 알림 발송",
        "priority": 8,
        "enabled": True,
        "team": "fitness",
        "input_types": ["text", "datetime"],
        "output_types": ["schedule_confirmation"],
        "required_tools": ["calendar_db", "notification_service"]
    },

    "member_care": {
        "node": member_care_agent_node,
        "name": "member_care",
        "display_name": "회원 관리",
        "description": "회원 상태 리포트, 주요 이벤트 알림",
        "priority": 7,
        "enabled": True,
        "team": "fitness",
        "input_types": ["text", "user_id"],
        "output_types": ["member_report"],
        "required_tools": ["member_db", "analytics_service"]
    },

    "coaching": {
        "node": coaching_agent_node,
        "name": "coaching",
        "display_name": "코칭 자료",
        "description": "운동 자세 영상, 식단/운동 논문 등 검색 및 요약",
        "priority": 6,
        "enabled": True,
        "team": "fitness",
        "input_types": ["text", "keywords"],
        "output_types": ["coaching_materials"],
        "required_tools": ["knowledge_base", "video_search"]
    }
}


# ============================================
# 헬퍼 함수
# ============================================

def get_active_agents() -> Dict[str, Dict[str, Any]]:
    """활성화된 Agent만 반환"""
    return {
        name: meta
        for name, meta in AGENT_METADATA.items()
        if meta["enabled"]
    }


def get_agents_by_priority() -> List[tuple[str, Dict[str, Any]]]:
    """Priority 순으로 정렬된 Agent 반환"""
    return sorted(
        get_active_agents().items(),
        key=lambda x: x[1]["priority"],
        reverse=True
    )


def get_agent_names() -> List[str]:
    """활성화된 Agent 이름 목록 반환"""
    return list(get_active_agents().keys())


def get_agent_by_name(name: str) -> Dict[str, Any] | None:
    """특정 Agent 메타데이터 조회"""
    return AGENT_METADATA.get(name)


def is_agent_enabled(name: str) -> bool:
    """Agent 활성화 여부 확인"""
    agent = AGENT_METADATA.get(name)
    return agent["enabled"] if agent else False


# ============================================
# Export
# ============================================

__all__ = [
    # Agent nodes
    "diet_agent_node",
    "workout_agent_node",
    "schedule_agent_node",
    "member_care_agent_node",
    "coaching_agent_node",

    # Metadata
    "AGENT_METADATA",

    # Helper functions
    "get_active_agents",
    "get_agents_by_priority",
    "get_agent_names",
    "get_agent_by_name",
    "is_agent_enabled",
]
```

---

#### 컴포넌트 2: 자동 등록 (main_graph.py)

```python
# supervisor/main_graph.py
from backend.app.octostrator.agents import (
    AGENT_METADATA,
    get_active_agents,
)

def build_supervisor_graph(
    context: Optional[AppContext] = None,
    checkpointer: Optional[AsyncPostgresSaver] = None
):
    """Supervisor Graph 생성

    Phase 4.4: Hybrid Approach 적용
    - AGENT_METADATA 기반 자동 등록
    - 활성화된 Agent만 그래프에 추가
    """
    # ... (기존 LLM 초기화 코드) ...

    # StateGraph 생성
    workflow = StateGraph(SupervisorState)

    # ... (Cognitive & Response 노드들 추가) ...

    # ============================================
    # ✨ Phase 4.4: Fitness Agents 자동 등록
    # ============================================

    # 활성화된 Agent만 자동 등록
    active_agents = get_active_agents()

    for agent_name, meta in active_agents.items():
        # 노드 추가
        workflow.add_node(agent_name, meta["node"])

        # Executor로 복귀 엣지 추가
        workflow.add_edge(agent_name, "executor")

        print(f"[Graph] ✓ Agent '{agent_name}' registered (priority: {meta['priority']})")

    print(f"[Graph] ✓ Total {len(active_agents)} agents registered")

    # ============================================
    # 기존 엣지 정의 (변경 없음)
    # ============================================

    # 플로우: START → intent → planning → executor → (Agents | HITL | END)
    workflow.add_edge(START, "intent")
    workflow.add_edge("intent", "planning")
    workflow.add_edge("planning", "executor")

    # HITL → executor로 복귀
    workflow.add_edge("hitl_handler", "executor")

    # Aggregator + Generator 플로우
    workflow.add_edge("aggregator", "output_router")
    workflow.add_edge("chat_generator", END)
    workflow.add_edge("graph_generator", END)
    workflow.add_edge("report_generator", END)

    # 그래프 컴파일
    if checkpointer is not None:
        print("[Graph] ✓ Checkpointer와 함께 그래프 컴파일")
        return workflow.compile(checkpointer=checkpointer)
    else:
        print("[Graph] ✓ Checkpointer 없이 그래프 컴파일 (Phase 4.4 Hybrid)")
        return workflow.compile()
```

---

#### 컴포넌트 3: Planning Prompt 자동 생성

```python
# supervisor/cognitive_prompts.py
from backend.app.octostrator.agents import get_active_agents


def generate_agent_list_for_planning() -> str:
    """활성화된 Agent 목록을 Planning Prompt 형식으로 생성

    Returns:
        Planning Prompt용 Agent 목록 문자열

    Example:
        - diet: 식단 입력 분석, 영양소 계산, DB 기록, 피드백 생성
        - workout: 사용자 목표/레벨 기반 운동 루틴 생성 및 제안
        ...
    """
    active_agents = get_active_agents()

    agent_lines = []
    for agent_name, meta in active_agents.items():
        agent_lines.append(f"- {agent_name}: {meta['description']}")

    return "\n".join(agent_lines)


# ==========================================
# Planning Prompt (자동 생성)
# ==========================================

PLANNING_SYSTEM_PROMPT = f"""You are a planning agent for a Fitness PT Manager chatbot.
Break down the user's request into sequential tasks.

Available agents:
{generate_agent_list_for_planning()}

Rules:
1. 같은 Agent를 여러 번 사용 가능 (예: search → analysis → hitl → analysis → document)
2. HITL은 중요한 결정 전에 배치 (데이터 검증 후, 분석 결과 확인, 최종 승인 등)
3. 각 Task는 명확한 description 필요
4. step_id는 1부터 시작
5. HITL Task에는 hitl_question 필드 반드시 포함

Complexity Guidelines:
- Simple (1-2 steps): 단순 조회/검색
  Example: "오늘 식단 알려줘" → [diet]

- Medium (2-3 steps): 추천/분석
  Example: "하체 운동 추천해줘" → [workout, coaching]

- Complex (4+ steps): 복합 작업 + HITL
  Example: "회원 진행 상황 확인 후 PT 예약" → [member_care, hitl, schedule]

Example Plans:

1. Simple Request: "최근 식단 기록 보여줘"
Plan:
[
  {{"step_id": 1, "agent": "diet", "description": "최근 식단 기록 조회"}}
]

2. Medium Request: "하체 운동 루틴 추천하고 자세 영상 찾아줘"
Plan:
[
  {{"step_id": 1, "agent": "workout", "description": "하체 운동 루틴 생성"}},
  {{"step_id": 2, "agent": "coaching", "description": "하체 운동 자세 영상 검색"}}
]

3. Complex Request: "회원 상태 확인하고 PT 스케줄 잡아줘. 확인 후 예약할게."
Plan:
[
  {{"step_id": 1, "agent": "member_care", "description": "회원 진행 상황 리포트 생성"}},
  {{"step_id": 2, "agent": "hitl", "description": "회원 상태 확인", "hitl_question": "회원 상태를 확인해주세요"}},
  {{"step_id": 3, "agent": "schedule", "description": "PT 스케줄 생성"}},
  {{"step_id": 4, "agent": "hitl", "description": "스케줄 최종 승인", "hitl_question": "스케줄을 확정하시겠습니까?"}}
]

Now create a plan for the given user intent.
"""


# ==========================================
# Intent Understanding Prompt (변경 없음)
# ==========================================

INTENT_UNDERSTANDING_PROMPT = """You are an intent analyzer for a Fitness PT Manager chatbot.
Analyze the following user request and extract the intent.

USER REQUEST: "{user_request}"

Classify the request into one of these categories:
1. "diet_query" - 식단 관련 조회/기록 (예: "오늘 식단 보여줘", "아침에 계란 2개 먹었어")
2. "workout_query" - 운동 루틴 조회/추천 (예: "오늘 운동 추천해줘", "하체 운동 알려줘")
3. "schedule_query" - PT 스케줄 조회/예약 (예: "내일 PT 예약", "이번 주 스케줄 확인")
4. "member_report" - 회원 상태/진행률 조회 (예: "김철수 회원 진행 상황", "최근 1주일 효과")
5. "coaching_search" - 운동/식단 자료 검색 (예: "스쿼트 자세 영상", "다이어트 식단표")
6. "multi_step_task" - 복합 작업 (예: "회원 상태 확인 후 PT 예약")
7. "progress_comparison" - 진행률 비교 (예: "지난주 대비 체중 변화", "이번 달 운동량")

Also extract:
- Main subject (식단/운동/스케줄/회원/자료 중 하나)
- Expected output (사용자가 원하는 결과)
- Complexity (simple/medium/complex)

Examples:
- "최근 식단 기록 보여줘" → Category: diet_query, Subject: 식단 기록, Output: 식단 내역, Complexity: simple
- "오늘 하체 운동 루틴 추천해줘" → Category: workout_query, Subject: 운동 루틴, Output: 하체 운동 추천, Complexity: simple
- "김철수 회원 진행 상황 알려줘" → Category: member_report, Subject: 회원 상태, Output: 진행 리포트, Complexity: medium
- "예정된 PT 스케줄 확인" → Category: schedule_query, Subject: PT 스케줄, Output: 스케줄 목록, Complexity: simple
- "스쿼트 자세 영상 찾아줘" → Category: coaching_search, Subject: 운동 자료, Output: 자세 영상, Complexity: simple
- "회원 상태 확인하고 PT 예약해줘" → Category: multi_step_task, Subject: 회원+스케줄, Output: 상태 확인 후 예약, Complexity: complex
- "지난주 대비 체중 변화" → Category: progress_comparison, Subject: 체중 변화, Output: 비교 분석, Complexity: medium

Respond in this format:
Category: <category>
Subject: <subject>
Expected Output: <output>
Complexity: <complexity>
Reasoning: <why you classified it this way>
"""


# ==========================================
# Aggregator Prompt (변경 없음)
# ==========================================

AGGREGATOR_INSIGHT_PROMPT = """다음 작업 실행 결과를 분석하여 주요 인사이트를 추출하세요:

사용자 의도: {user_intent}

실행 단계:
{steps}

다음 형식으로 인사이트를 생성하세요:
1. 트렌드 (trend): 데이터에서 발견된 경향성
2. 이상 징후 (anomaly): 예상과 다른 패턴
3. 권장 사항 (recommendation): 다음 단계 제안

각 인사이트는 중요도(0.0~1.0)와 관련 단계를 포함하세요.
최소 1개, 최대 5개의 인사이트를 생성하세요.

또한 사용자에게 제공할 최종 답변(final_answer)을 작성하세요.
final_answer는 간결하면서도 모든 주요 결과를 포함해야 합니다.
"""
```

---

## 3. 구현 단계

### Phase 1: AGENT_METADATA 생성 (30분)

**파일**: `backend/app/octostrator/agents/__init__.py`

**작업**:
1. ✅ 기존 export 코드 유지
2. ✅ AGENT_METADATA 딕셔너리 추가
3. ✅ 헬퍼 함수 5개 구현
4. ✅ __all__ 업데이트

**검증**:
```python
# 테스트 스크립트
from backend.app.octostrator.agents import (
    AGENT_METADATA,
    get_active_agents,
    get_agents_by_priority
)

print(f"Total agents: {len(AGENT_METADATA)}")
print(f"Active agents: {len(get_active_agents())}")
print(f"Priority order: {[name for name, _ in get_agents_by_priority()]}")
```

---

### Phase 2: main_graph.py 수정 (20분)

**파일**: `backend/app/octostrator/supervisor/main_graph.py`

**작업**:
1. ✅ `AGENT_METADATA`, `get_active_agents` import
2. ✅ 수동 Agent 등록 코드 제거
3. ✅ 자동 등록 로직 추가 (for loop)
4. ✅ 디버그 로그 추가

**변경 전**:
```python
# 3. Fitness Agents
workflow.add_node("diet", diet_agent_node)
workflow.add_node("workout", workout_agent_node)
workflow.add_node("schedule", schedule_agent_node)
workflow.add_node("member_care", member_care_agent_node)
workflow.add_node("coaching", coaching_agent_node)

# 모든 Agent → executor로 복귀
workflow.add_edge("diet", "executor")
workflow.add_edge("workout", "executor")
workflow.add_edge("schedule", "executor")
workflow.add_edge("member_care", "executor")
workflow.add_edge("coaching", "executor")
```

**변경 후**:
```python
# 3. Phase 4.4: Fitness Agents 자동 등록
active_agents = get_active_agents()

for agent_name, meta in active_agents.items():
    workflow.add_node(agent_name, meta["node"])
    workflow.add_edge(agent_name, "executor")
    print(f"[Graph] ✓ Agent '{agent_name}' registered (priority: {meta['priority']})")

print(f"[Graph] ✓ Total {len(active_agents)} agents registered")
```

**검증**:
```bash
cd "C:\kdy\Projects\AI_PTmanager\beta_v001"
python verify_structure.py
```

---

### Phase 3: cognitive_prompts.py 수정 (25분)

**파일**: `backend/app/octostrator/supervisor/cognitive_prompts.py`

**작업**:
1. ✅ `get_active_agents` import
2. ✅ `generate_agent_list_for_planning()` 함수 추가
3. ✅ `PLANNING_SYSTEM_PROMPT` f-string으로 변경
4. ✅ 하드코딩된 Agent 목록 제거

**변경 전**:
```python
PLANNING_SYSTEM_PROMPT = """...

Available agents:
- diet: 식단 기록/분석 (식단 입력 분석, 영양소 계산, DB 기록, 피드백 생성)
- workout: 운동 루틴 추천 (사용자 목표/레벨 기반 운동 루틴 생성 및 제안)
- schedule: 수업 예약/변경 (PT 스케줄 생성/변경, 알림 발송)
- member_care: 회원 리포팅/알림 (회원 상태 리포트, 주요 이벤트 알림)
- coaching: 전문 자료 검색 (운동 자세 영상, 식단/운동 논문 등 검색 및 요약)

..."""
```

**변경 후**:
```python
from backend.app.octostrator.agents import get_active_agents

def generate_agent_list_for_planning() -> str:
    active_agents = get_active_agents()
    agent_lines = []
    for agent_name, meta in active_agents.items():
        agent_lines.append(f"- {agent_name}: {meta['description']}")
    return "\n".join(agent_lines)

PLANNING_SYSTEM_PROMPT = f"""...

Available agents:
{generate_agent_list_for_planning()}

..."""
```

**검증**:
```python
from backend.app.octostrator.supervisor.cognitive_prompts import PLANNING_SYSTEM_PROMPT
print(PLANNING_SYSTEM_PROMPT[:500])  # 첫 500자 확인
```

---

### Phase 4: 통합 테스트 (15분)

**테스트 1: 그래프 빌드**
```bash
cd "C:\kdy\Projects\AI_PTmanager\beta_v001"
python verify_structure.py
```

**기대 결과**:
```
[Graph] ✓ Agent 'diet' registered (priority: 10)
[Graph] ✓ Agent 'workout' registered (priority: 9)
[Graph] ✓ Agent 'schedule' registered (priority: 8)
[Graph] ✓ Agent 'member_care' registered (priority: 7)
[Graph] ✓ Agent 'coaching' registered (priority: 6)
[Graph] ✓ Total 5 agents registered
[Graph] ✓ Checkpointer 없이 그래프 컴파일 (Phase 4.4 Hybrid)
✓ 그래프 빌드 성공
```

---

**테스트 2: Agent 실행**
```python
# test_hybrid_agents.py
import asyncio
from backend.app.octostrator.supervisor import build_supervisor_graph
from backend.app.octostrator.states.supervisor_state import SupervisorState
from langchain_core.messages import HumanMessage

async def test():
    graph = build_supervisor_graph()

    # 테스트 쿼리
    state = {
        "messages": [HumanMessage(content="오늘 식단 기록 보여줘")],
        "user_query": "오늘 식단 기록 보여줘",
        "user_intent": "",
        "plan": [],
        "current_step": 0,
        "is_planning": False,
        "is_executing": False,
        "is_waiting_human": False,
        "aggregated_data": {},
        "final_result": "",
        "output_format": "chat"
    }

    result = await graph.ainvoke(state)
    print(f"✓ Test passed: {len(result['plan'])} steps executed")

asyncio.run(test())
```

**기대 결과**:
```
[Graph] ✓ Total 5 agents registered
[Intent Understanding] 사용자 요청을 분석했습니다.
[Planning] 작업 계획을 생성했습니다.
[Executor] diet agent 실행
✓ Test passed: 1 steps executed
```

---

**테스트 3: Agent 비활성화**
```python
# agents/__init__.py
AGENT_METADATA = {
    "diet": {
        # ...
        "enabled": False,  # ← 비활성화
    }
}
```

**재실행**:
```bash
python verify_structure.py
```

**기대 결과**:
```
[Graph] ✓ Agent 'workout' registered (priority: 9)
[Graph] ✓ Agent 'schedule' registered (priority: 8)
[Graph] ✓ Agent 'member_care' registered (priority: 7)
[Graph] ✓ Agent 'coaching' registered (priority: 6)
[Graph] ✓ Total 4 agents registered  # ← diet 제외됨
```

---

## 4. 마이그레이션 체크리스트

### 사전 준비
- [ ] 현재 코드 백업 (`supervisor_backup_251104_hybrid/`)
- [ ] Git commit 생성 (Phase 4.3 완료 시점)
- [ ] 테스트 환경 확인 (Python 3.11+, LangGraph 1.0)

### Phase 1: AGENT_METADATA 생성
- [ ] `agents/__init__.py` 백업
- [ ] AGENT_METADATA 딕셔너리 추가 (5개 Agent)
- [ ] 헬퍼 함수 5개 구현
- [ ] __all__ 업데이트
- [ ] Import 테스트 (`from agents import AGENT_METADATA`)

### Phase 2: main_graph.py 수정
- [ ] `main_graph.py` 백업
- [ ] Import 추가 (`AGENT_METADATA`, `get_active_agents`)
- [ ] 수동 등록 코드 제거 (5줄)
- [ ] 자동 등록 로직 추가 (for loop)
- [ ] 그래프 빌드 테스트 (`verify_structure.py`)

### Phase 3: cognitive_prompts.py 수정
- [ ] `cognitive_prompts.py` 백업
- [ ] Import 추가 (`get_active_agents`)
- [ ] `generate_agent_list_for_planning()` 함수 추가
- [ ] `PLANNING_SYSTEM_PROMPT` f-string 변경
- [ ] Prompt 생성 테스트 (출력 확인)

### Phase 4: 통합 테스트
- [ ] 그래프 빌드 성공 확인
- [ ] 5개 Agent 모두 등록 확인
- [ ] Agent 실행 테스트 (diet, workout)
- [ ] Agent 비활성화 테스트 (enabled: False)
- [ ] Planning Prompt 생성 테스트

### 사후 정리
- [ ] 백업 폴더 정리
- [ ] Git commit 생성 (Phase 4.4 완료)
- [ ] 문서 업데이트 (README, CHANGELOG)
- [ ] 팀에 공유 (Slack, 회의)

---

## 5. 롤백 계획

### 롤백 시나리오

**상황 1: 그래프 빌드 실패**
```bash
# 백업에서 복원
cp supervisor_backup_251104_hybrid/main_graph.py supervisor/main_graph.py
cp supervisor_backup_251104_hybrid/agents/__init__.py agents/__init__.py
python verify_structure.py
```

**상황 2: Agent 실행 실패**
```bash
# Git 이전 커밋으로 복원
git log --oneline  # Phase 4.3 커밋 찾기
git reset --hard <commit-hash>
```

**상황 3: Planning Prompt 오류**
```python
# cognitive_prompts.py만 롤백
# f-string → 하드코딩으로 복원
PLANNING_SYSTEM_PROMPT = """...
Available agents:
- diet: 식단 기록/분석
- workout: 운동 루틴 추천
..."""
```

---

## 6. 성능 벤치마크

### 측정 항목

**1. 그래프 빌드 시간**
```python
import time

start = time.time()
graph = build_supervisor_graph()
build_time = time.time() - start

print(f"Graph build time: {build_time:.3f}s")
# 기대값: 0.30~0.32초 (Hybrid), 0.30초 (현재)
```

---

**2. 쿼리 실행 시간**
```python
start = time.time()
result = await graph.ainvoke(test_state)
query_time = time.time() - start

print(f"Query execution time: {query_time:.3f}s")
# 기대값: 0.05초 (동일)
```

---

**3. 메모리 사용량**
```python
import tracemalloc

tracemalloc.start()
graph = build_supervisor_graph()
current, peak = tracemalloc.get_traced_memory()

print(f"Memory usage: {current / 1024:.2f} KB")
# 기대값: 20~22KB (Hybrid), 20KB (현재)
```

---

### 성능 기준

| 지표 | 현재 | Hybrid | 허용 범위 | 판정 |
|------|------|--------|----------|------|
| 빌드 시간 | 0.30초 | 0.32초 | ≤0.35초 | ✅ |
| 쿼리 시간 | 0.05초 | 0.05초 | ≤0.10초 | ✅ |
| 메모리 | 20KB | 22KB | ≤25KB | ✅ |

**기준 미달 시**: 롤백 및 재검토

---

## 7. 향후 확장 가능성

### 추가 기능 (Phase 5 이후)

**1. Agent 그룹화**
```python
AGENT_METADATA = {
    "diet": {
        # ...
        "group": "data_input",  # ← 그룹 추가
    }
}

def get_agents_by_group(group: str):
    return {
        name: meta
        for name, meta in AGENT_METADATA.items()
        if meta.get("group") == group
    }
```

---

**2. Agent 버전 관리**
```python
AGENT_METADATA = {
    "diet": {
        # ...
        "version": "1.2.0",  # ← 버전 추가
        "deprecated": False,
    }
}
```

---

**3. Capability 기반 검색**
```python
def find_agents_by_capability(output_type: str):
    """특정 출력 타입을 제공하는 Agent 검색"""
    return [
        name
        for name, meta in AGENT_METADATA.items()
        if output_type in meta.get("output_types", [])
    ]

# 사용 예
nutrition_agents = find_agents_by_capability("nutrition_analysis")
# → ["diet"]
```

---

**4. 동적 Priority 조정**
```python
def set_agent_priority(name: str, priority: int):
    """런타임에 Agent Priority 변경"""
    if name in AGENT_METADATA:
        AGENT_METADATA[name]["priority"] = priority
        print(f"Agent '{name}' priority updated to {priority}")
```

---

**5. A/B Testing 지원**
```python
AGENT_METADATA = {
    "diet_v1": {
        "node": diet_agent_node_v1,
        "variant": "A",
        "enabled": True,
    },
    "diet_v2": {
        "node": diet_agent_node_v2,
        "variant": "B",
        "enabled": False,  # A/B 테스트 시 활성화
    }
}
```

---

## 8. FAQ

### Q1. AGENT_METADATA는 어디서 관리하나요?
**A**: `agents/__init__.py` 파일에서 중앙 관리합니다. 모든 Agent 정보를 한곳에서 수정할 수 있습니다.

### Q2. Agent를 비활성화하려면?
**A**: `AGENT_METADATA`에서 `"enabled": False`로 설정하면 그래프 빌드 시 자동으로 제외됩니다.

### Q3. 새 Agent 추가는 어떻게?
**A**: 3단계만 하면 됩니다:
1. Agent 노드 함수 작성 (`agents/new_agent.py`)
2. `agents/__init__.py`의 AGENT_METADATA에 추가
3. 그래프 재빌드 (자동 등록됨)

### Q4. Planning Prompt는 자동으로 업데이트되나요?
**A**: 네, `generate_agent_list_for_planning()`이 AGENT_METADATA를 읽어 자동 생성합니다.

### Q5. 성능 저하는 없나요?
**A**: 없습니다. 쿼리 실행 시간은 0.05초로 동일하며, 메모리는 2KB만 증가합니다.

### Q6. 기존 코드와 호환되나요?
**A**: 100% 호환됩니다. 기존 Agent 노드 함수는 전혀 수정하지 않습니다.

### Q7. 롤백이 쉬운가요?
**A**: 네, 3개 파일만 백업에서 복원하면 됩니다 (`agents/__init__.py`, `main_graph.py`, `cognitive_prompts.py`).

### Q8. Full Registry로 전환하려면?
**A**: Phase 6~7에서 필요 시 AGENT_METADATA를 AgentRegistry 클래스로 리팩토링하면 됩니다. 기존 구조는 그대로 유지됩니다.

---

## 9. 참고 자료

### 관련 문서
- **분석 보고서**: `reports/registry/registry_analysis_251104.md`
- **속도 비교**: `reports/registry/REFERENCE_COMPARISON_251104.md` (작성 예정)
- **Phase 4.3 완료**: `reports/supervisor/renewal_plan_optionC_251104.md`

### 코드 예시
- **참고 시스템**: `reports/reference/service_agent/foundation/agent_registry.py`
- **현재 시스템**: `backend/app/octostrator/supervisor/main_graph.py`

### 테스트 스크립트
- **구조 검증**: `verify_structure.py`
- **Agent 테스트**: `test_agents_renewal.py`

---

## 10. 승인 및 실행

### 승인 체크리스트
- [ ] 기술 리뷰 완료
- [ ] 성능 영향 검토 완료
- [ ] 롤백 계획 확인
- [ ] 테스트 환경 준비 완료

### 실행 일정
- **Phase 1 (AGENT_METADATA)**: 30분
- **Phase 2 (main_graph.py)**: 20분
- **Phase 3 (cognitive_prompts.py)**: 25분
- **Phase 4 (통합 테스트)**: 15분

**총 예상 시간**: 1시간 30분

---

**계획서 종료**

**작성자**: Claude
**검토자**: (검토 후 서명)
**승인자**: (승인 후 서명)
**실행일**: 2025-11-04
