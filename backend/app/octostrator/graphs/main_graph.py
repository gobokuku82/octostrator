"""Main supervisor graph for Octostrator"""

import os
from typing import List, Dict, Any, Literal, Optional
from datetime import datetime
from uuid import uuid4

from langgraph.graph import StateGraph, END
from langgraph.types import Command, Send, interrupt
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from loguru import logger

from .states import MainGraphState, GraphState
from .todo_graph import TodoGraph
from backend.schema.todo import TodoItem, TodoStatus, TodoPriority
from backend.app.octostrator.agents import AgentManager


class MainGraph:
    """Main Supervisor Graph - 전체 워크플로우 조정"""

    def __init__(self):
        """Initialize the main graph"""
        self.checkpointer = None
        self.graph = None
        self.todo_graph = TodoGraph()
        self.agent_manager = AgentManager()
        self._initialized = False

    async def initialize(self):
        """비동기 초기화"""
        if self._initialized:
            return

        # Check if we're in development mode
        use_dev_mode = os.getenv("USE_DEV_MODE", "true").lower() == "true"

        if use_dev_mode:
            # Use SQLite for development
            from .checkpointer_dev import SQLiteCheckpointer
            self.checkpointer = SQLiteCheckpointer("octostrator_checkpoints.db")
            logger.info("Development mode: Using SQLite checkpointer")
        else:
            # PostgreSQL Checkpointer 설정
            database_url = os.getenv("DATABASE_URL")
            if database_url and "postgresql" in database_url:
                try:
                    self.checkpointer = AsyncPostgresSaver.from_conn_string(database_url)
                    await self.checkpointer.setup()
                    logger.info("PostgreSQL checkpointer initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize PostgreSQL checkpointer: {e}")
                    # Fallback to SQLite
                    from .checkpointer_dev import SQLiteCheckpointer
                    self.checkpointer = SQLiteCheckpointer("octostrator_checkpoints.db")
                    logger.warning("Falling back to SQLite checkpointer")

        # 그래프 빌드
        self.graph = self._build_graph()
        self._initialized = True
        logger.info("Main graph initialized")

    def _build_graph(self) -> StateGraph:
        """그래프 구조 빌드"""
        workflow = StateGraph(MainGraphState)

        # Add nodes
        workflow.add_node("entry", self.entry_node)
        workflow.add_node("intent_analysis", self.intent_analysis_node)
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("router", self.router_node)
        workflow.add_node("executor", self.executor_node)
        workflow.add_node("validator", self.validator_node)
        workflow.add_node("response_generator", self.response_generator_node)

        # Set entry point
        workflow.set_entry_point("entry")

        # Add edges
        workflow.add_edge("entry", "intent_analysis")

        # Conditional routing after intent analysis
        workflow.add_conditional_edges(
            "intent_analysis",
            self._route_by_intent,
            {
                "planner": "planner",
                "executor": "executor",
                "response": "response_generator",
                "end": END
            }
        )

        workflow.add_edge("planner", "router")
        workflow.add_edge("router", "executor")
        workflow.add_edge("executor", "validator")
        workflow.add_edge("validator", "response_generator")
        workflow.add_edge("response_generator", END)

        # Compile with checkpointer if available
        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
        else:
            return workflow.compile()

    async def entry_node(self, state: GraphState) -> GraphState:
        """진입점 노드"""
        logger.info(f"Entry node - Session: {state.get('session_id')}")

        # Initialize state if needed
        if not state.get("created_at"):
            state["created_at"] = datetime.now()

        state["updated_at"] = datetime.now()

        # Initialize empty lists if not present
        if "todos" not in state:
            state["todos"] = []
        if "intent_history" not in state:
            state["intent_history"] = []
        if "pending_tasks" not in state:
            state["pending_tasks"] = []
        if "completed_tasks" not in state:
            state["completed_tasks"] = []

        return state

    async def intent_analysis_node(self, state: GraphState) -> GraphState:
        """Intent 분석 노드"""
        logger.info("Analyzing user intent")

        # Get latest user message
        messages = state.get("messages", [])
        if not messages:
            state["error"] = "No messages to analyze"
            return state

        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            state["error"] = "Last message is not from user"
            return state

        user_query = last_message.content

        # Simple intent detection (실제 구현시 LLM 사용)
        intent = self._detect_intent(user_query, state)

        state["detected_intent"] = intent
        state["user_query"] = user_query

        # Update intent history
        if intent:
            state["intent_history"].append(intent["primary"])
            state["previous_intent"] = intent["primary"]

        logger.info(f"Detected intent: {intent}")
        return state

    async def planner_node(self, state: GraphState) -> GraphState:
        """TODO 계획 노드 - 실제 TodoGraph 사용"""
        logger.info("Planning TODOs with TodoGraph")

        user_query = state.get("user_query", "")
        if not user_query:
            state["error"] = "No user query for planning"
            return state

        # Use TodoGraph to generate TODOs
        try:
            todo_result = await self.todo_graph.invoke(
                user_query=user_query,
                thread_id=state.get("thread_id", ""),
                session_id=state.get("session_id", "")
            )

            todos = todo_result.get("todos", [])
            validation_passed = todo_result.get("validation_passed", False)
            validation_errors = todo_result.get("validation_errors", [])
            requires_confirmation = todo_result.get("requires_confirmation", False)

            if not validation_passed:
                state["error"] = f"TODO validation failed: {', '.join(validation_errors)}"
                state["validation_errors"] = validation_errors
                return state

            # Check if confirmation is needed
            if requires_confirmation or len(todos) > 5:
                state["requires_confirmation"] = True

                # HITL: Request user confirmation
                user_response = interrupt({
                    "type": "todo_confirmation",
                    "message": "생성된 TODO 목록을 확인해주세요",
                    "todos": [t.dict() for t in todos],
                    "actions": ["approve", "edit", "cancel"]
                })

                if user_response.get("action") == "cancel":
                    state["error"] = "User cancelled TODO creation"
                    return state
                elif user_response.get("action") == "edit":
                    # Handle edits (simplified)
                    todos = self._edit_todos(todos, user_response.get("feedback", ""))

            state["todos"] = todos
            logger.info(f"Generated {len(todos)} TODOs using TodoGraph")

        except Exception as e:
            logger.error(f"Error in planner_node: {e}")
            state["error"] = f"TODO planning failed: {str(e)}"

        return state

    async def router_node(self, state: GraphState) -> GraphState:
        """작업 라우팅 노드"""
        logger.info("Routing tasks")

        todos = state.get("todos", [])
        if not todos:
            logger.warning("No TODOs to route")
            return state

        # Prepare tasks for execution
        tasks = []
        for todo in todos:
            task = {
                "id": str(todo.id),
                "type": self._determine_task_type(todo),
                "todo": todo.dict(),
                "priority": todo.priority
            }
            tasks.append(task)

        state["pending_tasks"] = tasks
        logger.info(f"Routed {len(tasks)} tasks")
        return state

    async def executor_node(self, state: GraphState) -> GraphState:
        """실행 노드 - Execute tasks with AgentManager"""
        logger.info("Executing tasks with AgentManager")

        tasks = state.get("pending_tasks", [])
        if not tasks:
            logger.warning("No tasks to execute")
            return state

        # Execute tasks with AgentManager
        if "execution_results" not in state:
            state["execution_results"] = {}

        # Execute all tasks (sequentially for now, can be parallelized later)
        for task in tasks:
            try:
                result = await self.agent_manager.execute_task(task)
                state["execution_results"][task["id"]] = result
                logger.info(f"Task {task['id']} executed: {result['status']}")

            except Exception as e:
                logger.error(f"Task {task['id']} execution error: {e}")
                state["execution_results"][task["id"]] = {
                    "status": "failure",
                    "error": str(e),
                    "task_id": task["id"]
                }

        logger.info(f"Executed {len(tasks)} tasks")
        return state

    async def validator_node(self, state: GraphState) -> GraphState:
        """검증 노드"""
        logger.info("Validating execution results")

        results = state.get("execution_results", {})
        todos = state.get("todos", [])

        # Check for failures
        failed_tasks = [
            task_id for task_id, result in results.items()
            if result.get("status") != "success"
        ]

        if failed_tasks:
            # HITL: Ask user what to do with failures
            user_response = interrupt({
                "type": "validation_failure",
                "message": f"{len(failed_tasks)}개 작업이 실패했습니다",
                "failed_tasks": failed_tasks,
                "actions": ["retry", "skip", "abort"]
            })

            if user_response.get("action") == "retry":
                # Mark for retry
                state["pending_tasks"] = [
                    t for t in state.get("pending_tasks", [])
                    if t["id"] in failed_tasks
                ]
                return state
            elif user_response.get("action") == "abort":
                state["error"] = "User aborted due to failures"
                return state

        # Update TODO statuses
        for todo in todos:
            todo_id = str(todo.id)
            if todo_id in results:
                result = results[todo_id]
                if result.get("status") == "success":
                    todo.status = TodoStatus.COMPLETED
                    todo.completed_at = datetime.now()
                else:
                    todo.status = TodoStatus.FAILED

        state["todos"] = todos
        state["validation_passed"] = len(failed_tasks) == 0

        logger.info(f"Validation completed. Passed: {state['validation_passed']}")
        return state

    async def response_generator_node(self, state: GraphState) -> GraphState:
        """응답 생성 노드"""
        logger.info("Generating response")

        todos = state.get("todos", [])
        error = state.get("error")

        if error:
            response = f"오류가 발생했습니다: {error}"
        else:
            completed = [t for t in todos if t.status == TodoStatus.COMPLETED]
            pending = [t for t in todos if t.status == TodoStatus.PENDING]

            response = f"작업 완료!\n"
            response += f"- 완료: {len(completed)}개\n"
            response += f"- 대기중: {len(pending)}개\n"

            if completed:
                response += "\n완료된 작업:\n"
                for todo in completed:
                    response += f"✓ {todo.title}\n"

        # Add AI message
        state["messages"].append(AIMessage(content=response))

        logger.info("Response generated")
        return state

    def _route_by_intent(self, state: GraphState) -> Literal["planner", "executor", "response", "end"]:
        """Intent 기반 라우팅"""
        intent = state.get("detected_intent")

        if not intent:
            return "end"

        primary = intent.get("primary")

        # Route based on primary intent
        if primary in ["create", "plan"]:
            return "planner"
        elif primary in ["execute", "run"]:
            return "executor"
        elif primary in ["query", "status"]:
            return "response"
        else:
            return "planner"  # Default to planner

    def _detect_intent(self, query: str, state: GraphState) -> Dict[str, Any]:
        """간단한 Intent 감지 (Mock)"""
        query_lower = query.lower()

        # Simple keyword-based detection
        if any(word in query_lower for word in ["만들", "생성", "create", "make"]):
            primary = "create"
        elif any(word in query_lower for word in ["실행", "run", "execute"]):
            primary = "execute"
        elif any(word in query_lower for word in ["상태", "status", "어떻게"]):
            primary = "query"
        else:
            primary = "create"  # Default

        return {
            "primary": primary,
            "secondary": None,
            "confidence": 0.8,
            "entities": {},
            "requires_context": False,
            "suggested_action": primary
        }

    def _generate_todos(self, query: str) -> List[TodoItem]:
        """TODO 생성 (Mock)"""
        # Mock TODO generation
        todos = [
            TodoItem(
                title="데이터 분석",
                description="사용자 쿼리에 대한 데이터 분석",
                priority=TodoPriority.HIGH,
                status=TodoStatus.PENDING
            ),
            TodoItem(
                title="보고서 작성",
                description="분석 결과를 바탕으로 보고서 작성",
                priority=TodoPriority.MEDIUM,
                status=TodoStatus.PENDING
            ),
            TodoItem(
                title="결과 검증",
                description="작성된 보고서 검증",
                priority=TodoPriority.LOW,
                status=TodoStatus.PENDING
            )
        ]
        return todos

    def _edit_todos(self, todos: List[TodoItem], feedback: str) -> List[TodoItem]:
        """TODO 수정 (Mock)"""
        # Simple mock editing
        return todos

    def _determine_task_type(self, todo: TodoItem) -> str:
        """작업 타입 결정 (Mock)"""
        title_lower = todo.title.lower()

        if "검색" in title_lower or "search" in title_lower:
            return "search"
        elif "분석" in title_lower or "analysis" in title_lower:
            return "analysis"
        elif "문서" in title_lower or "document" in title_lower:
            return "document"
        else:
            return "general"

    def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """작업 실행 (Mock)"""
        # Mock execution
        return {
            "status": "success",
            "result": f"Task {task['id']} completed",
            "execution_time": 0.5
        }

    async def invoke(self, input_data: Dict[str, Any], config: Optional[Dict] = None):
        """그래프 실행"""
        if not self._initialized:
            await self.initialize()

        return await self.graph.ainvoke(input_data, config=config)

    async def stream(self, input_data: Dict[str, Any], config: Optional[Dict] = None):
        """스트리밍 실행"""
        if not self._initialized:
            await self.initialize()

        async for event in self.graph.astream(input_data, config=config):
            yield event

    async def get_state(self, config: Dict) -> Any:
        """현재 상태 가져오기"""
        if not self._initialized:
            await self.initialize()

        if self.checkpointer:
            return await self.checkpointer.aget(config)
        return None