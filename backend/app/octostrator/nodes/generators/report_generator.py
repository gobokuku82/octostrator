"""Report Generator

Markdown 보고서 생성
Phase 3.6: Aggregated Data → Markdown Report
"""
from typing import Dict
from datetime import datetime
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def report_generator_node(state: SupervisorState) -> Dict:
    """Report Generator - Markdown 보고서 생성

    Frontend: Markdown 렌더링 또는 PDF 변환

    Args:
        state: 현재 SupervisorState (aggregated_data 포함)

    Returns:
        Dict: final_result에 Markdown 보고서 포함
    """
    aggregated_data = state["aggregated_data"]

    # Markdown 보고서 생성
    report = f"""# 분석 보고서

**생성 일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**요청 내용**: {aggregated_data['metadata'].get('user_intent', 'N/A')}

---

## 📋 요약

{aggregated_data['final_answer']}

---

## 📊 실행 통계

| 항목 | 수치 |
|------|------|
| 총 실행 단계 | {aggregated_data['execution_summary']['total_steps']}개 |
| 완료된 단계 | {aggregated_data['execution_summary']['completed_steps']}개 |
| 실패한 단계 | {aggregated_data['execution_summary']['failed_steps']}개 |
| 사용자 승인 | {aggregated_data['execution_summary']['hitl_interactions']}회 |
| 총 실행 시간 | {aggregated_data['execution_summary']['execution_time']:.2f}초 |

---

## 🔍 상세 실행 내역

"""

    # 각 단계별 상세 내역
    for step in aggregated_data["steps"]:
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "running": "🔄",
            "pending": "⏳",
            "waiting_human": "🙋"
        }.get(step["status"], "❓")

        # Agent별 아이콘
        agent_icon = {
            "search": "🔍",
            "validation": "✅",
            "analysis": "📊",
            "comparison": "⚖️",
            "document": "📄",
            "hitl": "🙋"
        }.get(step["agent"], "🔹")

        report += f"""
### {status_emoji} Step {step['step_id']}: {step['description']}

- **Agent**: {agent_icon} `{step['agent']}`
- **상태**: {step['status']}
- **신뢰도**: {step.get('confidence', 0.9) * 100:.1f}%

**실행 결과**:
```
{step['result'] if step['result'] else 'N/A'}
```

"""

        # 근거 자료가 있으면 추가
        evidence = step.get('evidence', [])
        if evidence:
            report += "**근거 자료**:\n"
            for ev in evidence:
                report += f"- {ev}\n"
            report += "\n"

    # 인사이트 섹션
    report += "\n---\n\n## 💡 주요 인사이트\n\n"

    # 카테고리별 분류
    insights_by_category = {}
    for insight in aggregated_data["insights"]:
        category = insight["category"]
        if category not in insights_by_category:
            insights_by_category[category] = []
        insights_by_category[category].append(insight)

    category_names = {
        "trend": "📈 트렌드",
        "anomaly": "⚠️ 이상 징후",
        "recommendation": "✅ 권장 사항"
    }

    for category, category_name in category_names.items():
        if category in insights_by_category:
            report += f"\n### {category_name}\n\n"
            for insight in sorted(
                insights_by_category[category],
                key=lambda x: x['importance'],
                reverse=True
            ):
                report += f"- **[중요도: {insight['importance']:.1%}]** {insight['description']}\n"
                related_steps = insight.get('related_steps', [])
                if related_steps:
                    step_refs = ', '.join(f'Step {s}' for s in related_steps)
                    report += f"  - 관련 단계: {step_refs}\n"
            report += "\n"

    # 결론
    report += """
---

## 📌 결론

"""
    report += aggregated_data['final_answer']

    report += """

---

*이 보고서는 Octostrator Planning-Based Multi-Agent System에 의해 자동 생성되었습니다.*
"""

    return {
        "final_result": report,
        "messages": []
    }
