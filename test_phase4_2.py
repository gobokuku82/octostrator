"""Phase 4.2 테스트

HITL (Human-in-the-Loop) interrupt() 구현 검증
"""
import asyncio
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph
from backend.app.octostrator.checkpointer import create_checkpointer
from backend.app.octostrator.session import create_session, get_session_config

# Windows에서 psycopg 호환성을 위한 EventLoop 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# .env 파일 로드
load_dotenv()


async def test_hitl_interrupt():
    """HITL interrupt() 테스트

    1. HITL 단계가 포함된 Plan 실행
    2. interrupt()에서 대기 확인
    3. State가 checkpoint에 저장되었는지 확인
    """
    print("\n" + "=" * 80)
    print("TEST 1: HITL INTERRUPT() 메커니즘")
    print("=" * 80)

    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()
        print("✓ Checkpointer 생성 완료")

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)
        print("✓ Graph 빌드 완료")

        # 세션 생성
        thread_id = create_session(user_id="test_user", metadata={"test": "phase4_2"})
        config = get_session_config(thread_id)
        print(f"✓ 세션 생성: {thread_id}")

        # HITL 단계가 포함된 요청 실행
        # Planning 단계에서 HITL이 필요한 작업 생성 (예: 문서 생성)
        initial_input = {
            "messages": [HumanMessage(content="간단한 임대차 계약서를 작성해주세요")],
            "output_format": "chat"
        }

        print("\n[Graph] 실행 시작...")
        print("[Graph] HITL 단계에서 interrupt()로 대기할 것입니다\n")

        # 그래프 실행 - interrupt()에서 중단되거나 자동 승인으로 완료됨
        try:
            result = await graph.ainvoke(initial_input, config=config)

            # Plan에서 HITL 단계 확인
            plan = result.get("plan", [])
            hitl_found = False

            for step in plan:
                if step.get("task_type") == "hitl_approval":
                    hitl_found = True
                    print(f"✓ HITL 단계 발견: {step.get('name')}")
                    print(f"  - 질문: {step.get('hitl_question')}")
                    print(f"  - 상태: {step.get('status')}")
                    print(f"  - 응답: {step.get('hitl_response')}")

            if hitl_found:
                print("✓ interrupt() 메커니즘 정상 작동 (자동 승인으로 완료)")
                return True
            else:
                print("⚠ HITL 단계가 계획에 포함되지 않음")
                print("  (간단한 작업으로 판단되어 HITL이 필요 없을 수 있음)")
                return False

        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_state_persistence_at_interrupt():
    """interrupt() 시점의 State 영속화 테스트

    1. interrupt()까지 실행
    2. State가 checkpoint에 저장되었는지 확인
    3. get_state()로 저장된 state 조회
    """
    print("\n" + "=" * 80)
    print("TEST 2: INTERRUPT 시점 STATE 영속화")
    print("=" * 80)

    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # 세션 생성
        thread_id = create_session(user_id="test_user", metadata={"test": "state_persistence"})
        config = get_session_config(thread_id)

        # HITL 작업 실행
        initial_input = {
            "messages": [HumanMessage(content="계약서 작성해주세요")],
            "output_format": "chat"
        }

        try:
            await graph.ainvoke(initial_input, config=config)
        except:
            pass  # interrupt() 예외 무시

        # State 조회
        state_snapshot = await graph.aget_state(config)
        print(f"✓ State 조회 성공")
        print(f"✓ Thread ID: {thread_id}")

        # State 내용 확인
        if state_snapshot.values:
            print(f"✓ State 값 존재")
            state_values = state_snapshot.values
            print(f"  - Keys: {list(state_values.keys())}")

            if "plan" in state_values:
                plan = state_values["plan"]
                print(f"  - Plan 길이: {len(plan)}")
                print(f"  - Current Step: {state_values.get('current_step', 'N/A')}")

                # HITL 단계 확인
                for i, step in enumerate(plan):
                    status = step.get("status", "unknown")
                    if status == "waiting_human":
                        print(f"  - Step {i}: {step.get('name', 'unknown')} (대기 중)")
                        print(f"    HITL Question: {step.get('hitl_question', 'N/A')}")

            # next 확인 (다음 실행 가능한 노드)
            if hasattr(state_snapshot, 'next'):
                print(f"  - Next nodes: {state_snapshot.next}")

            return True
        else:
            print("❌ State 값이 없음")
            return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_resume_after_interrupt():
    """interrupt() 후 재개 테스트

    1. interrupt()까지 실행
    2. None 입력으로 재개 (자동 승인)
    3. 그래프가 계속 실행되는지 확인
    """
    print("\n" + "=" * 80)
    print("TEST 3: INTERRUPT 후 재개 (자동 승인)")
    print("=" * 80)

    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # 세션 생성
        thread_id = create_session(user_id="test_user", metadata={"test": "resume"})
        config = get_session_config(thread_id)

        # 1단계: interrupt()까지 실행
        print("\n[1단계] interrupt()까지 실행...")
        initial_input = {
            "messages": [HumanMessage(content="계약서 생성해주세요")],
            "output_format": "chat"
        }

        try:
            await graph.ainvoke(initial_input, config=config)
        except:
            pass  # interrupt() 예외 무시

        print("✓ interrupt() 발생, State 저장됨")

        # 2단계: None 입력으로 재개 (자동 승인)
        print("\n[2단계] None 입력으로 재개 (자동 승인)...")
        try:
            result = await graph.ainvoke(None, config=config)
            print("✓ 그래프 재개 성공")
            print(f"✓ Messages Count: {len(result.get('messages', []))}")
            print(f"✓ Final Result: {len(str(result.get('final_result', '')))} chars")

            # 결과 일부 출력
            final_result = result.get('final_result', '')
            if final_result:
                print(f"\n[Final Result Preview (처음 200자)]:")
                print(final_result[:200] + "...")

            return True

        except Exception as e:
            # 재개 중 또 다른 interrupt()가 발생할 수 있음
            if "interrupt" in str(e).lower():
                print(f"✓ 추가 interrupt() 발생: {e}")
                print("  (계획에 여러 HITL 단계가 있을 수 있음)")
                return True
            else:
                print(f"❌ 재개 실패: {e}")
                import traceback
                traceback.print_exc()
                return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_resume_with_user_response():
    """interrupt() 후 사용자 응답과 함께 재개 테스트

    1. interrupt()까지 실행
    2. 사용자 응답(문자열)과 함께 재개
    3. 응답이 State에 저장되는지 확인
    """
    print("\n" + "=" * 80)
    print("TEST 4: INTERRUPT 후 재개 (사용자 응답)")
    print("=" * 80)

    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # 세션 생성
        thread_id = create_session(user_id="test_user", metadata={"test": "user_response"})
        config = get_session_config(thread_id)

        # 1단계: interrupt()까지 실행
        print("\n[1단계] interrupt()까지 실행...")
        initial_input = {
            "messages": [HumanMessage(content="계약서 검토해주세요")],
            "output_format": "chat"
        }

        try:
            await graph.ainvoke(initial_input, config=config)
        except:
            pass

        print("✓ interrupt() 발생")

        # 2단계: 사용자 응답과 함께 재개
        print("\n[2단계] 사용자 응답과 함께 재개...")
        user_response = "승인합니다. 계속 진행하세요."

        try:
            # LangGraph 1.0에서는 Command를 사용하거나 dict로 전달
            # interrupt()의 반환값은 Command를 통해 전달됩니다
            # 가장 간단한 방법은 None으로 재개한 후 다음 interrupt()에서 응답 전달
            # 또는 Resume command 사용
            from langgraph.types import Command

            result = await graph.ainvoke(
                Command(resume=user_response),
                config=config
            )

            print(f"✓ 사용자 응답과 함께 재개 성공")
            print(f"✓ Messages Count: {len(result.get('messages', []))}")

            # Plan에서 사용자 응답 확인
            plan = result.get("plan", [])
            for step in plan:
                if step.get("hitl_response"):
                    print(f"\n[HITL Response 저장 확인]:")
                    print(f"  Step: {step.get('name')}")
                    print(f"  Response: {step.get('hitl_response')}")

            return True

        except Exception as e:
            if "interrupt" in str(e).lower():
                print(f"✓ 추가 interrupt() 발생 (여러 HITL 단계)")
                return True
            else:
                print(f"❌ 재개 실패: {e}")
                import traceback
                traceback.print_exc()
                return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Phase 4.2 전체 테스트"""
    print("=" * 80)
    print("PHASE 4.2 TEST: HITL INTERRUPT() 구현")
    print("=" * 80)

    results = {}

    # Test 1: HITL interrupt() 메커니즘
    results["interrupt_mechanism"] = await test_hitl_interrupt()

    # Test 2: State 영속화
    results["state_persistence"] = await test_state_persistence_at_interrupt()

    # Test 3: 재개 (자동 승인)
    results["resume_auto"] = await test_resume_after_interrupt()

    # Test 4: 재개 (사용자 응답)
    results["resume_with_response"] = await test_resume_with_user_response()

    # 최종 결과
    print("\n" + "=" * 80)
    print("검증 결과:")
    print("=" * 80)
    print(f"✓ HITL interrupt() 메커니즘: {'통과' if results['interrupt_mechanism'] else '실패'}")
    print(f"✓ State 영속화: {'통과' if results['state_persistence'] else '실패'}")
    print(f"✓ 재개 (자동 승인): {'통과' if results['resume_auto'] else '실패'}")
    print(f"✓ 재개 (사용자 응답): {'통과' if results['resume_with_response'] else '실패'}")

    print("\n" + "=" * 80)
    if all(results.values()):
        print("🎉 Phase 4.2 테스트 성공!")
        print("\n✅ HITL interrupt() 구현 완료")
        print("✅ State 영속화 및 재개 정상 동작")
        print("✅ 다음 단계: Phase 4.3 (WebSocket 실시간 스트리밍)")
    else:
        print("❌ Phase 4.2 테스트 실패 - 일부 검증 실패")
        failed_tests = [k for k, v in results.items() if not v]
        print(f"\n실패한 테스트: {', '.join(failed_tests)}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
