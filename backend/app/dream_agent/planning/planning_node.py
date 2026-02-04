"""Planning Layer - 계획 수립 노드

Phase 1: ToolDiscovery 통합으로 YAML 기반 동적 도구/레이어 추론 지원.
"""

import json
from typing import Dict, Any, Optional, Tuple

from backend.app.core.logging import get_logger, LogContext
from backend.app.dream_agent.states.accessors import (
    get_user_input,
    get_intent,
    get_current_context,
    get_session_id,
)
from backend.app.dream_agent.workflow_manager.todo_manager import create_todo
from backend.app.dream_agent.llm_manager import (
    get_llm_client,
    PLANNING_SYSTEM_PROMPT,
    format_planning_prompt
)
from backend.app.dream_agent.workflow_manager import TodoValidator
from backend.app.dream_agent.workflow_manager.planning_manager import (
    plan_manager,
    resource_planner,
    execution_graph_builder
)

# Phase 1: Tool Discovery 통합
from backend.app.dream_agent.tools.discovery import get_tool_discovery

logger = get_logger(__name__)


def _get_layer_from_discovery(tool_name: str) -> Optional[str]:
    """ToolDiscovery에서 도구의 layer 조회

    Args:
        tool_name: 도구 이름

    Returns:
        layer 문자열 또는 None
    """
    discovery = get_tool_discovery()
    spec = discovery.get(tool_name)
    return spec.layer if spec else None


def _infer_tool_and_layer(
    task: str,
    tool: str,
    user_input: str,
    ml_tools: list,
    biz_tools: list,
    ml_keywords: list,
    biz_keywords: list,
    log: Any
) -> Tuple[str, str]:
    """도구와 레이어를 추론

    Phase 1: ToolDiscovery를 우선 사용하고, 없으면 fallback 로직 사용.

    Args:
        task: 작업 설명
        tool: LLM이 반환한 도구 이름 (빈 문자열일 수 있음)
        user_input: 사용자 입력
        ml_tools: ML 도구 목록 (fallback)
        biz_tools: BIZ 도구 목록 (fallback)
        ml_keywords: ML 키워드 목록
        biz_keywords: BIZ 키워드 목록
        log: 로거

    Returns:
        (tool, layer) 튜플
    """
    task_lower = task.lower() if task else ""
    inferred_tool = tool
    inferred_layer = None

    # Phase 1: ToolDiscovery에서 layer 조회
    if tool:
        discovery_layer = _get_layer_from_discovery(tool)
        if discovery_layer:
            log.debug(f"[Phase 1] Found layer '{discovery_layer}' from ToolDiscovery for tool '{tool}'")
            return tool, discovery_layer

    # Tool 추론 (tool이 없는 경우)
    if not tool:
        # task 내용에서 tool 추론
        if any(kw in task_lower for kw in ["수집", "collect", "크롤", "crawl"]):
            inferred_tool = "review_collector"  # YAML 이름 사용
        elif any(kw in task_lower for kw in ["전처리", "preprocess", "정제", "clean"]):
            inferred_tool = "preprocessor"
        elif any(kw in task_lower for kw in ["키워드", "keyword", "추출", "extract"]):
            inferred_tool = "keyword_extractor"
        elif any(kw in task_lower for kw in ["해시태그", "hashtag", "바이럴"]):
            inferred_tool = "hashtag_analyzer"
        elif any(kw in task_lower for kw in ["감성", "sentiment", "긍정", "부정"]):
            inferred_tool = "sentiment_analyzer"
        elif any(kw in task_lower for kw in ["문제", "problem", "이슈", "불만"]):
            inferred_tool = "problem_classifier"
        elif any(kw in task_lower for kw in ["인사이트", "insight", "분석 결과", "도출"]):
            user_input_lower = user_input.lower() if user_input else ""
            if any(kw in user_input_lower for kw in ["트렌드", "trend", "k-beauty", "kbeauty", "글로벌", "global", "마케팅", "marketing"]):
                inferred_tool = "insight_with_trends"
            else:
                inferred_tool = "insight_generator"
        elif any(kw in task_lower for kw in ["트렌드", "trend", "google"]):
            inferred_tool = "google_trends"
        elif any(kw in task_lower for kw in ["경쟁", "competitor", "swot", "비교"]):
            inferred_tool = "competitor_analyzer"
        elif any(kw in task_lower for kw in ["보고서", "report", "리포트"]):
            inferred_tool = "report_generator"
        elif any(kw in task_lower for kw in ["대시보드", "dashboard"]):
            inferred_tool = "dashboard_agent"
        elif any(kw in task_lower for kw in ["광고", "ad", "크리에이티브"]):
            inferred_tool = "ad_creative_agent"
        elif any(kw in task_lower for kw in ["영상", "비디오", "video", "동영상", "숏폼", "릴스", "reels"]):
            inferred_tool = "video_agent"
        elif any(kw in task_lower for kw in ["스토리보드", "storyboard", "콘텐츠 기획", "content plan"]):
            inferred_tool = "storyboard_agent"
        else:
            inferred_tool = "preprocessor"  # 기본값

        log.info(f"[Phase 1] Auto-inferred tool '{inferred_tool}' for task: {task}")

    # Phase 1: 추론된 tool로 ToolDiscovery에서 layer 재조회
    if inferred_tool:
        discovery_layer = _get_layer_from_discovery(inferred_tool)
        if discovery_layer:
            return inferred_tool, discovery_layer

    # Fallback: 기존 로직으로 layer 결정
    if inferred_tool in ml_tools:
        inferred_layer = "ml_execution"
    elif inferred_tool in biz_tools:
        inferred_layer = "biz_execution"
    elif any(kw in task_lower for kw in ml_keywords):
        inferred_layer = "ml_execution"
    elif any(kw in task_lower for kw in biz_keywords):
        inferred_layer = "biz_execution"
    else:
        inferred_layer = "ml_execution"  # 기본값

    return inferred_tool, inferred_layer


async def planning_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planning Layer - 계획 수립 및 Todo 생성

    Args:
        state: AgentState

    Returns:
        Dict with 'plan', 'todos', 'target_context'
    """
    log = LogContext(logger, node="planning")
    user_input = get_user_input(state)
    intent = get_intent(state)
    current_context = get_current_context(state)

    log.info(f"Starting planning for intent type: {intent.get('intent_type', 'unknown')}")
    log.info(f"[planning] Intent flags: requires_ml={intent.get('requires_ml')}, requires_biz={intent.get('requires_biz')}")

    # Session ID 가져오기
    session_id = get_session_id(state) or "unknown_session"

    # LLM 호출
    llm_client = get_llm_client()
    prompt = format_planning_prompt(user_input, intent, current_context)

    try:
        log.debug("Calling LLM for plan generation")
        response = await llm_client.chat_with_system(
            system_prompt=PLANNING_SYSTEM_PROMPT,
            user_message=prompt,
            max_tokens=1000,
            response_format={"type": "json_object"}  # JSON 형식 강제
        )

        # JSON 파싱 시도
        plan_data = json.loads(response)
        plan_description_text = {
            "plan_description": plan_data.get("plan_description", ""),
            "total_steps": plan_data.get("total_steps", 0),
            "estimated_complexity": plan_data.get("estimated_complexity", "low"),
            "workflow_type": plan_data.get("workflow_type", "linear"),
        }

        # Todo 생성
        todos = []
        raw_todos = plan_data.get("todos", [])

        # todos가 리스트가 아닌 경우 처리
        if not isinstance(raw_todos, list):
            log.warning(f"LLM returned non-list todos: {type(raw_todos)}. Using fallback.")
            raise ValueError("Invalid todos format from LLM")

        for idx, todo_data in enumerate(raw_todos):
            try:
                # LLM이 반환한 metadata dict를 개별 파라미터로 추출
                metadata_dict = todo_data.get("metadata", {})

                # task 필드 추출 (LLM이 'task' 또는 'description'으로 반환할 수 있음)
                task = todo_data.get("task") or todo_data.get("description") or todo_data.get("name")
                layer = todo_data.get("layer")

                # layer 검증 및 자동 추론/수정
                tool = metadata_dict.get("tool", "").lower()
                source = metadata_dict.get("source", "")
                tool_params = metadata_dict.get("tool_params", {})

                # task 필드 자동 생성 (LLM이 task를 반환하지 않은 경우)
                if not task:
                    if tool == "collector" and source:
                        task = f"{source}에서 데이터 수집"
                    elif tool == "collector" and tool_params.get("keyword"):
                        task = f"{tool_params['keyword']} 데이터 수집"
                    elif tool == "preprocessor":
                        task = "데이터 전처리"
                    elif tool == "analyzer":
                        task = "데이터 분석"
                    elif tool in ["insight", "insight_generator", "insight_with_trends"]:
                        task = "인사이트 도출"
                    elif tool == "report_agent":
                        task = "보고서 생성"
                    elif tool:
                        task = f"{tool} 실행"
                    else:
                        log.warning(f"Todo {idx} missing 'task' field and cannot auto-generate: {todo_data}")
                        continue  # 이 todo는 스킵

                    log.info(f"Auto-generated task '{task}' for todo {idx} (tool={tool})")

                # ================================================================
                # Phase 1: Tool/Layer 추론 (ToolDiscovery 우선, Fallback 로직 보조)
                # ================================================================
                ml_tools = [
                    "collector", "review_collector", "preprocessor", "analyzer", "insight",
                    "keyword_extractor", "absa_analyzer", "insight_generator",
                    "problem_classifier", "google_trends", "trends",
                    "sentiment", "sentiment_analyzer", "extractor",
                    "hashtag_analyzer", "hashtag", "competitor_analyzer", "competitor",
                    "insight_with_trends", "kbeauty_insight", "trend_insight", "rag_insight"
                ]
                biz_tools = [
                    "report_agent", "report_generator", "dashboard_agent", "ad_creative_agent",
                    "storyboard_agent", "video_agent", "sales_agent", "inventory_agent"
                ]
                ml_task_keywords = [
                    "수집", "collect", "전처리", "preprocess", "분석", "analy",
                    "감성", "sentiment", "키워드", "keyword", "인사이트", "insight",
                    "트렌드", "trend", "추출", "extract", "해시태그", "hashtag",
                    "바이럴", "viral", "경쟁사", "competitor", "SWOT"
                ]
                biz_task_keywords = [
                    "보고서", "report", "대시보드", "dashboard", "광고", "ad",
                    "스토리보드", "storyboard", "비디오", "video", "영상", "동영상",
                    "숏폼", "릴스", "reels", "마케팅"
                ]

                # Phase 1 헬퍼 함수로 tool/layer 추론
                inferred_tool, inferred_layer = _infer_tool_and_layer(
                    task=task,
                    tool=tool,
                    user_input=user_input,
                    ml_tools=ml_tools,
                    biz_tools=biz_tools,
                    ml_keywords=ml_task_keywords,
                    biz_keywords=biz_task_keywords,
                    log=log
                )

                # 추론 결과 적용
                if not tool:
                    tool = inferred_tool
                    log.info(f"[Phase 1] Using inferred tool '{tool}' for todo: {task}")

                if not layer:
                    layer = inferred_layer
                    log.info(f"[Phase 1] Using inferred layer '{layer}' for todo: {task} (tool={tool})")
                elif layer != inferred_layer and tool:
                    log.warning(f"[Phase 1] Layer mismatch for '{task}': LLM='{layer}', inferred='{inferred_layer}'. Using inferred.")
                    layer = inferred_layer

                todo = create_todo(
                    task=task,
                    layer=layer,
                    priority=todo_data.get("priority", 5),
                    tool=tool,  # 추론된 tool 사용 (LLM이 지정 안 한 경우 자동 추론됨)
                    tool_params=metadata_dict.get("tool_params", {}),
                    depends_on=metadata_dict.get("depends_on", []),
                    output_path=metadata_dict.get("output_path")
                )
                todos.append(todo)
            except Exception as todo_err:
                log.warning(f"Failed to create todo {idx}: {todo_err}. Skipping.")
                continue

        # LLM이 반환한 todos가 모두 invalid한 경우 fallback
        if not todos and raw_todos:
            log.warning("All LLM todos were invalid. Using fallback.")
            raise ValueError("No valid todos from LLM")

        log.info(f"Planning completed: {len(todos)} todos created ({plan_description_text['total_steps']} steps)")

        # ========== Phase 2 통합: PlanManager 사용 ==========

        # 1. Plan 객체 생성
        log.info("[Phase 2] Creating Plan object with PlanManager")
        plan_obj = plan_manager.create_plan_for_session(
            session_id=session_id,
            todos=todos,
            intent=intent,
            context={
                "user_input": user_input,
                "current_context": current_context,
                "plan_description": plan_description_text
            }
        )
        log.info(f"[Phase 2] Plan created: plan_id={plan_obj.plan_id}, version={plan_obj.current_version}")

        # 2. Todo 검증 (PlanManager 통합)
        log.info("[Phase 2] Validating todos with PlanManager")
        validation_result = plan_manager.validate_plan_todos(
            plan_id=plan_obj.plan_id,
            user_input=user_input
        )

        if not validation_result["valid"]:
            log.error(f"Todo validation failed: {validation_result['errors']}")
            log.warning("Using fallback todos due to validation failure")
            fallback_todos = TodoValidator.get_fallback_todos(intent, user_input)

            # Fallback todos로 Plan 재생성
            plan_obj = plan_manager.create_plan_for_session(
                session_id=session_id,
                todos=fallback_todos,
                intent=intent,
                context={
                    "user_input": user_input,
                    "current_context": current_context,
                    "plan_description": "Fallback plan due to validation failure"
                }
            )
            todos = fallback_todos
            log.info(f"[planning] Fallback created {len(todos)} todos")
        elif validation_result["warnings"]:
            log.warning(f"Todo validation warnings: {validation_result['warnings']}")

        # 3. 순환 의존성 검사
        log.info("[Phase 2] Checking for circular dependencies")
        cycles = plan_manager.check_circular_dependency(plan_obj.plan_id)
        if cycles:
            log.error(f"Circular dependency detected: {cycles}")
            # 순환 의존성 발견 시 의존성 제거
            for todo in plan_obj.todos:
                todo.depends_on = []
            log.warning("Removed all dependencies to break cycles")

        # 4. 위상 정렬
        log.info("[Phase 2] Applying topological sort to todos")
        sorted_todos = plan_manager.topological_sort_todos(
            plan_id=plan_obj.plan_id,
            apply_to_plan=True
        )
        if sorted_todos:
            todos = sorted_todos
            log.info(f"[Phase 2] Todos sorted topologically: {len(todos)} todos")

        # 5. 자원 할당
        log.info("[Phase 2] Allocating resources with ResourcePlanner")
        resource_plan = resource_planner.allocate_resources(
            plan_id=plan_obj.plan_id,
            todos=todos,
            constraints=None  # 기본 제약 조건 사용
        )
        log.info(f"[Phase 2] Resources allocated: {len(resource_plan.allocations)} allocations")

        # 6. 비용 예상
        cost_estimate = resource_planner.estimate_cost(todos)
        log.info(f"[Phase 2] Cost estimate: ${cost_estimate['total_cost']:.2f}, "
                f"Duration: {cost_estimate['estimated_duration_parallel']:.1f}s (parallel)")

        # 7. 실행 그래프 생성
        log.info("[Phase 2] Building execution graph with ExecutionGraphBuilder")
        execution_graph = execution_graph_builder.build(
            plan_id=plan_obj.plan_id,
            todos=todos,
            resource_plan=resource_plan
        )
        log.info(f"[Phase 2] Execution graph built: {len(execution_graph.nodes)} nodes, "
                f"{len(execution_graph.groups)} groups, "
                f"critical_path={execution_graph.critical_path_duration:.1f}s")

        # 8. Plan 상태를 approved로 변경 (검증 완료)
        plan_obj.status = "approved"
        log.info("[Phase 2] Plan approved and ready for execution")

    except json.JSONDecodeError as e:
        # JSON 파싱 실패 시 fallback todos 사용
        log.warning(f"Planning JSON parsing error: {e}. Using fallback todos.")
        plan_description_text = {
            "plan_description": "Fallback plan due to parsing error",
            "total_steps": 0,
            "estimated_complexity": "low",
            "workflow_type": "linear",
        }
        todos = TodoValidator.get_fallback_todos(intent, user_input)
        log.info(f"Generated {len(todos)} fallback todos")

        # Fallback Plan 생성
        plan_obj = plan_manager.create_plan_for_session(
            session_id=session_id,
            todos=todos,
            intent=intent,
            context={
                "user_input": user_input,
                "current_context": current_context,
                "plan_description": plan_description_text,
                "error": "JSON parsing error"
            }
        )
        plan_obj.status = "approved"

        # 간단한 자원 할당 및 실행 그래프 생성
        resource_plan = resource_planner.allocate_resources(
            plan_id=plan_obj.plan_id,
            todos=todos
        )
        execution_graph = execution_graph_builder.build(
            plan_id=plan_obj.plan_id,
            todos=todos,
            resource_plan=resource_plan
        )
        cost_estimate = resource_planner.estimate_cost(todos)

    except Exception as e:
        # 기타 에러
        log.error(f"Planning node error: {e}", exc_info=True)
        plan_description_text = {
            "plan_description": "Error in planning - using fallback",
            "total_steps": 0,
            "estimated_complexity": "low",
            "workflow_type": "linear",
            "error": str(e)
        }
        todos = TodoValidator.get_fallback_todos(intent, user_input)
        log.info(f"Generated {len(todos)} fallback todos due to error")

        # Fallback Plan 생성
        plan_obj = plan_manager.create_plan_for_session(
            session_id=session_id,
            todos=todos,
            intent=intent,
            context={
                "user_input": user_input,
                "current_context": current_context,
                "plan_description": plan_description_text,
                "error": str(e)
            }
        )
        plan_obj.status = "approved"

        # 간단한 자원 할당 및 실행 그래프 생성
        resource_plan = resource_planner.allocate_resources(
            plan_id=plan_obj.plan_id,
            todos=todos
        )
        execution_graph = execution_graph_builder.build(
            plan_id=plan_obj.plan_id,
            todos=todos,
            resource_plan=resource_plan
        )
        cost_estimate = resource_planner.estimate_cost(todos)

    log.info(f"[planning] Returning {len(todos)} todos to state")
    for t in todos:
        log.info(f"[planning] Todo: task={t.task}, layer={t.layer}, status={t.status}")

    # Phase 2 통합: 상세한 정보 반환
    return {
        # 기존 필드 (하위 호환성 유지)
        "plan": plan_description_text,
        "todos": todos,
        "target_context": plan_description_text["plan_description"],

        # Phase 2 신규 필드
        "plan_obj": plan_obj,  # Plan 객체
        "plan_id": plan_obj.plan_id,
        "resource_plan": resource_plan,
        "execution_graph": execution_graph,
        "cost_estimate": cost_estimate,
        "langgraph_commands": execution_graph.langgraph_commands,
        "mermaid_diagram": execution_graph.mermaid_diagram,
    }
