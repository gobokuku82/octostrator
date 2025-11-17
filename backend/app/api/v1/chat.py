"""Chat API endpoints"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from langchain_core.messages import HumanMessage
from loguru import logger
from uuid import uuid4
from datetime import datetime

from backend.schema.message import MessageCreate
from backend.schema.response import SuccessResponse, ErrorResponse
from backend.app.main import main_graph

router = APIRouter()


@router.post("/chat", response_model=SuccessResponse)
async def chat(message: MessageCreate):
    """Process a chat message"""
    try:
        if not main_graph:
            raise HTTPException(status_code=500, detail="Graph not initialized")

        # Create session and thread IDs if not provided
        thread_id = message.thread_id or f"thread_{uuid4()}"
        session_id = f"session_{uuid4()}"

        # Prepare input
        input_data = {
            "messages": [HumanMessage(content=message.content)],
            "session_id": session_id,
            "thread_id": thread_id,
            "user_id": None,  # TODO: Get from auth
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        # Invoke graph
        config = {"configurable": {"thread_id": thread_id}}
        result = await main_graph.invoke(input_data, config=config)

        # Extract response
        response_message = None
        if result and "messages" in result:
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and msg.content:
                    response_message = msg.content
                    break

        return SuccessResponse(
            message="Chat processed successfully",
            data={
                "response": response_message,
                "thread_id": thread_id,
                "todos": [todo.dict() for todo in result.get("todos", [])]
            }
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(message: MessageCreate):
    """Stream chat responses"""
    try:
        if not main_graph:
            raise HTTPException(status_code=500, detail="Graph not initialized")

        thread_id = message.thread_id or f"thread_{uuid4()}"
        session_id = f"session_{uuid4()}"

        input_data = {
            "messages": [HumanMessage(content=message.content)],
            "session_id": session_id,
            "thread_id": thread_id,
            "user_id": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        config = {"configurable": {"thread_id": thread_id}}

        # Stream events
        async for event in main_graph.stream(input_data, config=config):
            yield event

    except Exception as e:
        logger.error(f"Stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))