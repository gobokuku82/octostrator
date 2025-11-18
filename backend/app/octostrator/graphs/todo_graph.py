"""TODO Graph - Natural Language to TODO conversion"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from loguru import logger

from backend.app.octostrator.graphs.states import TodoState
from backend.schema.todo import TodoItem, TodoStatus, TodoPriority


class TodoGraph:
    """TODO 자동 생성 및 관리 그래프"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,  # 일관된 TODO 생성을 위해 낮은 temperature
        )
        self.graph = None

    def build_graph(self) -> StateGraph:
        """TODO 그래프 구축"""
        workflow = StateGraph(TodoState)

        # 노드 추가
        workflow.add_node("parse_query", self.parse_query_node)
        workflow.add_node("extract_todos", self.extract_todos_node)
        workflow.add_node("validate_todos", self.validate_todos_node)
        workflow.add_node("optimize_priority", self.optimize_priority_node)

        # 엣지 정의
        workflow.set_entry_point("parse_query")
        workflow.add_edge("parse_query", "extract_todos")
        workflow.add_edge("extract_todos", "validate_todos")
        workflow.add_edge("validate_todos", "optimize_priority")
        workflow.add_edge("optimize_priority", END)

        self.graph = workflow.compile()
        logger.info("TODO graph built successfully")
        return self.graph

    async def parse_query_node(self, state: TodoState) -> Dict[str, Any]:
        """사용자 쿼리를 파싱하여 의도 파악"""
        user_query = state["user_query"]

        system_prompt = """당신은 사용자의 요청을 분석하여 TODO 항목을 추출하는 전문가입니다.

사용자의 요청에서:
1. 해야 할 작업들을 식별
2. 작업 간의 순서/의존성 파악
3. 우선순위 힌트 감지
4. 예상 소요 시간 추정

응답은 JSON 형식으로:
{
    "tasks": [
        {
            "title": "작업 제목",
            "description": "상세 설명",
            "priority_hint": "high/medium/low",
            "estimated_time": "예상 시간 (분)",
            "dependencies": ["의존하는 작업 제목들"]
        }
    ]
}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            logger.debug(f"Query parsed: {response.content}")

            # messages에 분석 결과 추가
            state["messages"].append(HumanMessage(content=user_query))
            state["messages"].append(response)

            return {
                "messages": state["messages"],
                "user_query": user_query,
            }

        except Exception as e:
            logger.error(f"Error parsing query: {e}")
            return {
                "error": str(e),
                "validation_passed": False,
                "validation_errors": [f"Query parsing failed: {str(e)}"]
            }

    async def extract_todos_node(self, state: TodoState) -> Dict[str, Any]:
        """파싱된 정보에서 TODO 객체 생성"""
        try:
            import json
            import re
            from uuid import uuid4

            # 마지막 AI 메시지에서 JSON 추출
            last_message = state["messages"][-1].content

            # JSON 부분만 추출 (코드 블록 제거)
            json_match = re.search(r'\{[\s\S]*\}', last_message)
            if not json_match:
                raise ValueError("No JSON found in response")

            parsed_data = json.loads(json_match.group())
            tasks = parsed_data.get("tasks", [])

            # TODO 객체 생성
            todos: List[TodoItem] = []
            title_to_id = {}  # 의존성 매핑을 위한 제목->ID 맵

            for task in tasks:
                todo_id = uuid4()
                title_to_id[task["title"]] = todo_id

                # 우선순위 매핑
                priority_map = {
                    "high": TodoPriority.HIGH,
                    "medium": TodoPriority.MEDIUM,
                    "low": TodoPriority.LOW
                }
                priority = priority_map.get(
                    task.get("priority_hint", "medium").lower(),
                    TodoPriority.MEDIUM
                )

                todo = TodoItem(
                    id=todo_id,
                    title=task["title"],
                    description=task.get("description", ""),
                    status=TodoStatus.PENDING,
                    priority=priority,
                    estimated_time_minutes=int(task.get("estimated_time", 30)),
                    dependencies=[],  # 나중에 매핑
                    thread_id=state.get("thread_id"),
                )
                todos.append(todo)

            # 의존성 매핑
            for i, task in enumerate(tasks):
                dep_titles = task.get("dependencies", [])
                dep_ids = [
                    title_to_id[title]
                    for title in dep_titles
                    if title in title_to_id
                ]
                todos[i].dependencies = dep_ids

            logger.info(f"Extracted {len(todos)} TODO items")

            return {
                "todos": todos,
                "validation_passed": len(todos) > 0,
                "validation_errors": [] if len(todos) > 0 else ["No TODOs extracted"]
            }

        except Exception as e:
            logger.error(f"Error extracting TODOs: {e}")
            return {
                "todos": [],
                "validation_passed": False,
                "validation_errors": [f"TODO extraction failed: {str(e)}"]
            }

    async def validate_todos_node(self, state: TodoState) -> Dict[str, Any]:
        """TODO 검증 (순환 의존성 체크 등)"""
        todos = state.get("todos", [])
        errors = []

        if not todos:
            return {
                "validation_passed": False,
                "validation_errors": ["No TODOs to validate"]
            }

        # 순환 의존성 체크
        def has_cycle(todo_id, visited, rec_stack, dep_map):
            visited.add(todo_id)
            rec_stack.add(todo_id)

            for dep_id in dep_map.get(todo_id, []):
                if dep_id not in visited:
                    if has_cycle(dep_id, visited, rec_stack, dep_map):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(todo_id)
            return False

        # 의존성 맵 생성
        dep_map = {todo.id: todo.dependencies for todo in todos}
        visited = set()
        rec_stack = set()

        for todo in todos:
            if todo.id not in visited:
                if has_cycle(todo.id, visited, rec_stack, dep_map):
                    errors.append(f"Circular dependency detected involving: {todo.title}")

        # 존재하지 않는 의존성 체크
        todo_ids = {todo.id for todo in todos}
        for todo in todos:
            for dep_id in todo.dependencies:
                if dep_id not in todo_ids:
                    errors.append(
                        f"TODO '{todo.title}' has invalid dependency: {dep_id}"
                    )

        validation_passed = len(errors) == 0
        logger.info(f"Validation {'passed' if validation_passed else 'failed'}")

        return {
            "validation_passed": validation_passed,
            "validation_errors": errors,
            "requires_confirmation": len(todos) > 5,  # 5개 이상이면 확인 요청
        }

    async def optimize_priority_node(self, state: TodoState) -> Dict[str, Any]:
        """TODO 우선순위 자동 최적화"""
        todos = state.get("todos", [])

        if not state.get("validation_passed", False):
            logger.warning("Skipping priority optimization due to validation failure")
            return {}

        # 의존성 기반 우선순위 조정
        # 의존성이 많은 TODO는 우선순위를 높임
        dep_count = {}
        for todo in todos:
            dep_count[todo.id] = len(todo.dependencies)

        # 의존성이 0인 TODO (루트 작업)는 우선순위를 높임
        for todo in todos:
            if dep_count[todo.id] == 0 and todo.priority == TodoPriority.LOW:
                todo.priority = TodoPriority.MEDIUM
                logger.debug(f"Boosted priority for root task: {todo.title}")

        # 긴 작업은 우선순위를 높임
        for todo in todos:
            if todo.estimated_time_minutes and todo.estimated_time_minutes > 120:
                if todo.priority == TodoPriority.LOW:
                    todo.priority = TodoPriority.MEDIUM
                    logger.debug(f"Boosted priority for long task: {todo.title}")

        logger.info("Priority optimization completed")

        return {
            "todos": todos
        }

    async def invoke(self, user_query: str, thread_id: str, session_id: str) -> Dict[str, Any]:
        """TODO 그래프 실행"""
        if not self.graph:
            self.build_graph()

        initial_state: TodoState = {
            "messages": [],
            "session_id": session_id,
            "thread_id": thread_id,
            "user_id": None,
            "error": None,
            "created_at": None,
            "updated_at": None,
            "user_query": user_query,
            "todos": [],
            "current_todo": None,
            "todo_dependencies": {},
            "validation_passed": False,
            "validation_errors": [],
            "requires_confirmation": False,
            "user_feedback": None,
        }

        result = await self.graph.ainvoke(initial_state)
        return result
