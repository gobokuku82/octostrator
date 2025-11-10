"""
Phase 1 Quick Verification Test

빠른 검증: Execute Layer 통합만 테스트

Author: AI PT Manager Development Team
Date: 2025-11-06
"""

import sys
sys.path.insert(0, 'C:/kdy/Projects/AI_PTmanager/beta_v001')

print("\n" + "="*60)
print("Phase 1 Quick Verification Test")
print("="*60 + "\n")

# ====================================
# Test 1: Execute Layer Import
# ====================================
print("[Test 1] Execute Layer imports...")
try:
    from backend.app.octostrator.supervisors.execute.execute_nodes import (
        execute_layer_node,
        aggregator_node,
        error_handler_node,
        _create_llm_for_agents
    )

    assert callable(execute_layer_node)
    assert callable(aggregator_node)
    assert callable(error_handler_node)
    assert callable(_create_llm_for_agents)

    print("   ✅ All functions imported successfully")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)


# ====================================
# Test 2: Function Signature Check
# ====================================
print("\n[Test 2] Checking function signatures...")
try:
    import inspect

    # execute_layer_node 시그니처 확인
    sig = inspect.signature(execute_layer_node)
    params = sig.parameters

    # state 파라미터 존재
    assert "state" in params
    print("   ✅ 'state' parameter exists")

    # runtime 파라미터 존재 (Phase 2 확장 포인트)
    assert "runtime" in params
    assert params["runtime"].default is None
    print("   ✅ 'runtime' parameter exists (Phase 2 ready)")

    # _create_llm_for_agents 시그니처 확인
    sig2 = inspect.signature(_create_llm_for_agents)
    params2 = sig2.parameters
    assert "runtime" in params2
    assert params2["runtime"].default is None
    print("   ✅ '_create_llm_for_agents' has runtime parameter")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)


# ====================================
# Test 3: Octostrator Integration
# ====================================
print("\n[Test 3] Octostrator integration...")
try:
    from backend.app.octostrator.supervisors.octostrator.octostrator_nodes import (
        execute_layer_node as octostrator_execute
    )

    assert callable(octostrator_execute)
    print("   ✅ Octostrator can import execute_layer_node")

    # 시그니처 확인
    sig = inspect.signature(octostrator_execute)
    params = sig.parameters
    assert "state" in params
    print("   ✅ Octostrator wrapper signature is correct")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)


# ====================================
# Test 4: Basic Async Execution
# ====================================
print("\n[Test 4] Basic async execution...")
try:
    import asyncio

    async def test_empty_todos():
        """빈 todos로 실행 테스트"""
        state = {
            "session_id": "test-123",
            "user_id": "test-user",
            "todos": [],
            "checkpointer": None
        }

        result = await execute_layer_node(state, runtime=None)

        # 검증
        assert result["completed"] == 0, "completed should be 0"
        assert result["failed"] == 0, "failed should be 0"
        assert result["success_rate"] == 0.0, "success_rate should be 0.0"
        assert result["execution_results"] == {}, "execution_results should be empty"

        return True

    # Run async test
    success = asyncio.run(test_empty_todos())
    if success:
        print("   ✅ Execute layer runs correctly with empty todos")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ====================================
# Test 5: LLM Creation
# ====================================
print("\n[Test 5] LLM creation...")
try:
    # Phase 1: runtime=None
    llm = _create_llm_for_agents(runtime=None)

    assert llm is not None
    assert hasattr(llm, "model_name") or hasattr(llm, "model")
    print("   ✅ LLM created successfully (Phase 1 mode)")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ====================================
# Summary
# ====================================
print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("""
Phase 1 Integration: VERIFIED ✓

Components tested:
  ✓ Execute Layer nodes (execute_layer_node, aggregator_node, error_handler_node)
  ✓ LLM creation helper (_create_llm_for_agents)
  ✓ Extension points (runtime parameter for Phase 2)
  ✓ Octostrator integration
  ✓ Basic async execution

Next steps:
  - Step 5: Full workflow testing (optional)
  - Deploy to production
""")
