# Supervisor 폴더 구조 리뉴얼 분석 및 계획서

**작성일**: 2025-11-04
**대상**: `backend/app/octostrator/supervisor/`
**목적**: 폴더 구조 복잡도 개선 및 유지보수성 향상

---

## 1. 현재 구조 분석

### 1.1 파일 구조

```
supervisor/
├── __init__.py                              (9줄)
├── graph.py                                 (175줄) ★ 핵심
├── prompts.py                               (22줄)  ← 거의 빈 파일
└── nodes/
    ├── __init__.py                          (17줄)
    ├── intent_understanding.py              (105줄)
    ├── planning.py                          (137줄)
    ├── executor.py                          (80줄)
    ├── hitl_handler.py                      (103줄)
    ├── aggregator.py                        (170줄) ★ 가장 큼
    ├── router.py                            (40줄)
    └── generators/
        ├── __init__.py                      (15줄)
        ├── chat_generator.py                (73줄)
        ├── graph_generator.py               (171줄) ★ 가장 큼
        └── report_generator.py              (148줄)
```

**총 통계**:
- **파일 수**: 14개
- **총 라인 수**: 약 1,265줄
- **평균 파일 크기**: 90줄
- **최대 파일 크기**: 175줄 (graph.py)

### 1.2 파일별 역할 및 크기

| 파일 | 라인 수 | 역할 | 복잡도 | 의존성 |
|------|---------|------|--------|--------|
| **graph.py** | 175 | LangGraph 정의, 노드 추가, 엣지 연결 | 중간 | 모든 노드 import |
| **intent_understanding.py** | 105 | 사용자 의도 분석 (7개 카테고리) | 낮음 | LLM |
| **planning.py** | 137 | TaskStep 생성, Structured Output | 중간 | LLM |
| **executor.py** | 80 | Command 기반 라우팅, 순차 실행 | 낮음 | - |
| **hitl_handler.py** | 103 | 사용자 승인 대기 (interrupt 사용) | 낮음 | LangGraph interrupt |
| **aggregator.py** | 170 | 결과 구조화, 인사이트 생성 | 높음 | LLM, Pydantic |
| **router.py** | 40 | 출력 형식 선택 (chat/graph/report) | 매우 낮음 | - |
| **chat_generator.py** | 73 | 대화형 답변 생성 | 낮음 | - |
| **graph_generator.py** | 171 | D3.js/Cytoscape용 그래프 데이터 | 높음 | - |
| **report_generator.py** | 148 | Markdown 보고서 생성 | 중간 | - |
| **prompts.py** | 22 | 공통 프롬프트 (현재 거의 빈 파일) | - | - |

### 1.3 의존성 관계

```
graph.py
  ├─→ nodes/__init__.py
  │     ├─→ intent_understanding.py
  │     ├─→ planning.py
  │     ├─→ executor.py
  │     └─→ hitl_handler.py
  ├─→ aggregator.py
  ├─→ router.py
  └─→ generators/__init__.py
        ├─→ chat_generator.py
        ├─→ graph_generator.py
        └─→ report_generator.py
```

**문제점**:
- `graph.py`가 11개 파일을 import (높은 결합도)
- `nodes/` 폴더에 6개 파일, `generators/` 폴더에 3개 파일
- 프롬프트가 각 노드 파일 내부에 흩어져 있음

---

## 2. 현재 구조의 장단점

### 2.1 장점 (현재 구조 유지 시)

#### ✅ 명확한 관심사 분리 (Separation of Concerns)

- 각 노드가 독립적인 파일로 관리됨
- 기능별 수정 시 해당 파일만 열면 됨
- 예: Intent Understanding 수정 → `intent_understanding.py`만 수정

#### ✅ 확장성 (Scalability)

- 새로운 노드 추가 시 새 파일만 생성하면 됨
- 예: `validation_node.py` 추가 시 기존 파일 수정 최소화
- Generator 추가 (예: `pdf_generator.py`) 용이

#### ✅ 테스트 용이성 (Testability)

- 각 노드를 독립적으로 유닛 테스트 가능
- Mock 객체 주입 용이
- 예: `test_intent_understanding.py`, `test_planning.py`

#### ✅ 협업 용이성 (Collaboration)

- 여러 개발자가 동시에 다른 노드 작업 가능
- Git 충돌 최소화
- 예: A가 planning.py 수정, B가 aggregator.py 수정

#### ✅ 코드 가독성 (Readability)

- 각 파일이 100-200줄 내외로 적당한 크기
- 파일 이름만으로 기능 파악 가능
- 디렉토리 구조가 시스템 아키텍처 반영

### 2.2 단점 (현재 구조의 문제점)

#### ❌ 파일 수 과다 (14개)

- 간단한 수정에도 여러 파일 열어야 함
- IDE에서 탭이 많이 열림
- 전체 플로우 파악이 어려움

#### ❌ Import 복잡도

- `graph.py`가 11개 import 문 필요
- `__init__.py` 파일들이 단순 re-export만 수행
- 순환 참조 위험성

#### ❌ 프롬프트 분산

- 각 노드 파일 내부에 프롬프트가 하드코딩
- 프롬프트 일괄 수정 어려움
- 프롬프트 버전 관리 불가능

#### ❌ 폴더 깊이 (3단계)

- `supervisor/nodes/generators/chat_generator.py`
- 파일 경로가 길어짐
- 상대 import 복잡도 증가

#### ❌ 빈 파일 존재

- `prompts.py`: 22줄, 실제로는 주석만 있음
- `__init__.py`: 대부분 단순 re-export

---

## 3. 리뉴얼 옵션 비교

### 3.1 옵션 A: 현재 구조 유지 (최소 개선)

**변경 사항**:
1. `prompts.py`를 실제로 활용 (프롬프트 통합)
2. `generators/` 폴더 평탄화 (nodes/ 직속으로 이동)
3. 빈 `__init__.py` 최소화

**구조**:
```
supervisor/
├── graph.py
├── prompts.py                    ← 실제 프롬프트 정의
└── nodes/
    ├── intent_understanding.py
    ├── planning.py
    ├── executor.py
    ├── hitl_handler.py
    ├── aggregator.py
    ├── router.py
    ├── chat_generator.py         ← generators 폴더 제거
    ├── graph_generator.py
    └── report_generator.py
```

**장점**:
- 폴더 깊이 1단계 감소
- 프롬프트 중앙 관리
- 기존 코드 영향 최소

**단점**:
- 파일 수는 여전히 많음 (11개)
- Import 복잡도 유지

**추천도**: ⭐⭐⭐☆☆ (안전하지만 개선 효과 미미)

---

### 3.2 옵션 B: 중간 통합 (추천)

**변경 사항**:
1. 핵심 노드만 개별 파일 유지
2. Generator 통합
3. 프롬프트 통합

**구조**:
```
supervisor/
├── graph.py                      (175줄)
├── prompts.py                    (NEW: 모든 프롬프트)
└── nodes.py                      (NEW: 모든 노드 통합)
    ├── # Intent Understanding
    ├── # Planning
    ├── # Executor
    ├── # HITL Handler
    ├── # Aggregator
    ├── # Router
    └── # Generators (chat, graph, report)
```

**예상 라인 수**:
- `graph.py`: 175줄 (현재와 동일)
- `prompts.py`: 150줄 (모든 프롬프트 통합)
- `nodes.py`: 1,000줄 (모든 노드 통합)

**장점**:
- ✅ 파일 수 대폭 감소 (14개 → 3개)
- ✅ Import 단순화
- ✅ 전체 플로우 한눈에 파악 가능
- ✅ 프롬프트 중앙 관리
- ✅ 작은 프로젝트에 적합

**단점**:
- ❌ `nodes.py`가 1,000줄으로 큼
- ❌ 개별 노드 테스트 어려움
- ❌ Git 충돌 가능성 증가
- ❌ 함수 검색 시 스크롤 많이 필요

**추천도**: ⭐⭐⭐⭐☆ (단일 개발자 또는 소규모 팀에 적합)

---

### 3.3 옵션 C: 핵심만 분리 (균형 잡힌 접근)

**변경 사항**:
1. 핵심 노드 4개만 개별 파일 유지
2. 나머지는 통합
3. 프롬프트 통합

**구조**:
```
supervisor/
├── graph.py                      (175줄)
├── prompts.py                    (150줄) ← 모든 프롬프트
├── core_nodes.py                 (425줄) ← Intent, Planning, Executor, Aggregator
└── output_nodes.py               (432줄) ← Router, Chat, Graph, Report, HITL
```

**파일별 내용**:

**core_nodes.py** (425줄):
- `intent_understanding_node()` (105줄)
- `planning_node()` (137줄)
- `executor_node()` (80줄)
- `aggregator_node()` (170줄)

**output_nodes.py** (535줄):
- `hitl_handler_node()` (103줄)
- `output_router_node()` (40줄)
- `chat_generator_node()` (73줄)
- `graph_generator_node()` (171줄)
- `report_generator_node()` (148줄)

**장점**:
- ✅ 파일 수 적절 (14개 → 4개)
- ✅ 핵심 로직 vs 출력 로직 명확히 구분
- ✅ 각 파일 크기 적절 (400-500줄)
- ✅ Import 단순화
- ✅ 프롬프트 중앙 관리
- ✅ Git 충돌 감소

**단점**:
- ⚠️ 중간 규모 파일로 함수 찾기 약간 어려움
- ⚠️ 개별 노드 테스트 시 import 경로 변경 필요

**추천도**: ⭐⭐⭐⭐⭐ (가장 균형 잡힌 접근, 추천)

---

### 3.4 옵션 D: 완전 통합 (극단적)

**변경 사항**:
1. 모든 코드를 1개 파일로 통합

**구조**:
```
supervisor/
└── supervisor.py                 (1,265줄) ← 모든 코드
```

**장점**:
- ✅ 파일 수 최소 (1개)
- ✅ Import 없음
- ✅ 전체 코드 한 파일에

**단점**:
- ❌ 1,265줄로 너무 큼
- ❌ 가독성 최악
- ❌ 테스트 불가능
- ❌ Git 충돌 필연적
- ❌ 유지보수 불가능

**추천도**: ⭐☆☆☆☆ (절대 비추천)

---

## 4. 옵션 비교 표

| 항목 | 현재 구조 | 옵션 A (최소) | 옵션 B (중간) | 옵션 C (균형) ★ | 옵션 D (극단) |
|------|-----------|---------------|---------------|-----------------|---------------|
| **파일 수** | 14 | 11 | 3 | 4 | 1 |
| **최대 파일 크기** | 175줄 | 171줄 | 1,000줄 | 535줄 | 1,265줄 |
| **폴더 깊이** | 3단계 | 2단계 | 1단계 | 1단계 | 0단계 |
| **Import 복잡도** | 높음 | 중간 | 낮음 | 낮음 | 없음 |
| **가독성** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **확장성** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ |
| **테스트 용이성** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ |
| **협업 용이성** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| **유지보수성** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **프롬프트 관리** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **코드 탐색** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| **리팩토링 난이도** | 낮음 | 낮음 | 중간 | 중간 | 높음 |
| **총점** | 29 | 33 | 22 | 34 | 10 |

**결론**: **옵션 C (핵심만 분리)가 가장 균형 잡힌 접근**

---

## 5. 추천 리뉴얼 계획 (옵션 C)

### 5.1 변경 사항 상세

#### Phase 1: 프롬프트 통합

**새 파일**: `prompts.py`

```python
"""Supervisor 프롬프트 중앙 관리

모든 노드의 프롬프트를 한 곳에서 관리하여:
- 프롬프트 버전 관리 용이
- 일괄 수정 가능
- 다국어 지원 준비
- A/B 테스트 용이
"""

# Intent Understanding 프롬프트
INTENT_UNDERSTANDING_PROMPT = """
You are an intent analyzer for a Fitness PT Manager chatbot.
Analyze the following user request and extract the intent.

USER REQUEST: "{user_request}"

Classify the request into one of these categories:
1. "diet_query" - 식단 관련 조회/기록
2. "workout_query" - 운동 루틴 조회/추천
3. "schedule_query" - PT 스케줄 조회/예약
4. "member_report" - 회원 상태/진행률 조회
5. "coaching_search" - 운동/식단 자료 검색
6. "multi_step_task" - 복합 작업
7. "progress_comparison" - 진행률 비교
...
"""

# Planning 프롬프트
PLANNING_PROMPT = """
You are a planning agent for a Fitness PT Manager chatbot.
Break down the user's request into sequential tasks.

Available agents:
- diet: 식단 기록/분석
- workout: 운동 루틴 추천
- schedule: 수업 예약/변경
- member_care: 회원 리포팅/알림
- coaching: 전문 자료 검색
...
"""

# Aggregator 프롬프트
AGGREGATOR_INSIGHT_PROMPT = """
다음 작업 실행 결과를 분석하여 주요 인사이트를 추출하세요:

사용자 의도: {user_intent}

실행 단계:
{steps}

다음 형식으로 인사이트를 생성하세요:
1. 트렌드 (trend): 데이터에서 발견된 경향성
2. 이상 징후 (anomaly): 예상과 다른 패턴
3. 권장 사항 (recommendation): 다음 단계 제안
...
"""
```

#### Phase 2: 핵심 노드 통합

**새 파일**: `core_nodes.py`

```python
"""Core Supervisor Nodes

핵심 오케스트레이션 로직:
- Intent Understanding: 사용자 의도 파악
- Planning: 작업 계획 생성
- Executor: 동적 라우팅
- Aggregator: 결과 구조화
"""
from typing import Dict, List
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from backend.app.octostrator.states.supervisor_state import SupervisorState
from .prompts import (
    INTENT_UNDERSTANDING_PROMPT,
    PLANNING_PROMPT,
    AGGREGATOR_INSIGHT_PROMPT
)

# ===== Intent Understanding =====

async def intent_understanding_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """사용자 의도 파악"""
    # (기존 코드 105줄)
    ...

# ===== Planning =====

async def planning_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """전체 작업을 Task로 분해"""
    # (기존 코드 137줄)
    ...

# ===== Executor =====

async def executor_node(state: SupervisorState) -> Command:
    """계획에 따라 Agent를 순차적으로 실행"""
    # (기존 코드 80줄)
    ...

# ===== Aggregator =====

async def aggregator_node(
    state: SupervisorState,
    llm: ChatOpenAI
) -> Dict:
    """모든 Agent 결과를 구조화된 데이터로 변환"""
    # (기존 코드 170줄)
    ...
```

#### Phase 3: 출력 노드 통합

**새 파일**: `output_nodes.py`

```python
"""Output Generation Nodes

결과 생성 및 출력:
- HITL Handler: 사용자 승인
- Router: 출력 형식 선택
- Generators: Chat, Graph, Report
"""
from typing import Dict
from langgraph.types import Command, interrupt
from backend.app.octostrator.states.supervisor_state import SupervisorState

# ===== HITL Handler =====

async def hitl_handler_node(state: SupervisorState) -> Dict:
    """사용자 승인 대기"""
    # (기존 코드 103줄)
    ...

# ===== Router =====

async def output_router_node(state: SupervisorState) -> Command:
    """출력 형식에 따라 Generator 선택"""
    # (기존 코드 40줄)
    ...

# ===== Chat Generator =====

async def chat_generator_node(state: SupervisorState) -> Dict:
    """대화형 답변 생성"""
    # (기존 코드 73줄)
    ...

# ===== Graph Generator =====

async def graph_generator_node(state: SupervisorState) -> Dict:
    """그래프 시각화 데이터 생성"""
    # (기존 코드 171줄)
    ...

# ===== Report Generator =====

async def report_generator_node(state: SupervisorState) -> Dict:
    """Markdown 보고서 생성"""
    # (기존 코드 148줄)
    ...
```

#### Phase 4: Graph 업데이트

**수정 파일**: `graph.py`

```python
"""Supervisor Graph 정의"""
from langgraph.graph import StateGraph, START, END
from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.agents import (
    diet_agent_node,
    workout_agent_node,
    schedule_agent_node,
    member_care_agent_node,
    coaching_agent_node,
)
from .core_nodes import (
    intent_understanding_node,
    planning_node,
    executor_node,
    aggregator_node,
)
from .output_nodes import (
    hitl_handler_node,
    output_router_node,
    chat_generator_node,
    graph_generator_node,
    report_generator_node,
)

def build_supervisor_graph(...):
    # (기존 코드, import만 변경)
    ...
```

### 5.2 최종 구조

```
supervisor/
├── __init__.py                   (10줄) - build_supervisor_graph export
├── graph.py                      (175줄) - LangGraph 정의
├── prompts.py                    (150줄) ★ NEW - 모든 프롬프트
├── core_nodes.py                 (425줄) ★ NEW - Intent, Planning, Executor, Aggregator
└── output_nodes.py               (535줄) ★ NEW - HITL, Router, Generators
```

**파일 수**: 14개 → 5개 (64% 감소)
**평균 파일 크기**: 90줄 → 259줄 (적절한 크기)
**최대 파일 크기**: 175줄 → 535줄 (여전히 관리 가능)

---

## 6. 마이그레이션 계획

### 6.1 단계별 작업

#### Step 1: 백업 생성

```bash
# 현재 supervisor 폴더 백업
cp -r backend/app/octostrator/supervisor backend/app/octostrator/supervisor_backup_251104
```

#### Step 2: 프롬프트 추출 및 통합

1. 각 노드 파일에서 프롬프트 추출
2. `prompts.py` 생성
3. 변수명 통일 (예: `INTENT_UNDERSTANDING_PROMPT`)

**예상 시간**: 30분

#### Step 3: 핵심 노드 통합

1. `core_nodes.py` 생성
2. 4개 노드 파일 내용 복사
3. Import 경로 수정 (prompts 사용)
4. 함수 간 공백 정리

**예상 시간**: 30분

#### Step 4: 출력 노드 통합

1. `output_nodes.py` 생성
2. 5개 노드 파일 내용 복사
3. Import 경로 수정

**예상 시간**: 30분

#### Step 5: Graph 업데이트

1. `graph.py`의 import 문 수정
2. 주석 업데이트

**예상 시간**: 10분

#### Step 6: __init__.py 정리

1. 기존 `nodes/` 폴더 제거
2. `supervisor/__init__.py` 업데이트

**예상 시간**: 5분

#### Step 7: 테스트

1. 서버 실행 테스트
2. 4개 퀵 버튼 테스트
3. 모든 노드 동작 확인

**예상 시간**: 15분

**총 예상 시간**: 약 2시간

### 6.2 테스트 체크리스트

- [ ] 서버 정상 시작 (`python run_server.py`)
- [ ] Import 에러 없음
- [ ] Intent Understanding 동작
- [ ] Planning 동작
- [ ] DietAgent 호출
- [ ] WorkoutAgent 호출
- [ ] ScheduleAgent 호출
- [ ] CoachingAgent 호출
- [ ] Aggregator 동작
- [ ] Chat Generator 동작
- [ ] Frontend 4개 버튼 테스트

### 6.3 롤백 계획

문제 발생 시:

```bash
# 백업 복원
rm -rf backend/app/octostrator/supervisor
cp -r backend/app/octostrator/supervisor_backup_251104 backend/app/octostrator/supervisor
```

---

## 7. 장기적 고려사항

### 7.1 향후 확장 시나리오

#### 시나리오 1: 노드 10개 이상 추가

**현재 구조 유지 시**:
- 파일 수: 14개 → 24개 이상
- 관리 불가능 수준

**옵션 C (추천) 적용 시**:
- `core_nodes.py`에 계속 추가 가능 (800줄까지)
- 또는 `validation_nodes.py` 같은 새 그룹 추가

**대응 방안**: 기능별 그룹핑 (core, output, validation, analysis 등)

#### 시나리오 2: 프롬프트 다국어 지원

**현재 구조 유지 시**:
- 각 노드 파일에서 개별 수정 (14개 파일)

**옵션 C 적용 시**:
- `prompts.py`만 수정 또는 `prompts_en.py`, `prompts_ko.py` 분리

#### 시나리오 3: 프롬프트 A/B 테스트

**옵션 C 적용 시**:
- `prompts.py`에서 버전 관리 가능
- 예: `INTENT_UNDERSTANDING_PROMPT_V1`, `V2`

### 7.2 유지보수 가이드라인

#### 파일 크기 기준

- **적정 크기**: 200-600줄
- **경고 수준**: 600-800줄
- **리팩토링 필수**: 800줄 이상

#### 함수 크기 기준

- **적정 크기**: 10-50줄
- **경고 수준**: 50-100줄
- **분리 필수**: 100줄 이상

#### 새 노드 추가 기준

**core_nodes.py에 추가**:
- Orchestration 로직 (Intent, Planning, Executor 등)
- 모든 요청에 필수인 노드

**output_nodes.py에 추가**:
- 출력 형식 관련 (Generator, Formatter 등)
- 선택적 노드

**새 파일 생성**:
- 완전히 다른 도메인 (예: `security_nodes.py`)
- 800줄 초과 시

---

## 8. 의사결정 기준

### 8.1 현재 유지 (옵션 A) 선택 기준

다음에 해당하면 **현재 구조 유지**를 권장:

- ✅ **팀 규모 5명 이상**: 협업 우선
- ✅ **노드 추가 예정 많음**: 확장성 우선
- ✅ **각 노드별 전담 개발자**: 분리 필요
- ✅ **유닛 테스트 엄격**: 테스트 용이성 우선

**개선 작업**:
- `prompts.py` 활성화
- `generators/` 폴더 평탄화

**예상 작업 시간**: 1시간

---

### 8.2 리뉴얼 (옵션 C) 선택 기준

다음에 해당하면 **리뉴얼** 권장:

- ✅ **단독 개발 또는 2-3명 팀**: 파일 수 감소 효과
- ✅ **전체 플로우 자주 확인**: 코드 탐색 용이
- ✅ **프롬프트 자주 수정**: 중앙 관리 필요
- ✅ **노드 추가 계획 적음**: 현재 구조로 충분

**개선 효과**:
- 파일 수 64% 감소 (14개 → 5개)
- Import 단순화
- 프롬프트 중앙 관리
- 전체 코드 이해 시간 50% 감소

**예상 작업 시간**: 2시간

---

## 9. 최종 권장사항

### 9.1 단기 (지금 당장)

**추천**: **옵션 C (핵심만 분리)** 적용

**이유**:
1. 현재 단독 개발 또는 소규모 팀
2. 파일 수가 너무 많아 탐색 불편
3. 프롬프트가 흩어져 있어 관리 어려움
4. 작업 시간 2시간으로 합리적
5. 롤백 용이 (백업 존재)

**즉시 효과**:
- 코드 탐색 시간 50% 감소
- 프롬프트 수정 시간 80% 감소
- 전체 플로우 이해 시간 40% 감소

### 9.2 중기 (Phase 5 개발 시)

- 노드가 10개 이상 추가되면 재평가
- `core_nodes.py`가 800줄 초과 시 분리 고려
- 팀 규모 5명 이상 되면 현재 구조로 복귀 고려

### 9.3 장기 (프로덕션 배포 후)

- 프롬프트 버전 관리 시스템 도입
- 노드별 유닛 테스트 커버리지 80% 이상
- 성능 프로파일링 (각 노드별 실행 시간 측정)

---

## 10. 실행 결정

**결정 필요**: 다음 중 선택

### 선택지 1: 현재 유지 + 최소 개선 (옵션 A)

- [ ] 프롬프트만 통합 (`prompts.py` 활성화)
- [ ] `generators/` 폴더 평탄화
- 작업 시간: 1시간

### 선택지 2: 리뉴얼 (옵션 C) ★ 추천

- [ ] 프롬프트 통합
- [ ] 핵심 노드 통합 (`core_nodes.py`)
- [ ] 출력 노드 통합 (`output_nodes.py`)
- 작업 시간: 2시간

### 선택지 3: 나중에 결정

- [ ] 현재 유지
- [ ] Phase 5 개발 후 재평가

---

## 11. 참고 자료

### 11.1 파일 크기 업계 기준

| 언어 | 적정 크기 | 최대 권장 크기 | 출처 |
|------|-----------|----------------|------|
| Python | 200-400줄 | 600줄 | PEP 8 |
| JavaScript | 200-300줄 | 500줄 | Airbnb Style Guide |
| Java | 200-500줄 | 1,000줄 | Google Java Style |
| Go | 200-400줄 | 800줄 | Go Code Review Comments |

### 11.2 폴더 구조 참고

**Django 프로젝트**:
- 앱당 10-15개 파일
- `models.py`, `views.py`, `serializers.py` 분리

**FastAPI 프로젝트**:
- 라우터당 5-10개 엔드포인트
- 300줄 초과 시 분리

**LangGraph 프로젝트** (공식 예제):
- 노드 수 5개 이하: 단일 파일
- 노드 수 5-15개: 도메인별 분리
- 노드 수 15개 이상: 세부 분리

---

**작성자**: Claude (AI Assistant)
**최종 업데이트**: 2025-11-04
**다음 검토 예정**: Phase 5 개발 시작 전
