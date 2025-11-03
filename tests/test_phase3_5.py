"""Phase 3.5 테스트

Aggregator + Chat Generator 동작 검증
"""
import asyncio
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph


async def test_phase3_5():
    """Phase 3.5 기능 테스트"""

    # Graph 생성
    graph = build_supervisor_graph()

    print("=" * 80)
    print("PHASE 3.5 TEST: AGGREGATOR + CHAT GENERATOR")
    print("=" * 80)

    # 테스트 케이스: 간단한 멀티 스텝 요청
    print("\n테스트: 간단한 멀티 스텝 요청 (Aggregator + Chat Generator)")
    print("=" * 80)

    result = await graph.ainvoke({
        "messages": [HumanMessage(
            content="지난 분기 매출 데이터를 검색하고 분석해줘."
        )],
        "output_format": "chat"  # Phase 3.5: 출력 형식 지정
    })

    print("\n[최종 State]")
    print(f"Plan Steps: {len(result.get('plan', []))}")
    print(f"Current Step: {result.get('current_step', 'N/A')}")
    print(f"Is Executing: {result.get('is_executing', 'N/A')}")
    print(f"Output Format: {result.get('output_format', 'N/A')}")

    print("\n[Aggregated Data 존재 확인]")
    has_aggregated_data = result.get('aggregated_data') is not None
    print(f"✓ Aggregated Data 존재: {has_aggregated_data}")

    if has_aggregated_data:
        aggregated_data = result['aggregated_data']
        print(f"  - Execution Summary: {aggregated_data.get('execution_summary', {})}")
        print(f"  - Steps Count: {len(aggregated_data.get('steps', []))}")
        print(f"  - Insights Count: {len(aggregated_data.get('insights', []))}")
        print(f"  - Final Answer Preview: {aggregated_data.get('final_answer', '')[:100]}...")

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
        print()

    print("\n[Chat Generator 최종 결과]")
    if result.get("final_result"):
        print(result["final_result"])
    else:
        print("(최종 결과 없음)")

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

    # 검증 3: is_executing이 False인가?
    is_executing = result.get('is_executing', True)
    print(f"✓ 실행 완료 (is_executing=False): {not is_executing}")

    # 검증 4: aggregated_data가 있는가?
    has_aggregated_data = result.get('aggregated_data') is not None
    print(f"✓ Aggregated Data 존재: {has_aggregated_data}")

    # 검증 5: final_result가 Chat Generator 형식인가?
    final_result = result.get('final_result', '')
    has_chat_result = bool(final_result) and "실행 요약" in final_result
    print(f"✓ Chat Generator 결과 존재: {has_chat_result}")

    # 검증 6: Insights가 생성되었는가?
    if has_aggregated_data:
        insights_count = len(result['aggregated_data'].get('insights', []))
        print(f"✓ Insights 생성: {insights_count}개")
    else:
        insights_count = 0

    print("\n" + "=" * 80)
    if all([
        all_completed,
        current_step == len(plan),
        not is_executing,
        has_aggregated_data,
        has_chat_result
    ]):
        print("🎉 Phase 3.5 테스트 성공!")
    else:
        print("❌ Phase 3.5 테스트 실패 - 일부 검증 실패")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_phase3_5())
