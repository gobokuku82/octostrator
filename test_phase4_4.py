"""Phase 4.4 테스트

REST API 세션 관리 검증
"""
import asyncio
import sys
import requests
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph
from backend.app.octostrator.checkpointer import create_checkpointer
from backend.app.octostrator.session import get_session_config

# .env 파일 로드
load_dotenv()

# Windows에서 psycopg 호환성을 위한 EventLoop 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


BASE_URL = "http://localhost:8000"


def test_list_sessions():
    """세션 목록 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 1: 세션 목록 조회")
    print("=" * 80)

    try:
        response = requests.get(f"{BASE_URL}/api/sessions")
        response.raise_for_status()

        data = response.json()
        print(f"✓ 세션 목록 조회 성공")
        print(f"  - 총 세션 수: {data['total']}")
        print(f"  - 세션 목록: {len(data['sessions'])}개")

        for session in data['sessions'][:3]:  # 처음 3개만 출력
            print(f"    - {session.get('thread_id', 'N/A')}: {session.get('status', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ 세션 목록 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_session_state():
    """세션 상태 조회 테스트

    1. 새 세션 생성 (graph 실행)
    2. 세션 상태 조회
    """
    print("\n" + "=" * 80)
    print("TEST 2: 세션 상태 조회")
    print("=" * 80)

    try:
        # 1. 새 세션 생성
        thread_id = "test_session_state_001"
        print(f"\n[1단계] 새 세션 생성: {thread_id}")

        checkpointer = await create_checkpointer()
        graph = build_supervisor_graph(checkpointer=checkpointer)
        config = get_session_config(thread_id)

        # 간단한 작업 실행 (interrupt 없이)
        initial_input = {
            "messages": [HumanMessage(content="안녕하세요")],
            "output_format": "chat"
        }

        print("  그래프 실행 중...")
        result = await graph.ainvoke(initial_input, config=config)
        print(f"  ✓ 그래프 실행 완료")

        # 2. REST API로 세션 상태 조회
        print(f"\n[2단계] REST API로 세션 상태 조회")
        response = requests.get(f"{BASE_URL}/api/sessions/{thread_id}")
        response.raise_for_status()

        data = response.json()
        print(f"✓ 세션 상태 조회 성공")
        print(f"  - thread_id: {data['thread_id']}")
        print(f"  - status: {data['status']}")
        print(f"  - checkpoint_id: {data.get('checkpoint_id', 'N/A')}")
        print(f"  - state keys: {list(data['state'].keys())}")

        return True

    except Exception as e:
        print(f"❌ 세션 상태 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hitl_resume():
    """HITL 재개 테스트

    1. HITL이 포함된 세션 생성
    2. interrupt로 대기
    3. REST API로 재개
    """
    print("\n" + "=" * 80)
    print("TEST 3: HITL 재개")
    print("=" * 80)

    try:
        thread_id = "test_hitl_resume_001"
        print(f"\n[1단계] HITL 포함 세션 생성: {thread_id}")

        checkpointer = await create_checkpointer()
        graph = build_supervisor_graph(checkpointer=checkpointer)
        config = get_session_config(thread_id)

        # HITL이 포함될 수 있는 작업 (계약서 작성)
        initial_input = {
            "messages": [HumanMessage(content="간단한 계약서를 작성해주세요")],
            "output_format": "chat"
        }

        print("  그래프 실행 중... (HITL interrupt 예상)")

        try:
            # interrupt 발생 시 여기서 멈춤
            result = await graph.ainvoke(initial_input, config=config)

            # interrupt 없이 완료된 경우
            print("  ⚠ HITL 단계가 계획에 포함되지 않음 (간단한 작업으로 판단)")
            return False

        except Exception as e:
            # interrupt 발생 (정상)
            if "interrupt" in str(e).lower():
                print(f"  ✓ interrupt 발생 (예상된 동작)")
            else:
                raise

        # 2. 세션 상태 확인
        print(f"\n[2단계] HITL 대기 상태 확인")
        response = requests.get(f"{BASE_URL}/api/sessions/{thread_id}")
        response.raise_for_status()

        data = response.json()
        print(f"  - status: {data['status']}")

        if data['status'] != 'waiting_human':
            print(f"  ⚠ 예상 상태: waiting_human, 실제: {data['status']}")
            return False

        # 3. REST API로 재개 (자동 승인)
        print(f"\n[3단계] REST API로 HITL 재개 (자동 승인)")
        resume_response = requests.post(
            f"{BASE_URL}/api/sessions/{thread_id}/resume",
            json={"approve": True}
        )
        resume_response.raise_for_status()

        resume_data = resume_response.json()
        print(f"✓ HITL 재개 성공")
        print(f"  - success: {resume_data['success']}")
        print(f"  - message: {resume_data['message']}")

        return True

    except Exception as e:
        print(f"❌ HITL 재개 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_checkpoints():
    """체크포인트 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 4: 체크포인트 조회")
    print("=" * 80)

    try:
        # 1. 세션 생성 및 실행
        thread_id = "test_checkpoints_001"
        print(f"\n[1단계] 세션 생성 및 실행: {thread_id}")

        checkpointer = await create_checkpointer()
        graph = build_supervisor_graph(checkpointer=checkpointer)
        config = get_session_config(thread_id)

        initial_input = {
            "messages": [HumanMessage(content="테스트 메시지")],
            "output_format": "chat"
        }

        print("  그래프 실행 중...")
        result = await graph.ainvoke(initial_input, config=config)
        print(f"  ✓ 그래프 실행 완료")

        # 2. 체크포인트 목록 조회
        print(f"\n[2단계] 체크포인트 목록 조회")
        response = requests.get(f"{BASE_URL}/api/sessions/{thread_id}/checkpoints")
        response.raise_for_status()

        data = response.json()
        print(f"✓ 체크포인트 조회 성공")
        print(f"  - 총 체크포인트 수: {data['total']}")

        for i, cp in enumerate(data['checkpoints'][:5]):  # 처음 5개만 출력
            print(f"  [{i}] step: {cp['step']}, id: {cp['checkpoint_id'][:16]}...")

        return data['total'] > 0

    except Exception as e:
        print(f"❌ 체크포인트 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_session_history():
    """세션 히스토리 조회 테스트"""
    print("\n" + "=" * 80)
    print("TEST 5: 세션 히스토리 조회")
    print("=" * 80)

    try:
        # 1. 세션 생성
        thread_id = "test_history_001"
        print(f"\n[1단계] 세션 생성: {thread_id}")

        checkpointer = await create_checkpointer()
        graph = build_supervisor_graph(checkpointer=checkpointer)
        config = get_session_config(thread_id)

        initial_input = {
            "messages": [HumanMessage(content="히스토리 테스트")],
            "output_format": "chat"
        }

        print("  그래프 실행 중...")
        result = await graph.ainvoke(initial_input, config=config)
        print(f"  ✓ 그래프 실행 완료")

        # 2. 히스토리 조회
        print(f"\n[2단계] 세션 히스토리 조회")
        response = requests.get(f"{BASE_URL}/api/sessions/{thread_id}/history?limit=10")
        response.raise_for_status()

        data = response.json()
        print(f"✓ 히스토리 조회 성공")
        print(f"  - thread_id: {data['thread_id']}")
        print(f"  - total_messages: {data['total_messages']}")
        print(f"  - returned_messages: {data['returned_messages']}")

        for i, msg in enumerate(data['messages'][:3]):  # 처음 3개만 출력
            content_preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            print(f"  [{i}] {msg['type']}: {content_preview}")

        return data['returned_messages'] > 0

    except Exception as e:
        print(f"❌ 세션 히스토리 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_session():
    """세션 삭제 테스트"""
    print("\n" + "=" * 80)
    print("TEST 6: 세션 삭제")
    print("=" * 80)

    try:
        # 삭제할 세션 (존재하지 않아도 됨)
        thread_id = "test_delete_001"
        print(f"\n세션 삭제 시도: {thread_id}")

        response = requests.delete(f"{BASE_URL}/api/sessions/{thread_id}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ 세션 삭제 성공")
            print(f"  - message: {data['message']}")
            return True
        elif response.status_code == 404:
            print(f"⚠ 세션이 존재하지 않음 (정상)")
            return True
        else:
            print(f"❌ 예상치 못한 응답: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 세션 삭제 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Phase 4.4 전체 테스트"""
    print("=" * 80)
    print("PHASE 4.4 TEST: REST API 세션 관리")
    print("=" * 80)
    print("\n⚠ 테스트 실행 전에 서버가 실행 중이어야 합니다:")
    print("  uv run python run_server.py")
    print()

    results = {}

    # Test 1: 세션 목록 조회
    results["list_sessions"] = test_list_sessions()

    # Test 2: 세션 상태 조회
    results["session_state"] = await test_session_state()

    # Test 3: HITL 재개
    results["hitl_resume"] = await test_hitl_resume()

    # Test 4: 체크포인트 조회
    results["checkpoints"] = await test_checkpoints()

    # Test 5: 세션 히스토리 조회
    results["history"] = await test_session_history()

    # Test 6: 세션 삭제
    results["delete"] = test_delete_session()

    # 최종 결과
    print("\n" + "=" * 80)
    print("검증 결과:")
    print("=" * 80)
    print(f"✓ 세션 목록 조회: {'통과' if results['list_sessions'] else '실패'}")
    print(f"✓ 세션 상태 조회: {'통과' if results['session_state'] else '실패'}")
    print(f"✓ HITL 재개: {'통과' if results['hitl_resume'] else '실패'}")
    print(f"✓ 체크포인트 조회: {'통과' if results['checkpoints'] else '실패'}")
    print(f"✓ 세션 히스토리 조회: {'통과' if results['history'] else '실패'}")
    print(f"✓ 세션 삭제: {'통과' if results['delete'] else '실패'}")

    print("\n" + "=" * 80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    if passed == total:
        print(f"🎉 Phase 4.4 테스트 성공! ({passed}/{total})")
        print("\n✅ REST API 세션 관리 구현 완료")
        print("✅ HITL 재개 API 정상 동작")
        print("✅ 체크포인트 조회 정상 동작")
        print("✅ Phase 4 전체 완료!")
    else:
        print(f"⚠ Phase 4.4 테스트 부분 성공 ({passed}/{total})")
        failed_tests = [k for k, v in results.items() if not v]
        print(f"\n실패한 테스트: {', '.join(failed_tests)}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
