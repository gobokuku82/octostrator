# Phase 1 구현 가이드: 7개 에이전트 통합

**프로젝트**: AI PT Manager - 에이전트 통합 (Option A+)
**작성일**: 2025-11-06
**대상**: Phase 1 - 에이전트 통합 (Context API 확장 포인트 포함)
**예상 시간**: 5-7시간

---

## 📋 목차

1. [구현 개요](#1-구현-개요)
2. [Step 1: Execute Layer 구현](#2-step-1-execute-layer-구현)
3. [Step 2: Todo Manager Agent 선택](#3-step-2-todo-manager-agent-선택)
4. [Step 3: Octostrator 연결](#4-step-3-octostrator-연결)
5. [Step 4: 테스트](#5-step-4-테스트)
6. [검증 체크리스트](#6-검증-체크리스트)

---

## 1. 구현 개요

### 1.1 Phase 1 목표

✅ **7개 에이전트를 Execute Layer에 통합**
✅ **Todo 기반 동적 에이전트 라우팅**
✅ **Context API 확장 포인트 포함** (나중에 쉽게 추가 가능)
✅ **에이전트 코드는 수정하지 않음**

### 1.2 작업 파일

| 파일 | 작업 | 예상 시간 |
|------|------|----------|
| `backend/app/octostrator/supervisors/execute/execute_nodes.py` | 완전 재작성 | 2시간 |
| `backend/app/octostrator/supervisors/todo/todo_manager.py` | Agent 선택 로직 추가 | 1시간 |
| `backend/app/octostrator/supervisors/octostrator/octostrator_nodes.py` | import 수정 | 10분 |
| `tests/test_execute_layer.py` | 단위 테스트 작성 | 1시간 |
| `tests/test_full_workflow.py` | 통합 테스트 작성 | 1-2시간 |

**총 예상 시간**: 5-7시간

### 1.3 핵심 설계 포인트

1. **확장 포인트 1**: `_create_llm_for_agents(runtime=None)` 헬퍼 함수
   - Phase 1: `runtime=None`으로 기본 설정 사용
   - Phase 2: `runtime` 자동 주입 시 Context API 설정 사용

2. **확장 포인트 2**: `execute_layer_node(state, runtime=None)` 함수 시그니처
   - Phase 1: `runtime=None`으로 동작
   - Phase 2: Graph에 `context_schema` 등록하면 자동 주입

---

## 2. Step 1: Execute Layer 구현

### 2.1 파일: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

**작업**: 완전 재작성 (기존 시뮬레이션 코드 제거)

**전체 코드**:

```python
"""
Execute Layer Nodes

Execution and aggregation nodes for Layer 2.
Phase 1: 7개 에이전트 통합 (Context API 확장 포인트 포함)

Author: AI PT Manager Development Team
Date: 2025-11-06
Version: 2.0 (Option A+ - 확장 가능)
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langgraph.types import Runtime

logger = logging.getLogger(__name__)


# ====================================
# 확장 포인트: LLM 생성 헬퍼 함수
# ====================================

def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """
    Agent용 LLM 생성 (Context API 확장 포인트)

    [Phase 1] runtime=None: 기본 설정 사용
    [Phase 2] runtime 있음: Context API 설정 사용

    Args:
        runtime: LangGraph Runtime (Context API)

    Returns:
        ChatOpenAI instance
    """
    from backend.app.config.system import config as system_config

    # Phase 2: Context API 사용 (runtime이 있을 때)
    if runtime is not None:
        try:
            from backend.app.octostrator.contexts.app_context import AppContext
            context: AppContext = runtime.context
            settings = context.llm_settings

            logger.info(
                f"[Execute] Using Context API settings "
                f"(model={settings.agent_model}, temp={settings.agent_temperature}, "
                f"max_tokens={settings.agent_max_tokens})"
            )

            return ChatOpenAI(
                model=settings.agent_model,
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens,
                api_key=system_config.openai_api_key
            )
        except Exception as e:
            logger.warning(
                f"[Execute] Failed to use Context API, falling back to default: {e}"
            )

    # Phase 1: 기본 설정
    logger.info(
        f"[Execute] Using default LLM settings "
        f"(model={system_config.openai_model})"
    )

    return ChatOpenAI(
        model=system_config.openai_model,
        api_key=system_config.openai_api_key,
        temperature=0.7,
        max_tokens=4096
    )


# ====================================
# EXECUTION NODE
# ====================================

async def execute_layer_node(
    state: Dict[str, Any],
    runtime: Optional[Runtime] = None  # ⭐ Phase 2 확장 포인트
) -> Dict[str, Any]:
    """
    Execute Layer Node - 7개 에이전트 실행 및 결과 수집

    [Phase 1] runtime=None으로 동작 (Context API 없이)
    [Phase 2] runtime 자동 주입됨 (Graph에 context_schema 등록 시)

    Features:
    - Todo별 동적 Agent 라우팅
    - Agent 독립 실행 및 결과 수집
    - 에러 처리 및 graceful degradation
    - Context API 확장 포인트 포함

    Args:
        state: Octostrator State
        runtime: LangGraph Runtime (optional, Phase 2)

    Returns:
        Updated state with execution results
    """
    from backend.app.octostrator.agents import agent_registry

    try:
        # 1. State에서 필요한 데이터 가져오기
        todos = state.get("todos", [])
        checkpointer = state.get("checkpointer")
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id", "default")

        if not todos:
            logger.warning("[Execute] No todos to execute")
            return {
                "execution_results": {},
                "completed": 0,
                "failed": 0,
                "success_rate": 0.0
            }

        logger.info(f"[Execute] Starting execution for {len(todos)} todos")

        # 2. LLM 초기화 (확장 포인트 사용)
        llm = _create_llm_for_agents(runtime)

        # 3. 결과 수집 변수
        execution_results = {}
        completed = 0
        failed = 0

        # 4. Todo별 Agent 실행
        for todo in todos:
            # Skip non-pending todos
            if todo.get("status") != "pending":
                logger.debug(f"[Execute] Skipping todo {todo.get('id')} (status: {todo.get('status')})")
                continue

            agent_name = todo.get("agent")  # 예: "frontdesk_agent"
            task_description = todo.get("task")
            todo_id = todo.get("id")

            if not agent_name:
                logger.warning(f"[Execute] Todo {todo_id} has no agent assigned, skipping")
                continue

            try:
                # 4.1 Agent 가져오기 (Registry에서)
                agent_class = agent_registry.get(agent_name)
                if not agent_class:
                    raise ValueError(f"Agent '{agent_name}' not found in registry")

                logger.info(f"[Execute] Running {agent_name} for todo {todo_id}")

                # 4.2 Agent 인스턴스 생성
                agent = agent_class()

                # 4.3 Agent 초기화 (LLM + Checkpointer)
                await agent.initialize(llm=llm, checkpointer=checkpointer)

                # 4.4 Task 준비
                task = {
                    "task_id": todo_id,
                    "task_type": "todo_execution",
                    "description": task_description,
                    "todo_data": todo  # 전체 Todo 전달
                }

                context = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "parent_state": "octostrator"
                }

                # 4.5 Agent 실행
                result = await agent.execute(
                    task=task,
                    context=context,
                    thread_id=session_id  # Checkpoint용 (format: {session_id}_{agent_id})
                )

                # 4.6 결과 저장
                execution_results[todo_id] = {
                    "todo_id": todo_id,
                    "agent": agent_name,
                    "status": result.get("status", "unknown"),
                    "result": result.get("result", {}),
                    "started_at": result.get("started_at"),
                    "completed_at": result.get("completed_at"),
                    "error": result.get("error")
                }

                # 4.7 Todo 상태 업데이트
                if result.get("status") == "completed":
                    todo["status"] = "completed"
                    todo["completed_at"] = result.get("completed_at")
                    completed += 1
                    logger.info(f"[Execute] {agent_name} completed successfully for todo {todo_id}")
                else:
                    todo["status"] = "failed"
                    todo["error"] = result.get("error")
                    failed += 1
                    logger.error(f"[Execute] {agent_name} failed for todo {todo_id}: {result.get('error')}")

            except Exception as e:
                # 에러 처리: graceful degradation
                logger.error(f"[Execute] Exception while executing {agent_name}: {e}", exc_info=True)

                execution_results[todo_id] = {
                    "todo_id": todo_id,
                    "agent": agent_name,
                    "status": "failed",
                    "error": str(e),
                    "result": {}
                }

                todo["status"] = "failed"
                todo["error"] = str(e)
                failed += 1

        # 5. 실행 통계
        total_todos = len([t for t in todos if t.get("agent")])
        success_rate = completed / total_todos if total_todos > 0 else 0.0

        logger.info(
            f"[Execute] Execution completed: {completed} succeeded, {failed} failed "
            f"(success rate: {success_rate:.1%})"
        )

        # 6. State 업데이트
        return {
            "execution_results": execution_results,
            "completed": completed,
            "failed": failed,
            "success_rate": success_rate,
            "todos": todos,  # merge_todos_smart가 자동 병합
            "action_history": [{
                "action": "execute_layer_node",
                "result": {
                    "total_todos": total_todos,
                    "completed": completed,
                    "failed": failed,
                    "success_rate": success_rate
                }
            }]
        }

    except Exception as e:
        logger.error(f"[Execute] Critical error in execute_layer_node: {e}", exc_info=True)
        return {
            "error": str(e),
            "execution_results": {},
            "completed": 0,
            "failed": 0
        }


# ====================================
# AGGREGATOR NODE
# ====================================

async def aggregator_node(
    state: Dict[str, Any],
    runtime: Optional[Runtime] = None  # ⭐ Phase 2 확장 포인트
) -> Dict[str, Any]:
    """
    Aggregator Node - 실행 결과 집계

    [Phase 1] 간단한 집계
    [Phase 2] LLM으로 인사이트 생성 (Context API 사용)

    Args:
        state: Octostrator State
        runtime: LangGraph Runtime (optional, Phase 2)

    Returns:
        Aggregated data
    """
    try:
        execution_results = state.get("execution_results", {})

        if not execution_results:
            logger.warning("[Aggregator] No execution results to aggregate")
            return {"aggregated_data": {}}

        # Phase 1: 간단한 집계
        completed_count = sum(
            1 for r in execution_results.values() if r.get("status") == "completed"
        )
        failed_count = sum(
            1 for r in execution_results.values() if r.get("status") == "failed"
        )

        aggregated = {
            "total_steps": len(execution_results),
            "completed_steps": completed_count,
            "failed_steps": failed_count,
            "results": execution_results,
            "summary": (
                f"Execution completed: {completed_count} succeeded, "
                f"{failed_count} failed"
            )
        }

        logger.info(f"[Aggregator] Aggregated {aggregated['total_steps']} results")

        # TODO Phase 2: LLM으로 인사이트 생성
        # if runtime is not None:
        #     llm = _create_llm_for_aggregator(runtime)
        #     insights = await generate_insights(llm, execution_results)
        #     aggregated["insights"] = insights

        return {"aggregated_data": aggregated}

    except Exception as e:
        logger.error(f"[Aggregator] Error: {e}")
        return {"error": str(e)}


# ====================================
# ERROR HANDLER NODE
# ====================================

async def error_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Error Handler Node - 실행 중 발생한 에러 처리

    Features:
    - Error categorization
    - Error reporting
    - Recovery suggestions
    """
    try:
        error = state.get("error")
        failed_steps = [
            r for r in state.get("execution_results", {}).values()
            if r.get("status") == "failed"
        ]

        if not error and not failed_steps:
            return {}  # No errors to handle

        # 에러 리포트 생성
        error_report = {
            "has_errors": True,
            "error_count": len(failed_steps),
            "errors": failed_steps,
            "recovery_action": "manual_intervention_required"
        }

        if error:
            error_report["critical_error"] = error

        logger.warning(
            f"[ErrorHandler] Handling {error_report['error_count']} errors"
        )

        return {"error_report": error_report}

    except Exception as e:
        logger.error(f"[ErrorHandler] Error in error handler: {e}")
        return {"critical_error": str(e)}
```

### 2.2 검증

파일을 저장한 후 다음 명령으로 문법 검증:

```bash
python -m py_compile backend/app/octostrator/supervisors/execute/execute_nodes.py
```

---

## 3. Step 2: Todo Manager Agent 선택

### 3.1 파일: `backend/app/octostrator/supervisors/todo/todo_manager.py`

**작업**: `select_agent_for_task()` 함수 추가

**추가할 코드** (파일 끝에 추가):

```python
# ====================================
# AGENT SELECTION
# ====================================

async def select_agent_for_task(step: dict, llm) -> str:
    """
    Task를 분석하여 적절한 Agent 선택 (LLM 기반)

    Available agents:
    - frontdesk_agent: 신규 리드 관리, 상담 예약, 문의 응대
    - assessor_agent: 체성분 분석, 자세 평가, 피트니스 점수
    - program_designer_agent: 운동/식단 프로그램 설계
    - manager_agent: 회원 출석 관리, 이탈 위험 분석
    - marketing_agent: SNS 마케팅, 이벤트 운영
    - owner_assistant_agent: 매출 분석, 트레이너 성과 관리
    - trainer_education_agent: 트레이너 교육 및 스킬 평가

    Args:
        step: Plan step with description
        llm: Language Model instance

    Returns:
        Agent name (e.g., "frontdesk_agent")
    """
    from langchain.prompts import ChatPromptTemplate
    from langchain_core.messages import SystemMessage

    task_description = step.get("description", "")

    if not task_description:
        logger.warning("[TodoManager] Empty task description, using default agent")
        return "frontdesk_agent"

    try:
        # LLM 프롬프트
        prompt = f"""You are an AI agent router. Given a task description, select the most appropriate agent.

Available agents:
- frontdesk_agent: 신규 리드 관리, 상담 예약, 문의 응대, 고객 정보 수집
- assessor_agent: 체성분 분석(InBody), 자세 평가, 피트니스 점수 계산
- program_designer_agent: 운동 프로그램 설계, 식단 프로그램 작성
- manager_agent: 회원 출석 관리, 이탈 위험 분석, PT 세션 관리
- marketing_agent: SNS 콘텐츠 생성, 이벤트 기획, 마케팅 캠페인
- owner_assistant_agent: 매출 분석, 트레이너 성과 분석, 비즈니스 리포트
- trainer_education_agent: 트레이너 교육 자료 생성, 스킬 평가

Task: {task_description}

Return ONLY the agent name (e.g., "frontdesk_agent"), nothing else."""

        # LLM 호출
        response = await llm.ainvoke([SystemMessage(content=prompt)])
        agent_name = response.content.strip().lower()

        # Validation: 유효한 agent인지 확인
        valid_agents = [
            "frontdesk_agent",
            "assessor_agent",
            "program_designer_agent",
            "manager_agent",
            "marketing_agent",
            "owner_assistant_agent",
            "trainer_education_agent"
        ]

        if agent_name not in valid_agents:
            logger.warning(
                f"[TodoManager] Invalid agent '{agent_name}' returned by LLM, "
                f"using frontdesk_agent as fallback"
            )
            return "frontdesk_agent"

        logger.info(f"[TodoManager] Selected {agent_name} for task: {task_description}")
        return agent_name

    except Exception as e:
        logger.error(f"[TodoManager] Failed to select agent: {e}", exc_info=True)
        # Fallback: 기본 agent
        return "frontdesk_agent"
```

### 3.2 Todo Manager Node 수정

기존 `todo_layer_node` 함수를 수정하여 `select_agent_for_task()` 사용:

**수정 위치**: `todo_manager.py`의 `todo_layer_node` 함수 내부

**수정 전**:
```python
for idx, step in enumerate(steps, start=1):
    todo = {
        "task": step.get("description"),
        "agent": "frontdesk_agent",  # ❌ 하드코딩
        "priority": step.get("priority", 3),
        # ...
    }
```

**수정 후**:
```python
# LLM 가져오기
llm = state.get("llm") or _get_default_llm()

for idx, step in enumerate(steps, start=1):
    # ⭐ LLM으로 Agent 선택
    agent_name = await select_agent_for_task(step, llm=llm)

    todo = {
        "task": step.get("description"),
        "agent": agent_name,  # ✅ 동적 할당
        "priority": step.get("priority", 3),
        # ...
    }
```

**헬퍼 함수 추가** (LLM이 없을 경우):
```python
def _get_default_llm():
    """기본 LLM 생성 (state에 LLM이 없을 경우)"""
    from backend.app.config.system import config
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=config.openai_model,
        api_key=config.openai_api_key,
        temperature=0.7
    )
```

---

## 4. Step 3: Octostrator 연결

### 4.1 파일: `backend/app/octostrator/supervisors/octostrator/octostrator_nodes.py`

**작업**: Execute Layer import 수정

**수정 전**:
```python
from ..execute.execute_nodes import executor_node  # ❌ 구 함수
```

**수정 후**:
```python
from ..execute.execute_nodes import execute_layer_node  # ✅ 새 함수
```

**execute_layer_node 함수 수정**:

**수정 전**:
```python
async def execute_layer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Layer - 단순 호출"""
    from ..execute.execute_nodes import executor_node
    result = await executor_node(state)
    return result
```

**수정 후**:
```python
async def execute_layer_node_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Layer Wrapper - Octostrator → Execute Layer"""
    from ..execute.execute_nodes import execute_layer_node

    logger.info("[Octostrator] Delegating to Execute Layer")

    # Execute Layer 호출 (runtime은 Graph가 자동 주입)
    result = await execute_layer_node(state)

    logger.info(
        f"[Octostrator] Execute Layer completed: "
        f"{result.get('completed', 0)} succeeded, "
        f"{result.get('failed', 0)} failed"
    )

    return result
```

### 4.2 파일: `backend/app/octostrator/supervisors/octostrator/octostrator_graph.py`

**작업**: 노드 이름 업데이트

**수정 전**:
```python
graph.add_node("execute", execute_layer_node)
```

**수정 후** (이름 변경 필요 시):
```python
graph.add_node("execute", execute_layer_node_wrapper)
```

또는 함수 이름을 `execute_layer_node`로 유지하면 수정 불필요.

---

## 5. Step 4: 테스트

### 5.1 단위 테스트: `tests/test_execute_layer.py`

**새 파일 생성**:

```python
"""
Execute Layer 단위 테스트

7개 에이전트 통합 검증
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.app.octostrator.supervisors.execute.execute_nodes import (
    execute_layer_node,
    _create_llm_for_agents
)


@pytest.fixture
def mock_agent_registry():
    """Mock Agent Registry"""
    with patch("backend.app.octostrator.agents.agent_registry") as mock_registry:
        # Mock FrontdeskAgent
        mock_frontdesk_class = Mock()
        mock_frontdesk_instance = AsyncMock()
        mock_frontdesk_instance.initialize = AsyncMock()
        mock_frontdesk_instance.execute = AsyncMock(return_value={
            "status": "completed",
            "result": {"lead_id": 123},
            "started_at": "2025-11-06T12:00:00",
            "completed_at": "2025-11-06T12:00:05"
        })
        mock_frontdesk_class.return_value = mock_frontdesk_instance

        mock_registry.get.return_value = mock_frontdesk_class
        yield mock_registry


@pytest.mark.asyncio
async def test_execute_single_agent(mock_agent_registry):
    """단일 Agent 실행 테스트"""
    state = {
        "session_id": "test-123",
        "user_id": "user-1",
        "todos": [
            {
                "id": "todo-1",
                "task": "신규 리드 생성",
                "agent": "frontdesk_agent",
                "status": "pending"
            }
        ],
        "checkpointer": None
    }

    result = await execute_layer_node(state, runtime=None)

    # 검증
    assert result["completed"] == 1
    assert result["failed"] == 0
    assert result["success_rate"] == 1.0
    assert "todo-1" in result["execution_results"]
    assert result["execution_results"]["todo-1"]["status"] == "completed"

    # Agent가 호출되었는지 확인
    mock_agent_registry.get.assert_called_once_with("frontdesk_agent")


@pytest.mark.asyncio
async def test_execute_multiple_agents(mock_agent_registry):
    """복수 Agent 실행 테스트"""
    state = {
        "session_id": "test-123",
        "user_id": "user-1",
        "todos": [
            {"id": "todo-1", "task": "리드 생성", "agent": "frontdesk_agent", "status": "pending"},
            {"id": "todo-2", "task": "InBody 분석", "agent": "assessor_agent", "status": "pending"},
            {"id": "todo-3", "task": "프로그램 생성", "agent": "program_designer_agent", "status": "pending"}
        ],
        "checkpointer": None
    }

    result = await execute_layer_node(state, runtime=None)

    # 검증
    assert result["completed"] == 3
    assert result["failed"] == 0
    assert len(result["execution_results"]) == 3


@pytest.mark.asyncio
async def test_execute_agent_not_found():
    """Agent를 찾을 수 없는 경우 테스트"""
    with patch("backend.app.octostrator.agents.agent_registry") as mock_registry:
        mock_registry.get.return_value = None  # Agent 없음

        state = {
            "session_id": "test-123",
            "user_id": "user-1",
            "todos": [
                {"id": "todo-1", "task": "Invalid", "agent": "invalid_agent", "status": "pending"}
            ],
            "checkpointer": None
        }

        result = await execute_layer_node(state, runtime=None)

        # 검증
        assert result["completed"] == 0
        assert result["failed"] == 1
        assert result["execution_results"]["todo-1"]["status"] == "failed"


def test_create_llm_for_agents_without_runtime():
    """LLM 생성 테스트 (runtime=None)"""
    with patch("backend.app.config.system.config") as mock_config:
        mock_config.openai_model = "gpt-4o-mini"
        mock_config.openai_api_key = "test-key"

        llm = _create_llm_for_agents(runtime=None)

        assert llm is not None
        assert llm.model_name == "gpt-4o-mini"
```

### 5.2 통합 테스트: `tests/test_full_workflow.py`

**새 파일 생성**:

```python
"""
전체 워크플로우 통합 테스트

Cognitive → Todo → Execute → Response
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_full_workflow_frontdesk():
    """
    전체 워크플로우 테스트: Frontdesk Agent

    Flow:
    1. User query: "새로운 고객 상담 요청"
    2. Cognitive Layer: 의도 파악 및 Plan 생성
    3. Todo Manager: Plan → Todos 변환, Agent 할당
    4. Execute Layer: FrontdeskAgent 실행
    5. Response Layer: 최종 응답 생성
    """
    from backend.app.octostrator.supervisors.octostrator.octostrator_graph import (
        build_octostrator_graph
    )

    # Mock checkpointer
    mock_checkpointer = AsyncMock()

    # Graph 빌드
    graph = build_octostrator_graph(checkpointer=mock_checkpointer)

    # Input
    input_state = {
        "user_query": "새로운 고객이 PT 상담을 요청했습니다. 이름: 김철수, 전화: 010-1234-5678",
        "session_id": "test-session-1",
        "user_id": "test-user-1",
        "output_format": "chat"
    }

    # 실행
    result = await graph.ainvoke(input_state)

    # 검증
    assert result is not None
    assert "plan" in result or "todos" in result
    assert "execution_results" in result
    assert len(result.get("execution_results", {})) > 0

    # Agent가 frontdesk_agent인지 확인
    todos = result.get("todos", [])
    assert any(t.get("agent") == "frontdesk_agent" for t in todos)


@pytest.mark.asyncio
async def test_agent_selection():
    """
    Agent 선택 로직 테스트

    다양한 task에 대해 적절한 agent가 선택되는지 확인
    """
    from backend.app.octostrator.supervisors.todo.todo_manager import (
        select_agent_for_task
    )
    from langchain_openai import ChatOpenAI
    from backend.app.config.system import config

    llm = ChatOpenAI(
        model=config.openai_model,
        api_key=config.openai_api_key
    )

    # Test cases
    test_cases = [
        {"description": "신규 고객 상담 예약", "expected": "frontdesk_agent"},
        {"description": "InBody 체성분 분석", "expected": "assessor_agent"},
        {"description": "운동 프로그램 작성", "expected": "program_designer_agent"},
        {"description": "회원 출석 관리", "expected": "manager_agent"},
        {"description": "SNS 게시물 작성", "expected": "marketing_agent"},
        {"description": "월간 매출 리포트", "expected": "owner_assistant_agent"},
        {"description": "트레이너 교육 자료", "expected": "trainer_education_agent"}
    ]

    for test_case in test_cases:
        step = {"description": test_case["description"]}
        agent_name = await select_agent_for_task(step, llm=llm)

        print(f"Task: {test_case['description']} → Agent: {agent_name}")
        # Note: LLM 결과는 non-deterministic하므로 엄격한 assert는 하지 않음
        # 대신 valid agent인지만 확인
        valid_agents = [
            "frontdesk_agent", "assessor_agent", "program_designer_agent",
            "manager_agent", "marketing_agent", "owner_assistant_agent",
            "trainer_education_agent"
        ]
        assert agent_name in valid_agents
```

### 5.3 테스트 실행

```bash
# 단위 테스트
pytest tests/test_execute_layer.py -v

# 통합 테스트
pytest tests/test_full_workflow.py -v

# 모든 테스트
pytest tests/ -v
```

---

## 6. 검증 체크리스트

### 6.1 코드 완성도

- [ ] `execute_nodes.py` 완전 재작성 완료
- [ ] `_create_llm_for_agents()` 헬퍼 함수 구현
- [ ] `execute_layer_node()` 함수에 `runtime=None` 파라미터 추가
- [ ] `select_agent_for_task()` 함수 추가
- [ ] `todo_manager.py` Agent 선택 로직 통합
- [ ] `octostrator_nodes.py` import 수정

### 6.2 기능 검증

- [ ] 7개 에이전트 모두 Registry에 등록되어 있음
- [ ] Todo의 `agent` 필드로 Agent 동적 선택 가능
- [ ] Agent 실행 결과가 `execution_results`에 저장됨
- [ ] Todo 상태가 자동으로 업데이트됨 (pending → completed/failed)
- [ ] 에러 발생 시 graceful degradation 동작

### 6.3 테스트

- [ ] 단위 테스트 작성 완료
- [ ] 통합 테스트 작성 완료
- [ ] 모든 테스트 통과
- [ ] Mock 데이터로 검증 완료

### 6.4 확장 포인트 준비

- [ ] `_create_llm_for_agents(runtime)` 함수가 runtime=None과 runtime 모두 처리
- [ ] `execute_layer_node()` 함수 시그니처에 `runtime=None` 포함
- [ ] Phase 2에서 `context_schema=AppContext` 추가 시 자동 동작 확인

### 6.5 문서화

- [ ] 코드 주석 추가 (docstring)
- [ ] Phase 2 확장 방법 주석 추가
- [ ] README 업데이트 (선택적)

---

## 7. 다음 단계

### Phase 1 완료 후

1. **운영 환경 배포**
   - 7개 에이전트가 정상 동작하는지 확인
   - 1-2개월 사용하며 비용 측정

2. **Phase 2 진행 여부 결정**
   - 비용이 부담스러우면 → Phase 2 진행 (Context API)
   - 비용이 괜찮으면 → Phase 2는 보류

### Phase 2 진행 시 (선택적)

1. **Graph Builder 수정** (2-3줄)
   - `execute_graph.py`에 `context_schema=AppContext` 추가
   - `octostrator_graph.py`에 `context_schema=AppContext` 추가

2. **환경 변수 설정**
   - `export SYSTEM_ENV=production`

3. **테스트**
   - Context API 동작 확인
   - 비용 절감 측정 (47% 목표)

---

## 8. 문제 해결

### 8.1 Agent를 찾을 수 없음

**증상**: `Agent 'xxx_agent' not found in registry`

**해결**:
```python
# agents/__init__.py 확인
from .frontdesk.frontdesk_agent import FrontdeskAgent
# ...
register_all_agents()  # 이 함수가 호출되는지 확인
```

### 8.2 LLM API Key 오류

**증상**: `AuthenticationError: Invalid API Key`

**해결**:
```bash
# .env 파일 확인
OPENAI_API_KEY=sk-...

# config 로드 확인
from backend.app.config.system import config
print(config.openai_api_key)
```

### 8.3 Todo에 agent 필드가 없음

**증상**: Todo에 `agent` 필드가 비어있음

**해결**:
- `todo_manager.py`의 `select_agent_for_task()` 호출 확인
- LLM이 제대로 초기화되었는지 확인

---

**작성자**: AI Development Team
**날짜**: 2025-11-06
**버전**: 1.0 (Phase 1 구현 가이드)
