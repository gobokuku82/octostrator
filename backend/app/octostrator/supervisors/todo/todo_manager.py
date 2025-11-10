"""TODO Agent

TODO 관리와 Human-in-the-Loop (HITL)을 담당하는 Agent
계획을 TODO로 변환하고 사용자 승인을 처리합니다.
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import uuid
import json

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END, START
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...execution_agents.base.base_agent import BaseAgent, AgentStatus
from ...execution_agents.base.agent_registry import register_agent
from ...execution_agents.base.capabilities import Capability

logger = logging.getLogger(__name__)


# ====================================
# State Import
# ====================================
# Import state from centralized states folder
from ...states.todo_state import TodoAgentState


# ====================================
# TodoAgent Implementation
# ====================================

@register_agent("todo_agent")
class TodoAgent(BaseAgent):
    """TODO Management Agent with HITL Support

    주요 기능:
    1. Plan을 실행 가능한 TODO로 변환
    2. TODO 간 의존성 분석
    3. Human-in-the-Loop 처리
    4. TODO 수정 및 재구성
    5. 실행 우선순위 결정
    """

    def __init__(self):
        super().__init__(
            agent_id="todo_agent",
            agent_name="TODO Management Agent",
            description="Manages TODOs and handles human-in-the-loop interactions",
            enable_checkpoint=True,  # HITL을 위해 checkpoint 필요
            metadata={
                "version": "2.0",
                "supports_hitl": True,
                "max_todos": 100
            }
        )

        # Agent capabilities
        self.capabilities = [
            Capability.TODO_MANAGEMENT.value,
            Capability.TASK_PRIORITIZATION.value,
            Capability.DEPENDENCY_RESOLUTION.value,
            Capability.USER_INTERACTION.value
        ]

        self.primary_capabilities = [
            Capability.TODO_MANAGEMENT.value
        ]

        self.llm = None

    def build_graph(self, llm=None) -> StateGraph:
        """TODO Agent의 LangGraph workflow 구축"""

        # LLM 설정
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

        # StateGraph 생성
        workflow = StateGraph(TodoAgentState)

        # 노드 추가
        workflow.add_node("analyze_plan", self.analyze_plan_node)
        workflow.add_node("generate_todos", self.generate_todos_node)
        workflow.add_node("analyze_dependencies", self.analyze_dependencies_node)
        workflow.add_node("request_human_approval", self.request_human_approval_node)
        workflow.add_node("wait_for_human", self.wait_for_human_node)
        workflow.add_node("apply_modifications", self.apply_modifications_node)
        workflow.add_node("finalize_todos", self.finalize_todos_node)
        workflow.add_node("generate_execution_plan", self.generate_execution_plan_node)

        # 엣지 추가
        workflow.add_edge(START, "analyze_plan")
        workflow.add_edge("analyze_plan", "generate_todos")
        workflow.add_edge("generate_todos", "analyze_dependencies")
        workflow.add_edge("analyze_dependencies", "request_human_approval")

        # HITL 조건부 엣지
        workflow.add_conditional_edges(
            "request_human_approval",
            self.check_approval_required,
            {
                "need_approval": "wait_for_human",
                "auto_approve": "finalize_todos"
            }
        )

        # Human 응답 처리
        workflow.add_conditional_edges(
            "wait_for_human",
            self.check_human_response,
            {
                "approved": "finalize_todos",
                "modified": "apply_modifications",
                "rejected": END
            }
        )

        workflow.add_edge("apply_modifications", "analyze_dependencies")
        workflow.add_edge("finalize_todos", "generate_execution_plan")
        workflow.add_edge("generate_execution_plan", END)

        return workflow

    async def process_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """작업 처리 (BaseAgent 추상 메서드 구현)"""
        # 이 메서드는 execute()에서 graph를 통해 처리되므로 직접 구현 불필요
        pass

    # ====================================
    # Node Implementations
    # ====================================

    async def analyze_plan_node(self, state: TodoAgentState) -> Dict[str, Any]:
        """계획 분석"""
        try:
            plan = state.task.get("plan") or state.plan

            if not plan:
                logger.warning("[TodoAgent] No plan provided")
                return {"error": "No plan to analyze"}

            # 계획 검증
            validation = self._validate_plan(plan)

            if not validation["valid"]:
                logger.error(f"[TodoAgent] Invalid plan: {validation['errors']}")
                return {"error": f"Invalid plan: {', '.join(validation['errors'])}"}

            logger.info(
                f"[TodoAgent] Analyzing plan: {plan.get('goal', 'Unknown goal')}"
            )

            return {
                "plan": plan,
                "metadata": {
                    **state.metadata,
                    "plan_analyzed": True,
                    "plan_steps": len(plan.get("steps", []))
                }
            }

        except Exception as e:
            logger.error(f"[TodoAgent] Plan analysis failed: {e}")
            return {"error": str(e)}

    async def generate_todos_node(self, state: TodoAgentState) -> Dict[str, Any]:
        """Plan을 TODO로 변환"""
        try:
            plan = state.plan
            todos = []

            # LLM 가져오기 (Phase 1: Agent 선택용)
            llm = self.llm or ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

            for i, step in enumerate(plan.get("steps", [])):
                # ⭐ LLM으로 Agent 선택 (Phase 1 통합)
                agent_name = await select_agent_for_task(step, llm=llm)

                todo = {
                    "id": step.get("step_id", f"todo_{uuid.uuid4().hex[:8]}"),
                    "agent": agent_name,  # ✅ 동적 할당
                    "task": step.get("action", "process"),
                    "capability": step.get("capability", "general"),
                    "params": step.get("params", {}),
                    "dependencies": step.get("dependencies", []),
                    "priority": step.get("priority", "normal"),
                    "estimated_time": step.get("estimated_time", "unknown"),
                    "description": step.get("description", ""),
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                }
                todos.append(todo)

            # LLM으로 TODO 최적화 (필요시)
            if self.llm and len(todos) > 5:
                todos = await self._optimize_todos_with_llm(todos, plan)

            logger.info(f"[TodoAgent] Generated {len(todos)} TODOs")

            return {
                "todos": todos,
                "metadata": {
                    **state.metadata,
                    "todos_generated": len(todos)
                }
            }

        except Exception as e:
            logger.error(f"[TodoAgent] TODO generation failed: {e}")
            return {"todos": []}

    async def analyze_dependencies_node(self, state: TodoAgentState) -> Dict[str, Any]:
        """TODO 간 의존성 분석"""
        try:
            todos = state.todos

            # 의존성 그래프 생성
            dependency_graph = {}
            for todo in todos:
                todo_id = todo["id"]
                deps = todo.get("dependencies", [])
                dependency_graph[todo_id] = deps

            # 순환 의존성 검사
            cycles = self._detect_cycles(dependency_graph)
            if cycles:
                logger.warning(f"[TodoAgent] Circular dependencies detected: {cycles}")
                # 순환 의존성 제거
                todos = self._remove_cycles(todos, cycles)

            # 실행 레벨 계산 (병렬 실행 가능 그룹)
            execution_levels = self._calculate_execution_levels(todos)

            logger.info(
                f"[TodoAgent] Dependencies analyzed: "
                f"{len(execution_levels)} execution levels"
            )

            return {
                "todos": todos,
                "metadata": {
                    **state.metadata,
                    "dependency_analysis": {
                        "execution_levels": execution_levels,
                        "cycles_removed": len(cycles) if cycles else 0
                    }
                }
            }

        except Exception as e:
            logger.error(f"[TodoAgent] Dependency analysis failed: {e}")
            return {"todos": state.todos}

    async def request_human_approval_node(self, state: TodoAgentState) -> Dict[str, Any]:
        """Human 승인 요청"""
        try:
            # 승인 요청 메시지 생성
            approval_request = {
                "type": "todo_approval_request",
                "session_id": state.user_context.get("session_id"),
                "todos": state.todos,
                "plan_goal": state.plan.get("goal", "Unknown goal"),
                "total_todos": len(state.todos),
                "estimated_time": self._calculate_total_time(state.todos),
                "request_time": datetime.now().isoformat()
            }

            logger.info("[TodoAgent] Requesting human approval for TODOs")

            return {
                "requires_approval": True,
                "approval_status": "pending",
                "metadata": {
                    **state.metadata,
                    "approval_request": approval_request
                }
            }

        except Exception as e:
            logger.error(f"[TodoAgent] Failed to request approval: {e}")
            return {"requires_approval": False}

    async def wait_for_human_node(self, state: TodoAgentState) -> Dict[str, Any]:
        """Human 응답 대기 (실제 구현은 외부에서)"""
        # 이 노드는 checkpoint를 사용하여 상태를 저장하고
        # 외부에서 human_feedback이 설정될 때까지 대기
        logger.info("[TodoAgent] Waiting for human response...")

        # Human feedback이 이미 있으면 처리
        if state.human_feedback:
            return {
                "approval_status": state.human_feedback.get("action", "approved"),
                "modifications": state.human_feedback.get("modifications", [])
            }

        # 없으면 대기 상태 유지
        return {"approval_status": "pending"}

    async def apply_modifications_node(self, state: TodoAgentState) -> Dict[str, Any]:
        """Human이 요청한 수정사항 적용"""
        try:
            modifications = state.modifications
            todos = state.todos

            for modification in modifications:
                todo_id = modification.get("todo_id")
                changes = modification.get("changes", {})

                # 해당 TODO 찾기
                for todo in todos:
                    if todo["id"] == todo_id:
                        # 수정사항 적용
                        for key, value in changes.items():
                            todo[key] = value
                        break

                # 새 TODO 추가
                if modification.get("action") == "add":
                    new_todo = modification.get("new_todo")
                    if new_todo:
                        todos.append(new_todo)

                # TODO 삭제
                if modification.get("action") == "delete":
                    todos = [t for t in todos if t["id"] != todo_id]

            logger.info(
                f"[TodoAgent] Applied {len(modifications)} modifications"
            )

            return {
                "todos": todos,
                "approval_status": "modified",
                "metadata": {
                    **state.metadata,
                    "modifications_applied": len(modifications)
                }
            }

        except Exception as e:
            logger.error(f"[TodoAgent] Failed to apply modifications: {e}")
            return {"todos": state.todos}

    async def finalize_todos_node(self, state: TodoAgentState) -> Dict[str, Any]:
        """TODO 최종 확정"""
        try:
            todos = state.todos

            # 최종 검증
            for todo in todos:
                # ID 확인
                if "id" not in todo:
                    todo["id"] = f"todo_{uuid.uuid4().hex[:8]}"

                # 상태 초기화
                todo["status"] = "pending"
                todo["finalized_at"] = datetime.now().isoformat()

            logger.info(f"[TodoAgent] Finalized {len(todos)} TODOs")

            return {
                "todos": todos,
                "approval_status": "approved",
                "metadata": {
                    **state.metadata,
                    "todos_finalized": True,
                    "final_todo_count": len(todos)
                }
            }

        except Exception as e:
            logger.error(f"[TodoAgent] Failed to finalize TODOs: {e}")
            return {"todos": state.todos}

    async def generate_execution_plan_node(self, state: TodoAgentState) -> Dict[str, Any]:
        """실행 계획 생성"""
        try:
            todos = state.todos

            # 실행 순서 계산
            execution_order = self._calculate_execution_order(todos)

            execution_plan = {
                "total_todos": len(todos),
                "execution_levels": execution_order,
                "estimated_total_time": self._calculate_total_time(todos),
                "parallel_groups": len(execution_order),
                "created_at": datetime.now().isoformat()
            }

            logger.info(
                f"[TodoAgent] Execution plan created: "
                f"{len(execution_order)} parallel groups"
            )

            return {
                "execution_plan": execution_plan,
                "result": {
                    "todos": todos,
                    "execution_plan": execution_plan,
                    "status": "ready_for_execution"
                }
            }

        except Exception as e:
            logger.error(f"[TodoAgent] Failed to generate execution plan: {e}")
            return {
                "result": {
                    "todos": state.todos,
                    "status": "planning_failed",
                    "error": str(e)
                }
            }

    # ====================================
    # Conditional Functions
    # ====================================

    def check_approval_required(self, state: TodoAgentState) -> Literal["need_approval", "auto_approve"]:
        """승인 필요 여부 확인"""
        # 설정에 따라 자동 승인 가능
        if state.user_context.get("auto_approve", False):
            return "auto_approve"

        # TODO 수가 적으면 자동 승인
        if len(state.todos) <= 2:
            return "auto_approve"

        # 높은 우선순위 작업이 있으면 승인 필요
        has_high_priority = any(
            t.get("priority") == "high" for t in state.todos
        )
        if has_high_priority:
            return "need_approval"

        return "need_approval"

    def check_human_response(self, state: TodoAgentState) -> Literal["approved", "modified", "rejected"]:
        """Human 응답 확인"""
        if state.approval_status == "rejected":
            return "rejected"
        elif state.approval_status == "modified" or state.modifications:
            return "modified"
        else:
            return "approved"

    # ====================================
    # Helper Methods
    # ====================================

    def _validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """계획 검증"""
        errors = []

        if not plan:
            errors.append("Plan is empty")
            return {"valid": False, "errors": errors}

        if "goal" not in plan:
            errors.append("Missing goal")

        if "steps" not in plan or not plan["steps"]:
            errors.append("No steps defined")

        return {"valid": len(errors) == 0, "errors": errors}

    def _detect_cycles(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """순환 의존성 감지"""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    # 순환 발견
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:])
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _remove_cycles(self, todos: List[Dict], cycles: List[List[str]]) -> List[Dict]:
        """순환 의존성 제거"""
        for cycle in cycles:
            # 마지막 의존성 제거
            if len(cycle) >= 2:
                last_todo_id = cycle[-1]
                dep_to_remove = cycle[0]

                for todo in todos:
                    if todo["id"] == last_todo_id:
                        if dep_to_remove in todo.get("dependencies", []):
                            todo["dependencies"].remove(dep_to_remove)

        return todos

    def _calculate_execution_levels(self, todos: List[Dict]) -> List[List[str]]:
        """실행 레벨 계산 (병렬 실행 가능 그룹)"""
        levels = []
        completed = set()
        todo_map = {t["id"]: t for t in todos}

        while len(completed) < len(todos):
            level = []

            for todo in todos:
                if todo["id"] in completed:
                    continue

                # 모든 의존성이 완료되었는지 확인
                deps = todo.get("dependencies", [])
                if all(d in completed for d in deps):
                    level.append(todo["id"])

            if not level:
                # 더 이상 진행할 수 없음
                break

            levels.append(level)
            completed.update(level)

        return levels

    def _calculate_execution_order(self, todos: List[Dict]) -> List[List[str]]:
        """실행 순서 계산"""
        return self._calculate_execution_levels(todos)

    def _calculate_total_time(self, todos: List[Dict]) -> str:
        """총 예상 시간 계산"""
        # 간단한 구현 (실제로는 더 복잡한 로직 필요)
        total_minutes = len(todos) * 2  # 각 TODO당 평균 2분
        return f"{total_minutes} minutes"

    async def _optimize_todos_with_llm(
        self,
        todos: List[Dict],
        plan: Dict[str, Any]
    ) -> List[Dict]:
        """LLM을 사용한 TODO 최적화"""
        # TODO: 구현 필요
        return todos


# ====================================
# AGENT SELECTION (Phase 1 통합)
# ====================================

async def select_agent_for_task(step: dict, llm) -> str:
    """
    Task를 분석하여 적절한 Agent 선택 (LLM 기반)

    ⚠️ 현재 상태 (TEMPORARY - 하드코딩)
    ==========================================
    PT 도메인 Agent 7개가 하드코딩되어 있습니다:
    - frontdesk_agent, assessor_agent, program_designer_agent
    - manager_agent, marketing_agent, owner_assistant_agent
    - trainer_education_agent

    🔮 향후 계획 (Dynamic Agent Discovery)
    ==========================================
    Agent Registry 기반 동적 탐색으로 전환하여
    어떤 도메인 Agent든 추가 즉시 자동으로 사용 가능하게 합니다.

    📝 향후 구현 방법 (상세 가이드)
    ==========================================

    ## Step 1: Agent Registry에서 동적으로 Agent 목록 가져오기

    ```python
    from backend.app.octostrator.execution_agents import agent_registry

    # 등록된 모든 Agent 조회
    available_agents = agent_registry.list_agents()

    if not available_agents:
        logger.warning("[TodoManager] No agents registered")
        return None  # Agent 없음 명시

    # Agent 정보 수집
    agents_info = []
    for agent_id in available_agents:
        agent = agent_registry.get_agent_instance(agent_id)
        if agent:
            agents_info.append({
                "id": agent_id,
                "name": agent.agent_name,
                "description": agent.description,
                "capabilities": [c.value for c in agent.capabilities]
            })
    ```

    ## Step 2: 동적으로 LLM 프롬프트 생성

    ```python
    # Agent 설명 자동 생성
    agent_descriptions = "\\n".join([
        f"- {a['id']}: {a['description']} "
        f"(Capabilities: {', '.join(a['capabilities'])})"
        for a in agents_info
    ])

    prompt = f'''You are an AI agent router.

    Available agents:
    {agent_descriptions}

    Task: {task_description}

    Select the most appropriate agent and return ONLY the agent ID.
    If no suitable agent exists, return "none".
    '''

    # LLM 호출
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    agent_name = response.content.strip().lower()

    # Validation (동적)
    if agent_name not in available_agents and agent_name != "none":
        logger.warning(f"Invalid agent '{agent_name}', no fallback")
        return None

    return agent_name if agent_name != "none" else None
    ```

    ## Step 3: 새 Agent 추가 방법 (예시)

    ```python
    # 1. BaseAgent를 상속받는 클래스 생성
    from backend.app.octostrator.execution_agents.base import BaseAgent
    from backend.app.octostrator.execution_agents.base.capabilities import Capability
    from backend.app.octostrator.execution_agents.base import register_agent

    @register_agent("my_custom_agent")
    class MyCustomAgent(BaseAgent):
        def __init__(self):
            super().__init__(
                agent_id="my_custom_agent",
                agent_name="My Custom Agent",
                description="Handles data analysis and reporting for business domain"
            )

            # Agent가 제공하는 능력 선언
            self.capabilities = [
                Capability.DATA_ANALYSIS,
                Capability.REPORT_GENERATION,
                Capability.TASK_MANAGEMENT
            ]

            # 주 능력 (우선순위 높음)
            self.primary_capabilities = [
                Capability.DATA_ANALYSIS
            ]

        async def process_task(self, task, context):
            # Agent 로직 구현
            return {"status": "completed", "result": {...}}

    # 2. 이제 select_agent_for_task()가 자동으로 이 Agent를 인식!
    #    "데이터 분석해줘" → my_custom_agent 선택됨
    ```

    ✅ Migration Checklist
    ==========================================
    현재 하드코딩을 동적 탐색으로 전환하려면:

    - [ ] Line 594-608: LLM 프롬프트를 동적 생성으로 변경
    - [ ] Line 615-623: valid_agents 리스트를 agent_registry.list_agents()로 대체
    - [ ] Line 625-630: Fallback 로직 개선 (Agent 없을 때 None 반환)
    - [ ] Line 590-591: 기본 Agent fallback 제거
    - [ ] 테스트 시나리오:
          * Agent 0개 → None 반환
          * Agent 1개 → 해당 Agent 선택
          * Agent 여러 개 → LLM이 적합한 Agent 선택

    Args:
        step (dict): Plan step with task description
            - "description": Task description string
            - "action": Alternative task description (fallback)
        llm: Language Model instance for agent selection

    Returns:
        str: Selected agent ID (e.g., "frontdesk_agent")
             현재는 항상 문자열 반환 (fallback 있음)
             향후에는 None 반환 가능 (Agent 없을 때)

    Example:
        >>> # 현재 동작 (하드코딩)
        >>> agent = await select_agent_for_task(
        ...     {"description": "체성분 분석해줘"},
        ...     llm
        ... )
        >>> print(agent)
        "assessor_agent"

        >>> # 향후 동작 (동적)
        >>> agent = await select_agent_for_task(
        ...     {"description": "데이터 분석해줘"},
        ...     llm
        ... )
        >>> print(agent)
        "my_custom_agent"  # Agent Registry에 등록된 Agent 자동 선택

        >>> # Agent 없을 때
        >>> agent = await select_agent_for_task(
        ...     {"description": "테스트"},
        ...     llm
        ... )
        >>> print(agent)
        None  # 향후에는 None 반환 (현재는 fallback)

    See Also:
        - backend/app/octostrator/execution_agents/base/agent_registry.py
        - backend/app/octostrator/execution_agents/base/base_agent.py
        - reports/base_agent/SUPERVISOR_GENERALIZATION_PLAN_251110.md
    """
    task_description = step.get("description", "") or step.get("action", "")

    if not task_description:
        logger.warning("[TodoManager] Empty task description, using default agent")
        return "frontdesk_agent"

    try:
        # LLM 프롬프트
        prompt = f"""You are an AI agent router. Given a task description, select the most appropriate agent.

Available agents:
- frontdesk_agent: 신규 리드 관리, 상담 예약, 문의 응대, 고객 정보 수집
- assessor_agent: 체성분 분석(InBody), 자세 평가, 피트니스 점수 계산
- program_designer_agent: 운동 프로그램 설계, 식단 프로그램 작성
- manager_agent: 회원 출석 관리, 이탈 위험 분석, PT 세션 관리
- marketing_agent: SNS 콘텐츠 생성, 이벤트 기획, 마케팅 캠페인
- owner_assistant_agent: 매출 분석, 트레이너 성과 분석, 비즈니스 리포트
- trainer_education_agent: 트레이너 교육 자료 생성, 스킬 평가

Task: {task_description}

Return ONLY the agent name (e.g., "frontdesk_agent"), nothing else."""

        # LLM 호출
        response = await llm.ainvoke([SystemMessage(content=prompt)])
        agent_name = response.content.strip().lower()

        # Validation: 유효한 agent인지 확인
        valid_agents = [
            "frontdesk_agent",
            "assessor_agent",
            "program_designer_agent",
            "manager_agent",
            "marketing_agent",
            "owner_assistant_agent",
            "trainer_education_agent"
        ]

        if agent_name not in valid_agents:
            logger.warning(
                f"[TodoManager] Invalid agent '{agent_name}' returned by LLM, "
                f"using frontdesk_agent as fallback"
            )
            return "frontdesk_agent"

        logger.info(f"[TodoManager] Selected {agent_name} for task: {task_description}")
        return agent_name

    except Exception as e:
        logger.error(f"[TodoManager] Failed to select agent: {e}", exc_info=True)
        # Fallback: 기본 agent
        return "frontdesk_agent"