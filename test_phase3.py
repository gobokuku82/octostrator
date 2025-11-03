"""Phase 3 테스트

Executor + Agents 동작 검증 (완전한 Execution Loop)
"""
import asyncio
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph


async def test_phase3():
    """Phase 3 기능 테스트"""

    # Graph 생성
    graph = build_supervisor_graph()

    print("=" * 80)
    print("PHASE 3 TEST: COMPLETE EXECUTION LOOP")
    print("=" * 80)

    # 테스트 케이스: 복잡한 멀티 스텝 + HITL
    print("\n테스트: 복잡한 멀티 스텝 요청 (실제 Agent 실행)")
    print("=" * 80)

    result = await graph.ainvoke({
        "messages": [HumanMessage(
            content="지난 분기 매출 분석 후 전년 동기 대비 비교하고 보고서 작성해줘. 각 단계마다 확인할게."
        )]
    })

    print("\n[최종 State]")
    print(f"Plan Steps: {len(result.get('plan', []))}")
    print(f"Current Step: {result.get('current_step', 'N/A')}")
    print(f"Is Executing: {result.get('is_executing', 'N/A')}")
    print(f"Is Waiting Human: {result.get('is_waiting_human', 'N/A')}")

    print("\n[전체 Plan 상태]")
    for step in result.get('plan', []):
        status_emoji = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "waiting_human": "🙋"
        }.get(step['status'], "❓")

        print(f"{status_emoji} Step {step['step_id']}: [{step['agent']}] {step['description']}")
        print(f"   Status: {step['status']}")
        if step.get('result'):
            print(f"   Result: {step['result'][:100]}...")
        if step.get('hitl_response'):
            print(f"   HITL Response: {step['hitl_response']}")
        print()

    print("\n[메시지 흐름]")
    messages = result.get("messages", [])
    print(f"총 메시지 수: {len(messages)}")

    # 최근 5개 메시지만 출력
    print("\n최근 5개 메시지:")
    for i, msg in enumerate(messages[-5:]):
        print(f"\n--- Message {len(messages) - 5 + i + 1} [{msg.__class__.__name__}] ---")
        print(msg.content[:300] + ("..." if len(msg.content) > 300 else ""))

    print("\n[최종 결과]")
    if result.get("final_result"):
        print(result["final_result"])
    else:
        print("(실행 중 또는 대기 중)")

    print("\n" + "=" * 80)
    print("검증 결과:")
    print("=" * 80)

    plan = result.get('plan', [])

    # 검증 1: 모든 단계가 완료되었는가?
    all_completed = all(s['status'] == 'completed' for s in plan)
    print(f"✓ 모든 단계 완료: {all_completed}")
    print(f"  - 완료된 단계: {sum(1 for s in plan if s['status'] == 'completed')}/{len(plan)}")

    # 검증 2: current_step이 plan 길이와 일치하는가?
    current_step = result.get('current_step', 0)
    print(f"✓ Current step: {current_step} (예상: {len(plan)})")

    # 검증 3: HITL 단계가 자동 승인되었는가?
    hitl_steps = [s for s in plan if s['agent'] == 'hitl']
    hitl_auto_approved = all(
        s.get('hitl_response') == "[Auto-approved in Phase 3]"
        for s in hitl_steps
    )
    print(f"✓ HITL 단계 자동 승인: {hitl_auto_approved}")
    print(f"  - HITL 단계 수: {len(hitl_steps)}")

    # 검증 4: is_executing이 False인가?
    is_executing = result.get('is_executing', True)
    print(f"✓ 실행 완료 (is_executing=False): {not is_executing}")

    # 검증 5: final_result가 있는가?
    has_final_result = bool(result.get('final_result'))
    print(f"✓ 최종 결과 존재: {has_final_result}")

    print("\n" + "=" * 80)
    if all([all_completed, current_step == len(plan), hitl_auto_approved, not is_executing, has_final_result]):
        print("🎉 Phase 3 테스트 성공!")
    else:
        print("❌ Phase 3 테스트 실패 - 일부 검증 실패")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_phase3())
