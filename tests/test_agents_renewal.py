"""
Agent Renewal Test
Phase 4.3: 새 구조 테스트 (cognitive_nodes + response_nodes)

4개 에이전트 Quick Button 테스트:
1. diet - 식단 조회
2. workout - 운동 추천
3. schedule - PT 스케줄
4. coaching - 자료 검색
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python Path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.app.octostrator.supervisor import build_supervisor_graph
from backend.app.octostrator.states.supervisor_state import SupervisorState
from langchain_core.messages import HumanMessage


async def test_agent(agent_name: str, query: str):
    """단일 에이전트 테스트"""
    print(f"\n{'='*60}")
    print(f"Testing: {agent_name}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")

    # 그래프 생성 (Checkpointer 없이)
    graph = build_supervisor_graph()

    # 초기 상태
    initial_state: SupervisorState = {
        "messages": [HumanMessage(content=query)],
        "user_query": query,
        "user_intent": "",
        "plan": [],
        "current_step": 0,
        "is_planning": False,
        "is_executing": False,
        "is_waiting_human": False,
        "aggregated_data": {},
        "final_result": "",
        "output_format": "chat"  # chat/graph/report
    }

    # 실행
    try:
        final_state = await graph.ainvoke(initial_state)

        print("\n[✓] 테스트 성공!")
        print(f"실행된 단계: {len(final_state.get('plan', []))}개")
        print(f"최종 결과 존재: {'final_result' in final_state and bool(final_state['final_result'])}")

        # 최종 결과 출력 (처음 300자만)
        if final_state.get('final_result'):
            result = final_state['final_result']
            if isinstance(result, str):
                print(f"\n최종 결과 미리보기:\n{result[:300]}...")
            elif isinstance(result, dict):
                print(f"\n최종 결과 타입: {result.get('nodes', []).__class__.__name__}")

        return True

    except Exception as e:
        print(f"\n[✗] 테스트 실패!")
        print(f"에러: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """모든 에이전트 테스트"""
    print("\n" + "="*60)
    print("Phase 4.3 Renewal Test: 새 구조 검증")
    print("="*60)

    # 테스트 케이스
    test_cases = [
        ("diet", "오늘 식단 기록 보여줘"),
        ("workout", "하체 운동 루틴 추천해줘"),
        ("schedule", "내일 PT 스케줄 확인"),
        ("coaching", "스쿼트 자세 영상 찾아줘"),
    ]

    results = []
    for agent_name, query in test_cases:
        success = await test_agent(agent_name, query)
        results.append((agent_name, success))

        # 각 테스트 사이에 짧은 대기
        await asyncio.sleep(1)

    # 최종 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)

    for agent_name, success in results:
        status = "✓ 성공" if success else "✗ 실패"
        print(f"{agent_name:15s} {status}")

    success_count = sum(1 for _, s in results if s)
    total_count = len(results)

    print(f"\n총 {total_count}개 중 {success_count}개 성공")

    if success_count == total_count:
        print("\n🎉 모든 에이전트가 새 구조에서 정상 작동합니다!")
        return 0
    else:
        print("\n⚠️ 일부 에이전트 테스트 실패")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
