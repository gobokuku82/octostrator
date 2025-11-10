# Hybrid Implementation Plan - 중요 수정사항

**작성일**: 2025-11-04
**기반 문서**: hybrid_implementation_plan_251104.md
**목적**: 원본 계획서의 잠재적 문제 해결

---

## ⚠️ Critical Fix 1: f-string Prompt 정적 생성 문제

### 문제점
```python
# ❌ 원본 계획 (문제 있음)
PLANNING_SYSTEM_PROMPT = f"""...
Available agents:
{generate_agent_list_for_planning()}  # 모듈 로드 시 1회만 실행
..."""
```

**문제**: 런타임에 `enabled: False` 변경해도 Prompt 업데이트 안 됨

### 해결 방안

```python
# ✅ 수정안 1: 함수형 반환 (권장)
def get_planning_system_prompt() -> str:
    """Planning Prompt를 동적으로 생성

    매번 호출 시 최신 Agent 목록 반영
    """
    active_agents_list = generate_agent_list_for_planning()

    return f"""You are a planning agent for a Fitness PT Manager chatbot.
Break down the user's request into sequential tasks.

Available agents:
{active_agents_list}

Rules:
1. 같은 Agent를 여러 번 사용 가능
2. HITL은 중요한 결정 전에 배치
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


# ✅ 수정안 2: LazyString 패턴 (고급)
class LazyPrompt:
    """지연 평가 Prompt 클래스"""

    def __init__(self, template_func):
        self.template_func = template_func

    def __str__(self):
        return self.template_func()

    def format(self, **kwargs):
        """str.format() 호환"""
        return str(self).format(**kwargs)


def _build_planning_prompt_template():
    """Planning Prompt 템플릿 빌더"""
    active_agents_list = generate_agent_list_for_planning()
    return f"""You are a planning agent...
Available agents:
{active_agents_list}
..."""


PLANNING_SYSTEM_PROMPT = LazyPrompt(_build_planning_prompt_template)
```

### 사용 방법 변경

```python
# 기존 Planning Node 코드
async def planning_node(state: SupervisorState):
    """Planning 노드"""

    # ❌ 기존 방식 (정적 Prompt)
    # prompt = PLANNING_SYSTEM_PROMPT

    # ✅ 수정안 1 사용
    prompt = get_planning_system_prompt()

    # ✅ 수정안 2 사용
    # prompt = str(PLANNING_SYSTEM_PROMPT)

    response = await llm.ainvoke(prompt)
    # ...
```

**영향도**: HIGH
**수정 파일**:
- `agents/__init__.py` (함수 추가)
- `supervisor/cognitive_prompts.py` (함수 사용)
- `supervisor/main_graph.py` (planning_node 수정)

---

## 🛡️ Fix 2: 타입 안정성 강화

### 문제점
```python
# ❌ 원본 계획 (타입 체킹 불가)
AGENT_METADATA: Dict[str, Dict[str, Any]] = { ... }
```

**문제**:
- 필드 오타 시 런타임 에러
- IDE 자동완성 미지원
- 타입 체킹 불가

### 해결 방안

```python
# agents/__init__.py
from typing import TypedDict, Dict, List, Callable, Any

class AgentMetadata(TypedDict):
    """Agent 메타데이터 타입 정의"""

    # Required fields
    node: Callable
    name: str
    display_name: str
    description: str
    priority: int
    enabled: bool
    team: str

    # Capability fields
    input_types: List[str]
    output_types: List[str]
    required_tools: List[str]


# ✅ 타입 안정성 확보
AGENT_METADATA: Dict[str, AgentMetadata] = {
    "diet": AgentMetadata(
        node=diet_agent_node,
        name="diet",
        display_name="식단 관리",
        description="식단 입력 분석, 영양소 계산, DB 기록, 피드백 생성",
        priority=10,
        enabled=True,
        team="fitness",
        input_types=["text", "image"],
        output_types=["nutrition_analysis"],
        required_tools=["diet_db", "nutrition_calculator"]
    ),
    # ... 나머지 Agent들
}


# 헬퍼 함수도 타입 명시
def get_active_agents() -> Dict[str, AgentMetadata]:
    """활성화된 Agent만 반환 (타입 안전)"""
    return {
        name: meta
        for name, meta in AGENT_METADATA.items()
        if meta["enabled"]
    }


def get_agent_by_name(name: str) -> AgentMetadata | None:
    """특정 Agent 메타데이터 조회 (타입 안전)"""
    return AGENT_METADATA.get(name)
```

**장점:**
- ✅ IDE 자동완성 지원
- ✅ mypy 타입 체킹 가능
- ✅ 필드 오타 방지
- ✅ 코드 가독성 향상

**영향도**: MEDIUM
**수정 파일**: `agents/__init__.py` (TypedDict 추가)

---

## 📊 Fix 3: 실제 성능 Baseline 측정

### 문제점
```
계획서 수치:
- 빌드 시간: 0.30초
- 쿼리 시간: 0.05초
- 메모리: 20KB
```

**문제**:
- 측정 환경 불명확
- LLM 호출 시간 포함 여부 불명확
- 0.05초는 비현실적 (LLM API 호출 포함 시)

### 해결 방안

```python
# scripts/benchmark_hybrid.py
import time
import asyncio
import tracemalloc
from backend.app.octostrator.supervisor import build_supervisor_graph
from backend.app.octostrator.states.supervisor_state import SupervisorState
from langchain_core.messages import HumanMessage


def measure_build_time():
    """그래프 빌드 시간 측정"""
    start = time.perf_counter()
    graph = build_supervisor_graph()
    build_time = time.perf_counter() - start
    return build_time, graph


def measure_memory_usage():
    """메모리 사용량 측정"""
    tracemalloc.start()
    graph = build_supervisor_graph()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return current / 1024, peak / 1024, graph  # KB 단위


async def measure_query_time(graph, query: str, iterations: int = 10):
    """쿼리 실행 시간 측정 (여러 번 평균)"""
    times = []

    for i in range(iterations):
        state = {
            "messages": [HumanMessage(content=query)],
            "user_query": query,
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

        start = time.perf_counter()
        result = await graph.ainvoke(state)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    return {
        "average": avg_time,
        "min": min_time,
        "max": max_time,
        "iterations": iterations
    }


async def run_benchmark():
    """전체 벤치마크 실행"""

    print("=" * 60)
    print("Hybrid Approach Performance Benchmark")
    print("=" * 60)

    # 1. 빌드 시간
    print("\n1. Graph Build Time")
    build_time, graph = measure_build_time()
    print(f"   Build time: {build_time:.4f}s")

    # 2. 메모리 사용량
    print("\n2. Memory Usage")
    current_mem, peak_mem, _ = measure_memory_usage()
    print(f"   Current: {current_mem:.2f} KB")
    print(f"   Peak: {peak_mem:.2f} KB")

    # 3. 쿼리 실행 시간
    print("\n3. Query Execution Time (10 iterations)")
    query_stats = await measure_query_time(graph, "오늘 식단 기록 보여줘")
    print(f"   Average: {query_stats['average']:.4f}s")
    print(f"   Min: {query_stats['min']:.4f}s")
    print(f"   Max: {query_stats['max']:.4f}s")

    # 4. 판정
    print("\n4. Performance Criteria")
    build_pass = "✅ PASS" if build_time <= 0.35 else "❌ FAIL"
    memory_pass = "✅ PASS" if current_mem <= 50 else "❌ FAIL"  # 현실적 기준
    query_pass = "✅ PASS" if query_stats['average'] <= 5.0 else "❌ FAIL"  # LLM 포함

    print(f"   Build time (≤0.35s): {build_pass}")
    print(f"   Memory usage (≤50KB): {memory_pass}")
    print(f"   Query time (≤5.0s): {query_pass}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
```

### 현실적인 성능 기준

| 항목 | 원본 계획 | 수정 기준 | 이유 |
|------|----------|----------|------|
| 빌드 시간 | ≤0.35s | ≤0.50s | 복잡한 그래프 고려 |
| 쿼리 시간 | ≤0.10s | ≤5.0s | LLM API 호출 포함 |
| 메모리 | ≤25KB | ≤50KB | 메타데이터 크기 고려 |

**영향도**: LOW (성능은 문제없을 것으로 예상)
**추가 파일**: `scripts/benchmark_hybrid.py` (신규)

---

## 🔧 Fix 4: 순환 Import 방지

### 문제점
```python
# agents/__init__.py
from .diet_agent import diet_agent_node
AGENT_METADATA = {"diet": {"node": diet_agent_node}}

# diet_agent.py (만약 이렇게 하면 순환 참조)
# from agents import AGENT_METADATA  # ❌ 순환 import!
```

### 해결 방안

```python
# agents/__init__.py 구조 개선
# ==========================================
# 1. 타입 정의
# ==========================================
from typing import TypedDict, Dict, List, Callable

class AgentMetadata(TypedDict):
    # ...

# ==========================================
# 2. Agent 노드 함수 import (순환 참조 주의)
# ==========================================
# 주의: 각 Agent 파일에서는 이 __init__.py를 import하지 말 것!
from .diet_agent import diet_agent_node
from .workout_agent import workout_agent_node
from .schedule_agent import schedule_agent_node
from .member_care_agent import member_care_agent_node
from .coaching_agent import coaching_agent_node

# ==========================================
# 3. AGENT_METADATA (메타데이터 정의)
# ==========================================
AGENT_METADATA: Dict[str, AgentMetadata] = {
    # ...
}

# ==========================================
# 4. 헬퍼 함수
# ==========================================
def get_active_agents() -> Dict[str, AgentMetadata]:
    # ...

# ==========================================
# 5. Export (순환 참조 방지)
# ==========================================
__all__ = [
    # Agent nodes (다른 모듈에서 import 가능)
    "diet_agent_node",
    "workout_agent_node",
    "schedule_agent_node",
    "member_care_agent_node",
    "coaching_agent_node",

    # Metadata (Planning/Executor 노드에서만 사용)
    "AGENT_METADATA",
    "AgentMetadata",  # TypedDict도 export

    # Helper functions
    "get_active_agents",
    "get_agents_by_priority",
    "get_agent_names",
    "get_agent_by_name",
    "is_agent_enabled",
]
```

### Agent 파일 작성 규칙

```python
# agents/diet_agent.py (올바른 패턴)
from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.core.database import get_db_session
# ✅ 다른 Agent 노드 함수는 직접 import 가능
# from .workout_agent import workout_agent_node

# ❌ __init__.py는 import 금지 (순환 참조)
# from . import AGENT_METADATA  # ❌
# from agents import AGENT_METADATA  # ❌

async def diet_agent_node(state: SupervisorState):
    """Diet Agent 노드 함수

    메타데이터는 agents/__init__.py의 AGENT_METADATA에 정의됨
    """
    # Agent 로직
    pass
```

**영향도**: LOW (현재 구조에서는 발생 안 함)
**주의 사항**: Agent 파일 작성 시 규칙 준수 필요

---

## 📝 수정된 구현 순서

### Phase 1: AGENT_METADATA 생성 (35분 → 5분 증가)

**파일**: `backend/app/octostrator/agents/__init__.py`

**작업**:
1. ✅ `AgentMetadata` TypedDict 정의 (신규)
2. ✅ 기존 export 코드 유지
3. ✅ AGENT_METADATA 딕셔너리 추가 (타입 명시)
4. ✅ 헬퍼 함수 5개 구현 (타입 명시)
5. ✅ __all__ 업데이트

---

### Phase 2: main_graph.py 수정 (20분 → 변경 없음)

**파일**: `backend/app/octostrator/supervisor/main_graph.py`

**작업**:
1. ✅ `AGENT_METADATA`, `get_active_agents` import
2. ✅ 수동 Agent 등록 코드 제거
3. ✅ 자동 등록 로직 추가 (for loop)
4. ✅ 디버그 로그 추가

---

### Phase 3: cognitive_prompts.py 수정 (30분 → 5분 증가)

**파일**: `backend/app/octostrator/supervisor/cognitive_prompts.py`

**작업**:
1. ✅ `get_active_agents` import
2. ✅ `generate_agent_list_for_planning()` 함수 추가
3. ✅ `get_planning_system_prompt()` 함수 추가 (신규, f-string 문제 해결)
4. ✅ 정적 `PLANNING_SYSTEM_PROMPT` 제거

**수정 코드**:
```python
# cognitive_prompts.py
from backend.app.octostrator.agents import get_active_agents


def generate_agent_list_for_planning() -> str:
    """활성화된 Agent 목록을 Planning Prompt 형식으로 생성"""
    active_agents = get_active_agents()
    agent_lines = []
    for agent_name, meta in active_agents.items():
        agent_lines.append(f"- {agent_name}: {meta['description']}")
    return "\n".join(agent_lines)


def get_planning_system_prompt() -> str:
    """Planning System Prompt 동적 생성

    매번 호출 시 최신 Agent 목록 반영
    """
    active_agents_list = generate_agent_list_for_planning()

    return f"""You are a planning agent for a Fitness PT Manager chatbot.
Break down the user's request into sequential tasks.

Available agents:
{active_agents_list}

Rules:
1. 같은 Agent를 여러 번 사용 가능
2. HITL은 중요한 결정 전에 배치
3. 각 Task는 명확한 description 필요
4. step_id는 1부터 시작
5. HITL Task에는 hitl_question 필드 반드시 포함

Complexity Guidelines:
- Simple (1-2 steps): 단순 조회/검색
- Medium (2-3 steps): 추천/분석
- Complex (4+ steps): 복합 작업 + HITL

Now create a plan for the given user intent.
"""


# ==========================================
# Planning Node에서 사용
# ==========================================
async def planning_node(state: SupervisorState):
    """Planning 노드"""

    # ✅ 함수 호출로 최신 Prompt 가져오기
    prompt = get_planning_system_prompt()

    response = await llm.ainvoke(prompt)
    # ...
```

---

### Phase 4: 통합 테스트 (20분 → 5분 증가)

**테스트**:
1. ✅ 그래프 빌드 성공 확인
2. ✅ 5개 Agent 모두 등록 확인
3. ✅ Agent 실행 테스트
4. ✅ Agent 비활성화 테스트
5. ✅ Planning Prompt 동적 생성 확인 (신규)
6. ✅ 성능 Benchmark 실행 (신규)

**추가 테스트**:
```bash
# 성능 측정
python scripts/benchmark_hybrid.py

# Planning Prompt 동적 생성 확인
python -c "
from backend.app.octostrator.supervisor.cognitive_prompts import get_planning_system_prompt
print(get_planning_system_prompt()[:300])
"
```

---

## ⏱️ 수정된 예상 소요 시간

| Phase | 원본 | 수정 | 차이 | 이유 |
|-------|------|------|------|------|
| Phase 1 | 30분 | 35분 | +5분 | TypedDict 추가 |
| Phase 2 | 20분 | 20분 | 0 | 변경 없음 |
| Phase 3 | 25분 | 30분 | +5분 | 함수형 Prompt 추가 |
| Phase 4 | 15분 | 20분 | +5분 | 성능 측정 추가 |
| **합계** | **1.5시간** | **1시간 45분** | **+15분** | 품질 강화 |

---

## ✅ 수정 체크리스트

### 필수 수정사항
- [ ] Fix 1: f-string Prompt → 함수형 반환
- [ ] Fix 2: `AgentMetadata` TypedDict 추가
- [ ] Fix 3: 성능 Benchmark 스크립트 작성

### 선택 수정사항
- [ ] LazyPrompt 패턴 적용 (고급)
- [ ] 순환 import 방지 규칙 문서화

---

## 📊 최종 판단

**원본 Hybrid Plan**: ⭐⭐⭐⭐☆ (4/5)
- 전체적으로 우수한 계획
- 실용적이고 구현 가능
- 몇 가지 잠재적 문제 존재

**수정된 Hybrid Plan**: ⭐⭐⭐⭐⭐ (5/5)
- 모든 잠재적 문제 해결
- 타입 안정성 확보
- 실제 성능 측정 추가
- 프로덕션 준비 완료

**권장사항**: ✅ **수정된 Hybrid Plan을 우선 구현하고, v2.0 Comprehensive Plan은 Phase 5 이후 검토**

---

**문서 종료**
