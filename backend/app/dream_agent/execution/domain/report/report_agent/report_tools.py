"""Report Tools - 리포트 생성 및 처리 Tools

ML 분석 결과를 기반으로 비즈니스 리포트를 생성합니다.
"""

from typing import Dict, Any, List
from langchain_core.tools import tool
from pathlib import Path
from datetime import datetime
import json


@tool
def validate_ml_result(ml_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    ML 분석 결과 유효성 검증

    Args:
        ml_result: ML 분석 결과

    Returns:
        검증 결과
    """
    errors = []
    warnings = []

    # 필수 필드 확인
    required_fields = ["analysis_type", "total_reviews"]
    for field in required_fields:
        if field not in ml_result:
            errors.append(f"Missing required field: {field}")

    # 데이터 형식 확인
    if "sentiment" in ml_result:
        sentiment = ml_result["sentiment"]
        total = sum(sentiment.get(key, 0) for key in ["positive", "neutral", "negative"])
        if abs(total - 1.0) > 0.01:
            warnings.append(f"Sentiment values don't sum to 1.0: {total:.2f}")

    # 키워드 확인
    if "keywords" in ml_result:
        if not isinstance(ml_result["keywords"], list):
            errors.append("Keywords must be a list")
        elif len(ml_result["keywords"]) == 0:
            warnings.append("No keywords found")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "data_quality": "good" if len(errors) == 0 and len(warnings) == 0 else "acceptable"
    }


@tool
def extract_key_insights(ml_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    ML 결과에서 주요 인사이트 추출

    Args:
        ml_result: ML 분석 결과

    Returns:
        인사이트 목록
    """
    insights = []

    # Sentiment 인사이트
    if "sentiment" in ml_result:
        sentiment = ml_result["sentiment"]
        positive_ratio = sentiment.get("positive", 0)
        negative_ratio = sentiment.get("negative", 0)

        if positive_ratio > 0.6:
            insights.append({
                "type": "positive",
                "category": "sentiment",
                "title": "높은 긍정 반응",
                "description": f"고객의 {positive_ratio:.1%}가 긍정적 평가를 남겼습니다.",
                "priority": "high"
            })
        elif negative_ratio > 0.3:
            insights.append({
                "type": "negative",
                "category": "sentiment",
                "title": "부정 반응 주의 필요",
                "description": f"고객의 {negative_ratio:.1%}가 부정적 평가를 남겼습니다.",
                "priority": "high"
            })

    # 키워드 인사이트
    if "keywords" in ml_result:
        top_keywords = ml_result["keywords"][:3]
        insights.append({
            "type": "info",
            "category": "keywords",
            "title": "주요 언급 키워드",
            "description": f"가장 많이 언급된 키워드: {', '.join(top_keywords)}",
            "priority": "medium"
        })

    # 평점 인사이트
    if "avg_rating" in ml_result:
        avg_rating = ml_result["avg_rating"]
        if avg_rating >= 4.0:
            insights.append({
                "type": "positive",
                "category": "rating",
                "title": "우수한 평점",
                "description": f"평균 평점 {avg_rating:.1f}/5.0으로 높은 만족도를 보입니다.",
                "priority": "high"
            })
        elif avg_rating < 3.0:
            insights.append({
                "type": "negative",
                "category": "rating",
                "title": "낮은 평점",
                "description": f"평균 평점 {avg_rating:.1f}/5.0으로 개선이 필요합니다.",
                "priority": "high"
            })

    return insights


@tool
def generate_report_structure(
    ml_result: Dict[str, Any],
    insights: List[Dict[str, Any]],
    report_type: str = "comprehensive"
) -> Dict[str, Any]:
    """
    리포트 구조 생성

    Args:
        ml_result: ML 분석 결과
        insights: 인사이트 목록
        report_type: 리포트 유형 (comprehensive/summary/executive)

    Returns:
        리포트 구조
    """
    # 섹션 구성
    sections = []

    # 1. Executive Summary
    sections.append({
        "id": "executive_summary",
        "title": "Executive Summary",
        "order": 1,
        "type": "text",
        "content": {
            "summary": _generate_executive_summary(ml_result, insights)
        }
    })

    # 2. Key Metrics
    sections.append({
        "id": "key_metrics",
        "title": "Key Metrics",
        "order": 2,
        "type": "metrics",
        "content": {
            "total_reviews": ml_result.get("total_reviews", 0),
            "avg_rating": ml_result.get("avg_rating", 0),
            "sentiment_score": ml_result.get("sentiment_score", 0),
            "analysis_period": ml_result.get("analysis_period", "N/A")
        }
    })

    # 3. Sentiment Analysis
    if "sentiment" in ml_result:
        sections.append({
            "id": "sentiment_analysis",
            "title": "Sentiment Analysis",
            "order": 3,
            "type": "chart",
            "content": {
                "chart_type": "pie",
                "data": ml_result["sentiment"]
            }
        })

    # 4. Key Insights
    sections.append({
        "id": "key_insights",
        "title": "Key Insights",
        "order": 4,
        "type": "insights",
        "content": {
            "insights": insights
        }
    })

    # 5. Keywords (comprehensive only)
    if report_type == "comprehensive" and "keywords" in ml_result:
        sections.append({
            "id": "keywords",
            "title": "Top Keywords",
            "order": 5,
            "type": "wordcloud",
            "content": {
                "keywords": ml_result["keywords"][:20]
            }
        })

    # 6. Recommendations
    sections.append({
        "id": "recommendations",
        "title": "Recommendations",
        "order": 6,
        "type": "text",
        "content": {
            "recommendations": _generate_recommendations(ml_result, insights)
        }
    })

    return {
        "report_type": report_type,
        "sections": sections,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source": "ml_analysis",
            "total_sections": len(sections)
        }
    }


@tool
def render_report(
    report_structure: Dict[str, Any],
    output_format: str = "html"
) -> str:
    """
    리포트 렌더링

    Args:
        report_structure: 리포트 구조
        output_format: 출력 형식 (html/json/markdown)

    Returns:
        렌더링된 리포트 파일 경로
    """
    output_dir = Path("data/output/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_id = f"report_{timestamp}"

    if output_format == "json":
        # JSON 출력
        output_path = output_dir / f"{report_id}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_structure, f, ensure_ascii=False, indent=2)

    elif output_format == "markdown":
        # Markdown 출력
        output_path = output_dir / f"{report_id}.md"
        markdown_content = _render_markdown(report_structure)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

    elif output_format == "html":
        # HTML 출력
        output_path = output_dir / f"{report_id}.html"
        html_content = _render_html(report_structure)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    else:
        raise ValueError(f"Unsupported output format: {output_format}")

    return str(output_path)


# ============================================================
# Helper Functions
# ============================================================

def _generate_executive_summary(ml_result: Dict[str, Any], insights: List[Dict[str, Any]]) -> str:
    """Executive Summary 텍스트 생성"""
    total_reviews = ml_result.get("total_reviews", 0)
    avg_rating = ml_result.get("avg_rating", 0)

    high_priority_insights = [i for i in insights if i.get("priority") == "high"]
    insight_count = len(high_priority_insights)

    summary = f"""
본 리포트는 총 {total_reviews:,}건의 리뷰를 분석한 결과를 담고 있습니다.
평균 평점은 {avg_rating:.1f}/5.0이며, {insight_count}개의 주요 인사이트가 도출되었습니다.

분석 결과 다음과 같은 주요 발견사항이 있습니다:
"""

    for idx, insight in enumerate(high_priority_insights[:3], 1):
        summary += f"\n{idx}. {insight.get('title')}: {insight.get('description')}"

    return summary.strip()


def _generate_recommendations(ml_result: Dict[str, Any], insights: List[Dict[str, Any]]) -> List[str]:
    """추천 사항 생성"""
    recommendations = []

    # Sentiment 기반 추천
    if "sentiment" in ml_result:
        negative_ratio = ml_result["sentiment"].get("negative", 0)
        if negative_ratio > 0.2:
            recommendations.append("부정 리뷰 원인 분석 및 개선 조치가 필요합니다.")

    # 평점 기반 추천
    if "avg_rating" in ml_result:
        avg_rating = ml_result["avg_rating"]
        if avg_rating < 3.5:
            recommendations.append("제품/서비스 품질 개선이 우선 필요합니다.")
        elif avg_rating >= 4.0:
            recommendations.append("현재 높은 만족도를 유지하기 위한 전략을 수립하세요.")

    # 키워드 기반 추천
    if "keywords" in ml_result:
        recommendations.append("주요 키워드를 마케팅 메시지에 활용하세요.")

    if not recommendations:
        recommendations.append("현재 상태를 지속적으로 모니터링하세요.")

    return recommendations


def _render_markdown(report_structure: Dict[str, Any]) -> str:
    """Markdown 형식으로 렌더링"""
    sections = report_structure.get("sections", [])
    lines = []

    lines.append(f"# Analysis Report")
    lines.append(f"\nGenerated: {report_structure['metadata']['generated_at']}")
    lines.append(f"\n---\n")

    for section in sorted(sections, key=lambda s: s["order"]):
        lines.append(f"\n## {section['title']}\n")

        content = section.get("content", {})
        section_type = section.get("type")

        if section_type == "text":
            if "summary" in content:
                lines.append(content["summary"])
            if "recommendations" in content:
                lines.append("\n**Recommendations:**\n")
                for rec in content["recommendations"]:
                    lines.append(f"- {rec}")

        elif section_type == "metrics":
            for key, value in content.items():
                lines.append(f"- **{key}**: {value}")

        elif section_type == "insights":
            for insight in content.get("insights", []):
                lines.append(f"### {insight['title']}")
                lines.append(f"{insight['description']}\n")

        elif section_type == "chart":
            lines.append(f"*[Chart: {content.get('chart_type', 'N/A')}]*\n")
            lines.append(f"Data: {content.get('data', {})}")

    return "\n".join(lines)


def _render_html(report_structure: Dict[str, Any]) -> str:
    """HTML 형식으로 렌더링"""
    sections = report_structure.get("sections", [])

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .insight {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .insight.positive {{ border-left: 4px solid #4caf50; }}
        .insight.negative {{ border-left: 4px solid #f44336; }}
        .insight.info {{ border-left: 4px solid #2196f3; }}
    </style>
</head>
<body>
    <h1>Analysis Report</h1>
    <p><em>Generated: {report_structure['metadata']['generated_at']}</em></p>
    <hr>
"""

    for section in sorted(sections, key=lambda s: s["order"]):
        html += f"<h2>{section['title']}</h2>\n"

        content = section.get("content", {})
        section_type = section.get("type")

        if section_type == "text":
            if "summary" in content:
                html += f"<p>{content['summary'].replace(chr(10), '<br>')}</p>\n"
            if "recommendations" in content:
                html += "<ul>\n"
                for rec in content["recommendations"]:
                    html += f"<li>{rec}</li>\n"
                html += "</ul>\n"

        elif section_type == "metrics":
            for key, value in content.items():
                html += f'<div class="metric"><strong>{key}:</strong> {value}</div>\n'

        elif section_type == "insights":
            for insight in content.get("insights", []):
                insight_type = insight.get("type", "info")
                html += f'<div class="insight {insight_type}">\n'
                html += f'<h3>{insight["title"]}</h3>\n'
                html += f'<p>{insight["description"]}</p>\n'
                html += '</div>\n'

    html += """
</body>
</html>
"""

    return html
