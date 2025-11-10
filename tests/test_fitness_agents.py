"""Fitness Agents 테스트 스크립트

5개 새 에이전트가 정상적으로 동작하는지 테스트합니다.
"""
import asyncio
import sys
import os

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def test_graph_build():
    """그래프 빌드 테스트"""
    print("\n=== 테스트 1: 그래프 빌드 ===\n")

    try:
        from backend.app.octostrator.supervisor.graph import build_supervisor_graph

        # 그래프 빌드 (Checkpointer 없이)
        graph = build_supervisor_graph()

        print("✅ 그래프 빌드 성공!")
        print(f"   노드 수: {len(graph.nodes)}")

        # 노드 목록 확인
        print("\n등록된 노드:")
        for node_name in graph.nodes:
            print(f"  - {node_name}")

        return True

    except Exception as e:
        print(f"❌ 그래프 빌드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_imports():
    """에이전트 import 테스트"""
    print("\n=== 테스트 2: 에이전트 Import ===\n")

    try:
        from backend.app.octostrator.agents import (
            diet_agent_node,
            workout_agent_node,
            schedule_agent_node,
            member_care_agent_node,
            coaching_agent_node,
        )

        print("✅ 모든 에이전트 import 성공!")
        print("  - diet_agent_node")
        print("  - workout_agent_node")
        print("  - schedule_agent_node")
        print("  - member_care_agent_node")
        print("  - coaching_agent_node")

        return True

    except Exception as e:
        print(f"❌ 에이전트 import 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_simple_execution():
    """간단한 실행 테스트"""
    print("\n=== 테스트 3: 간단한 실행 ===\n")

    try:
        from backend.app.octostrator.supervisor.graph import build_supervisor_graph
        from backend.app.octostrator.states.supervisor_state import SupervisorState

        # 그래프 빌드
        graph = build_supervisor_graph()

        # 초기 상태
        initial_state = {
            "user_query": "최근 식단 기록 보여줘",
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

        print("📝 사용자 쿼리: '최근 식단 기록 보여줘'")
        print("\n그래프 실행 중...\n")

        # 그래프 실행
        config = {"configurable": {"thread_id": "test_001"}}
        final_state = None

        async for state in graph.astream(initial_state, config):
            # 각 노드 실행 결과 출력
            for node_name, node_state in state.items():
                print(f"[노드: {node_name}]")

                if "plan" in node_state and node_state["plan"]:
                    plan = node_state["plan"]
                    print(f"  계획: {len(plan)}단계")
                    for step in plan:
                        status_emoji = "✅" if step["status"] == "completed" else "⏳"
                        print(f"    {status_emoji} Step {step['step_id']}: [{step['agent']}] {step['description']}")

                if "messages" in node_state and node_state["messages"]:
                    last_msg = node_state["messages"][-1]
                    if hasattr(last_msg, "content"):
                        content = last_msg.content
                        # 긴 내용은 요약
                        if len(content) > 200:
                            content = content[:200] + "..."
                        print(f"  메시지: {content}")

                print()

            final_state = state

        if final_state:
            print("✅ 그래프 실행 완료!")
            return True
        else:
            print("❌ 그래프 실행 결과 없음")
            return False

    except Exception as e:
        print(f"❌ 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("Fitness Agents 테스트")
    print("=" * 60)

    results = []

    # 테스트 1: 그래프 빌드
    results.append(await test_graph_build())

    # 테스트 2: 에이전트 import
    results.append(await test_agent_imports())

    # 테스트 3: 간단한 실행
    results.append(await test_simple_execution())

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"총 테스트: {len(results)}개")
    print(f"성공: {sum(results)}개")
    print(f"실패: {len(results) - sum(results)}개")

    if all(results):
        print("\n🎉 모든 테스트 통과!")
        return 0
    else:
        print("\n⚠️ 일부 테스트 실패")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
