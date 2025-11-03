"""
Test that TeamSupervisor has checkpointer field
Verifies minimal modification to supervisor without breaking existing functionality
"""

import sys
from pathlib import Path
import unittest

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.foundation.context import create_default_llm_context


class TestSupervisorCheckpointerField(unittest.TestCase):
    """Test that TeamSupervisor has checkpointer field added"""

    def test_supervisor_has_checkpointer_field(self):
        """Test that TeamBasedSupervisor has checkpointer attribute"""
        # Create supervisor with default context
        supervisor = TeamBasedSupervisor()

        # Check that checkpointer field exists
        self.assertTrue(
            hasattr(supervisor, 'checkpointer'),
            "TeamBasedSupervisor should have 'checkpointer' attribute"
        )
        print("[PASS] TeamBasedSupervisor has 'checkpointer' attribute")

    def test_checkpointer_initially_none(self):
        """Test that checkpointer is initially None"""
        supervisor = TeamBasedSupervisor()

        self.assertIsNone(
            supervisor.checkpointer,
            "Checkpointer should initially be None"
        )
        print("[PASS] Checkpointer is initially None (placeholder)")

    def test_existing_attributes_still_present(self):
        """Test that existing attributes are not affected"""
        supervisor = TeamBasedSupervisor()

        # Check that essential existing attributes still exist
        essential_attrs = [
            'llm_context',
            'planning_agent',
            'teams',
            'app'
        ]

        for attr in essential_attrs:
            self.assertTrue(
                hasattr(supervisor, attr),
                f"TeamBasedSupervisor should still have '{attr}' attribute"
            )
            print(f"[PASS] Existing attribute still present: {attr}")

    def test_supervisor_initialization_works(self):
        """Test that supervisor can still be initialized properly"""
        try:
            supervisor = TeamBasedSupervisor()
            self.assertIsNotNone(supervisor)
            print("[PASS] TeamBasedSupervisor initialization works")
        except Exception as e:
            self.fail(f"TeamBasedSupervisor initialization failed: {e}")

    def test_supervisor_with_custom_context(self):
        """Test that supervisor works with custom LLM context"""
        context = create_default_llm_context()

        try:
            supervisor = TeamBasedSupervisor(llm_context=context)
            self.assertIsNotNone(supervisor)
            self.assertEqual(supervisor.llm_context, context)
            self.assertTrue(hasattr(supervisor, 'checkpointer'))
            print("[PASS] TeamBasedSupervisor works with custom context")
        except Exception as e:
            self.fail(f"TeamBasedSupervisor with custom context failed: {e}")

    def test_teams_initialized(self):
        """Test that teams are still initialized properly"""
        supervisor = TeamBasedSupervisor()

        self.assertIn('search', supervisor.teams)
        self.assertIn('document', supervisor.teams)
        self.assertIn('analysis', supervisor.teams)
        print("[PASS] Teams are properly initialized")

    def test_workflow_app_created(self):
        """Test that workflow app is still created"""
        supervisor = TeamBasedSupervisor()

        self.assertIsNotNone(
            supervisor.app,
            "Workflow app should be created"
        )
        print("[PASS] Workflow app is created")

    def test_checkpointer_can_be_set(self):
        """Test that checkpointer can be set after initialization"""
        supervisor = TeamBasedSupervisor()

        # Initially None
        self.assertIsNone(supervisor.checkpointer)

        # Set to a dummy value
        dummy_checkpointer = "dummy_checkpointer_placeholder"
        supervisor.checkpointer = dummy_checkpointer

        self.assertEqual(
            supervisor.checkpointer,
            dummy_checkpointer,
            "Checkpointer should be settable"
        )
        print("[PASS] Checkpointer field can be set after initialization")


def run_tests():
    """Run all tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSupervisorCheckpointerField)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed successfully!")
        print("\nNote: Checkpointer is currently a placeholder (None).")
        print("It will be properly initialized in future steps.")
    else:
        print("\n[FAILED] Some tests failed.")
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")

    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)