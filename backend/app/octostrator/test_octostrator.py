"""Test Octostrator Architecture

Simple test to verify the octostrator supervisor is working correctly.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

import asyncio
import sys
from pathlib import Path

# Add backend path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Set event loop policy for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def test_imports():
    """Test if octostrator imports work"""
    print("\n" + "="*50)
    print("Testing Octostrator Imports")
    print("="*50)

    errors = []

    # Test octostrator imports
    print("\nTesting octostrator imports...")
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
        print("   ✓ Octostrator supervisor helper imported")
    except ImportError as e:
        errors.append(f"   ✗ Octostrator supervisor helper: {e}")
        print(errors[-1])

    try:
        from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph
        print("   ✓ Octostrator graph builder imported")
    except ImportError as e:
        errors.append(f"   ✗ Octostrator graph builder: {e}")
        print(errors[-1])

    return errors


def test_graph_build():
    """Test if octostrator graph can be built"""
    print("\n" + "="*50)
    print("Testing Octostrator Graph Building")
    print("="*50)

    errors = []

    try:
        from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph

        # Build graph
        graph = build_octostrator_graph()
        print("\n✓ Octostrator graph built successfully")

        # Check if it's compiled
        if hasattr(graph, 'ainvoke'):
            print("✓ Graph has ainvoke method (compiled)")
        else:
            errors.append("✗ Graph missing ainvoke method")
            print(errors[-1])

    except Exception as e:
        errors.append(f"Graph build error: {e}")
        print(f"\n✗ {errors[-1]}")
        import traceback
        traceback.print_exc()

    return errors


def check_folder_structure():
    """Check if octostrator folder exists"""
    print("\n" + "="*50)
    print("Checking Octostrator Folder Structure")
    print("="*50)

    base_path = Path(__file__).parent / "supervisors"

    expected_files = [
        "octostrator/__init__.py",
        "octostrator/octostrator_graph.py",
        "octostrator/octostrator_nodes.py",
        "octostrator/octostrator_helpers.py"
    ]

    errors = []

    for file_path in expected_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"  ✓ {file_path} found")
        else:
            errors.append(f"  ✗ {file_path} missing")
            print(errors[-1])

    return errors


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TESTING OCTOSTRATOR ARCHITECTURE")
    print("="*60)

    all_errors = []

    # 1. Check folder structure
    errors = check_folder_structure()
    all_errors.extend(errors)

    # 2. Test imports
    errors = test_imports()
    all_errors.extend(errors)

    # 3. Test graph building
    errors = test_graph_build()
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
        print("\nThe octostrator architecture is working correctly.")
        print("\nNext steps:")
        print("1. Test the complete workflow with a real request")
        print("2. Update documentation")

    return len(all_errors) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
