"""
Execute Layer Prompts

Prompt templates for execution processing.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

# ====================================
# EXECUTION PROMPTS
# ====================================

EXECUTION_INSTRUCTION_PROMPT = """
You are executing a task as part of a fitness management workflow.

Task Details:
Agent: {agent}
Action: {action}
Parameters: {params}
Context: {context}

Execute the task and provide:
1. Status (completed/failed)
2. Result data
3. Any warnings or notes
4. Next recommended actions
"""

# ====================================
# AGGREGATION PROMPTS
# ====================================

AGGREGATION_PROMPT = """
You are aggregating execution results from multiple agents.

Execution Results:
{results}

Create a comprehensive summary that includes:
1. Overall status
2. Key achievements
3. Any failures or issues
4. Insights and patterns
5. Recommendations

Format the response for clarity and actionability.
"""

INSIGHT_GENERATION_PROMPT = """
Analyze the following execution results and generate insights:

{results}

Focus on:
1. Trends: What patterns do you see?
2. Anomalies: Any unexpected results?
3. Opportunities: What improvements are possible?
4. Risks: What issues need attention?

Provide 3-5 actionable insights.
"""

# ====================================
# ERROR HANDLING PROMPTS
# ====================================

ERROR_ANALYSIS_PROMPT = """
Analyze the following execution error:

Error: {error}
Context: {context}
Failed Task: {task}

Provide:
1. Error classification (temporary/permanent/user_error/system_error)
2. Root cause analysis
3. Recommended recovery action
4. Prevention suggestions
"""

RETRY_DECISION_PROMPT = """
Should we retry the following failed task?

Task: {task}
Error: {error}
Previous Attempts: {retry_count}
Max Retries: {max_retries}

Consider:
- Error type
- Likelihood of success on retry
- Resource cost
- User impact

Respond with: RETRY, SKIP, or FAIL with reasoning.
"""