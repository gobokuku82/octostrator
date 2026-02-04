"""Report Tool - 분석 보고서 생성

ML 분석 결과를 기반으로 비즈니스 보고서를 생성합니다.

Phase 0: Stub 구현 (ImportError 방지)
Phase 2: LLM 통합 완전 구현 예정

(기존 biz_execution/tools/report.py에서 이전)
"""

import logging
from typing import Dict, Any

from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def generate_report(
    analysis_result: Dict[str, Any],
    report_type: str = "summary",
    format: str = "markdown"
) -> Dict[str, Any]:
    """
    ML 분석 결과 기반 비즈니스 보고서 생성

    Phase 0: Stub 모드 - 최소 기능 구현
    Phase 2: Full 모드 - LLM 통합 완전 구현 예정

    Args:
        analysis_result: ML 분석 결과 데이터
        report_type: 보고서 유형 (summary, detailed, executive)
        format: 출력 포맷 (markdown, html, json)

    Returns:
        보고서 생성 결과:
        {
            "report_content": str,    # 보고서 내용
            "format": str,            # 출력 포맷
            "type": str,              # 보고서 유형
            "stub": bool,             # Stub 모드 여부
            "summary": str            # 요약 메시지
        }
    """
    logger.info(f"[Report] Generating {report_type} report (format={format})")

    # Stub 모드 확인
    is_stub = _is_stub_mode()

    if is_stub:
        return _generate_stub_report(report_type, format)
    else:
        return _generate_full_report(analysis_result, report_type, format)


def _is_stub_mode() -> bool:
    """Stub 모드 여부 확인"""
    try:
        from backend.app.dream_agent.llm_manager import agent_config
        return agent_config.get_tool_config("biz_execution", {}).get("stub_mode", True)
    except Exception:
        return True


def _generate_stub_report(report_type: str, format: str) -> Dict[str, Any]:
    """Phase 0: Stub 보고서 생성"""
    stub_content = """# 분석 보고서 (Stub)

Phase 2에서 다음과 같은 완전한 보고서가 생성됩니다:

## 요약
ML 분석 결과를 바탕으로 한 비즈니스 인사이트를 제공합니다.

## 주요 발견 사항
- (Phase 2에서 자동 생성)

## 추천 사항
- (Phase 2에서 자동 생성)

---
*이 보고서는 Stub 모드에서 생성된 샘플입니다.*
"""
    return {
        "report_content": stub_content,
        "format": format,
        "type": report_type,
        "stub": True,
        "summary": "[Phase 0 Stub] 보고서 생성 기능은 Phase 2에서 구현 예정입니다."
    }


def _generate_full_report(
    analysis_result: Dict[str, Any],
    report_type: str,
    format: str
) -> Dict[str, Any]:
    """Phase 2: 완전 구현 (LLM 통합)"""
    raise NotImplementedError(
        "Full implementation is planned for Phase 2. "
        "Set stub_mode=false in tool_settings.yaml when Phase 2 is complete."
    )


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("report")
class ReportTool(BaseTool):
    """분석 보고서 생성 도구

    BaseTool 패턴으로 구현된 Report Generator.
    ML 분석 결과 기반 비즈니스 보고서를 생성합니다.

    Phase 0: Stub 구현
    Phase 2: LLM 통합 완전 구현 예정
    """

    name: str = "report"
    description: str = "ML 분석 결과 기반 비즈니스 보고서 생성"
    category: str = "content"
    version: str = "0.1.0"  # Phase 0: Stub

    # 보고서 유형
    REPORT_TYPES = ["summary", "detailed", "executive"]

    # 출력 포맷
    OUTPUT_FORMATS = ["markdown", "html", "json"]

    def execute(
        self,
        analysis_result: Dict[str, Any],
        report_type: str = "summary",
        format: str = "markdown",
        **kwargs
    ) -> Dict[str, Any]:
        """보고서 생성 실행

        Args:
            analysis_result: ML 분석 결과
            report_type: 보고서 유형
            format: 출력 포맷

        Returns:
            보고서 생성 결과
        """
        return generate_report.invoke({
            "analysis_result": analysis_result,
            "report_type": report_type,
            "format": format
        })

    async def aexecute(
        self,
        analysis_result: Dict[str, Any],
        report_type: str = "summary",
        format: str = "markdown",
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 보고서 생성 실행"""
        return await generate_report.ainvoke({
            "analysis_result": analysis_result,
            "report_type": report_type,
            "format": format
        })


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def generate_report_direct(
    analysis_result: Dict[str, Any],
    report_type: str = "summary",
    format: str = "markdown"
) -> Dict[str, Any]:
    """Agent 없이 직접 보고서 생성

    Args:
        analysis_result: ML 분석 결과 데이터
        report_type: 보고서 유형 (summary, detailed, executive)
        format: 출력 포맷 (markdown, html, json)

    Returns:
        보고서 생성 결과
    """
    logger.info(f"[Report] Direct generation: {report_type} (format={format})")
    return generate_report.invoke({
        "analysis_result": analysis_result,
        "report_type": report_type,
        "format": format
    })


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

REPORT_TOOLS = [
    generate_report,
]
