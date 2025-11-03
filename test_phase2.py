"""Phase 2 테스트

Intent Understanding + Planning Agent 동작 검증
"""
import asyncio
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph
from backend.app.config.system import config


async def test_phase2():
    """Phase 2 기능 테스트"""

    # Graph 생성
    graph = build_supervisor_graph()

    # 테스트 케이스 1: 간단한 요청
    print("=" * 80)
    print("Test Case 1: Simple Request")
    print("=" * 80)

    result1 = await graph.ainvoke({
        "messages": [HumanMessage(content="최근 매출 데이터 검색해줘")]
    })

    print("\n[State After Execution]")
    print(f"User Intent: {result1.get('user_intent', 'N/A')}")
    print(f"Plan: {result1.get('plan', [])}")
    print(f"Current Step: {result1.get('current_step', 'N/A')}")
    print(f"Is Planning: {result1.get('is_planning', 'N/A')}")
    print(f"Is Executing: {result1.get('is_executing', 'N/A')}")

    print("\n[Messages]")
    for i, msg in enumerate(result1.get("messages", [])):
        print(f"\nMessage {i+1} [{msg.__class__.__name__}]:")
        print(msg.content)

    # 테스트 케이스 2: 중간 복잡도 요청
    print("\n" + "=" * 80)
    print("Test Case 2: Medium Complexity Request")
    print("=" * 80)

    result2 = await graph.ainvoke({
        "messages": [HumanMessage(content="지난 분기 매출 분석해줘")]
    })

    print("\n[State After Execution]")
    print(f"User Intent: {result2.get('user_intent', 'N/A')[:200]}...")
    print(f"Plan Steps: {len(result2.get('plan', []))}")

    print("\n[Plan Details]")
    for step in result2.get('plan', []):
        print(f"  Step {step['step_id']}: [{step['agent']}] {step['description']}")

    print("\n[Final Message]")
    final_msg = result2.get("messages", [])[-1]
    print(final_msg.content)

    # 테스트 케이스 3: 복잡한 멀티 스텝 요청
    print("\n" + "=" * 80)
    print("Test Case 3: Complex Multi-Step Request with HITL")
    print("=" * 80)

    result3 = await graph.ainvoke({
        "messages": [HumanMessage(
            content="지난 분기 매출 분석 후 전년 동기 대비 비교하고 보고서 작성해줘. 각 단계마다 확인할게."
        )]
    })

    print("\n[State After Execution]")
    print(f"Plan Steps: {len(result3.get('plan', []))}")

    print("\n[Plan Details]")
    for step in result3.get('plan', []):
        hitl_info = f" (Question: {step.get('hitl_question', 'N/A')})" if step['agent'] == 'hitl' else ""
        print(f"  Step {step['step_id']}: [{step['agent']}] {step['description']}{hitl_info}")

    print("\n[Validation]")
    plan = result3.get('plan', [])
    hitl_steps = [s for s in plan if s['agent'] == 'hitl']
    print(f"✓ HITL steps included: {len(hitl_steps)}")
    print(f"✓ Total steps: {len(plan)}")
    print(f"✓ Is executing: {result3.get('is_executing', False)}")

    print("\n" + "=" * 80)
    print("Phase 2 Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_phase2())
