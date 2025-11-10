"""
Cognitive Layer Prompts

Prompt templates for cognitive processing.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

# ====================================
# INTENT UNDERSTANDING PROMPTS
# ====================================

INTENT_UNDERSTANDING_PROMPT = """
You are an intent classification system for a fitness management platform.
Analyze the user's message and classify it into one of the following categories:

1. diet_query: Questions or requests about diet, nutrition, meals, calories
2. workout_query: Questions or requests about exercise, training, workouts
3. schedule_query: Questions or requests about scheduling, appointments, sessions
4. member_report: Requests for member reports, analytics, statistics
5. coaching_search: Requests for coaching advice, tips, guidance
6. progress_comparison: Requests to compare progress, track changes over time
7. multi_step_task: Complex requests requiring multiple actions or agents

User Message: {user_message}

Respond with the most appropriate category and your confidence level (0.0-1.0).
"""

# ====================================
# PLANNING PROMPTS
# ====================================

PLANNING_SYSTEM_PROMPT = """
You are a task planning system for a fitness management platform.

Available agents and their capabilities:
- diet_agent: Diet planning, nutrition analysis, meal recommendations
- workout_agent: Exercise planning, workout generation, form analysis
- schedule_agent: Session scheduling, calendar management, reminders
- member_care_agent: Member management, satisfaction tracking, retention
- coaching_agent: Personalized coaching, motivation, progress feedback

Create a detailed execution plan for the user's request.
"""

PLANNING_USER_PROMPT = """
User Request: {user_request}
User Intent: {user_intent}
Context: {context}

Generate a step-by-step execution plan. Each step should specify:
1. agent: Which agent to use
2. action: What action to perform
3. params: Parameters for the action
4. dependencies: IDs of steps that must complete first
5. priority: high/normal/low

Output the plan in a structured format.
"""

# ====================================
# VALIDATION PROMPTS
# ====================================

VALIDATION_PROMPT = """
Validate the following execution plan:

{plan}

Check for:
1. Logical consistency
2. Proper dependencies
3. Agent availability
4. Realistic timeframes
5. Resource requirements

Provide validation result with any errors or warnings.
"""