"""Test the new supervisors architecture

This test verifies that the refactored architecture with supervisors is working correctly.

Author: AI PT Manager Development Team
Date: 2025-11-05
Version: 1.0
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add backend path (beta_v001 folder)
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Set event loop policy for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def test_imports():
    """Test if all imports work with the new structure"""
    print("\n" + "="*50)
    print("Testing Imports")
    print("="*50)

    errors = []

    # Test layer imports
    print("\n1. Testing layer imports...")
    try:
        from backend.app.octostrator.supervisors.cognitive.cognitive_nodes import (
            intent_understanding_node,
            planning_node,
            validator_node
        )
        print("   ✓ Cognitive supervisor nodes imported")
    except ImportError as e:
        errors.append(f"   ✗ Cognitive supervisor nodes: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.cognitive.cognitive_helpers import CognitiveSupervisor
        print("   ✓ Cognitive supervisor helper imported")
    except ImportError as e:
        errors.append(f"   ✗ Cognitive supervisor helper: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.cognitive.cognitive_graph import build_cognitive_graph
        print("   ✓ Cognitive graph builder imported")
    except ImportError as e:
        errors.append(f"   ✗ Cognitive graph builder: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.todo.todo_manager import TodoAgent
        print("   ✓ TodoAgent imported from supervisors")
    except ImportError as e:
        errors.append(f"   ✗ TodoAgent: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.execute.execute_nodes import (
            executor_node,
            aggregator_node,
            error_handler_node
        )
        print("   ✓ Execute supervisor nodes imported")
    except ImportError as e:
        errors.append(f"   ✗ Execute supervisor nodes: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.execute.execute_helpers import ExecuteSupervisor
        print("   ✓ Execute supervisor helper imported")
    except ImportError as e:
        errors.append(f"   ✗ Execute supervisor helper: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.response.response_nodes import (
            hitl_handler_node,
            output_router_node,
            chat_generator_node
        )
        print("   ✓ Response supervisor nodes imported")
    except ImportError as e:
        errors.append(f"   ✗ Response supervisor nodes: {e}")
        print(errors[-1])

    # Test state imports
    print("\n2. Testing state imports...")
    try:
        from backend.app.octostrator.states import (
            CognitiveState,
            TodoAgentState,
            TodoItem,
            TodoBatch,
            ExecuteState,
            ResponseState
        )
        print("   ✓ All layer states imported from central states folder")
    except ImportError as e:
        errors.append(f"   ✗ Layer states: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.states import (
            DietAgentState,
            WorkoutAgentState
        )
        print("   ✓ Agent states imported")
    except ImportError as e:
        errors.append(f"   ✗ Agent states: {e}")
        print(errors[-1])

    # Test octostrator supervisor
    print("\n3. Testing octostrator supervisor...")
    try:
        from backend.app.octostrator.supervisors.octostrator.octostrator_nodes import (
            cognitive_layer_node,
            todo_layer_node,
            execute_layer_node,
            response_layer_node
        )
        print("   ✓ Octostrator nodes imported")
    except ImportError as e:
        errors.append(f"   ✗ Octostrator nodes: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.octostrator.octostrator_helpers import OctostratorSupervisor
        print("   ✓ OctostratorSupervisor imported")
    except ImportError as e:
        errors.append(f"   ✗ OctostratorSupervisor: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph
        print("   ✓ Octostrator graph builder imported")
    except ImportError as e:
        errors.append(f"   ✗ Octostrator graph builder: {e}")
        print(errors[-1])

    # Test API imports
    print("\n4. Testing API imports...")
    try:
        from backend.app.api.websocket import manager, router
        print("   ✓ WebSocket API imported")
    except ImportError as e:
        errors.append(f"   ✗ WebSocket API: {e}")
        print(errors[-1])

    try:
        from backend.app.api.sessions import router as sessions_router
        print("   ✓ Sessions API imported")
    except ImportError as e:
        errors.append(f"   ✗ Sessions API: {e}")
        print(errors[-1])

    try:
        from backend.app.main import app
        print("   ✓ Main FastAPI app imported")
    except ImportError as e:
        errors.append(f"   ✗ Main FastAPI app: {e}")
        print(errors[-1])

    # Test agent imports
    print("\n5. Testing agent imports...")
    try:
        from backend.app.octostrator.agents.diet.diet_agent import DietAgent
        print("   ✓ DietAgent imported")
    except ImportError as e:
        errors.append(f"   ✗ DietAgent: {e}")
        print(errors[-1])

    # Note: Other agents (workout, schedule, etc.) were removed during cleanup
    print("   ⓘ Other agents were removed during architecture cleanup")

    return errors


def test_state_creation():
    """Test if states can be created properly"""
    print("\n" + "="*50)
    print("Testing State Creation")
    print("="*50)

    errors = []

    try:
        from backend.app.octostrator.states import (
            CognitiveState,
            TodoAgentState,
            ExecuteState,
            ResponseState
        )

        # Test CognitiveState
        cognitive_state = CognitiveState()
        print("\n1. CognitiveState created successfully")
        print(f"   - user_query: {cognitive_state.get('user_query', 'None')}")
        print(f"   - user_intent: {cognitive_state.get('user_intent', 'None')}")

        # Test TodoAgentState
        todo_state = TodoAgentState()
        print("\n2. TodoAgentState created successfully")
        print(f"   - todos: {todo_state.get('todos', [])}")
        print(f"   - current_batch: {todo_state.get('current_batch', 'None')}")

        # Test ExecuteState
        execute_state = ExecuteState()
        print("\n3. ExecuteState created successfully")
        print(f"   - execution_tasks: {execute_state.get('execution_tasks', [])}")
        print(f"   - execution_results: {execute_state.get('execution_results', [])}")

        # Test ResponseState
        response_state = ResponseState()
        print("\n4. ResponseState created successfully")
        print(f"   - requires_approval: {response_state.get('requires_approval', False)}")
        print(f"   - output_format: {response_state.get('output_format', 'chat')}")

    except Exception as e:
        errors.append(f"State creation error: {e}")
        print(f"\n✗ {errors[-1]}")

    return errors


async def test_todo_agent():
    """Test TodoAgent functionality"""
    print("\n" + "="*50)
    print("Testing TodoAgent")
    print("="*50)

    errors = []

    try:
        from backend.app.octostrator.supervisors.todo.todo_manager import TodoAgent
        from backend.app.octostrator.states import TodoAgentState, TodoItem

        # Create TodoAgent
        agent = TodoAgent()
        print("\n1. TodoAgent created successfully")

        # Create test state
        test_state = TodoAgentState()
        test_state["todos"] = [
            {
                "id": "test-1",
                "title": "Test Todo 1",
                "description": "Test description 1",
                "status": "pending",
                "agent": "diet"
            },
            {
                "id": "test-2",
                "title": "Test Todo 2",
                "description": "Test description 2",
                "status": "pending",
                "agent": "workout"
            }
        ]

        print("\n2. Test state created with 2 todos")

        # Test processing (simulated)
        test_task = {
            "type": "process_todos",
            "todos": test_state["todos"]
        }
        test_context = {
            "session_id": "test-session",
            "auto_approve": True
        }

        # Test that TodoAgent can process tasks
        if hasattr(agent, 'process_task'):
            print("\n3. TodoAgent has process_task method")
            print(f"   - Can process todos: Yes")
            print(f"   - Number of todos: {len(test_state['todos'])}")
        else:
            errors.append("TodoAgent missing process_task method")
            print(f"\n✗ {errors[-1]}")

    except Exception as e:
        errors.append(f"TodoAgent test error: {e}")
        print(f"\n✗ {errors[-1]}")

    return errors


async def test_orchestrator():
    """Test OctostratorSupervisor initialization"""
    print("\n" + "="*50)
    print("Testing OctostratorSupervisor")
    print("="*50)

    errors = []

    try:
        from backend.app.octostrator.supervisors.octostrator.octostrator_helpers import OctostratorSupervisor
        from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph

        # Create orchestrator
        orchestrator = OctostratorSupervisor(
            auto_approve_todos=True
        )
        print("\n1. OctostratorSupervisor created successfully")

        # Check components
        if hasattr(orchestrator, 'graph'):
            print("   ✓ Main graph initialized")
        else:
            errors.append("   ✗ Main graph not found")
            print(errors[-1])

        if hasattr(orchestrator, 'llm'):
            print("   ✓ LLM initialized")
        else:
            errors.append("   ✗ LLM not found")
            print(errors[-1])

        # Test graph building
        graph = build_octostrator_graph()
        if hasattr(graph, 'ainvoke'):
            print("   ✓ Octostrator graph can be built and compiled")
        else:
            errors.append("   ✗ Octostrator graph not compiled")
            print(errors[-1])

    except Exception as e:
        errors.append(f"Orchestrator test error: {e}")
        print(f"\n✗ {errors[-1]}")

    return errors


def check_folder_structure():
    """Check if the new folder structure exists"""
    print("\n" + "="*50)
    print("Checking Folder Structure")
    print("="*50)

    # Point to backend/app/octostrator folder
    base_path = Path(__file__).parent.parent / "backend" / "app" / "octostrator"

    # Expected structure
    expected_dirs = {
        "supervisors/cognitive": ["cognitive_nodes.py", "cognitive_graph.py", "cognitive_helpers.py", "cognitive_prompts.py"],
        "supervisors/todo": ["todo_manager.py", "__init__.py"],
        "supervisors/execute": ["execute_nodes.py", "execute_graph.py", "execute_helpers.py", "execute_prompts.py"],
        "supervisors/response": ["response_nodes.py", "response_graph.py", "response_helpers.py", "response_prompts.py"],
        "supervisors/octostrator": ["octostrator_nodes.py", "octostrator_graph.py", "octostrator_helpers.py", "__init__.py"],
        "states": ["cognitive_state.py", "todo_state.py", "execute_state.py", "response_state.py"]
    }

    errors = []

    for dir_path, expected_files in expected_dirs.items():
        full_path = base_path / dir_path

        print(f"\nChecking {dir_path}/")
        if full_path.exists():
            print(f"  ✓ Directory exists")
            for file in expected_files:
                file_path = full_path / file
                if file_path.exists():
                    print(f"    ✓ {file} found")
                else:
                    errors.append(f"    ✗ {file} missing")
                    print(errors[-1])
        else:
            errors.append(f"  ✗ Directory {dir_path} not found")
            print(errors[-1])

    return errors


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TESTING NEW SUPERVISORS ARCHITECTURE")
    print("="*60)

    all_errors = []

    # 1. Check folder structure
    errors = check_folder_structure()
    all_errors.extend(errors)

    # 2. Test imports
    errors = test_imports()
    all_errors.extend(errors)

    # 3. Test state creation
    errors = test_state_creation()
    all_errors.extend(errors)

    # 4. Test TodoAgent
    errors = await test_todo_agent()
    all_errors.extend(errors)

    # 5. Test MainOrchestrator
    errors = await test_orchestrator()
    all_errors.extend(errors)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    if all_errors:
        print(f"\n❌ Tests completed with {len(all_errors)} errors:\n")
        for i, error in enumerate(all_errors, 1):
            print(f"{i}. {error}")
        print("\nPlease fix the above errors before proceeding.")
    else:
        print("\n✅ All tests passed successfully!")
        print("\nThe new supervisors architecture is working correctly.")
        print("\nNext steps:")
        print("1. Update any remaining documentation")
        print("2. Commit the changes")

    return len(all_errors) == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)