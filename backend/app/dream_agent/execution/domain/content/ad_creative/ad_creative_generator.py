"""Ad Creative Generator - 광고 크리에이티브 생성 함수"""

from datetime import datetime
from typing import Dict, Any

from backend.app.dream_agent.biz_execution.ad_creative.ad_creative_agent_tool import AdCreativeAgentTool
from backend.app.dream_agent.models.todo import TodoItem


async def generate_ad_creative(todo: TodoItem, log: Any) -> Dict[str, Any]:
    """
    광고 크리에이티브 생성

    Args:
        todo: TodoItem
        log: LogContext

    Returns:
        Dict with result
    """
    tool = AdCreativeAgentTool()
    context = {}

    result = await tool.execute(todo, context, log)

    return {
        "result_type": "ad_creative",
        "output_path": result.output_path,
        "summary": result.summary,
        "preview": result.preview,
        "output_data": result.output_data,
        "timestamp": datetime.now().isoformat()
    }
