# Migration Guide - 3-Layer 아키텍처 전환

**작성일**: 2025-11-05
**버전**: 2.0
**목적**: 기존 시스템에서 새로운 3-Layer 아키텍처로 마이그레이션

---

## 목차

1. [마이그레이션 개요](#1-마이그레이션-개요)
2. [Phase 1: 준비 단계](#2-phase-1-준비-단계)
3. [Phase 2: Agent 마이그레이션](#3-phase-2-agent-마이그레이션)
4. [Phase 3: Supervisor 전환](#4-phase-3-supervisor-전환)
5. [Phase 4: 통합 테스트](#5-phase-4-통합-테스트)
6. [롤백 계획](#6-롤백-계획)
7. [체크리스트](#7-체크리스트)

---

## 1. 마이그레이션 개요

### 1.1 현재 상태 (AS-IS)

```
기존 아키텍처:
- 단일 Supervisor Graph
- Function 기반 Agent 노드
- cognitive_nodes.py + response_nodes.py
- 중앙집중식 상태 관리
```

### 1.2 목표 상태 (TO-BE)

```
3-Layer 아키텍처:
- Layer 1: Cognitive Supervisor (계획)
- Layer 2: TodoAgent (관리)
- Layer 3: Execute Supervisor (실행)
- BaseAgent 기반 Domain Agents
- 분산형 상태 관리
```

### 1.3 마이그레이션 전략

```
1. 병행 운영 (Parallel Run)
   - 기존 시스템과 새 시스템 공존
   - 점진적 트래픽 이동

2. 단계적 전환 (Phased Migration)
   - Agent부터 시작
   - Supervisor 점진적 전환
   - 최종 통합

3. 기능별 전환 (Feature-based)
   - 신규 기능은 새 아키텍처
   - 기존 기능 점진적 이동
```

---

## 2. Phase 1: 준비 단계

### 2.1 환경 설정

#### Step 1: 백업

```bash
# 전체 프로젝트 백업
cp -r backend/app/octostrator backend/app/octostrator_backup_$(date +%Y%m%d)

# 중요 파일 개별 백업
cd backend/app/octostrator/supervisor
for file in *.py; do
    cp "$file" "${file%.py}_old.py"
done
```

#### Step 2: 의존성 설치

```bash
# requirements.txt 업데이트
pip install langgraph==1.0.0
pip install langchain-openai==0.1.0
pip install pydantic==2.0.0
pip install asyncpg  # PostgreSQL checkpoint용
```

#### Step 3: 환경 변수 설정

```bash
# .env 파일
POSTGRES_URL=postgresql://user:pass@localhost/ptmanager
OPENAI_API_KEY=sk-...
AUTO_APPROVE_TODOS=false
LLM_MODEL=gpt-4o-mini
```

### 2.2 기본 구조 생성

```python
# 디렉토리 구조 생성
mkdir -p backend/app/octostrator/agents/base
mkdir -p backend/app/octostrator/agents/todo
mkdir -p backend/app/octostrator/manual
```

---

## 3. Phase 2: Agent 마이그레이션

### 3.1 기존 Agent 분석

#### 현재 Agent 구조 (Function 기반)

```python
# 기존: backend/app/octostrator/agents/diet/agent.py
async def diet_agent_node(state: SupervisorState) -> Command[Literal["aggregator"]]:
    """Diet Agent - 식단 관리"""
    # 단순 함수 기반
    # State 직접 수정
    # Checkpoint 없음
```

#### 새로운 Agent 구조 (BaseAgent 기반)

```python
# 새로운: backend/app/octostrator/agents/diet/diet_agent_v2.py
@register_agent("diet_agent_v2")
class DietAgentV2(BaseAgent):
    """Diet Agent - LangGraph 기반"""
    # Class 기반
    # StateGraph 워크플로우
    # Checkpoint 지원
```

### 3.2 Agent 변환 템플릿

```python
"""Agent Migration Template"""

# Step 1: Import 변경
from backend.app.octostrator.agents.base.base_agent import BaseAgent
from backend.app.octostrator.agents.base.agent_registry import register_agent
from langgraph.graph import StateGraph, START, END

# Step 2: State 정의
class MyAgentState(BaseAgentState):
    # 기존 state 필드들 이동
    input_data: Optional[Dict] = None
    result: Optional[Dict] = None

# Step 3: Agent 클래스 생성
@register_agent("my_agent_v2")
class MyAgentV2(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="my_agent_v2",
            agent_name="My Agent V2",
            enable_checkpoint=True
        )

    def build_graph(self, llm=None):
        workflow = StateGraph(MyAgentState)

        # 기존 로직을 노드로 변환
        workflow.add_node("process", self.process_node)

        workflow.add_edge(START, "process")
        workflow.add_edge("process", END)

        return workflow

    async def process_node(self, state):
        # 기존 함수 로직 이동
        result = await original_logic(state.input_data)
        return {"result": result}
```

### 3.3 단계별 마이그레이션

#### Step 1: 새 Agent 생성 (공존)

```python
# diet_agent_v2.py 생성
class DietAgentV2(BaseAgent):
    # 새로운 구현
```

#### Step 2: Agent Registry 등록

```python
# 자동 등록 (데코레이터)
@register_agent("diet_agent_v2")

# 또는 수동 등록
agent_registry.register(DietAgentV2, "diet_agent_v2")
```

#### Step 3: 라우팅 설정

```python
# 트래픽 분배 (카나리 배포)
AGENT_ROUTING = {
    "diet_tasks": {
        "diet_agent": 0.8,      # 80% 기존
        "diet_agent_v2": 0.2    # 20% 새 버전
    }
}
```

#### Step 4: 점진적 전환

```python
# 성능 모니터링 후 비율 조정
AGENT_ROUTING["diet_tasks"]["diet_agent_v2"] = 0.5  # 50%
# ... 검증 ...
AGENT_ROUTING["diet_tasks"]["diet_agent_v2"] = 1.0  # 100%
```

#### Step 5: 기존 Agent 제거

```python
# 완전 전환 후
agent_registry.unregister("diet_agent")
# diet_agent_v2 → diet_agent 이름 변경
```

---

## 4. Phase 3: Supervisor 전환

### 4.1 기존 Supervisor 분석

```python
# 기존: build_supervisor_graph()
def build_supervisor_graph(context, checkpointer):
    workflow = StateGraph(SupervisorState)
    # 모든 노드가 한 그래프에
    workflow.add_node("intent", intent_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("diet", diet_agent_node)
    # ...
```

### 4.2 새로운 구조로 전환

#### Step 1: Main Orchestrator 추가

```python
# main_orchestrator.py
orchestrator = MainOrchestrator(
    llm=llm,
    checkpointer=checkpointer,
    auto_approve_todos=False
)
```

#### Step 2: API 래퍼 생성

```python
# main_graph.py에 호환성 레이어 추가
async def process_user_request(message, session_id):
    """새로운 API (권장)"""
    orchestrator = await get_orchestrator()
    return await orchestrator.process_request(message, session_id)

def build_supervisor_graph(context, checkpointer):
    """기존 API (호환성)"""
    # 기존 그래프 유지
    # 또는 새 orchestrator로 래핑
```

#### Step 3: 점진적 전환

```python
# 조건부 라우팅
USE_NEW_ARCHITECTURE = os.getenv("USE_NEW_ARCH", "false") == "true"

if USE_NEW_ARCHITECTURE:
    # 새 orchestrator 사용
    result = await orchestrator.process_request(...)
else:
    # 기존 graph 사용
    result = await graph.ainvoke(...)
```

### 4.3 컴포넌트별 전환

#### Cognitive Nodes → Cognitive Supervisor

```python
# 기존
from .cognitive_nodes import intent_understanding_node

# 새로운
from .cognitive_supervisor import CognitiveSupervisor
cognitive = CognitiveSupervisor(llm, checkpointer)
plan = await cognitive.plan(message, session_id)
```

#### HITL Handler → TodoAgent

```python
# 기존
from .response_nodes import hitl_handler_node

# 새로운
todo_agent = TodoAgent()
todos = await todo_agent.execute({"plan": plan}, context)
```

#### Executor → Execute Supervisor

```python
# 기존
from .cognitive_nodes import executor_node

# 새로운
execute = ExecuteSupervisor(checkpointer)
results = await execute.execute(todos, session_id)
```

---

## 5. Phase 4: 통합 테스트

### 5.1 단위 테스트

```python
# test_new_architecture.py

import pytest
from backend.app.octostrator.main_orchestrator import create_orchestrator

@pytest.mark.asyncio
async def test_orchestrator_initialization():
    orchestrator = await create_orchestrator()
    assert orchestrator is not None

@pytest.mark.asyncio
async def test_agent_migration():
    # 기존 Agent
    old_result = await old_diet_agent(state)

    # 새 Agent
    new_agent = DietAgentV2()
    new_result = await new_agent.execute(task, context)

    # 결과 비교
    assert_equivalent_results(old_result, new_result)
```

### 5.2 통합 테스트

```python
@pytest.mark.asyncio
async def test_full_flow():
    orchestrator = await create_orchestrator()

    # 전체 플로우 테스트
    result = await orchestrator.process_request(
        user_message="테스트 요청",
        session_id="test_session"
    )

    assert result["success"] == True
    assert result["completed"] > 0
```

### 5.3 성능 테스트

```python
import time
import asyncio

async def performance_test():
    # 기존 시스템
    start = time.time()
    old_result = await old_system_process(request)
    old_time = time.time() - start

    # 새 시스템
    start = time.time()
    new_result = await new_system_process(request)
    new_time = time.time() - start

    print(f"Old: {old_time:.2f}s, New: {new_time:.2f}s")
    print(f"Improvement: {((old_time - new_time) / old_time * 100):.1f}%")
```

---

## 6. 롤백 계획

### 6.1 즉시 롤백

```python
# 환경 변수로 제어
USE_NEW_ARCHITECTURE = False

# 또는 feature flag
if feature_flags.get("use_3layer_architecture"):
    # 새 시스템
else:
    # 기존 시스템
```

### 6.2 데이터 롤백

```sql
-- Checkpoint 데이터 백업
CREATE TABLE checkpoint_backup AS
SELECT * FROM checkpoint WHERE created_at >= '2025-11-05';

-- 필요시 복원
INSERT INTO checkpoint
SELECT * FROM checkpoint_backup;
```

### 6.3 코드 롤백

```bash
# Git 태그 사용
git tag before-migration
git push origin before-migration

# 롤백 필요시
git checkout before-migration
```

---

## 7. 체크리스트

### 7.1 사전 준비

- [ ] 전체 백업 완료
- [ ] 테스트 환경 구축
- [ ] 의존성 설치
- [ ] 환경 변수 설정
- [ ] 문서 검토

### 7.2 Agent 마이그레이션

- [ ] BaseAgent 클래스 생성
- [ ] Agent Registry 구현
- [ ] Capability 정의
- [ ] 각 Agent 변환
  - [ ] DietAgent → DietAgentV2
  - [ ] WorkoutAgent → WorkoutAgentV2
  - [ ] ScheduleAgent → ScheduleAgentV2
  - [ ] 기타 Agent들
- [ ] Agent 테스트

### 7.3 Supervisor 전환

- [ ] Cognitive Supervisor 구현
- [ ] TodoAgent 구현
- [ ] Execute Supervisor 구현
- [ ] Main Orchestrator 구현
- [ ] API 래퍼 생성

### 7.4 통합 및 테스트

- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 성능 테스트 완료
- [ ] HITL 워크플로우 테스트
- [ ] WebSocket 연동 테스트

### 7.5 배포

- [ ] 카나리 배포 (10%)
- [ ] 모니터링 설정
- [ ] 점진적 확대 (25% → 50% → 100%)
- [ ] 기존 시스템 제거
- [ ] 문서 업데이트

---

## 부록

### A. 일반적인 문제 해결

#### 문제 1: Import 에러

```python
# 해결책: 경로 확인
import sys
sys.path.append("backend/app")

# 또는 상대 경로 사용
from ..base.base_agent import BaseAgent
```

#### 문제 2: State 호환성

```python
# 기존 State를 새 State로 변환
def convert_state(old_state):
    return NewState(
        task=old_state.get("task"),
        user_context=old_state.get("context"),
        # 매핑...
    )
```

#### 문제 3: Checkpoint 마이그레이션

```python
# 기존 checkpoint 데이터 변환
async def migrate_checkpoints():
    old_data = await old_checkpointer.get_all()
    for item in old_data:
        new_format = convert_checkpoint(item)
        await new_checkpointer.save(new_format)
```

### B. 성능 최적화

1. **Agent 캐싱**
```python
# Registry에서 인스턴스 재사용
agent = agent_registry.get_agent_instance("diet_agent")
if not agent:
    agent = agent_registry.create_agent("diet_agent")
```

2. **병렬 실행**
```python
# 의존성 없는 Agent들 병렬 실행
tasks = [agent1.execute(), agent2.execute()]
results = await asyncio.gather(*tasks)
```

3. **Lazy Loading**
```python
# 필요시에만 Agent 로드
if task_requires("diet"):
    diet_agent = load_agent("diet_agent")
```

### C. 모니터링

```python
# 로깅 설정
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 메트릭 수집
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')

@request_duration.time()
async def process_request():
    request_count.inc()
    # 처리...
```

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문의**: AI PT Manager Development Team