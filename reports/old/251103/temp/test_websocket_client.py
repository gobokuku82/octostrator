"""
WebSocket Test Client
간단한 WebSocket 테스트 클라이언트
"""

import asyncio
import json
import websockets
from datetime import datetime


async def test_websocket():
    """WebSocket 연결 및 쿼리 테스트"""

    # 1. 세션 생성 (HTTP POST /api/v1/chat/start)
    print("=" * 60)
    print("1. Session 생성 (HTTP POST 필요 - 수동으로 먼저 생성)")
    print("   curl -X POST http://localhost:8000/api/v1/chat/start")
    print("=" * 60)

    session_id = input("생성된 session_id 입력: ").strip()
    if not session_id:
        session_id = "test-session-001"
        print(f"기본값 사용: {session_id}")

    # 2. WebSocket 연결
    uri = f"ws://localhost:8000/api/v1/chat/ws/{session_id}"
    print(f"\n2. WebSocket 연결: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 연결 성공!\n")

            # 3. 연결 확인 메시지 수신
            connected_msg = await websocket.recv()
            print(f"📥 Server: {connected_msg}\n")

            # 4. 쿼리 전송
            query = input("테스트 쿼리 입력 (Enter=기본값): ").strip()
            if not query:
                query = "강남구 아파트 시세 알려줘"
                print(f"기본값 사용: {query}")

            query_message = {
                "type": "query",
                "query": query,
                "enable_checkpointing": True
            }

            print(f"\n📤 Sending: {json.dumps(query_message, ensure_ascii=False)}\n")
            await websocket.send(json.dumps(query_message))

            # 5. 실시간 메시지 수신 (10초 타임아웃)
            print("=" * 60)
            print("실시간 메시지 수신 중...")
            print("=" * 60)

            message_count = 0
            timeout = 30  # 30초

            try:
                async for message in websocket:
                    message_count += 1
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    timestamp = data.get("timestamp", "")

                    print(f"\n[{message_count}] Type: {msg_type}")
                    print(f"    Time: {timestamp}")

                    if msg_type == "connected":
                        print(f"    Session: {data.get('session_id')}")

                    elif msg_type == "plan_ready":
                        print(f"    Plan: {data.get('plan', {}).get('execution_strategy', 'N/A')}")
                        print(f"    Todos: {len(data.get('todos', []))} items")

                    elif msg_type == "todo_created":
                        todos = data.get('todos', [])
                        print(f"    Created {len(todos)} todos")
                        for todo in todos:
                            print(f"      - {todo.get('task')} ({todo.get('status')})")

                    elif msg_type == "todo_updated":
                        todo = data.get('todo', {})
                        print(f"    Updated: {todo.get('task')} → {todo.get('status')}")

                    elif msg_type == "step_start":
                        print(f"    Agent: {data.get('agent')}")
                        print(f"    Task: {data.get('task')}")

                    elif msg_type == "step_progress":
                        print(f"    Agent: {data.get('agent')}")
                        print(f"    Progress: {data.get('progress')}%")

                    elif msg_type == "step_complete":
                        print(f"    Agent: {data.get('agent')}")
                        print(f"    Status: {data.get('status', 'completed')}")

                    elif msg_type == "final_response":
                        print(f"    Response: {json.dumps(data.get('response', {}), ensure_ascii=False, indent=2)}")
                        print("\n✅ 처리 완료!")
                        break  # 최종 응답 수신 후 종료

                    elif msg_type == "error":
                        print(f"    ❌ Error: {data.get('error')}")
                        print(f"    Details: {data.get('details', {})}")
                        break

                    else:
                        print(f"    Data: {json.dumps(data, ensure_ascii=False, indent=2)}")

            except asyncio.TimeoutError:
                print(f"\n⏱️ Timeout ({timeout}초 경과)")

            print(f"\n총 {message_count}개 메시지 수신")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket 연결 실패: {e}")
        print("   - 세션이 존재하는지 확인하세요 (POST /api/v1/chat/start)")
        print("   - 백엔드 서버가 실행 중인지 확인하세요")

    except ConnectionRefusedError:
        print("❌ 연결 거부: 백엔드 서버가 실행 중이 아닙니다")
        print("   venv/Scripts/python -m uvicorn app.main:app --reload")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         WebSocket Test Client (Beta v001)                ║
    ╚══════════════════════════════════════════════════════════╝

    사전 준비:
    1. 백엔드 서버 실행: venv/Scripts/python -m uvicorn app.main:app --reload
    2. 세션 생성: curl -X POST http://localhost:8000/api/v1/chat/start
    """)

    asyncio.run(test_websocket())
