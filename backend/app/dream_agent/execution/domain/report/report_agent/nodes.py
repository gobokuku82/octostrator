"""Report Agent Nodes - 리포트 생성 Subgraph의 노드 함수들

ML 분석 결과를 기반으로 비즈니스 리포트를 생성합니다.
"""

from typing import Dict, Any
from backend.app.dream_agent.biz_execution.agents.report.report_tools import (
    validate_ml_result,
    extract_key_insights,
    generate_report_structure,
    render_report
)


def ml_result_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ML 결과 검증 노드

    Args:
        state: {
            "ml_result": Dict[str, Any],
            "validation_result": Dict[str, Any] | None
        }

    Returns:
        state with updated "validation_result"
    """
    ml_result = state.get("ml_result")

    if not ml_result:
        return {
            **state,
            "validation_result": {
                "valid": False,
                "errors": ["ML result not found in state"],
                "warnings": [],
                "data_quality": "poor"
            },
            "error": "Missing ML result"
        }

    # Tool 호출
    validation_result = validate_ml_result.invoke({"ml_result": ml_result})

    return {
        **state,
        "validation_result": validation_result
    }


def insight_extractor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    인사이트 추출 노드

    Args:
        state: {
            "ml_result": Dict[str, Any],
            "insights": List[Dict[str, Any]] | None
        }

    Returns:
        state with updated "insights"
    """
    validation_result = state.get("validation_result", {})

    # 검증 실패 시 중단
    if not validation_result.get("valid", False):
        return {
            **state,
            "error": f"ML result validation failed: {validation_result.get('errors', [])}"
        }

    ml_result = state.get("ml_result")

    # Tool 호출
    insights = extract_key_insights.invoke({"ml_result": ml_result})

    return {
        **state,
        "insights": insights
    }


def report_structure_builder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    리포트 구조 생성 노드

    Args:
        state: {
            "ml_result": Dict[str, Any],
            "insights": List[Dict[str, Any]],
            "report_type": str,
            "report_structure": Dict[str, Any] | None
        }

    Returns:
        state with updated "report_structure"
    """
    ml_result = state.get("ml_result")
    insights = state.get("insights", [])
    report_type = state.get("report_type", "comprehensive")

    if not ml_result or not insights:
        return {
            **state,
            "error": "Missing ML result or insights for report structure generation"
        }

    # Tool 호출
    report_structure = generate_report_structure.invoke({
        "ml_result": ml_result,
        "insights": insights,
        "report_type": report_type
    })

    return {
        **state,
        "report_structure": report_structure
    }


def report_renderer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    리포트 렌더링 노드

    Args:
        state: {
            "report_structure": Dict[str, Any],
            "output_format": str,
            "output_path": str | None
        }

    Returns:
        state with updated "output_path" and "final_result"
    """
    report_structure = state.get("report_structure")
    output_format = state.get("output_format", "html")

    if not report_structure:
        return {
            **state,
            "error": "Missing report structure for rendering"
        }

    # Tool 호출
    try:
        output_path = render_report.invoke({
            "report_structure": report_structure,
            "output_format": output_format
        })

        # 최종 결과 구성
        final_result = {
            "status": "success",
            "output_path": output_path,
            "report_type": report_structure.get("report_type"),
            "output_format": output_format,
            "section_count": len(report_structure.get("sections", [])),
            "insight_count": len(state.get("insights", [])),
            "generated_at": report_structure.get("metadata", {}).get("generated_at")
        }

        return {
            **state,
            "output_path": output_path,
            "final_result": final_result
        }
    except Exception as e:
        return {
            **state,
            "error": f"Report rendering failed: {str(e)}"
        }


def error_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    에러 처리 노드

    에러 발생 시 호출되어 최종 에러 상태 반환
    """
    error_message = state.get("error", "Unknown error")

    return {
        **state,
        "final_result": {
            "status": "failed",
            "error": error_message,
            "output_path": None
        }
    }
