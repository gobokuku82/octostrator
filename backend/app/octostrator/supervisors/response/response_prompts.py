"""
Response Layer Prompts

Prompt templates for response generation.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

# ====================================
# CHAT GENERATION PROMPTS
# ====================================

CHAT_GENERATION_PROMPT = """
Convert the following execution results into a natural, conversational response for the user.

Execution Results:
{results}

Original Request: {user_request}

Guidelines:
- Be friendly and encouraging
- Use appropriate emojis sparingly
- Highlight key achievements
- Be honest about any issues
- Provide clear next steps
- Keep it concise but informative

Generate a response in Korean that feels natural and helpful.
"""

# ====================================
# REPORT GENERATION PROMPTS
# ====================================

REPORT_GENERATION_PROMPT = """
Generate a professional report based on the execution results.

Execution Results:
{results}

Report Sections Required:
1. Executive Summary
2. Detailed Results
3. Performance Metrics
4. Issues and Resolutions
5. Recommendations
6. Next Steps

Format as a structured Markdown document.
"""

# ====================================
# GRAPH DESCRIPTION PROMPTS
# ====================================

GRAPH_DESCRIPTION_PROMPT = """
Describe the workflow graph for the user.

Graph Data:
{graph_data}

Provide:
1. Overview of the workflow
2. Key decision points
3. Parallel vs sequential execution
4. Critical path
5. Optimization opportunities

Make it easy to understand for non-technical users.
"""

# ====================================
# HITL PROMPTS
# ====================================

HITL_APPROVAL_REQUEST_PROMPT = """
Create a clear approval request for the user.

Execution Plan:
{plan}

Format the request to include:
1. What will be done
2. Why approval is needed
3. Potential impacts
4. Options (Approve/Modify/Reject)
5. Recommended action

Use clear, simple language.
"""

HITL_MODIFICATION_PROMPT = """
The user wants to modify the execution plan.

Original Plan:
{original_plan}

User Feedback:
{user_feedback}

Apply the modifications and create an updated plan.
Explain what changed and why.
"""

# ====================================
# FORMAT SELECTION PROMPTS
# ====================================

FORMAT_SELECTION_PROMPT = """
Based on the user's request and the execution results, determine the best output format.

User Request: {user_request}
Results Type: {results_type}
Data Complexity: {complexity}

Choose one:
- chat: For conversational responses
- graph: For workflow or relationship visualization
- report: For detailed analysis and documentation

Consider:
- User's implied preference
- Data characteristics
- Use case context

Respond with the format name and brief reasoning.
"""