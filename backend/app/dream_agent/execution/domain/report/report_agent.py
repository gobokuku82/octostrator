"""Report Agent - 보고서 생성"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from backend.app.core.logging import LogContext


async def generate_report(current_todo, log: LogContext) -> Dict[str, Any]:
    """
    보고서 생성

    Args:
        current_todo: TodoItem
        log: LogContext

    Returns:
        Biz result dict
    """
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    output_dir = project_root / "data/output/ml_results"

    # 최신 분석 결과 및 인사이트 찾기
    analysis_files = sorted(output_dir.glob("analysis_*.json"))
    insight_files = sorted(output_dir.glob("insights_*.json"))

    if not analysis_files or not insight_files:
        log.warning("No analysis or insight files found for report generation")
        return {
            "result_type": "report",
            "report_path": None,
            "summary": "분석 결과를 찾을 수 없습니다.",
            "timestamp": datetime.now().isoformat()
        }

    # 분석 결과 로드
    with open(analysis_files[-1], 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    with open(insight_files[-1], 'r', encoding='utf-8') as f:
        insights = json.load(f)

    # Markdown 보고서 생성
    report_content = _generate_markdown_report(analysis, insights)

    # 보고서 저장
    report_dir = project_root / "data/output/reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"laneige_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    log.info(f"Report generated: {report_path}")

    return {
        "result_type": "report",
        "report_path": str(report_path),
        "summary": f"라네즈 분석 보고서 생성 완료 (총 {analysis.get('total_reviews', 0)}개 리뷰 분석)",
        "preview": report_content[:500] + "...",
        "metadata": {
            "total_reviews": analysis.get('total_reviews', 0),
            "average_rating": analysis.get('average_rating', 0),
            "positive_ratio": analysis.get('sentiment', {}).get('positive_ratio', 0)
        },
        "timestamp": datetime.now().isoformat()
    }


def _generate_markdown_report(analysis: dict, insights: dict) -> str:
    """Markdown 보고서 생성"""
    report_content = f"""# 라네즈 제품 분석 보고서

## 📊 분석 개요
- **분석일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **총 리뷰 수**: {analysis.get('total_reviews', 0)}
- **평균 평점**: {analysis.get('average_rating', 0)} / 5.0

## 🎯 감성 분석 결과

### 전체 감성 분포
- 😊 **긍정**: {analysis.get('sentiment', {}).get('positive', 0)}개 ({analysis.get('sentiment', {}).get('positive_ratio', 0)}%)
- 😐 **중립**: {analysis.get('sentiment', {}).get('neutral', 0)}개
- 😞 **부정**: {analysis.get('sentiment', {}).get('negative', 0)}개

## 💡 주요 인사이트

"""
    # 인사이트 추가
    for idx, insight in enumerate(insights.get('insights', []), 1):
        report_content += f"{idx}. {insight}\n"

    report_content += f"""

## 📈 추천 사항

### 즉시 실행 가능한 액션
{chr(10).join('- ' + rec for rec in insights.get('recommendations', ['분석 결과를 마케팅 전략에 반영하세요']))}

## 📌 결론

{insights.get('conclusion', '라네즈 제품에 대한 고객 반응은 대체로 긍정적입니다.')}

---
*본 보고서는 moaDREAM AI Agent에 의해 자동 생성되었습니다.*
"""

    return report_content
