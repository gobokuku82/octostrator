"""Phase 2 테스트 실행 스크립트

Phase 2 API 테스트를 실행하고 결과를 보고합니다.

Usage:
    python tests/run_phase2_tests.py
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Phase 2 API 테스트 실행"""

    # 테스트 파일 경로
    test_dir = Path(__file__).parent / "api"

    # pytest 명령어 구성
    pytest_args = [
        "pytest",
        str(test_dir),
        "-v",                    # Verbose
        "--tb=short",           # Short traceback
        "--color=yes",          # Color output
        "-p", "no:warnings",    # Disable warnings
    ]

    print("=" * 80)
    print("Phase 2 API Tests")
    print("=" * 80)
    print(f"Test directory: {test_dir}")
    print(f"Command: {' '.join(pytest_args)}")
    print("=" * 80)
    print()

    # pytest 실행
    result = subprocess.run(pytest_args, cwd=Path(__file__).parent.parent)

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
