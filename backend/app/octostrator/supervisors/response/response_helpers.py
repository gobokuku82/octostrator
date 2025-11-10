"""
Response Layer Helper Classes

Helper classes and utilities for response generation.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

import logging
from typing import Dict, Any, List
import json

logger = logging.getLogger(__name__)


class ChatGenerator:
    """
    대화형 응답 생성기

    자연어 대화 형식의 응답을 생성합니다.
    """

    def generate(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """
        데이터를 기반으로 대화형 응답을 생성합니다.
        """
        try:
            # Extract key information
            total_steps = data.get("total_steps", 0)
            completed = data.get("completed_steps", 0)
            failed = data.get("failed_steps", 0)

            # Generate response
            response_parts = []

            # Greeting
            if completed == total_steps:
                response_parts.append("모든 작업이 성공적으로 완료되었습니다! 🎉")
            elif failed > 0:
                response_parts.append("작업이 일부 완료되었으나 문제가 발생했습니다. ⚠️")
            else:
                response_parts.append("작업이 진행 중입니다... ⏳")

            # Details
            response_parts.append(f"\n📊 실행 결과:")
            response_parts.append(f"• 총 작업: {total_steps}개")
            response_parts.append(f"• 완료: {completed}개")

            if failed > 0:
                response_parts.append(f"• 실패: {failed}개")

            # Summary
            if summary := data.get("summary"):
                response_parts.append(f"\n💡 요약: {summary}")

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"[ChatGenerator] Error: {e}")
            return "응답 생성 중 오류가 발생했습니다."


class GraphGenerator:
    """
    그래프 데이터 생성기

    시각화를 위한 그래프 데이터를 생성합니다.
    """

    def generate(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        데이터를 기반으로 그래프 구조를 생성합니다.

        Returns:
            dict: D3.js/Cytoscape 호환 형식
        """
        try:
            nodes = []
            edges = []

            # Create start node
            nodes.append({
                "id": "start",
                "label": "Start",
                "type": "entry",
                "x": 0,
                "y": 0
            })

            # Create nodes for each step
            results = data.get("results", [])
            for i, result in enumerate(results):
                node_id = f"step_{i}"
                nodes.append({
                    "id": node_id,
                    "label": result.get("agent", f"Step {i+1}"),
                    "type": "process",
                    "status": result.get("status", "unknown"),
                    "x": 100 * (i + 1),
                    "y": 0
                })

                # Add edge from previous node
                if i == 0:
                    edges.append({
                        "source": "start",
                        "target": node_id,
                        "label": "execute"
                    })
                else:
                    edges.append({
                        "source": f"step_{i-1}",
                        "target": node_id,
                        "label": "next"
                    })

            # Create end node
            if nodes:
                last_node = f"step_{len(results)-1}" if results else "start"
                nodes.append({
                    "id": "end",
                    "label": "End",
                    "type": "exit",
                    "x": 100 * (len(results) + 1),
                    "y": 0
                })
                edges.append({
                    "source": last_node,
                    "target": "end",
                    "label": "complete"
                })

            return {
                "nodes": nodes,
                "edges": edges,
                "metadata": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "layout": "horizontal"
                }
            }

        except Exception as e:
            logger.error(f"[GraphGenerator] Error: {e}")
            return {"nodes": [], "edges": [], "error": str(e)}


class ReportGenerator:
    """
    보고서 생성기

    구조화된 보고서를 생성합니다.
    """

    def generate(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """
        데이터를 기반으로 Markdown 보고서를 생성합니다.
        """
        try:
            # Build report sections
            report_parts = []

            # Title
            report_parts.append("# Execution Report")
            report_parts.append("")

            # Summary section
            report_parts.append("## Executive Summary")
            report_parts.append(f"- **Total Tasks**: {data.get('total_steps', 0)}")
            report_parts.append(f"- **Completed**: {data.get('completed_steps', 0)}")
            report_parts.append(f"- **Failed**: {data.get('failed_steps', 0)}")
            report_parts.append("")

            # Details section
            if results := data.get("results", []):
                report_parts.append("## Task Details")
                report_parts.append("")
                report_parts.append("| Task | Agent | Status | Result |")
                report_parts.append("|------|-------|--------|--------|")

                for i, result in enumerate(results):
                    task = f"Task {i+1}"
                    agent = result.get("agent", "N/A")
                    status = result.get("status", "unknown")
                    res = result.get("result", "")[:50]  # Truncate
                    report_parts.append(f"| {task} | {agent} | {status} | {res} |")

                report_parts.append("")

            # Recommendations
            report_parts.append("## Recommendations")
            if data.get("failed_steps", 0) > 0:
                report_parts.append("- Review and retry failed tasks")
            report_parts.append("- Monitor system performance")
            report_parts.append("- Consider optimization opportunities")
            report_parts.append("")

            # Footer
            report_parts.append("---")
            report_parts.append(f"*Generated at: {context.get('timestamp', 'N/A')}*")

            return "\n".join(report_parts)

        except Exception as e:
            logger.error(f"[ReportGenerator] Error: {e}")
            return "# Error\n\nFailed to generate report."


class ResponseFormatter:
    """
    응답 포맷터

    최종 응답을 적절한 형식으로 포맷팅합니다.
    """

    def __init__(self):
        self.chat_gen = ChatGenerator()
        self.graph_gen = GraphGenerator()
        self.report_gen = ReportGenerator()

    def format(self, data: Dict[str, Any], format_type: str = "chat", context: Dict[str, Any] = None) -> Any:
        """
        데이터를 지정된 형식으로 포맷팅합니다.
        """
        if format_type == "chat":
            return self.chat_gen.generate(data, context)
        elif format_type == "graph":
            return self.graph_gen.generate(data, context)
        elif format_type == "report":
            return self.report_gen.generate(data, context)
        else:
            # Default to JSON
            return json.dumps(data, ensure_ascii=False, indent=2)