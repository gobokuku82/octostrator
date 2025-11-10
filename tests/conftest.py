"""Pytest Configuration

Phase 3 테스트 설정
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# AsyncIO 설정 (Windows)
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop_policy():
    """Event loop policy for Windows"""
    if sys.platform == 'win32':
        import asyncio
        return asyncio.WindowsSelectorEventLoopPolicy()
    return None
