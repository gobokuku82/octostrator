"""Chat Generator

자연스러운 대화형 답변 생성
Phase 3.5: Aggregated Data → Natural Language Response
"""
from typing import Dict
from langchain_core.messages import AIMessage
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def chat_generator_node(state: SupervisorState) -> Dict:
    """Chat Generator - 자연스러운 대화형 답변 생성

    Frontend: 일반적인 채팅 인터페이스

    Args:
        state: 현재 SupervisorState (aggregated_data 포함)

    Returns:
        Dict: final_result와 messages 업데이트
    """
    aggregated_data = state["aggregated_data"]

    # 구조화된 데이터 → 자연어 변환
    chat_response = f"""{aggregated_data['final_answer']}

---

📊 **실행 요약**
- 총 {aggregated_data['execution_summary']['total_steps']}개 단계 실행
- 완료: {aggregated_data['execution_summary']['completed_steps']}개
- 실패: {aggregated_data['execution_summary']['failed_steps']}개
- 사용자 승인: {aggregated_data['execution_summary']['hitl_interactions']}회

💡 **주요 인사이트**
"""

    # 인사이트 추가 (중요도 높은 순)
    insights = sorted(
        aggregated_data['insights'],
        key=lambda x: x['importance'],
        reverse=True
    )

    for i, insight in enumerate(insights[:3], 1):  # 상위 3개만
        emoji = {
            "trend": "📈",
            "anomaly": "⚠️",
            "recommendation": "✅"
        }.get(insight['category'], "•")

        chat_response += f"\n{emoji} {insight['description']}"

    # 단계별 상세 정보 (선택적, 간략하게)
    chat_response += "\n\n---\n\n"
    chat_response += "**실행 단계**\n\n"

    for step in aggregated_data['steps']:
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "running": "🔄",
            "pending": "⏳",
            "waiting_human": "🙋"
        }.get(step['status'], "❓")

        chat_response += f"{status_emoji} Step {step['step_id']}: [{step['agent']}] {step['description']}\n"

    return {
        "final_result": chat_response,
        "messages": [AIMessage(content=chat_response)]
    }
