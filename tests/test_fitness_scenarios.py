"""Fitness 시나리오 테스트

실제 Fitness 도메인 쿼리로 테스트합니다.
"""
import asyncio
import sys
import os

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def test_scenario(query: str, thread_id: str):
    """시나리오 테스트"""
    print(f"\n{'='*60}")
    print(f"쿼리: '{query}'")
    print('=' * 60)

    try:
        from backend.app.octostrator.supervisor.graph import build_supervisor_graph

        # 그래프 빌드
        graph = build_supervisor_graph()

        # 초기 상태
        initial_state = {
            "user_query": query,
            "user_intent": "",
            "plan": [],
            "current_step": 0,
            "is_planning": True,
            "is_executing": False,
            "is_waiting_human": False,
            "messages": [],
            "aggregated_data": {},
            "output_format": "chat",
            "final_answer": "",
        }

        # 그래프 실행
        config = {"configurable": {"thread_id": thread_id}}

        print("\n실행 중...\n")

        step_count = 0
        async for state in graph.astream(initial_state, config):
            step_count += 1

            for node_name, node_state in state.items():
                print(f"[Step {step_count}: {node_name}]")

                # Plan 출력
                if "plan" in node_state and node_state["plan"]:
                    plan = node_state["plan"]
                    print(f"\n📋 계획 ({len(plan)}단계):")
                    for step in plan:
                        status = "✅" if step["status"] == "completed" else "⏳"
                        print(f"  {status} {step['step_id']}. [{step['agent']}] {step['description']}")

                # Messages 출력
                if "messages" in node_state and node_state["messages"]:
                    last_msg = node_state["messages"][-1]
                    if hasattr(last_msg, "content"):
                        content = last_msg.content
                        print(f"\n💬 응답:\n{content}")

                print()

        print(f"✅ 완료 (총 {step_count} 단계)\n")
        return True

    except Exception as e:
        print(f"\n❌ 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 함수"""
    print("=" * 60)
    print("Fitness Agents 시나리오 테스트")
    print("=" * 60)

    scenarios = [
        ("최근 식단 기록 보여줘", "scenario_1"),
        ("오늘 하체 운동 루틴 추천해줘", "scenario_2"),
        ("김철수 회원의 진행 상황 알려줘", "scenario_3"),
        ("예정된 PT 스케줄 확인", "scenario_4"),
        ("스쿼트 자세 영상 찾아줘", "scenario_5"),
    ]

    results = []

    for query, thread_id in scenarios:
        result = await test_scenario(query, thread_id)
        results.append(result)
        await asyncio.sleep(1)  # 각 테스트 사이에 잠깐 대기

    # 결과 요약
    print("\n" + "=" * 60)
    print("시나리오 테스트 결과")
    print("=" * 60)
    print(f"총 시나리오: {len(results)}개")
    print(f"성공: {sum(results)}개")
    print(f"실패: {len(results) - sum(results)}개")

    if all(results):
        print("\n🎉 모든 시나리오 테스트 통과!")
        return 0
    else:
        print("\n⚠️ 일부 시나리오 실패")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
