"""Graph Generator

그래프 시각화 데이터 생성
Phase 3.6: Aggregated Data → Graph Visualization JSON
"""
from typing import Dict, List
from backend.app.octostrator.states.supervisor_state import SupervisorState


async def graph_generator_node(state: SupervisorState) -> Dict:
    """Graph Generator - 그래프 시각화 데이터 생성

    Frontend: D3.js, Cytoscape.js, React Flow 등으로 렌더링

    Args:
        state: 현재 SupervisorState (aggregated_data 포함)

    Returns:
        Dict: final_result에 그래프 데이터 포함
    """
    aggregated_data = state["aggregated_data"]

    # 노드 생성
    nodes = []
    edges = []

    # START 노드
    nodes.append({
        "id": "start",
        "label": "START",
        "type": "start",
        "color": "#4CAF50",
        "metadata": {}
    })

    # 각 단계별 노드 생성
    steps = aggregated_data["steps"]
    for i, step in enumerate(steps):
        node_id = f"step_{step['step_id']}"

        # 노드 색상 (상태별)
        color = {
            "completed": "#4CAF50",
            "failed": "#F44336",
            "running": "#2196F3",
            "pending": "#9E9E9E",
            "waiting_human": "#FF9800"
        }.get(step["status"], "#9E9E9E")

        # Agent별 아이콘
        icon = {
            "search": "🔍",
            "validation": "✅",
            "analysis": "📊",
            "comparison": "⚖️",
            "document": "📄",
            "hitl": "🙋"
        }.get(step["agent"], "🔹")

        nodes.append({
            "id": node_id,
            "label": f"{icon} {step['agent']}\n{step['description'][:30]}...",
            "type": step["agent"],
            "status": step["status"],
            "color": color,
            "metadata": {
                "step_id": step["step_id"],
                "agent": step["agent"],
                "description": step["description"],
                "result": step["result"],
                "confidence": step.get("confidence", 0.9)
            }
        })

        # 엣지 생성 (이전 단계 → 현재 단계)
        if i == 0:
            edges.append({
                "id": f"edge_start_to_{node_id}",
                "source": "start",
                "target": node_id,
                "label": "",
                "type": "default"
            })
        else:
            prev_node_id = f"step_{steps[i-1]['step_id']}"
            edges.append({
                "id": f"edge_{prev_node_id}_to_{node_id}",
                "source": prev_node_id,
                "target": node_id,
                "label": "",
                "type": "default"
            })

    # END 노드
    nodes.append({
        "id": "end",
        "label": "END",
        "type": "end",
        "color": "#4CAF50",
        "metadata": {}
    })

    if steps:
        last_node_id = f"step_{steps[-1]['step_id']}"
        edges.append({
            "id": f"edge_{last_node_id}_to_end",
            "source": last_node_id,
            "target": "end",
            "label": "",
            "type": "default"
        })

    # 인사이트를 주석 노드로 추가
    insights = aggregated_data.get("insights", [])
    for insight in insights:
        if insight["importance"] > 0.7:  # 중요한 인사이트만
            # 관련 단계에 주석 노드 연결
            related_steps = insight.get("related_steps", [])
            if related_steps:
                for step_id in related_steps:
                    # step_id가 실제 존재하는지 확인
                    if any(s["step_id"] == step_id for s in steps):
                        annotation_id = f"insight_{step_id}_{insight['category']}"

                        # 인사이트 아이콘
                        insight_icon = {
                            "trend": "📈",
                            "anomaly": "⚠️",
                            "recommendation": "💡"
                        }.get(insight["category"], "ℹ️")

                        nodes.append({
                            "id": annotation_id,
                            "label": f"{insight_icon} {insight['description'][:40]}...",
                            "type": "insight",
                            "color": "#FF9800",
                            "metadata": {
                                "category": insight["category"],
                                "description": insight["description"],
                                "importance": insight["importance"]
                            }
                        })

                        edges.append({
                            "id": f"edge_step_{step_id}_to_{annotation_id}",
                            "source": f"step_{step_id}",
                            "target": annotation_id,
                            "label": "insight",
                            "type": "dashed"
                        })

    # 최종 그래프 데이터
    graph_data = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_steps": len(steps),
            "completed": aggregated_data["execution_summary"]["completed_steps"],
            "failed": aggregated_data["execution_summary"]["failed_steps"],
            "hitl_interactions": aggregated_data["execution_summary"]["hitl_interactions"],
            "execution_time": aggregated_data["execution_summary"]["execution_time"]
        },
        "summary": aggregated_data["final_answer"],
        "insights": insights
    }

    return {
        "final_result": graph_data,
        "messages": []  # 그래프는 메시지 불필요
    }
