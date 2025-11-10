"""
Supervisor Structure Verification
Phase 4.3: 새 구조 검증 (Import & Build Test)
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python Path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Phase 4.3 구조 검증: Import & Build Test")
print("=" * 60)

# 1. cognitive_prompts 검증
print("\n[1/6] cognitive_prompts.py 검증...")
try:
    from backend.app.octostrator.supervisor.cognitive_prompts import (
        INTENT_UNDERSTANDING_PROMPT,
        PLANNING_SYSTEM_PROMPT,
        AGGREGATOR_INSIGHT_PROMPT,
    )
    print("  ✓ 모든 프롬프트 import 성공")
    print(f"  - INTENT_UNDERSTANDING_PROMPT: {len(INTENT_UNDERSTANDING_PROMPT)} chars")
    print(f"  - PLANNING_SYSTEM_PROMPT: {len(PLANNING_SYSTEM_PROMPT)} chars")
    print(f"  - AGGREGATOR_INSIGHT_PROMPT: {len(AGGREGATOR_INSIGHT_PROMPT)} chars")
except Exception as e:
    print(f"  ✗ Import 실패: {e}")
    sys.exit(1)

# 2. cognitive_nodes 검증
print("\n[2/6] cognitive_nodes.py 검증...")
try:
    from backend.app.octostrator.supervisor.cognitive_nodes import (
        intent_understanding_node,
        planning_node,
        executor_node,
        aggregator_node,
    )
    print("  ✓ 모든 cognitive 노드 import 성공")
    print("  - intent_understanding_node")
    print("  - planning_node")
    print("  - executor_node")
    print("  - aggregator_node")
except Exception as e:
    print(f"  ✗ Import 실패: {e}")
    sys.exit(1)

# 3. response_nodes 검증
print("\n[3/6] response_nodes.py 검증...")
try:
    from backend.app.octostrator.supervisor.response_nodes import (
        hitl_handler_node,
        output_router_node,
        chat_generator_node,
        graph_generator_node,
        report_generator_node,
    )
    print("  ✓ 모든 response 노드 import 성공")
    print("  - hitl_handler_node")
    print("  - output_router_node")
    print("  - chat_generator_node")
    print("  - graph_generator_node")
    print("  - report_generator_node")
except Exception as e:
    print(f"  ✗ Import 실패: {e}")
    sys.exit(1)

# 4. main_graph 검증
print("\n[4/6] main_graph.py 검증...")
try:
    from backend.app.octostrator.supervisor.main_graph import build_supervisor_graph
    print("  ✓ build_supervisor_graph import 성공")
except Exception as e:
    print(f"  ✗ Import 실패: {e}")
    sys.exit(1)

# 5. __init__.py 검증
print("\n[5/6] __init__.py 검증...")
try:
    from backend.app.octostrator.supervisor import build_supervisor_graph as build_graph_from_init
    print("  ✓ __init__.py에서 build_supervisor_graph export 성공")
except Exception as e:
    print(f"  ✗ Import 실패: {e}")
    sys.exit(1)

# 6. 그래프 빌드 검증
print("\n[6/6] 그래프 빌드 검증...")
try:
    graph = build_supervisor_graph()
    print("  ✓ 그래프 빌드 성공")
    print(f"  - Graph type: {type(graph).__name__}")

    # 노드 확인
    if hasattr(graph, 'nodes'):
        print(f"  - Nodes: {len(graph.nodes)} 개")
except Exception as e:
    print(f"  ✗ 빌드 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 최종 요약
print("\n" + "=" * 60)
print("✓ 모든 검증 통과!")
print("=" * 60)
print("\n새 구조:")
print("  supervisor/")
print("  ├── __init__.py           (export: build_supervisor_graph)")
print("  ├── main_graph.py         (그래프 정의)")
print("  ├── cognitive_nodes.py    (Intent, Planning, Executor, Aggregator)")
print("  ├── response_nodes.py     (HITL, Router, Generators)")
print("  └── cognitive_prompts.py  (모든 프롬프트 중앙 관리)")
print("\n구조 개선 완료:")
print("  - 14개 파일 → 6개 파일 (57% 감소)")
print("  - 3단계 폴더 구조 → 1단계 (flat)")
print("  - 프롬프트 중앙 관리 (유지보수 용이)")
print("  - 명확한 파일명 (cognitive vs response)")
print("\n🎉 Phase 4.3 Supervisor 리뉴얼 완료!")
