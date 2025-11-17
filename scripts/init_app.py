"""Initialize application and test basic functionality"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import application components
from backend.app.octostrator.graphs import MainGraph
from backend.core.config import settings


async def test_graph():
    """Test the main graph functionality"""
    logger.info("Initializing Main Graph...")

    # Initialize graph
    graph = MainGraph()
    await graph.initialize()

    logger.info("Graph initialized successfully!")

    # Test query
    test_query = "API 엔드포인트 3개를 구현해주세요"
    logger.info(f"Testing with query: {test_query}")

    input_data = {
        "messages": [HumanMessage(content=test_query)],
        "session_id": "test_session",
        "thread_id": "test_thread",
        "user_id": "test_user"
    }

    config = {"configurable": {"thread_id": "test_thread"}}

    try:
        # Invoke graph
        result = await graph.invoke(input_data, config=config)

        logger.success("Graph execution completed!")

        # Print results
        if "todos" in result:
            logger.info(f"Generated {len(result['todos'])} TODOs:")
            for todo in result["todos"]:
                logger.info(f"  - {todo.title} ({todo.priority})")

        if "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                logger.info(f"Response: {last_message.content}")

    except Exception as e:
        logger.error(f"Error during graph execution: {e}")
        raise


async def test_streaming():
    """Test streaming functionality"""
    logger.info("\n--- Testing Streaming ---")

    graph = MainGraph()
    await graph.initialize()

    input_data = {
        "messages": [HumanMessage(content="스트리밍 테스트입니다")],
        "session_id": "stream_test",
        "thread_id": "stream_thread",
        "user_id": "test_user"
    }

    config = {"configurable": {"thread_id": "stream_thread"}}

    try:
        event_count = 0
        async for event in graph.stream(input_data, config=config):
            event_count += 1
            logger.info(f"Stream event {event_count}: {type(event)}")

            if isinstance(event, dict) and "todos" in event:
                logger.info(f"  TODOs updated: {len(event['todos'])} items")

        logger.success(f"Streaming completed with {event_count} events!")

    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        raise


async def main():
    """Main test function"""
    logger.info("="*50)
    logger.info("Octostrator Test Suite")
    logger.info("="*50)

    # Check environment
    logger.info("\nEnvironment Check:")
    logger.info(f"  - Database URL: {settings.database_url[:30]}...")
    logger.info(f"  - Redis URL: {settings.redis_url}")
    logger.info(f"  - OpenAI API Key: {'✓' if settings.openai_api_key else '✗'}")

    if not settings.openai_api_key:
        logger.warning("OpenAI API key not found! Some features may not work.")

    # Run tests
    try:
        await test_graph()
        await test_streaming()

        logger.success("\n✓ All tests passed!")

    except Exception as e:
        logger.error(f"\n✗ Tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())