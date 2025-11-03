"""
Test for basic checkpointer class creation
Verifies that the checkpointer module works correctly
"""

import sys
import asyncio
from pathlib import Path
import unittest

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.checkpointer import (
    CheckpointerManager,
    get_checkpointer_manager,
    create_checkpointer
)
from app.service_agent.foundation.config import Config


class TestCheckpointerCreation(unittest.TestCase):
    """Test basic checkpointer functionality"""

    def test_checkpointer_manager_creation(self):
        """Test that CheckpointerManager can be created"""
        manager = CheckpointerManager()

        self.assertIsNotNone(manager)
        self.assertEqual(manager.checkpoint_dir, Config.CHECKPOINT_DIR)
        print(f"[PASS] CheckpointerManager created with dir: {manager.checkpoint_dir}")

    def test_singleton_pattern(self):
        """Test that get_checkpointer_manager returns singleton"""
        manager1 = get_checkpointer_manager()
        manager2 = get_checkpointer_manager()

        self.assertIs(manager1, manager2)
        print("[PASS] Singleton pattern working - same instance returned")

    def test_checkpoint_dir_exists(self):
        """Test that checkpoint directory is created on init"""
        manager = CheckpointerManager()

        self.assertTrue(manager.checkpoint_dir.exists())
        self.assertTrue(manager.checkpoint_dir.is_dir())
        print(f"[PASS] Checkpoint directory exists: {manager.checkpoint_dir}")

    def test_get_checkpoint_path(self):
        """Test get_checkpoint_path method"""
        manager = CheckpointerManager()
        agent_name = "test_agent"
        session_id = "test_session"

        path = manager.get_checkpoint_path(agent_name, session_id)
        expected = Config.CHECKPOINT_DIR / agent_name / f"{session_id}.db"

        self.assertEqual(path, expected)
        print(f"[PASS] Checkpoint path generated correctly: {path}")

    def test_validate_checkpoint_setup(self):
        """Test checkpoint setup validation"""
        manager = CheckpointerManager()
        is_valid = manager.validate_checkpoint_setup()

        self.assertTrue(is_valid)
        print("[PASS] Checkpoint setup validation passed")

    def test_checkpoint_dir_writable(self):
        """Test that checkpoint directory is writable"""
        manager = CheckpointerManager()
        test_file = manager.checkpoint_dir / "test_write.tmp"

        try:
            # Try to write a test file
            test_file.write_text("test")
            self.assertTrue(test_file.exists())
            content = test_file.read_text()
            self.assertEqual(content, "test")
            print(f"[PASS] Checkpoint directory is writable: {manager.checkpoint_dir}")
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()


class TestAsyncCheckpointer(unittest.TestCase):
    """Test async checkpointer functions"""

    def test_create_checkpointer_async(self):
        """Test async create_checkpointer function"""

        async def async_test():
            # Test with default path
            checkpointer = await create_checkpointer()
            # Currently returns None (placeholder)
            self.assertIsNone(checkpointer)
            print("[PASS] create_checkpointer (default) executed without error")

            # Test with custom path
            custom_path = Config.CHECKPOINT_DIR / "custom" / "test.db"
            checkpointer = await create_checkpointer(str(custom_path))
            self.assertIsNone(checkpointer)
            print(f"[PASS] create_checkpointer (custom) executed with path: {custom_path}")

        # Run async test
        asyncio.run(async_test())

    def test_manager_create_checkpointer(self):
        """Test manager's create_checkpointer method"""

        async def async_test():
            manager = get_checkpointer_manager()

            # Test with None (default)
            checkpointer = await manager.create_checkpointer()
            self.assertIsNone(checkpointer)
            print("[PASS] Manager create_checkpointer (default) executed")

            # Test with custom path
            custom_path = str(Config.CHECKPOINT_DIR / "manager_test.db")
            checkpointer = await manager.create_checkpointer(custom_path)
            self.assertIsNone(checkpointer)
            print(f"[PASS] Manager create_checkpointer (custom) executed")

        asyncio.run(async_test())


def run_tests():
    """Run all tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCheckpointerCreation))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncCheckpointer))

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
        print("\nNote: Actual AsyncSqliteSaver will be integrated later.")
        print("Current implementation is a placeholder structure.")
    else:
        print("\n[FAILED] Some tests failed.")

    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)