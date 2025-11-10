"""Phase 2 API 검증 스크립트

pytest-asyncio 이슈로 인해 직접 API 엔드포인트를 검증합니다.

Usage:
    python tests/validate_phase2_apis.py
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Windows에서 psycopg 호환성을 위한 EventLoop 설정
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from backend.app.main import app
from fastapi.routing import APIRoute


def validate_apis():
    """API 엔드포인트 검증"""

    print("=" * 80)
    print("Phase 2 API Validation")
    print("=" * 80)
    print()

    # 모든 routes 수집
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })

    # Session API 검증 (4개 신규 엔드포인트)
    print("📋 Session API (Phase 2 - 4 endpoints)")
    print("-" * 80)

    session_endpoints = [
        ("GET", "/api/sessions/{thread_id}/summary", "get_session_summary"),
        ("GET", "/api/sessions/{thread_id}/action/{step}", "get_action_at_step"),
        ("PUT", "/api/sessions/{thread_id}/state", "update_session_state"),
        ("POST", "/api/sessions/{thread_id}/interrupt", "interrupt_session"),
    ]

    for method, path, name in session_endpoints:
        found = any(
            r["path"] == path and method in r["methods"]
            for r in routes
        )
        status = "✅" if found else "❌"
        print(f"  {status} {method:6} {path:50} ({name})")

    print()

    # Todo API 검증 (6개 엔드포인트)
    print("📝 Todo Management API (Phase 2 - 6 endpoints)")
    print("-" * 80)

    todo_endpoints = [
        ("POST", "/api/sessions/{thread_id}/todos", "add_todo"),
        ("DELETE", "/api/sessions/{thread_id}/todos/{todo_id}", "delete_todo"),
        ("PUT", "/api/sessions/{thread_id}/todos/{todo_id}", "update_todo"),
        ("PUT", "/api/sessions/{thread_id}/todos/reorder", "reorder_todos"),
        ("POST", "/api/sessions/{thread_id}/retry/{todo_id}", "retry_todo"),
        ("PUT", "/api/sessions/{thread_id}/todos/{todo_id}/agent", "change_todo_agent"),
    ]

    for method, path, name in todo_endpoints:
        found = any(
            r["path"] == path and method in r["methods"]
            for r in routes
        )
        status = "✅" if found else "❌"
        print(f"  {status} {method:6} {path:60} ({name})")

    print()

    # Agent API 검증 (1개 엔드포인트)
    print("🤖 Agent Management API (Phase 2 - 1 endpoint)")
    print("-" * 80)

    agent_endpoints = [
        ("GET", "/api/agents", "list_agents"),
    ]

    for method, path, name in agent_endpoints:
        found = any(
            r["path"] == path and method in r["methods"]
            for r in routes
        )
        status = "✅" if found else "❌"
        print(f"  {status} {method:6} {path:50} ({name})")

    print()

    # 통계
    print("📊 Statistics")
    print("-" * 80)

    total_phase2 = len(session_endpoints) + len(todo_endpoints) + len(agent_endpoints)
    all_endpoints = session_endpoints + todo_endpoints + agent_endpoints

    found_count = sum(
        1 for method, path, name in all_endpoints
        if any(r["path"] == path and method in r["methods"] for r in routes)
    )

    print(f"  Total Phase 2 endpoints: {total_phase2}")
    print(f"  Found: {found_count}")
    print(f"  Missing: {total_phase2 - found_count}")
    print(f"  Total app routes: {len(routes)}")

    print()

    # 성공 여부
    if found_count == total_phase2:
        print("✅ All Phase 2 APIs are registered!")
        print()
        return 0
    else:
        print("❌ Some Phase 2 APIs are missing!")
        print()
        return 1


def list_all_routes():
    """모든 route 나열"""

    print("=" * 80)
    print("All Registered Routes")
    print("=" * 80)
    print()

    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })

    # 경로별로 정렬
    routes.sort(key=lambda x: x["path"])

    for route in routes:
        methods_str = ", ".join(sorted(route["methods"]))
        print(f"  {methods_str:20} {route['path']:60} ({route['name']})")

    print()
    print(f"Total routes: {len(routes)}")
    print()


if __name__ == "__main__":
    try:
        # API 검증
        result = validate_apis()

        # 모든 route 나열
        list_all_routes()

        sys.exit(result)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
