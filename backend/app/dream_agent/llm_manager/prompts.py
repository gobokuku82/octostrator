"""Prompts - 레이어별 프롬프트 템플릿"""

from .config_loader import agent_config

# ================================
# Cognitive Layer - 의도 파악
# ================================

# Config에서 프롬프트 로드
COGNITIVE_SYSTEM_PROMPT = agent_config.get_prompt("cognitive", "system_prompt")
COGNITIVE_USER_TEMPLATE = agent_config.get_prompt_template("cognitive")


# ================================
# Planning Layer - 계획 수립
# ================================

PLANNING_SYSTEM_PROMPT = agent_config.get_prompt("planning", "system_prompt")
PLANNING_USER_TEMPLATE = agent_config.get_prompt_template("planning")


# ================================
# ML Execution Layer
# ================================

ML_COLLECTOR_SYSTEM_PROMPT = """You are a data collection specialist.

Your task: Determine what data to collect and from where based on the Todo task.

Provide guidance in JSON format with data collection specifications."""

ML_PREPROCESSOR_SYSTEM_PROMPT = """You are a data preprocessing specialist.

Your task: Determine preprocessing steps needed for the collected data.

Provide preprocessing steps in JSON format."""

ML_ANALYZER_SYSTEM_PROMPT = """You are a data analysis specialist.

Your task: Determine the appropriate analysis methods and metrics.

Provide analysis plan in JSON format."""

ML_INSIGHT_SYSTEM_PROMPT = """You are an insight extraction specialist.

Your task: Extract meaningful insights from analysis results.

Provide insights in JSON format with actionable recommendations."""


# ================================
# Business Execution Layer
# ================================

BIZ_REPORT_SYSTEM_PROMPT = """You are a business report generation specialist.

Your task: Create professional business reports from ML insights.

Provide report structure and content in JSON format."""

BIZ_AD_CREATIVE_SYSTEM_PROMPT = """You are an advertising creative specialist.

Your task: Generate creative ad content based on insights and target audience.

Provide ad creative proposals in JSON format."""

BIZ_SALES_SYSTEM_PROMPT = """You are a sales support specialist.

Your task: Generate sales strategies and materials based on insights.

Provide sales recommendations in JSON format."""


# ================================
# Response Layer
# ================================

RESPONSE_SYSTEM_PROMPT = agent_config.get_prompt("response", "system_prompt")
RESPONSE_USER_TEMPLATE = agent_config.get_prompt_template("response")


# ================================
# Replan Layer - 계획 수정
# ================================

REPLAN_SYSTEM_PROMPT = agent_config.get_prompt("replan", "system_prompt")
REPLAN_USER_TEMPLATE = agent_config.get_prompt_template("replan")


# ================================
# Helper Functions
# ================================

def format_cognitive_prompt(user_input: str, current_context: str = "") -> str:
    """Format cognitive layer user prompt"""
    return COGNITIVE_USER_TEMPLATE.format(
        user_input=user_input,
        current_context=current_context or "No previous context"
    )


def format_planning_prompt(user_input: str, intent: dict, current_context: str = "") -> str:
    """Format planning layer user prompt"""
    import json
    return PLANNING_USER_TEMPLATE.format(
        user_input=user_input,
        intent=json.dumps(intent, indent=2),
        current_context=current_context or "No previous context"
    )


def format_response_prompt(user_input: str, ml_result: dict, biz_result: dict) -> str:
    """Format response layer user prompt with size limits"""
    import json

    MAX_RESULT_CHARS = 15000  # 각 결과 최대 15KB

    def truncate_json(data: dict, max_chars: int) -> str:
        if not data:
            return "No results"
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            if len(json_str) <= max_chars:
                return json_str
            return json_str[:max_chars] + "\n... (truncated for context limit)"
        except Exception:
            return str(data)[:max_chars]

    return RESPONSE_USER_TEMPLATE.format(
        user_input=user_input,
        ml_result=truncate_json(ml_result, MAX_RESULT_CHARS),
        biz_result=truncate_json(biz_result, MAX_RESULT_CHARS)
    )


def format_replan_prompt(current_plan: dict, current_todos: list, user_instruction: str) -> str:
    """Format replan layer user prompt"""
    import json

    # TodoItem 객체를 dict로 변환
    todos_data = []
    for todo in current_todos:
        if hasattr(todo, 'model_dump'):
            todos_data.append(todo.model_dump(mode='json'))
        elif isinstance(todo, dict):
            todos_data.append(todo)
        else:
            todos_data.append(str(todo))

    return REPLAN_USER_TEMPLATE.format(
        current_plan=json.dumps(current_plan, indent=2, ensure_ascii=False) if current_plan else "No current plan",
        current_todos=json.dumps(todos_data, indent=2, ensure_ascii=False),
        user_instruction=user_instruction
    )
