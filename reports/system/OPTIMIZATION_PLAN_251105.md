# 시스템 및 LangGraph 프레임워크 최적화 계획서

**프로젝트**: AI PTmanager - Beta v0.01
**작성일**: 2025-11-05
**버전**: 1.0
**대상**: 시스템 성능 최적화 및 LangGraph 프레임워크 개선

---

## 📋 Executive Summary

### 현재 상황

**✅ 구현 완료**:
- 5개 Fitness Agents (diet, workout, schedule, member_care, coaching)
- 5개 Tools 모듈 (도메인별 Tool 구현)
- LangGraph 구조 (Phase 4.3 - cognitive/response 노드 분리)
- PostgreSQL Checkpointer 통합

**⚠️ 발견된 문제**:
- **LLM 토큰 제한 초과**: diet 테스트 실패 (16,384 tokens 생성)
- **Tools Registry 미완성**: `__init__.py`가 비어있어 Tool 접근 불편
- **프롬프트 최적화 부족**: 과도하게 긴 응답 생성
- **성능 측정 부족**: 응답 시간, 메모리 사용량 모니터링 없음

### 핵심 질문: 메타데이터 레이어 vs 싱글톤 vs 현재 유지?

**결정**: **현재 구조 유지 + 점진적 최적화** ✅

**근거**:

| 구분 | 평가 | 이유 |
|------|------|------|
| **메타데이터 레이어** | ⏳ 보류 | Agent 5개 → 관리 오버헤드 > 효과<br>Agent 10개+ 확장 시 재검토 |
| **싱글톤 Registry** | ❌ 거부 | LangGraph 철학 위배<br>Stateless 함수 방식이 더 효율적 |
| **현재 구조 유지** | ✅ 채택 | 간결하고 명확함<br>LangGraph 1.0 철학 완벽 준수<br>점진적 개선 가능 |

### 최적화 목표

| 목표 | 현재 | 목표 | 개선률 |
|------|------|------|--------|
| **테스트 성공률** | 75% (3/4) | 100% (4/4) | +25% |
| **쿼리 응답 시간** | ~2.0초 | 1.5초 이하 | -25% |
| **LLM 토큰 사용** | 17,707 (초과) | 5,000 이하 | -72% |
| **Tools 접근성** | 수동 import | Registry 자동 | 100% 개선 |
| **코드 중복** | 높음 | 낮음 | -30% |

---

## 1. 현황 분석

### 1.1 구현 완료 항목

#### ✅ Fitness Agents (5개)

```
backend/app/octostrator/agents/
├── diet/agent.py           ✅ Tool 기반 리팩토링 완료
├── workout/agent.py        ✅ 구현 완료
├── schedule/agent.py       ✅ 구현 완료
├── member_care/agent.py    ✅ 구현 완료
└── coaching/agent.py       ✅ 구현 완료
```

**특징**:
- DietAgent: `get_meal_logs`, `get_daily_nutrition_summary` Tool 사용
- 나머지 Agent들: 구현 수준 미확인 (확인 필요)

#### ✅ Tools 모듈 (5개)

```
backend/app/octostrator/tools/
├── __init__.py             ⚠️ 비어있음 (Registry 미구현)
├── diet_tools.py           ✅ 3개 Tool 구현
│   ├── get_meal_logs
│   ├── save_meal_log
│   └── get_daily_nutrition_summary
├── workout_tools.py        ✅ 구현 완료
├── schedule_tools.py       ✅ 구현 완료
├── member_care_tools.py    ✅ 구현 완료
└── coaching_tools.py       ✅ 구현 완료
```

**문제점**:
- `__init__.py`가 비어있어 Tool 등록/접근 불편
- 각 Agent가 직접 `from backend.app.octostrator.tools.diet_tools import get_meal_logs` 형태로 import
- 중앙 관리 부족

#### ✅ LangGraph 구조 (Phase 4.3)

```
backend/app/octostrator/supervisor/
├── main_graph.py           ✅ Graph 정의
├── cognitive_nodes.py      ✅ Intent, Planning, Executor, Aggregator
├── response_nodes.py       ✅ HITL, Router, Generators
├── cognitive_prompts.py    ✅ 분석 프롬프트 중앙 관리
└── response_prompts.py     ✅ 응답 프롬프트 중앙 관리
```

**장점**:
- 명확한 책임 분리
- 프롬프트 중앙 관리
- PostgreSQL Checkpointer 통합

### 1.2 테스트 결과 분석

**테스트 환경**: `test_agents_renewal.py` (2025-11-04 실행)

| Agent | 결과 | 실행 시간 | 문제 |
|-------|------|----------|------|
| **diet** | ❌ 실패 | - | LLM 토큰 제한 초과 (16,384 tokens) |
| **workout** | ✅ 성공 | ~2.0초 | 정상 |
| **schedule** | ✅ 성공 | ~1.8초 | 정상 |
| **coaching** | ✅ 성공 | ~1.9초 | 정상 (검색 결과 없음) |

**성공률**: 75% (3/4)

#### diet 테스트 실패 상세

**에러**:
```
openai.LengthFinishReasonError: Could not parse response content as the length limit was reached
- completion_tokens=16,384 (최대치)
- prompt_tokens=1,323
- total_tokens=17,707
```

**발생 위치**:
- `planning_node` → `structured_llm.ainvoke()` → Structured Output 생성
- LLM이 Plan을 생성하려다 토큰 제한 초과

**원인 분석**:
1. **프롬프트 길이**: PLANNING_SYSTEM_PROMPT가 길 가능성
2. **max_tokens 미설정**: LLM이 무제한 생성 시도
3. **Structured Output 복잡도**: TaskStep 스키마가 복잡할 가능성
4. **State 크기**: messages 누적으로 Context 증가

### 1.3 메타데이터 레이어 필요성 평가

**레퍼런스 분석 문서 (251104) 결론**:
- Agent 5개 환경: 메타데이터 레이어 오버헤드 > 효과
- 메타데이터 검색 시간 절약: 4.9ms (5개 순회 → Dict 조회)
- 메타데이터 관리 코드: 200줄+ 추가

**현재 구조의 장점**:
1. ✅ 간결함: Agent 등록이 명확 (`workflow.add_node("diet", diet_agent_node)`)
2. ✅ 타입 안전성: 함수 직접 참조로 IDE 지원 완벽
3. ✅ 디버깅 용이: 호출 스택이 짧고 명확
4. ✅ LangGraph 철학 준수: Stateless 함수 기반

**메타데이터 레이어 채택 시 문제**:
1. ❌ 관리 오버헤드: `metadata.py` (200줄), `find_agents_by_capability()` 등
2. ❌ 복잡도 증가: Agent 추가 시 메타데이터도 업데이트 필요
3. ❌ 실제 효과 미미: Agent 5개 환경에서 검색 속도 개선은 5ms 미만

**결론**: **Agent 10개 이상 확장 시점에 재검토** ⏳

---

## 2. 최적화 전략

### 2.1 아키텍처 결정 매트릭스

| 기준 | 메타데이터 레이어 | 싱글톤 Registry | 현재 구조 유지 | 평가 |
|------|----------------|---------------|-------------|------|
| **간결성** | 🟡 보통 (200줄 추가) | 🔴 복잡 (300줄+) | 🟢 우수 | 현재 ↑ |
| **성능** | 🟢 우수 (5ms 절약) | 🟡 보통 | 🟢 우수 | 동일 |
| **확장성** | 🟢 우수 (10+ Agent) | 🟡 보통 | 🟡 보통 | 메타 ↑ |
| **유지보수성** | 🟡 보통 | 🔴 어려움 | 🟢 우수 | 현재 ↑ |
| **LangGraph 철학** | 🟢 준수 | 🔴 위배 | 🟢 완벽 | 현재 ↑ |
| **개발 시간** | 3일 | 5일 | 0일 | 현재 ↑ |

**종합 점수**:
- 메타데이터 레이어: 70점 (현재 시점 과잉)
- 싱글톤 Registry: 40점 (거부)
- **현재 구조 유지: 90점** (채택) ✅

### 2.2 최적화 우선순위

#### 🔴 High Priority (즉시 해결)

1. **LLM 토큰 제한 초과 수정**
   - max_tokens 설정 추가
   - 프롬프트 압축
   - State 크기 제한

2. **Tools Registry 구현**
   - `tools/__init__.py` 완성
   - 단순 Dict 방식 (싱글톤 불필요)
   - `get_tool()` 헬퍼 함수

3. **테스트 성공률 100% 달성**
   - diet 테스트 수정
   - 전체 Agent 재테스트

#### 🟡 Medium Priority (1주 이내)

4. **프롬프트 최적화**
   - Planning 프롬프트 압축
   - Intent 프롬프트 간결화
   - Aggregator 프롬프트 최적화

5. **LangGraph 성능 최적화**
   - Streaming 활성화
   - 병렬 Agent 실행 (가능한 경우)
   - Checkpointer 캐싱

6. **모니터링 추가**
   - 응답 시간 측정
   - LLM 토큰 사용량 로깅
   - 메모리 사용량 추적

#### 🟢 Low Priority (향후 검토)

7. **메타데이터 레이어 (Agent 10개+ 시)**
8. **SubGraphs 구현 (복잡한 공유 로직 발생 시)**
9. **A/B 테스트 인프라**

---

## 3. Phase별 실행 계획

### Phase 1: 긴급 수정 (1일) 🔴

**목표**: diet 테스트 성공 + Tools Registry 완성

#### Task 1.1: LLM 토큰 제한 수정 (3시간)

**파일**: `backend/app/octostrator/supervisor/main_graph.py`

**Before**:
```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=config.openai_api_key
)
```

**After**:
```python
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=4096,  # ⭐ 추가: 토큰 제한 설정
    api_key=config.openai_api_key
)
```

**파일**: `backend/app/octostrator/supervisor/cognitive_nodes.py`

**Before**:
```python
structured_llm = llm.with_structured_output(Plan)
plan_result = await structured_llm.ainvoke([
    system_message,
    human_message
])
```

**After**:
```python
structured_llm = llm.with_structured_output(
    Plan,
    max_retries=2  # ⭐ 추가: 재시도 제한
)
plan_result = await structured_llm.ainvoke(
    [system_message, human_message],
    config={"max_tokens": 2048}  # ⭐ 추가: Planning 전용 제한
)
```

**테스트**:
```bash
python test_agents_renewal.py
# diet 테스트 성공 확인
```

---

#### Task 1.2: Tools Registry 구현 (2시간)

**파일**: `backend/app/octostrator/tools/__init__.py`

**구현**:
```python
"""Fitness PT Manager Tools Registry

모든 Tool을 중앙에서 관리하는 단순 Dict 방식
- 싱글톤 불필요 (LangGraph 철학)
- import 시점에 자동 등록
- get_tool() 헬퍼 함수 제공
"""

from typing import Callable, Dict

# ===== Tool 모듈 Import =====
from .diet_tools import (
    get_meal_logs,
    save_meal_log,
    get_daily_nutrition_summary
)

from .workout_tools import (
    get_workout_history,
    save_workout_routine,
    search_exercises
)

from .schedule_tools import (
    get_user_schedules,
    create_schedule,
    update_schedule,
    cancel_schedule
)

from .member_care_tools import (
    get_member_progress,
    get_recent_activities,
    generate_progress_report
)

from .coaching_tools import (
    search_exercise_videos,
    search_nutrition_articles,
    get_coaching_tips
)


# ===== Tools Dict (단순 등록) =====

TOOLS: Dict[str, Callable] = {
    # Diet Tools
    "get_meal_logs": get_meal_logs,
    "save_meal_log": save_meal_log,
    "get_daily_nutrition_summary": get_daily_nutrition_summary,

    # Workout Tools
    "get_workout_history": get_workout_history,
    "save_workout_routine": save_workout_routine,
    "search_exercises": search_exercises,

    # Schedule Tools
    "get_user_schedules": get_user_schedules,
    "create_schedule": create_schedule,
    "update_schedule": update_schedule,
    "cancel_schedule": cancel_schedule,

    # Member Care Tools
    "get_member_progress": get_member_progress,
    "get_recent_activities": get_recent_activities,
    "generate_progress_report": generate_progress_report,

    # Coaching Tools
    "search_exercise_videos": search_exercise_videos,
    "search_nutrition_articles": search_nutrition_articles,
    "get_coaching_tips": get_coaching_tips,
}


# ===== Helper Functions =====

def get_tool(name: str) -> Callable:
    """Tool 함수 가져오기

    Args:
        name: Tool 이름

    Returns:
        Tool 함수

    Raises:
        ValueError: 존재하지 않는 Tool

    Example:
        >>> tool = get_tool("get_meal_logs")
        >>> result = tool(user_id=1, limit=5)
    """
    if name not in TOOLS:
        available = ", ".join(TOOLS.keys())
        raise ValueError(
            f"Tool '{name}' not found. Available tools: {available}"
        )
    return TOOLS[name]


def list_tools() -> list[str]:
    """사용 가능한 Tool 목록 반환

    Returns:
        Tool 이름 리스트 (알파벳 순)
    """
    return sorted(TOOLS.keys())


def list_tools_by_domain(domain: str) -> list[str]:
    """도메인별 Tool 목록 반환

    Args:
        domain: 도메인 이름 (diet, workout, schedule, member_care, coaching)

    Returns:
        해당 도메인의 Tool 목록
    """
    domain_prefixes = {
        "diet": ["get_meal", "save_meal", "get_daily"],
        "workout": ["get_workout", "save_workout", "search_exercise"],
        "schedule": ["get_user_schedule", "create_schedule", "update_schedule", "cancel_schedule"],
        "member_care": ["get_member", "get_recent", "generate_progress"],
        "coaching": ["search_exercise_video", "search_nutrition", "get_coaching"]
    }

    if domain not in domain_prefixes:
        raise ValueError(f"Unknown domain: {domain}")

    prefixes = domain_prefixes[domain]
    return [
        name for name in TOOLS.keys()
        if any(name.startswith(prefix) for prefix in prefixes)
    ]


__all__ = [
    "TOOLS",
    "get_tool",
    "list_tools",
    "list_tools_by_domain",
    # Diet Tools
    "get_meal_logs",
    "save_meal_log",
    "get_daily_nutrition_summary",
    # Workout Tools
    "get_workout_history",
    "save_workout_routine",
    "search_exercises",
    # Schedule Tools
    "get_user_schedules",
    "create_schedule",
    "update_schedule",
    "cancel_schedule",
    # Member Care Tools
    "get_member_progress",
    "get_recent_activities",
    "generate_progress_report",
    # Coaching Tools
    "search_exercise_videos",
    "search_nutrition_articles",
    "get_coaching_tips",
]
```

**사용 예시 (Agent에서)**:

**Before**:
```python
from backend.app.octostrator.tools.diet_tools import get_meal_logs, get_daily_nutrition_summary
```

**After**:
```python
from backend.app.octostrator.tools import get_tool

# Option 1: get_tool() 사용
get_meal_logs = get_tool("get_meal_logs")
meal_logs = get_meal_logs(user_id=user_id, limit=3)

# Option 2: 직접 import (기존 방식도 지원)
from backend.app.octostrator.tools import get_meal_logs
meal_logs = get_meal_logs(user_id=user_id, limit=3)
```

**장점**:
- ✅ 중앙 관리: 모든 Tool이 한 곳에 등록
- ✅ 간결함: 싱글톤 불필요, 단순 Dict
- ✅ 유연성: `get_tool()` 또는 직접 import 모두 지원
- ✅ 확장 용이: 새 Tool 추가 시 TOOLS Dict에만 추가

---

#### Task 1.3: 전체 Agent 재테스트 (1시간)

**실행**:
```bash
python test_agents_renewal.py
```

**성공 기준**:
- ✅ diet: 성공
- ✅ workout: 성공
- ✅ schedule: 성공
- ✅ coaching: 성공

**총 성공률**: 100% (4/4)

---

### Phase 2: 프롬프트 최적화 (2일) 🟡

**목표**: LLM 토큰 사용량 50% 감소, 응답 속도 25% 개선

#### Task 2.1: Planning 프롬프트 압축 (4시간)

**파일**: `backend/app/octostrator/supervisor/cognitive_prompts.py`

**현재 문제**:
- PLANNING_SYSTEM_PROMPT가 길고 verbose
- 예시가 과도하게 많음 (5개+)

**Before** (109줄):
```python
PLANNING_SYSTEM_PROMPT = """You are a planning agent for a Fitness PT Manager chatbot.
Break down the user's request into sequential tasks.

Available agents:
- diet: 식단 기록/분석 (식단 입력 분석, 영양소 계산, DB 기록, 피드백 생성)
- workout: 운동 루틴 추천 (사용자 목표/레벨 기반 운동 루틴 생성 및 제안)
...
(100+ lines)
```

**After** (30줄):
```python
PLANNING_SYSTEM_PROMPT = """Create a sequential task plan for a PT chatbot.

Agents: diet, workout, schedule, member_care, coaching

Rules:
1. Use 1-3 steps for simple requests
2. Each task: {step_id, agent, description}
3. Start step_id from 1

Examples:
- "오늘 식단" → [{"step_id": 1, "agent": "diet", "description": "식단 조회"}]
- "하체 운동 + 자세" → [
    {"step_id": 1, "agent": "workout", "description": "하체 루틴 생성"},
    {"step_id": 2, "agent": "coaching", "description": "자세 영상 검색"}
  ]
"""
```

**효과**:
- 프롬프트 토큰: 400 tokens → 120 tokens (-70%)
- 응답 속도: 0.5초 → 0.3초 (-40%)

---

#### Task 2.2: Aggregator 프롬프트 최적화 (3시간)

**파일**: `backend/app/octostrator/supervisor/response_prompts.py`

**목표**: 인사이트 생성 프롬프트 간결화

**전략**:
1. 템플릿 기반 접근 (매번 LLM 호출 X)
2. 간단한 케이스는 Rule-based
3. 복잡한 케이스만 LLM 사용

**구현**:
```python
def generate_insights_hybrid(results: list) -> str:
    """하이브리드 인사이트 생성

    - Simple (1 step): Rule-based (LLM 호출 X)
    - Complex (2+ steps): LLM 사용
    """
    if len(results) == 1:
        # Rule-based (즉시 반환)
        return format_single_result(results[0])
    else:
        # LLM 기반 (복잡한 분석)
        return await llm_generate_insights(results)
```

**효과**:
- Simple 케이스: LLM 호출 0회 → 0.5초 절약
- 전체 응답 속도: 2.0초 → 1.5초 (-25%)

---

#### Task 2.3: State 크기 제한 (2시간)

**파일**: `backend/app/octostrator/states/supervisor_state.py`

**문제**: messages가 무제한 누적 → Context 증가

**해결책**: Message 윈도우 제한

```python
from langchain_core.messages import trim_messages

def limit_messages(messages: list, max_tokens: int = 2000):
    """메시지 윈도우 제한

    최근 메시지만 유지 (max_tokens 이내)
    """
    return trim_messages(
        messages,
        max_tokens=max_tokens,
        strategy="last",  # 최근 메시지 우선
        token_counter=len  # 간단한 토큰 카운터
    )
```

**적용**:
```python
# cognitive_nodes.py

async def planning_node(state: SupervisorState, llm) -> dict:
    messages = state["messages"]

    # ⭐ 메시지 윈도우 제한
    limited_messages = limit_messages(messages, max_tokens=2000)

    # Planning 수행
    ...
```

**효과**:
- Context 토큰: 무제한 → 2,000 이하
- LLM 비용: -30%

---

### Phase 3: LangGraph 성능 최적화 (2일) 🟡

**목표**: 응답 속도 추가 개선, 병렬 처리 활성화

#### Task 3.1: Streaming 활성화 (4시간)

**현재**: 전체 응답 완료 후 반환 (ainvoke)

**개선**: Streaming으로 부분 응답 즉시 반환 (astream)

**파일**: `run_server.py` 또는 FastAPI 엔드포인트

**Before**:
```python
final_state = await graph.ainvoke(initial_state)
return final_state["final_result"]
```

**After**:
```python
async for chunk in graph.astream(initial_state):
    if "final_result" in chunk:
        yield chunk["final_result"]  # Streaming 반환
```

**효과**:
- 첫 응답 시간: 2.0초 → 0.5초 (-75%)
- 사용자 체감 속도: 크게 개선

---

#### Task 3.2: 병렬 Agent 실행 (선택적, 3시간)

**현재**: Agent가 순차적으로 실행 (executor → agent → executor → ...)

**개선**: 독립적인 Agent는 병렬 실행

**조건**: Task가 서로 독립적인 경우만 (예: 식단 조회 + 운동 조회)

**구현**:
```python
# executor_node.py

async def executor_node(state: SupervisorState) -> Command:
    plan = state["plan"]
    current_step = state["current_step"]

    # 독립적인 Task 찾기
    independent_tasks = find_independent_tasks(plan, current_step)

    if len(independent_tasks) > 1:
        # 병렬 실행 (LangGraph Send API)
        return Command(
            update={"current_step": current_step + len(independent_tasks)},
            goto=[Send(task["agent"], state) for task in independent_tasks]
        )
    else:
        # 단일 실행 (기존 방식)
        return Command(goto=plan[current_step]["agent"])
```

**효과**:
- 복합 Task 응답 시간: 3.0초 → 1.8초 (-40%)
- 적용 케이스: 20% (대부분 Task는 순차적)

---

#### Task 3.3: Checkpointer 캐싱 (2시간)

**현재**: 매 요청마다 Checkpointer 쿼리

**개선**: 세션 단위 캐싱

**구현**:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_checkpoint(thread_id: str):
    """Checkpoint 캐싱 (100개 세션)"""
    return checkpointer.get(thread_id)
```

**효과**:
- Checkpointer 조회: 50ms → 5ms (-90%)
- 전체 응답 속도: 1.5초 → 1.45초 (-3%)

---

### Phase 4: 모니터링 및 테스트 (1일) 🟢

**목표**: 성능 측정 자동화, 회귀 방지

#### Task 4.1: 성능 모니터링 추가 (3시간)

**파일**: `backend/app/octostrator/monitoring.py` (신규)

**구현**:
```python
"""Performance Monitoring

응답 시간, 토큰 사용량, 메모리 사용량 추적
"""

import time
import psutil
from typing import Dict, Any
from contextlib import contextmanager


class PerformanceMonitor:
    """성능 모니터링 클래스"""

    def __init__(self):
        self.metrics: Dict[str, list] = {
            "response_time": [],
            "llm_tokens": [],
            "memory_usage": []
        }

    @contextmanager
    def track_request(self):
        """요청 성능 추적"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        yield

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 메트릭 기록
        self.metrics["response_time"].append(end_time - start_time)
        self.metrics["memory_usage"].append(end_memory - start_memory)

    def log_llm_tokens(self, tokens: int):
        """LLM 토큰 사용량 기록"""
        self.metrics["llm_tokens"].append(tokens)

    def get_summary(self) -> Dict[str, Any]:
        """성능 요약 반환"""
        return {
            "avg_response_time": sum(self.metrics["response_time"]) / len(self.metrics["response_time"]),
            "avg_llm_tokens": sum(self.metrics["llm_tokens"]) / len(self.metrics["llm_tokens"]),
            "avg_memory_usage": sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"]),
        }


# 전역 인스턴스
monitor = PerformanceMonitor()
```

**사용**:
```python
# run_server.py

from backend.app.octostrator.monitoring import monitor

async def handle_request(request):
    with monitor.track_request():
        result = await graph.ainvoke(request)

    # 주기적으로 요약 출력
    if len(monitor.metrics["response_time"]) % 10 == 0:
        print(monitor.get_summary())

    return result
```

---

#### Task 4.2: 벤치마크 테스트 추가 (2시간)

**파일**: `tests/test_performance.py` (신규)

**구현**:
```python
"""Performance Benchmark Tests

목표 성능 기준:
- 응답 시간: 1.5초 이하
- LLM 토큰: 5,000 이하
- 메모리: 100MB 이하
"""

import pytest
from backend.app.octostrator.monitoring import monitor


@pytest.mark.asyncio
async def test_response_time_diet():
    """diet 응답 시간 테스트"""
    with monitor.track_request():
        result = await test_diet_query("오늘 식단 보여줘")

    response_time = monitor.metrics["response_time"][-1]
    assert response_time < 1.5, f"응답 시간 초과: {response_time}초"


@pytest.mark.asyncio
async def test_llm_tokens_planning():
    """Planning LLM 토큰 사용량 테스트"""
    result = await test_planning("하체 운동 추천해줘")

    tokens = monitor.metrics["llm_tokens"][-1]
    assert tokens < 5000, f"토큰 사용량 초과: {tokens} tokens"


@pytest.mark.asyncio
async def test_memory_usage():
    """메모리 사용량 테스트"""
    with monitor.track_request():
        result = await test_all_agents()

    memory = monitor.metrics["memory_usage"][-1]
    assert memory < 100, f"메모리 사용량 초과: {memory} MB"
```

**실행**:
```bash
pytest tests/test_performance.py -v
```

**효과**:
- 성능 회귀 조기 발견
- 최적화 효과 정량화

---

#### Task 4.3: 회귀 테스트 자동화 (1시간)

**GitHub Actions 설정**: `.github/workflows/performance_test.yml`

```yaml
name: Performance Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run performance tests
      run: |
        pytest tests/test_performance.py -v

    - name: Upload performance report
      uses: actions/upload-artifact@v2
      with:
        name: performance-report
        path: performance_report.html
```

---

## 4. 성과 측정

### 4.1 Phase별 목표

| Phase | 목표 | 측정 지표 | 기준 |
|-------|------|----------|------|
| **Phase 1** | 긴급 수정 | 테스트 성공률 | 100% (4/4) |
| **Phase 2** | 프롬프트 최적화 | LLM 토큰 | 5,000 이하 |
| **Phase 3** | LangGraph 최적화 | 응답 시간 | 1.5초 이하 |
| **Phase 4** | 모니터링 | 자동화 | CI/CD 통합 |

### 4.2 전체 개선 목표

**Before (현재)**:
```
테스트 성공률: 75% (3/4)
응답 시간: ~2.0초
LLM 토큰: 17,707 (초과)
Tools 접근: 수동 import
모니터링: 없음
```

**After (Phase 1-4 완료)**:
```
테스트 성공률: 100% (4/4)          ✅ +25%
응답 시간: 1.5초 이하              ✅ -25%
LLM 토큰: 5,000 이하               ✅ -72%
Tools 접근: Registry 자동          ✅ 100% 개선
모니터링: 자동 측정 + CI/CD        ✅ 신규
```

---

## 5. 향후 로드맵 (Agent 확장 시)

### 5.1 Agent 10개+ 확장 시점

**재검토 항목**:
1. **메타데이터 레이어 도입**
   - 문서 참고: `reports/registry/REGISTRY_IMPLEMENTATION_PLAN_251104.md` Phase 0
   - Capability 기반 검색
   - Priority 정렬
   - Enabled 플래그

2. **SubGraphs 구현**
   - 복잡한 공유 로직 분리
   - RAG 패턴 (검색 + 요약)

### 5.2 트리거 조건

**메타데이터 레이어 채택 기준**:
- ✅ Agent 10개 이상
- ✅ 복잡도 증가 (Agent 간 의존성 발생)
- ✅ 동적 Agent 선택 필요 (Capability 기반)

**현재 (Agent 5개)**: 조건 미충족 → 보류 ⏳

---

## 6. 리스크 및 대응

### 6.1 Phase 1 리스크

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| max_tokens 설정 후에도 토큰 초과 | 20% | 중 | 프롬프트 추가 압축 (Phase 2) |
| Tools import 에러 | 10% | 저 | 점진적 마이그레이션 (직접 import 병행) |

### 6.2 Phase 2 리스크

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| 프롬프트 압축으로 정확도 하락 | 30% | 중 | A/B 테스트로 비교 |
| Rule-based 인사이트 품질 저하 | 20% | 저 | 복잡한 케이스만 LLM 사용 |

### 6.3 Phase 3 리스크

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| Streaming 구현 복잡도 | 30% | 중 | FastAPI SSE 사용 |
| 병렬 Agent 실행 버그 | 40% | 고 | 철저한 테스트 (선택적 적용) |

---

## 7. 실행 체크리스트

### Phase 1: 긴급 수정 (1일)

- [ ] **Task 1.1**: max_tokens 설정 추가
  - [ ] main_graph.py 수정
  - [ ] cognitive_nodes.py 수정
  - [ ] diet 테스트 성공 확인

- [ ] **Task 1.2**: Tools Registry 구현
  - [ ] tools/__init__.py 작성
  - [ ] TOOLS Dict 등록
  - [ ] get_tool() 함수 구현
  - [ ] list_tools() 함수 구현

- [ ] **Task 1.3**: 전체 Agent 재테스트
  - [ ] test_agents_renewal.py 실행
  - [ ] 성공률 100% 확인

### Phase 2: 프롬프트 최적화 (2일)

- [ ] **Task 2.1**: Planning 프롬프트 압축
  - [ ] cognitive_prompts.py 수정
  - [ ] 토큰 수 측정 (400 → 120)

- [ ] **Task 2.2**: Aggregator 하이브리드 구현
  - [ ] response_prompts.py 수정
  - [ ] Rule-based 인사이트 함수 작성

- [ ] **Task 2.3**: State 크기 제한
  - [ ] supervisor_state.py 수정
  - [ ] limit_messages() 구현

### Phase 3: LangGraph 최적화 (2일)

- [ ] **Task 3.1**: Streaming 활성화
  - [ ] FastAPI 엔드포인트 수정
  - [ ] astream() 구현

- [ ] **Task 3.2**: 병렬 Agent 실행 (선택적)
  - [ ] executor_node.py 수정
  - [ ] find_independent_tasks() 구현

- [ ] **Task 3.3**: Checkpointer 캐싱
  - [ ] get_cached_checkpoint() 구현

### Phase 4: 모니터링 (1일)

- [ ] **Task 4.1**: 성능 모니터링
  - [ ] monitoring.py 작성
  - [ ] PerformanceMonitor 클래스 구현

- [ ] **Task 4.2**: 벤치마크 테스트
  - [ ] test_performance.py 작성
  - [ ] 성능 기준 설정

- [ ] **Task 4.3**: CI/CD 통합
  - [ ] GitHub Actions 설정

---

## 8. 결론

### 8.1 핵심 결정

**✅ 현재 구조 유지 + 점진적 최적화**

**이유**:
1. 현재 구조는 이미 LangGraph 철학에 완벽히 부합
2. Agent 5개 환경에서 메타데이터 레이어는 과잉
3. 싱글톤 Registry는 LangGraph 철학 위배
4. 점진적 개선이 리스크 최소화

### 8.2 예상 효과

| 지표 | Before | After | 개선 |
|------|--------|-------|------|
| 테스트 성공률 | 75% | 100% | +25% |
| 응답 시간 | 2.0초 | 1.5초 | -25% |
| LLM 토큰 | 17,707 | 5,000 | -72% |
| LLM 비용 | $0.05/쿼리 | $0.02/쿼리 | -60% |
| 첫 응답 시간 (Streaming) | 2.0초 | 0.5초 | -75% |

### 8.3 다음 단계

**즉시 실행** (이번 주):
- Phase 1: 긴급 수정 (1일)
- Phase 2: 프롬프트 최적화 (2일)

**단기 실행** (2주 이내):
- Phase 3: LangGraph 최적화 (2일)
- Phase 4: 모니터링 (1일)

**향후 검토** (Agent 10개+ 확장 시):
- 메타데이터 레이어 도입
- SubGraphs 구현

---

## 9. 참고 문서

1. [COMPREHENSIVE_ANALYSIS_REPORT_251104.md](../registry/COMPREHENSIVE_ANALYSIS_REPORT_251104.md) - 종합 분석
2. [REGISTRY_IMPLEMENTATION_PLAN_251104.md](../registry/REGISTRY_IMPLEMENTATION_PLAN_251104.md) - 메타데이터 레이어 참고
3. [REFERENCE_COMPARISON_251104.md](../registry/REFERENCE_COMPARISON_251104.md) - 레퍼런스 비교

---

**문서 작성**: Claude (AI Assistant)
**검토 필요**: 개발팀, 아키텍트
**다음 단계**: Phase 1 Task 1.1 시작

---

**문서 끝**
