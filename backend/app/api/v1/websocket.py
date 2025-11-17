"""WebSocket API for real-time communication"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from loguru import logger
import json
import asyncio
from uuid import uuid4
from datetime import datetime

from backend.app.main import main_graph

router = APIRouter()


class WebSocketManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.graph_instances: Dict[str, Any] = {}
        self.session_states: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.graph_instances:
            del self.graph_instances[session_id]
        if session_id in self.session_states:
            del self.session_states[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: Dict):
        """Send message to specific session"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)

    async def handle_message(self, session_id: str, data: Dict):
        """Handle incoming WebSocket message"""
        websocket = self.active_connections.get(session_id)
        if not websocket:
            return

        message_type = data.get("type")
        logger.info(f"Handling message type: {message_type}")

        try:
            if message_type == "query":
                await self.handle_query(session_id, data)

            elif message_type == "esc_interrupt":
                await self.handle_esc_interrupt(session_id)

            elif message_type == "resume":
                await self.handle_resume(session_id, data)

            elif message_type == "edit_todo":
                await self.handle_todo_edit(session_id, data)

            else:
                await self.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_message(session_id, {
                "type": "error",
                "message": str(e)
            })

    async def handle_query(self, session_id: str, data: Dict):
        """Process user query through graph"""
        query = data.get("content", "")
        thread_id = data.get("thread_id", f"thread_{uuid4()}")

        if not main_graph:
            await self.send_message(session_id, {
                "type": "error",
                "message": "Graph not initialized"
            })
            return

        # Prepare input
        input_data = {
            "messages": [HumanMessage(content=query)],
            "session_id": session_id,
            "thread_id": thread_id,
            "user_id": data.get("user_id"),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        config = {"configurable": {"thread_id": thread_id}}

        # Save session state
        self.session_states[session_id] = {
            "thread_id": thread_id,
            "config": config,
            "last_input": input_data
        }

        try:
            # Stream graph events
            async for event in main_graph.stream(input_data, config=config):
                # Send different event types to client
                if isinstance(event, dict):
                    # State update
                    if "todos" in event:
                        await self.send_message(session_id, {
                            "type": "state_update",
                            "data": {
                                "todos": [t.dict() if hasattr(t, "dict") else t
                                         for t in event.get("todos", [])]
                            }
                        })

                    # Check for interrupts
                    if "__interrupt__" in event:
                        await self.send_message(session_id, {
                            "type": "interrupt",
                            "data": event["__interrupt__"]
                        })

                    # General update
                    await self.send_message(session_id, {
                        "type": "update",
                        "data": event
                    })

            # Send completion
            await self.send_message(session_id, {
                "type": "complete",
                "message": "Query processed successfully"
            })

        except Exception as e:
            logger.error(f"Query processing error: {e}")
            await self.send_message(session_id, {
                "type": "error",
                "message": str(e)
            })

    async def handle_esc_interrupt(self, session_id: str):
        """Handle ESC key interrupt"""
        logger.info(f"ESC interrupt for session: {session_id}")

        # Get current state
        session_state = self.session_states.get(session_id)
        if not session_state:
            await self.send_message(session_id, {
                "type": "error",
                "message": "No active session state"
            })
            return

        # TODO: Implement actual graph interruption
        # For now, send interrupt acknowledgment
        await self.send_message(session_id, {
            "type": "esc_interrupted",
            "data": {
                "thread_id": session_state.get("thread_id"),
                "message": "Execution interrupted by user",
                "actions": ["resume", "edit", "cancel"]
            }
        })

    async def handle_resume(self, session_id: str, data: Dict):
        """Handle resume after interrupt"""
        logger.info(f"Resume for session: {session_id}")

        session_state = self.session_states.get(session_id)
        if not session_state:
            await self.send_message(session_id, {
                "type": "error",
                "message": "No active session state"
            })
            return

        # Get resume value
        resume_value = data.get("value", {})

        # TODO: Implement actual graph resume with Command
        # For now, acknowledge resume
        await self.send_message(session_id, {
            "type": "resumed",
            "message": "Execution resumed",
            "data": resume_value
        })

    async def handle_todo_edit(self, session_id: str, data: Dict):
        """Handle TODO natural language edit"""
        todo_id = data.get("todo_id")
        edit_command = data.get("edit_command")

        logger.info(f"Edit TODO {todo_id}: {edit_command}")

        # TODO: Implement actual TODO editing with LLM
        # For now, send acknowledgment
        await self.send_message(session_id, {
            "type": "todo_edited",
            "data": {
                "todo_id": todo_id,
                "message": f"TODO edited: {edit_command}"
            }
        })


# Global WebSocket manager
ws_manager = WebSocketManager()


@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint"""
    await ws_manager.connect(websocket, session_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            # Parse JSON
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await ws_manager.send_message(session_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                continue

            # Handle message
            await ws_manager.handle_message(session_id, message)

    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(session_id)
        raise