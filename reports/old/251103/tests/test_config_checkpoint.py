"""
Test for checkpoint configuration in config.py
Verifies that the checkpoint directory is correctly set to backend/data/system/checkpoints
"""

import sys
from pathlib import Path
import unittest

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.config import Config


class TestCheckpointConfig(unittest.TestCase):
    """Test checkpoint configuration"""

    def test_checkpoint_dir_path(self):
        """Test that CHECKPOINT_DIR is set to the correct path"""
        expected_path = Config.BASE_DIR / "data" / "system" / "checkpoints"
        actual_path = Config.CHECKPOINT_DIR

        self.assertEqual(
            actual_path,
            expected_path,
            f"CHECKPOINT_DIR should be {expected_path}, but got {actual_path}"
        )
        print(f"[PASS] CHECKPOINT_DIR correctly set to: {actual_path}")

    def test_checkpoint_dir_exists(self):
        """Test that checkpoint directory exists or can be created"""
        checkpoint_dir = Config.CHECKPOINT_DIR

        # The directory should exist (created by Config on import)
        self.assertTrue(
            checkpoint_dir.exists(),
            f"Checkpoint directory should exist: {checkpoint_dir}"
        )
        print(f"[PASS] Checkpoint directory exists: {checkpoint_dir}")

    def test_checkpoint_dir_is_directory(self):
        """Test that checkpoint path is a directory, not a file"""
        checkpoint_dir = Config.CHECKPOINT_DIR

        self.assertTrue(
            checkpoint_dir.is_dir(),
            f"Checkpoint path should be a directory: {checkpoint_dir}"
        )
        print(f"[PASS] Checkpoint path is a directory: {checkpoint_dir}")

    def test_get_checkpoint_path_method(self):
        """Test the get_checkpoint_path helper method"""
        agent_name = "test_agent"
        session_id = "test_session_123"

        checkpoint_path = Config.get_checkpoint_path(agent_name, session_id)
        expected_path = Config.CHECKPOINT_DIR / agent_name / f"{session_id}.db"

        self.assertEqual(
            checkpoint_path,
            expected_path,
            f"get_checkpoint_path should return {expected_path}, but got {checkpoint_path}"
        )
        print(f"[PASS] get_checkpoint_path returns correct path: {checkpoint_path}")

    def test_checkpoint_subdirectory_creation(self):
        """Test that agent-specific subdirectories can be created"""
        agent_name = "test_agent_subdirectory"
        session_id = "test_session_456"

        # Get checkpoint path (this should create the subdirectory)
        checkpoint_path = Config.get_checkpoint_path(agent_name, session_id)

        # Check that the parent directory (agent directory) exists
        agent_dir = checkpoint_path.parent
        self.assertTrue(
            agent_dir.exists(),
            f"Agent subdirectory should be created: {agent_dir}"
        )
        print(f"[PASS] Agent subdirectory created successfully: {agent_dir}")

    def test_checkpoint_path_consistency(self):
        """Test that checkpoint paths are consistent across calls"""
        agent_name = "consistency_test"
        session_id = "session_789"

        path1 = Config.get_checkpoint_path(agent_name, session_id)
        path2 = Config.get_checkpoint_path(agent_name, session_id)

        self.assertEqual(
            path1,
            path2,
            "get_checkpoint_path should return consistent paths"
        )
        print(f"[PASS] Checkpoint paths are consistent: {path1}")


def run_tests():
    """Run all tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCheckpointConfig)

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
    else:
        print("\n[FAILED] Some tests failed.")

    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)