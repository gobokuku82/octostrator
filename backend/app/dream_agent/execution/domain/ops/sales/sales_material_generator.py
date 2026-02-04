"""Sales Material Generator - 영업 자료 생성"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from backend.app.dream_agent.models.todo import TodoItem


async def generate_sales_material(todo: TodoItem, log: Any) -> Dict[str, Any]:
    """
    영업 자료 생성

    Args:
        todo: TodoItem
        log: LogContext

    Returns:
        Dict with result
    """
    log.info(f"Generating sales material: {todo.task}")

    params = todo.metadata.execution.tool_params if todo.metadata else {}
    material_type = params.get("type", "presentation")
    target_audience = params.get("target", "retailer")

    content = _generate_content(material_type, target_audience, todo.task)

    output_path = _save_material(content)

    return {
        "result_type": "sales_material",
        "output_path": str(output_path),
        "material_type": material_type,
        "target_audience": target_audience,
        "preview": content.get("summary", ""),
        "timestamp": datetime.now().isoformat()
    }


def _generate_content(material_type: str, target_audience: str, task: str) -> Dict[str, Any]:
    """영업 자료 내용 생성"""

    if material_type == "presentation":
        return {
            "type": "presentation",
            "title": f"K-Beauty 제품 소개 - {target_audience}",
            "slides": [
                {"slide": 1, "title": "표지", "content": "K-Beauty 브랜드 파트너십 제안"},
                {"slide": 2, "title": "회사 소개", "content": "글로벌 K-Beauty 리더"},
                {"slide": 3, "title": "제품 라인업", "content": "스킨케어, 메이크업, 헤어케어"},
                {"slide": 4, "title": "시장 분석", "content": "K-Beauty 시장 성장 트렌드"},
                {"slide": 5, "title": "파트너십 혜택", "content": "마진, 마케팅 지원, 교육"},
                {"slide": 6, "title": "다음 단계", "content": "미팅 일정, 연락처"}
            ],
            "summary": f"{target_audience} 대상 프레젠테이션 자료 생성 완료"
        }

    elif material_type == "proposal":
        return {
            "type": "proposal",
            "title": f"비즈니스 제안서 - {target_audience}",
            "sections": [
                {"section": "Executive Summary", "content": "파트너십 핵심 가치 제안"},
                {"section": "Market Opportunity", "content": "시장 기회 분석"},
                {"section": "Product Portfolio", "content": "제품 포트폴리오"},
                {"section": "Partnership Terms", "content": "파트너십 조건"},
                {"section": "Investment & ROI", "content": "투자 및 예상 수익"},
                {"section": "Next Steps", "content": "다음 단계"}
            ],
            "summary": f"{target_audience} 대상 제안서 생성 완료"
        }

    elif material_type == "brochure":
        return {
            "type": "brochure",
            "title": f"제품 브로셔 - {target_audience}",
            "pages": [
                {"page": 1, "content": "브랜드 스토리"},
                {"page": 2, "content": "베스트셀러 제품"},
                {"page": 3, "content": "성분 및 기술"},
                {"page": 4, "content": "연락처 및 주문 정보"}
            ],
            "summary": f"{target_audience} 대상 브로셔 생성 완료"
        }

    else:
        return {
            "type": material_type,
            "title": f"영업 자료 - {target_audience}",
            "content": task,
            "summary": f"{material_type} 자료 생성 완료"
        }


def _save_material(content: Dict[str, Any]) -> Path:
    """자료 저장"""
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    output_dir = project_root / "data/output/sales_materials"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"sales_material_{timestamp}.json"
    output_path.write_text(
        json.dumps(content, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return output_path
