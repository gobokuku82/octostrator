"""Phase 4.1 테스트

PostgreSQL Checkpointer 통합 검증
"""
import asyncio
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph
from backend.app.octostrator.checkpointer import create_checkpointer, setup_tables
from backend.app.octostrator.session import create_session, get_session_config

# Windows에서 psycopg 호환성을 위한 EventLoop 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# .env 파일 로드
load_dotenv()


async def test_setup_tables():
    """Checkpoint 테이블 생성 테스트 (선택적)

    Note: create_checkpointer()가 자동으로 setup()을 호출하므로
    이 테스트는 선택적입니다.
    """
    print("\n" + "=" * 80)
    print("TEST 1: SETUP CHECKPOINT TABLES (Optional)")
    print("=" * 80)

    try:
        # setup_tables()는 내부적으로 create_checkpointer()를 호출
        await setup_tables()
        print("✓ Checkpoint 테이블 설정 성공")
        return True
    except Exception as e:
        print(f"❌ 테이블 설정 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_checkpointer_initialization():
    """Checkpointer 생성 테스트 (CheckpointerManager 패턴)"""
    print("\n" + "=" * 80)
    print("TEST 2: CHECKPOINTER CREATION (CheckpointerManager)")
    print("=" * 80)

    try:
        checkpointer = await create_checkpointer()  # 비동기 함수 (AsyncPostgresSaver 반환)
        print("✓ Checkpointer 생성 성공 (연결 유지)")
        print(f"✓ Type: {type(checkpointer)}")
        return True, checkpointer
    except Exception as e:
        print(f"❌ Checkpointer 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_graph_with_checkpointer(checkpointer):
    """Checkpointer와 함께 그래프 빌드 테스트"""
    print("\n" + "=" * 80)
    print("TEST 2: GRAPH WITH CHECKPOINTER")
    print("=" * 80)

    try:
        graph = build_supervisor_graph(checkpointer=checkpointer)
        print("✓ Checkpointer와 함께 그래프 빌드 성공")
        return True, graph
    except Exception as e:
        print(f"❌ 그래프 빌드 실패: {e}")
        return False, None


async def test_session_creation():
    """세션 생성 테스트"""
    print("\n" + "=" * 80)
    print("TEST 3: SESSION CREATION")
    print("=" * 80)

    try:
        thread_id = create_session(user_id="test_user", metadata={"test": "phase4_1"})
        print(f"✓ 세션 생성 성공: {thread_id}")

        config = get_session_config(thread_id)
        print(f"✓ Config 생성 성공: {config}")

        return True, thread_id, config
    except Exception as e:
        print(f"❌ 세션 생성 실패: {e}")
        return False, None, None


async def test_graph_execution_with_checkpoint(graph, config):
    """Checkpointer를 사용한 그래프 실행 테스트"""
    print("\n" + "=" * 80)
    print("TEST 4: GRAPH EXECUTION WITH CHECKPOINT")
    print("=" * 80)

    try:
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="간단한 검색 작업")],
                "output_format": "chat"
            },
            config=config
        )

        print("✓ 그래프 실행 성공")
        print(f"✓ Final Result Length: {len(str(result.get('final_result', '')))}")
        print(f"✓ Messages Count: {len(result.get('messages', []))}")

        # 결과 일부 출력
        final_result = result.get('final_result', '')
        if final_result:
            print(f"\n[Final Result Preview (처음 200자)]:")
            print(final_result[:200] + "...")

        return True, result
    except Exception as e:
        print(f"❌ 그래프 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_state_persistence(graph, thread_id, config):
    """State 영속화 테스트"""
    print("\n" + "=" * 80)
    print("TEST 5: STATE PERSISTENCE")
    print("=" * 80)

    try:
        # State 조회
        state_snapshot = await graph.aget_state(config)

        print("✓ State 조회 성공")
        print(f"✓ State Type: {type(state_snapshot)}")
        print(f"✓ Thread ID: {thread_id}")

        # State 내용 확인
        state_values = state_snapshot.values
        print(f"✓ State Keys: {list(state_values.keys())}")

        if "plan" in state_values:
            plan = state_values["plan"]
            print(f"✓ Plan Length: {len(plan)}")
            print(f"✓ Current Step: {state_values.get('current_step', 'N/A')}")

        if "aggregated_data" in state_values:
            print("✓ Aggregated Data 존재")

        return True
    except Exception as e:
        print(f"❌ State 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_state_restoration(graph, config):
    """State 복원 테스트"""
    print("\n" + "=" * 80)
    print("TEST 6: STATE RESTORATION")
    print("=" * 80)

    try:
        # 동일한 thread_id로 새로운 메시지 전송
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="두 번째 요청")]
            },
            config=config
        )

        print("✓ State 복원 후 실행 성공")
        print(f"✓ Messages Count: {len(result.get('messages', []))}")

        return True
    except Exception as e:
        print(f"❌ State 복원 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Phase 4.1 전체 테스트"""
    print("=" * 80)
    print("PHASE 4.1 TEST: POSTGRESQL CHECKPOINTER")
    print("=" * 80)

    results = {}

    # Test 1: Checkpointer 초기화
    test1_pass, checkpointer = await test_checkpointer_initialization()
    results["checkpointer_init"] = test1_pass

    if not test1_pass:
        print("\n❌ Checkpointer 초기화 실패 - 이후 테스트 중단")
        return

    # Test 2: 그래프 빌드
    test2_pass, graph = await test_graph_with_checkpointer(checkpointer)
    results["graph_build"] = test2_pass

    if not test2_pass:
        print("\n❌ 그래프 빌드 실패 - 이후 테스트 중단")
        return

    # Test 3: 세션 생성
    test3_pass, thread_id, config = await test_session_creation()
    results["session_creation"] = test3_pass

    if not test3_pass:
        print("\n❌ 세션 생성 실패 - 이후 테스트 중단")
        return

    # Test 4: 그래프 실행 (Checkpoint 저장)
    test4_pass, result = await test_graph_execution_with_checkpoint(graph, config)
    results["graph_execution"] = test4_pass

    if not test4_pass:
        print("\n❌ 그래프 실행 실패 - 이후 테스트 중단")
        return

    # Test 5: State 영속화 확인
    test5_pass = await test_state_persistence(graph, thread_id, config)
    results["state_persistence"] = test5_pass

    # Test 6: State 복원 테스트
    test6_pass = await test_state_restoration(graph, config)
    results["state_restoration"] = test6_pass

    # 최종 결과
    print("\n" + "=" * 80)
    print("검증 결과:")
    print("=" * 80)
    print(f"✓ Checkpointer 초기화: {'통과' if results['checkpointer_init'] else '실패'}")
    print(f"✓ 그래프 빌드: {'통과' if results['graph_build'] else '실패'}")
    print(f"✓ 세션 생성: {'통과' if results['session_creation'] else '실패'}")
    print(f"✓ 그래프 실행 (Checkpoint 저장): {'통과' if results['graph_execution'] else '실패'}")
    print(f"✓ State 영속화: {'통과' if results['state_persistence'] else '실패'}")
    print(f"✓ State 복원: {'통과' if results['state_restoration'] else '실패'}")

    print("\n" + "=" * 80)
    if all(results.values()):
        print("🎉 Phase 4.1 테스트 성공!")
        print("\n✅ PostgreSQL Checkpointer 통합 완료")
        print("✅ State 영속화 및 복원 정상 동작")
        print("✅ 다음 단계: Phase 4.2 (HITL Interrupt 구현)")
    else:
        print("❌ Phase 4.1 테스트 실패 - 일부 검증 실패")
        failed_tests = [k for k, v in results.items() if not v]
        print(f"\n실패한 테스트: {', '.join(failed_tests)}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
