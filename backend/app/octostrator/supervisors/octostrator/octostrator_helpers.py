"""
Octostrator Helper Classes

Main orchestrator that coordinates all supervisor layers.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from .octostrator_graph import build_octostrator_graph

logger = logging.getLogger(__name__)


class OctostratorSupervisor:
    """
    Main Orchestrator Supervisor

    Coordinates all layers:
    - Cognitive: Planning
    - Todo: Task management
    - Execute: Agent execution
    - Response: Output generation
    """

    def __init__(
        self,
        llm=None,
        checkpointer: Optional[AsyncPostgresSaver] = None,
        memory_manager=None,
        auto_approve_todos: bool = False
    ):
        """
        Initialize Octostrator

        Args:
            llm: Language Model
            checkpointer: Checkpoint storage
            memory_manager: Memory Manager
            auto_approve_todos: Auto-approve todos without HITL
        """
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        self.checkpointer = checkpointer
        self.memory_manager = memory_manager
        self.auto_approve_todos = auto_approve_todos

        # Build main graph
        self.graph = build_octostrator_graph()

        # WebSocket handler (optional)
        self.websocket_handler = None

        logger.info("[Octostrator] Initialized successfully")

    async def process_request(
        self,
        user_message: str,
        session_id: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        output_format: str = "chat"
    ) -> Dict[str, Any]:
        """
        Process user request through complete pipeline

        Flow:
        1. Cognitive Layer: Intent & Planning
        2. Todo Layer: Task breakdown & HITL
        3. Execute Layer: Agent execution
        4. Response Layer: Output generation

        Args:
            user_message: User's input message
            session_id: Session identifier
            user_id: User identifier (optional)
            context: Additional context (optional)
            output_format: Output format (chat/graph/report)

        Returns:
            Final response with execution results
        """
        try:
            start_time = datetime.now()
            logger.info(f"[Octostrator] Processing request for session: {session_id}")

            # Prepare context
            full_context = {
                "session_id": session_id,
                "user_id": user_id,
                "auto_approve": self.auto_approve_todos,
                "timestamp": start_time.isoformat(),
                **(context or {})
            }

            # Prepare initial state
            initial_state = {
                # User input
                "user_query": user_message,
                "session_id": session_id,
                "output_format": output_format,

                # Resources
                "llm": self.llm,
                "checkpointer": self.checkpointer,
                "context": full_context,

                # State tracking
                "plan": {},
                "todos": [],
                "execution_results": {},
                "final_response": "",

                # Flags
                "plan_valid": False,
                "requires_approval": False,
                "error": None
            }

            # Execute main graph
            logger.info("[Octostrator] Starting workflow execution")

            final_state = await self.graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": session_id}}
            )

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Build final result
            final_result = {
                "success": final_state.get("error") is None,
                "session_id": session_id,
                "user_message": user_message,

                # Planning
                "plan_goal": final_state.get("plan", {}).get("goal", ""),

                # Execution
                "total_todos": final_state.get("total_todos", 0),
                "completed": final_state.get("completed", 0),
                "failed": final_state.get("failed", 0),
                "skipped": final_state.get("skipped", 0),
                "success_rate": final_state.get("success_rate", 0),

                # Response
                "final_response": final_state.get("final_response", ""),
                "response_format": final_state.get("response_format", output_format),

                # Metadata
                "execution_time": f"{execution_time:.2f} seconds",
                "timestamp": datetime.now().isoformat(),

                # Error (if any)
                "error": final_state.get("error")
            }

            # Save to memory (optional)
            if self.memory_manager:
                await self._save_to_memory(
                    session_id=session_id,
                    user_message=user_message,
                    result=final_result
                )

            # Notify completion (optional)
            await self._notify_progress(
                session_id,
                "execution_complete",
                final_result
            )

            logger.info(
                f"[Octostrator] Request processed successfully in {execution_time:.2f}s"
            )

            return final_result

        except Exception as e:
            logger.error(f"[Octostrator] Request processing failed: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }

    async def _save_to_memory(
        self,
        session_id: str,
        user_message: str,
        result: Dict[str, Any]
    ):
        """
        Save conversation to memory

        Args:
            session_id: Session ID
            user_message: User's message
            result: Processing result
        """
        try:
            if self.memory_manager:
                await self.memory_manager.save_conversation(
                    session_id=session_id,
                    user_message=user_message,
                    ai_response=result,
                    metadata={
                        "plan_goal": result.get("plan_goal"),
                        "success_rate": result.get("success_rate"),
                        "execution_time": result.get("execution_time")
                    }
                )
        except Exception as e:
            logger.error(f"[Octostrator] Failed to save to memory: {e}")

    async def _notify_progress(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """
        Send progress notification via WebSocket

        Args:
            session_id: Session ID
            event_type: Event type
            data: Event data
        """
        try:
            if self.websocket_handler:
                await self.websocket_handler.send_message(
                    session_id,
                    {
                        "type": event_type,
                        "data": data,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        except Exception as e:
            logger.debug(f"[Octostrator] Failed to send notification: {e}")

    def set_websocket_handler(self, handler):
        """
        Set WebSocket handler for progress notifications

        Args:
            handler: WebSocket handler instance
        """
        self.websocket_handler = handler

    async def handle_human_feedback(
        self,
        session_id: str,
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle human feedback (HITL)

        Args:
            session_id: Session ID
            feedback: Human feedback data

        Returns:
            Processing result
        """
        try:
            logger.info(f"[Octostrator] Processing human feedback for {session_id}")

            # TODO: Resume from checkpoint with updated state
            # This requires retrieving state from checkpointer
            # and re-executing from the HITL point

            return {
                "success": True,
                "message": "Feedback processed",
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"[Octostrator] Failed to process feedback: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }


# ====================================
# Factory Function
# ====================================

async def create_octostrator(
    db_url: Optional[str] = None,
    llm_model: str = "gpt-4o-mini",
    auto_approve: bool = False
) -> OctostratorSupervisor:
    """
    Factory function to create Octostrator

    Args:
        db_url: PostgreSQL connection URL (for checkpointing)
        llm_model: LLM model name
        auto_approve: Auto-approve todos without HITL

    Returns:
        Initialized OctostratorSupervisor
    """
    # Create LLM
    llm = ChatOpenAI(model=llm_model, temperature=0.3)

    # Create checkpointer (optional)
    checkpointer = None
    if db_url:
        checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
        await checkpointer.setup()

    # Create Octostrator
    octostrator = OctostratorSupervisor(
        llm=llm,
        checkpointer=checkpointer,
        auto_approve_todos=auto_approve
    )

    logger.info("[Factory] Octostrator created successfully")
    return octostrator
