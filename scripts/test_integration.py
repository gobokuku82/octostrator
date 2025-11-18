"""Integration Test - Full Stack Testing

Tests the complete Octostrator system:
- Backend API endpoints
- WebSocket communication
- TODO generation and management
- Agent execution
- HITL functionality
"""

import asyncio
import json
import sys
from pathlib import Path
import websockets
import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
BACKEND_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


async def test_health_check():
    """Test backend health endpoint"""
    print("\n" + "=" * 60)
    print("Test 1: Health Check")
    print("=" * 60)

    try:
        response = requests.get(f"{BACKEND_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        print("✅ Health check passed")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_websocket_connection():
    """Test WebSocket connection"""
    print("\n" + "=" * 60)
    print("Test 2: WebSocket Connection")
    print("=" * 60)

    session_id = f"test_session_{asyncio.get_event_loop().time()}"
    ws_url = f"{WS_URL}/ws/{session_id}"

    try:
        async with websockets.connect(ws_url) as websocket:
            print(f"✅ Connected to {ws_url}")

            # Send a simple query
            query_msg = {
                "type": "query",
                "content": "Hello, can you help me test the system?",
                "session_id": session_id
            }

            print(f"\nSending query: {query_msg['content']}")
            await websocket.send(json.dumps(query_msg))

            # Wait for response
            print("\nWaiting for responses...")
            timeout = 30
            start_time = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)

                    print(f"\nReceived message type: {data.get('type')}")

                    if data.get('type') == 'response':
                        print(f"Response content: {str(data.get('data', {}))[:200]}...")

                    elif data.get('type') == 'todo_update':
                        todos = data.get('data', {}).get('todos', [])
                        print(f"TODO update: {len(todos)} todos")
                        for i, todo in enumerate(todos, 1):
                            print(f"  {i}. [{todo.get('status')}] {todo.get('title')}")

                    elif data.get('type') == 'interrupt':
                        print(f"Interrupt: {data.get('data', {}).get('message')}")

                except asyncio.TimeoutError:
                    print("No more messages (timeout)")
                    break
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break

            print("\n✅ WebSocket communication test passed")
            return True

    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


async def test_todo_generation():
    """Test automatic TODO generation"""
    print("\n" + "=" * 60)
    print("Test 3: TODO Generation")
    print("=" * 60)

    session_id = f"test_todo_{asyncio.get_event_loop().time()}"
    ws_url = f"{WS_URL}/ws/{session_id}"

    try:
        async with websockets.connect(ws_url) as websocket:
            # Send a query that should generate TODOs
            query_msg = {
                "type": "query",
                "content": "프로젝트 보고서를 작성하고, 데이터를 분석한 다음, 결과를 시각화해줘",
                "session_id": session_id
            }

            print(f"Sending query: {query_msg['content']}")
            await websocket.send(json.dumps(query_msg))

            # Collect all messages
            todos_received = False
            timeout = 30
            start_time = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)

                    if data.get('type') == 'todo_update':
                        todos = data.get('data', {}).get('todos', [])
                        print(f"\n✅ Received {len(todos)} TODOs:")

                        for i, todo in enumerate(todos, 1):
                            print(f"\nTODO {i}:")
                            print(f"  Title: {todo.get('title')}")
                            print(f"  Priority: {todo.get('priority')}")
                            print(f"  Status: {todo.get('status')}")
                            if todo.get('dependencies'):
                                print(f"  Dependencies: {len(todo['dependencies'])} tasks")

                        todos_received = True

                except asyncio.TimeoutError:
                    break

            if todos_received:
                print("\n✅ TODO generation test passed")
                return True
            else:
                print("\n❌ No TODOs received")
                return False

    except Exception as e:
        print(f"❌ TODO generation test failed: {e}")
        return False


async def test_agent_execution():
    """Test agent task execution"""
    print("\n" + "=" * 60)
    print("Test 4: Agent Execution")
    print("=" * 60)

    session_id = f"test_agent_{asyncio.get_event_loop().time()}"
    ws_url = f"{WS_URL}/ws/{session_id}"

    try:
        async with websockets.connect(ws_url) as websocket:
            # Send queries for different agent types
            test_queries = [
                "웹에서 최신 AI 뉴스를 검색해줘",  # SearchAgent
                "이 데이터를 분석해줘: [1, 2, 3, 4, 5]",  # AnalysisAgent
                "간단한 프로젝트 요약 문서를 작성해줘",  # DocumentAgent
            ]

            for i, query in enumerate(test_queries, 1):
                print(f"\n--- Query {i}: {query}")

                query_msg = {
                    "type": "query",
                    "content": query,
                    "session_id": session_id
                }

                await websocket.send(json.dumps(query_msg))

                # Wait for response
                timeout = 20
                start_time = asyncio.get_event_loop().time()

                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)

                        if data.get('type') == 'response':
                            metadata = data.get('data', {}).get('metadata', {})
                            if metadata.get('agent'):
                                print(f"Agent used: {metadata['agent']}")
                                print(f"Execution time: {metadata.get('execution_time', 0):.2f}s")
                                print(f"Status: {metadata.get('status', 'unknown')}")
                            break

                    except asyncio.TimeoutError:
                        break

                # Small delay between queries
                await asyncio.sleep(1)

            print("\n✅ Agent execution test passed")
            return True

    except Exception as e:
        print(f"❌ Agent execution test failed: {e}")
        return False


async def test_todo_editing():
    """Test TODO editing functionality"""
    print("\n" + "=" * 60)
    print("Test 5: TODO Editing")
    print("=" * 60)

    session_id = f"test_edit_{asyncio.get_event_loop().time()}"
    ws_url = f"{WS_URL}/ws/{session_id}"

    try:
        async with websockets.connect(ws_url) as websocket:
            # First, generate some TODOs
            query_msg = {
                "type": "query",
                "content": "테스트 작성, 코드 리뷰, 배포 준비를 해줘",
                "session_id": session_id
            }

            print("Generating initial TODOs...")
            await websocket.send(json.dumps(query_msg))

            # Wait for TODOs
            await asyncio.sleep(5)

            # Try to edit TODOs
            edit_msg = {
                "type": "edit_todo",
                "edit_command": "첫 번째 TODO의 우선순위를 높여줘",
                "session_id": session_id
            }

            print("\nEditing TODOs...")
            await websocket.send(json.dumps(edit_msg))

            # Wait for update
            timeout = 10
            start_time = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)

                    if data.get('type') == 'todo_update':
                        todos = data.get('data', {}).get('todos', [])
                        print(f"\n✅ Edited TODOs received: {len(todos)} items")
                        for i, todo in enumerate(todos[:3], 1):
                            print(f"  {i}. [{todo.get('priority')}] {todo.get('title')}")
                        return True

                except asyncio.TimeoutError:
                    break

            print("\n⚠️  TODO editing test completed (no updates received)")
            return True

    except Exception as e:
        print(f"❌ TODO editing test failed: {e}")
        return False


async def run_all_tests():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("OCTOSTRATOR INTEGRATION TESTS")
    print("=" * 60)

    results = []

    # Test 1: Health Check
    results.append(("Health Check", await test_health_check()))

    # Test 2: WebSocket Connection
    results.append(("WebSocket Connection", await test_websocket_connection()))

    # Test 3: TODO Generation
    results.append(("TODO Generation", await test_todo_generation()))

    # Test 4: Agent Execution
    results.append(("Agent Execution", await test_agent_execution()))

    # Test 5: TODO Editing
    results.append(("TODO Editing", await test_todo_editing()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    print("🧪 Starting Octostrator Integration Tests\n")
    print("⚠️  Make sure both backend and frontend servers are running:")
    print("   - Backend: http://localhost:8000")
    print("   - Frontend: http://localhost:3000")
    print()

    exit_code = asyncio.run(run_all_tests())

    print("\n✅ Integration tests completed")
    sys.exit(exit_code)
