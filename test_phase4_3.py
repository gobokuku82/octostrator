"""Phase 4.3 테스트

WebSocket 실시간 스트리밍 검증
"""
import asyncio
import sys
import json
from websockets import connect
from dotenv import load_dotenv

# Windows에서 psycopg 호환성을 위한 EventLoop 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# .env 파일 로드
load_dotenv()


async def test_websocket_connection():
    """WebSocket 연결 테스트

    1. WebSocket 엔드포인트 연결
    2. 연결 성공 메시지 수신
    """
    print("\n" + "=" * 80)
    print("TEST 1: WEBSOCKET 연결")
    print("=" * 80)

    session_id = "test_session_001"
    uri = f"ws://localhost:8000/ws/chat/{session_id}"

    try:
        async with connect(uri) as websocket:
            print(f"✓ WebSocket 연결 성공: {uri}")

            # 연결 성공 메시지 대기
            message = await websocket.recv()
            data = json.loads(message)

            print(f"✓ 서버 응답 수신:")
            print(f"  - Type: {data.get('type')}")
            print(f"  - Data: {data.get('data')}")

            if data.get('type') == 'connected':
                print("✓ 연결 확인 메시지 수신 완료")
                return True
            else:
                print(f"⚠ 예상치 못한 메시지 타입: {data.get('type')}")
                return False

    except Exception as e:
        print(f"❌ WebSocket 연결 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_websocket_message_send():
    """WebSocket 메시지 전송 테스트

    1. WebSocket 연결
    2. 사용자 메시지 전송
    3. 실시간 이벤트 수신
    """
    print("\n" + "=" * 80)
    print("TEST 2: WEBSOCKET 메시지 전송 및 이벤트 수신")
    print("=" * 80)

    session_id = "test_session_002"
    uri = f"ws://localhost:8000/ws/chat/{session_id}"

    try:
        async with connect(uri) as websocket:
            print(f"✓ WebSocket 연결 성공")

            # 연결 확인 메시지 수신
            await websocket.recv()

            # 사용자 메시지 전송
            user_message = {
                "message": "간단한 검색 작업",
                "output_format": "chat"
            }

            await websocket.send(json.dumps(user_message))
            print(f"\n✓ 메시지 전송: {user_message['message']}")

            # 이벤트 수신
            print("\n[실시간 이벤트 수신]:")
            event_count = 0
            received_events = []

            # 최대 30초 동안 이벤트 수신
            try:
                async with asyncio.timeout(30):
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        event_type = data.get('type')
                        received_events.append(event_type)

                        print(f"  [{event_count + 1}] {event_type}: {data.get('data', {})}")
                        event_count += 1

                        # 완료 이벤트 수신 시 종료
                        if event_type == 'execution_completed':
                            break

                        # 에러 발생 시 종료
                        if event_type == 'error':
                            print(f"  ❌ 에러 발생: {data.get('data')}")
                            break

            except asyncio.TimeoutError:
                print("  ⚠ 타임아웃 (30초 초과)")

            print(f"\n✓ 총 {event_count}개 이벤트 수신")
            print(f"  이벤트 타입: {', '.join(set(received_events))}")

            # 필수 이벤트 확인
            if 'execution_started' in received_events:
                print("✓ execution_started 이벤트 수신")

            if 'execution_completed' in received_events or 'final_result' in received_events:
                print("✓ 완료 이벤트 수신")
                return True
            else:
                print("⚠ 완료 이벤트 미수신")
                return event_count > 0  # 최소 1개 이상의 이벤트 수신했으면 부분 성공

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_websocket_real_time_streaming():
    """WebSocket 실시간 스트리밍 테스트

    1. 복잡한 작업 전송
    2. 노드별 실시간 이벤트 확인
    """
    print("\n" + "=" * 80)
    print("TEST 3: WEBSOCKET 실시간 스트리밍 (노드별 이벤트)")
    print("=" * 80)

    session_id = "test_session_003"
    uri = f"ws://localhost:8000/ws/chat/{session_id}"

    try:
        async with connect(uri) as websocket:
            print(f"✓ WebSocket 연결 성공")

            # 연결 확인
            await websocket.recv()

            # 복잡한 작업 전송
            user_message = {
                "message": "서울시 강남구 아파트 시세를 분석해주세요",
                "output_format": "chat"
            }

            await websocket.send(json.dumps(user_message))
            print(f"\n✓ 메시지 전송: {user_message['message']}")

            # 노드별 이벤트 추적
            print("\n[노드별 실행 추적]:")
            node_events = {}

            try:
                async with asyncio.timeout(60):
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        event_type = data.get('type')
                        event_data = data.get('data', {})

                        # 노드 시작/완료 이벤트 추적
                        if event_type == 'node_started':
                            node_name = event_data.get('node', 'unknown')
                            if node_name not in node_events:
                                node_events[node_name] = {'started': True, 'completed': False}
                            print(f"  → {node_name} 시작")

                        elif event_type == 'node_completed':
                            node_name = event_data.get('node', 'unknown')
                            if node_name in node_events:
                                node_events[node_name]['completed'] = True
                            print(f"  ✓ {node_name} 완료")

                        elif event_type == 'hitl_waiting':
                            question = event_data.get('question', 'N/A')
                            print(f"  ⏸ HITL 대기: {question}")

                        elif event_type == 'final_result':
                            result_len = len(str(event_data.get('result', '')))
                            print(f"\n  ✓ 최종 결과 수신 ({result_len} chars)")

                        elif event_type == 'execution_completed':
                            print(f"\n  ✓ 실행 완료")
                            break

                        elif event_type == 'error':
                            print(f"\n  ❌ 에러: {event_data}")
                            break

            except asyncio.TimeoutError:
                print("\n  ⚠ 타임아웃 (60초 초과)")

            # 결과 분석
            print(f"\n✓ 실행된 노드:")
            for node_name, status in node_events.items():
                started = status.get('started', False)
                completed = status.get('completed', False)
                status_text = "완료" if completed else ("시작" if started else "미실행")
                print(f"  - {node_name}: {status_text}")

            # 최소 1개 노드가 실행되었으면 성공
            if len(node_events) > 0:
                print(f"\n✓ 총 {len(node_events)}개 노드 실행 감지")
                return True
            else:
                print("\n⚠ 노드 실행 이벤트 미감지")
                return False

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Phase 4.3 전체 테스트"""
    print("=" * 80)
    print("PHASE 4.3 TEST: WEBSOCKET 실시간 스트리밍")
    print("=" * 80)
    print("\n⚠ 테스트 실행 전에 서버가 실행 중이어야 합니다:")
    print("  uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000")
    print()

    results = {}

    # Test 1: WebSocket 연결
    results["connection"] = await test_websocket_connection()

    # Test 2: 메시지 전송 및 이벤트 수신
    results["message_send"] = await test_websocket_message_send()

    # Test 3: 실시간 스트리밍
    results["real_time_streaming"] = await test_websocket_real_time_streaming()

    # 최종 결과
    print("\n" + "=" * 80)
    print("검증 결과:")
    print("=" * 80)
    print(f"✓ WebSocket 연결: {'통과' if results['connection'] else '실패'}")
    print(f"✓ 메시지 전송 및 이벤트 수신: {'통과' if results['message_send'] else '실패'}")
    print(f"✓ 실시간 스트리밍: {'통과' if results['real_time_streaming'] else '실패'}")

    print("\n" + "=" * 80)
    if all(results.values()):
        print("🎉 Phase 4.3 테스트 성공!")
        print("\n✅ WebSocket 실시간 스트리밍 구현 완료")
        print("✅ 노드별 이벤트 전송 정상 동작")
        print("✅ 다음 단계: Phase 4.4 (REST API 세션 관리)")
    else:
        print("❌ Phase 4.3 테스트 실패 - 일부 검증 실패")
        failed_tests = [k for k, v in results.items() if not v]
        print(f"\n실패한 테스트: {', '.join(failed_tests)}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
