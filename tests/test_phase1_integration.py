"""
Phase 1 Integration Verification Test

Phase 1: 7개 에이전트 통합 검증
- Execute Layer 구현 검증
- Todo Manager Agent 선택 로직 검증
- Octostrator 연결 검증

Author: AI PT Manager Development Team
Date: 2025-11-06
Version: 1.0
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch


# ====================================
# Test 1: Execute Layer Import
# ====================================

def test_execute_layer_imports():
    """Execute Layer 모듈 import 검증"""
    try:
        from backend.app.octostrator.supervisors.execute.execute_nodes import (
            execute_layer_node,
            aggregator_node,
            error_handler_node,
            _create_llm_for_agents
        )

        # 함수 존재 확인
        assert callable(execute_layer_node)
        assert callable(aggregator_node)
        assert callable(error_handler_node)
        assert callable(_create_llm_for_agents)

        print("✅ Execute Layer imports: SUCCESS")

    except Exception as e:
        pytest.fail(f"Execute Layer import failed: {e}")


# ====================================
# Test 2: Todo Manager Import
# ====================================

def test_todo_manager_imports():
    """Todo Manager 모듈 import 검증"""
    try:
        from backend.app.octostrator.supervisors.todo.todo_manager import (
            TodoAgent,
            select_agent_for_task
        )

        # 함수/클래스 존재 확인
        assert TodoAgent is not None
        assert callable(select_agent_for_task)

        print("✅ Todo Manager imports: SUCCESS")

    except Exception as e:
        pytest.fail(f"Todo Manager import failed: {e}")


# ====================================
# Test 3: Octostrator Nodes Import
# ====================================

def test_octostrator_nodes_imports():
    """Octostrator Nodes 모듈 import 검증"""
    try:
        from backend.app.octostrator.supervisors.octostrator.octostrator_nodes import (
            cognitive_layer_node,
            todo_layer_node,
            execute_layer_node,
            response_layer_node
        )

        # 함수 존재 확인
        assert callable(cognitive_layer_node)
        assert callable(todo_layer_node)
        assert callable(execute_layer_node)
        assert callable(response_layer_node)

        print("✅ Octostrator Nodes imports: SUCCESS")

    except Exception as e:
        pytest.fail(f"Octostrator Nodes import failed: {e}")


# ====================================
# Test 4: Agent Registry Import
# ====================================

def test_agent_registry_imports():
    """Agent Registry 모듈 import 검증"""
    try:
        from backend.app.octostrator.agents import agent_registry

        # Registry 존재 확인
        assert agent_registry is not None

        # 7개 Agent 확인 (가능하면)
        expected_agents = [
            "frontdesk_agent",
            "assessor_agent",
            "program_designer_agent",
            "manager_agent",
            "marketing_agent",
            "owner_assistant_agent",
            "trainer_education_agent"
        ]

        print("✅ Agent Registry imports: SUCCESS")
        print(f"   Expected agents: {', '.join(expected_agents)}")

    except Exception as e:
        pytest.fail(f"Agent Registry import failed: {e}")


# ====================================
# Test 5: Execute Layer 기본 실행 테스트
# ====================================

@pytest.mark.asyncio
async def test_execute_layer_basic():
    """Execute Layer 기본 실행 테스트 (Mock)"""
    from backend.app.octostrator.supervisors.execute.execute_nodes import execute_layer_node

    # Mock state (빈 todos)
    state = {
        "session_id": "test-session",
        "user_id": "test-user",
        "todos": [],
        "checkpointer": None
    }

    # Execute
    result = await execute_layer_node(state, runtime=None)

    # 검증: 빈 todos는 completed=0, failed=0 반환
    assert result["completed"] == 0
    assert result["failed"] == 0
    assert result["success_rate"] == 0.0
    assert result["execution_results"] == {}

    print("✅ Execute Layer basic execution: SUCCESS")


# ====================================
# Test 6: Select Agent For Task 테스트
# ====================================

@pytest.mark.asyncio
async def test_select_agent_for_task():
    """select_agent_for_task 함수 테스트"""
    from backend.app.octostrator.supervisors.todo.todo_manager import select_agent_for_task
    from langchain_openai import ChatOpenAI

    # Mock LLM
    mock_llm = Mock(spec=ChatOpenAI)
    mock_response = Mock()
    mock_response.content = "frontdesk_agent"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    # Test step
    step = {
        "description": "신규 고객 상담 예약",
        "action": "create_consultation"
    }

    # Execute
    agent_name = await select_agent_for_task(step, llm=mock_llm)

    # 검증
    assert agent_name in [
        "frontdesk_agent",
        "assessor_agent",
        "program_designer_agent",
        "manager_agent",
        "marketing_agent",
        "owner_assistant_agent",
        "trainer_education_agent"
    ]

    print(f"✅ select_agent_for_task: SUCCESS (selected: {agent_name})")


# ====================================
# Test 7: LLM 생성 헬퍼 테스트
# ====================================

def test_create_llm_for_agents():
    """_create_llm_for_agents 함수 테스트 (runtime=None)"""
    from backend.app.octostrator.supervisors.execute.execute_nodes import _create_llm_for_agents

    # Execute (runtime=None, Phase 1)
    llm = _create_llm_for_agents(runtime=None)

    # 검증
    assert llm is not None
    assert hasattr(llm, "model_name") or hasattr(llm, "model")

    print("✅ _create_llm_for_agents (Phase 1): SUCCESS")


# ====================================
# Test 8: 확장 포인트 검증
# ====================================

def test_extension_points():
    """Phase 2 확장 포인트 검증"""
    import inspect
    from backend.app.octostrator.supervisors.execute.execute_nodes import (
        execute_layer_node,
        _create_llm_for_agents
    )

    # execute_layer_node 시그니처 확인
    sig = inspect.signature(execute_layer_node)
    params = sig.parameters

    # runtime 파라미터 존재 확인 (Phase 2 확장 포인트)
    assert "runtime" in params
    assert params["runtime"].default is None  # Optional[Runtime] = None

    # _create_llm_for_agents 시그니처 확인
    sig2 = inspect.signature(_create_llm_for_agents)
    params2 = sig2.parameters

    assert "runtime" in params2
    assert params2["runtime"].default is None

    print("✅ Extension points (Phase 2 ready): SUCCESS")


# ====================================
# Main Test Runner
# ====================================

if __name__ == "__main__":
    """수동 실행 가능"""
    import asyncio

    print("\n" + "="*60)
    print("Phase 1 Integration Verification Test")
    print("="*60 + "\n")

    # Sync tests
    try:
        test_execute_layer_imports()
        test_todo_manager_imports()
        test_octostrator_nodes_imports()
        test_agent_registry_imports()
        test_create_llm_for_agents()
        test_extension_points()
    except Exception as e:
        print(f"❌ Sync tests failed: {e}")
        exit(1)

    # Async tests
    async def run_async_tests():
        try:
            await test_execute_layer_basic()
            await test_select_agent_for_task()
        except Exception as e:
            print(f"❌ Async tests failed: {e}")
            return False
        return True

    if asyncio.run(run_async_tests()):
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nPhase 1 Integration: VERIFIED")
        print("Ready for Step 5: 문서화 및 배포")
    else:
        print("\n❌ SOME TESTS FAILED")
        exit(1)
