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
from backend.app.octostrator.graphs.todo_editor import TodoEditor

router = APIRouter()


class WebSocketManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.graph_instances: Dict[str, Any] = {}
        self.session_states: Dict[str, Dict] = {}
        self.todo_editor = TodoEditor()
        self.interrupted_sessions: Dict[str, asyncio.Task] = {}  # Track running tasks

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
            "last_input": input_data,
            "is_interrupted": False
        }

        # Create a task for the graph execution
        task = asyncio.create_task(self._run_graph(session_id, input_data, config))
        self.interrupted_sessions[session_id] = task

        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Graph execution cancelled for session: {session_id}")
            await self.send_message(session_id, {
                "type": "cancelled",
                "message": "Execution was cancelled"
            })
        finally:
            if session_id in self.interrupted_sessions:
                del self.interrupted_sessions[session_id]

    async def _run_graph(self, session_id: str, input_data: Dict, config: Dict):
        """Run graph with interrupt handling"""
        try:
            # Stream graph events
            async for event in main_graph.stream(input_data, config=config):
                # Check if session was interrupted
                if self.session_states.get(session_id, {}).get("is_interrupted"):
                    logger.info(f"Execution paused due to interrupt: {session_id}")
                    break

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

                    # Check for interrupts (LangGraph interrupt() calls)
                    if "__interrupt__" in event:
                        # Save interrupt state
                        self.session_states[session_id]["interrupt_data"] = event["__interrupt__"]
                        self.session_states[session_id]["is_interrupted"] = True

                        await self.send_message(session_id, {
                            "type": "interrupt",
                            "data": event["__interrupt__"]
                        })
                        break

                    # General update
                    await self.send_message(session_id, {
                        "type": "update",
                        "data": event
                    })

            # Send completion if not interrupted
            if not self.session_states.get(session_id, {}).get("is_interrupted"):
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
        """Handle ESC key interrupt - Cancel running task"""
        logger.info(f"ESC interrupt for session: {session_id}")

        # Get current state
        session_state = self.session_states.get(session_id)
        if not session_state:
            await self.send_message(session_id, {
                "type": "error",
                "message": "No active session state"
            })
            return

        # Cancel the running task
        if session_id in self.interrupted_sessions:
            task = self.interrupted_sessions[session_id]
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled task for session: {session_id}")

        # Mark as interrupted
        session_state["is_interrupted"] = True

        # Get current graph state
        current_state = None
        if main_graph and main_graph._initialized:
            try:
                current_state = await main_graph.get_state(session_state["config"])
            except Exception as e:
                logger.warning(f"Could not get current state: {e}")

        await self.send_message(session_id, {
            "type": "esc_interrupted",
            "data": {
                "thread_id": session_state.get("thread_id"),
                "message": "Execution interrupted by user (ESC)",
                "actions": ["resume", "edit_todos", "cancel"],
                "current_state": current_state.values if current_state else None
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

        if not session_state.get("is_interrupted"):
            await self.send_message(session_id, {
                "type": "error",
                "message": "No active interrupt to resume from"
            })
            return

        # Get resume value from user
        resume_value = data.get("value", {})

        # Reset interrupt flag
        session_state["is_interrupted"] = False

        # Resume graph execution with user's response
        try:
            # If there was an interrupt() call, we need to resume with the user's response
            if "interrupt_data" in session_state:
                interrupt_data = session_state["interrupt_data"]

                # Create updated input with resume value
                config = session_state["config"]

                # Update the config with the resume value (Command.update)
                config["configurable"]["resume_value"] = resume_value

                # Re-run the graph from where it was interrupted
                await self.send_message(session_id, {
                    "type": "resuming",
                    "message": "Resuming execution with your input..."
                })

                # Create new task for resumed execution
                resumed_input = session_state["last_input"].copy()
                resumed_input["user_response"] = resume_value

                task = asyncio.create_task(self._run_graph(session_id, resumed_input, config))
                self.interrupted_sessions[session_id] = task

                await task

        except Exception as e:
            logger.error(f"Resume error: {e}")
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Failed to resume: {str(e)}"
            })

    async def handle_todo_edit(self, session_id: str, data: Dict):
        """Handle TODO natural language edit"""
        edit_command = data.get("edit_command")

        logger.info(f"Edit TODOs with command: {edit_command}")

        session_state = self.session_states.get(session_id)
        if not session_state:
            await self.send_message(session_id, {
                "type": "error",
                "message": "No active session state"
            })
            return

        try:
            # Get current graph state to access todos
            config = session_state["config"]
            current_state = await main_graph.get_state(config)

            if current_state and hasattr(current_state, 'values'):
                todos = current_state.values.get("todos", [])

                if not todos:
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": "No TODOs found in current state"
                    })
                    return

                # Use TODO editor to edit
                edit_result = await self.todo_editor.edit_todos(todos, edit_command)

                if edit_result["success"]:
                    # Update the graph state with edited todos
                    # (In a real implementation, you would update the checkpointed state)
                    await self.send_message(session_id, {
                        "type": "todo_edited",
                        "data": {
                            "action": edit_result["action"],
                            "changes_count": edit_result["changes_count"],
                            "reason": edit_result.get("reason", ""),
                            "todos": [t.dict() for t in edit_result["todos"]]
                        }
                    })
                else:
                    await self.send_message(session_id, {
                        "type": "error",
                        "message": f"Edit failed: {edit_result.get('error')}"
                    })
            else:
                await self.send_message(session_id, {
                    "type": "error",
                    "message": "Could not retrieve current state"
                })

        except Exception as e:
            logger.error(f"TODO edit error: {e}")
            await self.send_message(session_id, {
                "type": "error",
                "message": f"Failed to edit TODO: {str(e)}"
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