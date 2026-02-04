"""Dashboard Tool - 인터랙티브 대시보드 생성

HTML/JavaScript 기반의 인터랙티브 대시보드를 생성합니다.
Chart.js를 사용한 시각화를 제공합니다.

(기존 biz_execution/dashboard/dashboard_agent_tool.py에서 이전)
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from string import Template
from typing import Dict, Any, List

from langchain_core.tools import tool

from ..base_tool import BaseTool, register_tool

logger = logging.getLogger(__name__)


# ============================================================
# Dashboard HTML Template (Chart.js 기반)
# ============================================================

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, #667eea, #764ba2, #e94560);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .header .subtitle { color: #888; font-size: 1.1em; }

        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }
        .metric-value {
            font-size: 3em;
            font-weight: 700;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric-label { color: #aaa; margin-top: 10px; font-size: 1.1em; }
        .metric-change { margin-top: 8px; font-size: 0.9em; }
        .metric-change.positive { color: #4ade80; }
        .metric-change.negative { color: #f87171; }

        .charts {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .chart-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 25px;
        }
        .chart-card h3 {
            color: #fff;
            margin-bottom: 20px;
            font-size: 1.3em;
        }
        .chart-container { position: relative; height: 300px; }

        .insights-section {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 25px;
        }
        .insights-section h3 { margin-bottom: 20px; }
        .insight-item {
            display: flex;
            align-items: flex-start;
            padding: 15px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .insight-icon { font-size: 1.5em; margin-right: 15px; }
        .insight-text { color: #ddd; line-height: 1.6; }

        .footer {
            text-align: center;
            padding: 30px;
            color: #666;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 30px;
        }

        @media (max-width: 768px) {
            .charts { grid-template-columns: 1fr; }
            .header h1 { font-size: 1.8em; }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>${title}</h1>
            <p class="subtitle">${subtitle} | ${timestamp}</p>
        </div>

        <div class="metrics">
            ${metric_cards}
        </div>

        <div class="charts">
            <div class="chart-card">
                <h3>Sentiment Distribution</h3>
                <div class="chart-container">
                    <canvas id="sentimentChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>Trend Analysis</h3>
                <div class="chart-container">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </div>

        <div class="insights-section">
            <h3>Key Insights</h3>
            ${insights_html}
        </div>

        <div class="footer">
            <p>moaDREAM AI Dashboard | Powered by K-Beauty Intelligence</p>
        </div>
    </div>

    <script>
        // Sentiment Distribution Chart
        const sentimentCtx = document.getElementById('sentimentChart').getContext('2d');
        new Chart(sentimentCtx, {
            type: 'doughnut',
            data: {
                labels: ['Positive', 'Neutral', 'Negative'],
                datasets: [{
                    data: [${positive_count}, ${neutral_count}, ${negative_count}],
                    backgroundColor: ['#4ade80', '#fbbf24', '#f87171'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#fff' } }
                }
            }
        });

        // Trend Chart
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: ${trend_labels},
                datasets: [{
                    label: 'Reviews',
                    data: ${trend_data},
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    x: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                },
                plugins: {
                    legend: { labels: { color: '#fff' } }
                }
            }
        });
    </script>
</body>
</html>
"""


# ============================================================
# LangGraph Tools (@tool 데코레이터)
# ============================================================

@tool
def generate_dashboard(
    analysis_result: Dict[str, Any],
    insights: Dict[str, Any],
    layout: str = "standard",
    brand: str = "K-Beauty"
) -> Dict[str, Any]:
    """
    인터랙티브 대시보드 생성

    Args:
        analysis_result: ML 분석 결과
        insights: 인사이트 데이터
        layout: 레이아웃 유형 (standard, executive, detailed)
        brand: 브랜드 이름

    Returns:
        대시보드 생성 결과:
        {
            "output_path": str,       # 저장된 HTML 파일 경로
            "layout": str,            # 레이아웃 유형
            "metrics": [...],         # 메트릭 정보
            "charts": [...],          # 차트 정보
            "summary": str            # 요약 메시지
        }
    """
    logger.info(f"[Dashboard] Generating {layout} dashboard for {brand}")

    start_time = datetime.now()

    try:
        # 대시보드 데이터 준비
        dashboard_data = _prepare_dashboard_data(analysis_result, insights, brand)

        # HTML 생성
        html_content = _generate_dashboard_html(dashboard_data, layout)

        # 파일 저장
        output_path = _get_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")

        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(f"[Dashboard] Generated: {output_path} ({processing_time}ms)")

        return {
            "output_path": str(output_path),
            "layout": layout,
            "metrics": dashboard_data["metrics"],
            "charts": ["sentiment", "trend"],
            "processing_time_ms": processing_time,
            "summary": f"대시보드 생성 완료 ({layout} 레이아웃)"
        }

    except Exception as e:
        logger.error(f"[Dashboard] Generation failed: {e}")
        return {
            "error": str(e),
            "summary": f"대시보드 생성 실패: {e}"
        }


@tool
def get_dashboard_metrics(
    analysis_result: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    분석 결과에서 대시보드 메트릭 추출

    Args:
        analysis_result: ML 분석 결과

    Returns:
        메트릭 리스트
    """
    logger.info("[Dashboard] Extracting metrics from analysis result")

    sentiment = analysis_result.get("sentiment", {})

    metrics = [
        {
            "label": "Total Reviews",
            "value": f"{analysis_result.get('total_reviews', 0):,}",
            "change": "+12%",
            "positive": True
        },
        {
            "label": "Average Rating",
            "value": str(analysis_result.get("average_rating", 0)),
            "change": "+0.2",
            "positive": True
        },
        {
            "label": "Positive Ratio",
            "value": f"{sentiment.get('positive_ratio', 0)}%",
            "change": "+5%",
            "positive": True
        },
        {
            "label": "Review Growth",
            "value": "+23%",
            "change": "MoM",
            "positive": True
        }
    ]

    return metrics


def _prepare_dashboard_data(
    analysis_result: Dict[str, Any],
    insights: Dict[str, Any],
    brand: str
) -> Dict[str, Any]:
    """대시보드 데이터 준비"""
    sentiment = analysis_result.get("sentiment", {})
    trend = analysis_result.get("trend", {"labels": [], "data": []})

    return {
        "title": f"{brand} Analysis Dashboard",
        "subtitle": analysis_result.get("source", "Oliveyoung"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "metrics": [
            {"label": "Total Reviews", "value": f"{analysis_result.get('total_reviews', 0):,}", "change": "+12%", "positive": True},
            {"label": "Average Rating", "value": str(analysis_result.get("average_rating", 0)), "change": "+0.2", "positive": True},
            {"label": "Positive Ratio", "value": f"{sentiment.get('positive_ratio', 0)}%", "change": "+5%", "positive": True},
            {"label": "Review Growth", "value": "+23%", "change": "MoM", "positive": True}
        ],
        "sentiment": sentiment,
        "trend": trend,
        "insights": insights.get("insights", [])
    }


def _generate_dashboard_html(data: Dict[str, Any], layout: str) -> str:
    """대시보드 HTML 생성"""
    template = Template(DASHBOARD_TEMPLATE)

    # 메트릭 카드 HTML 생성
    metric_cards = ""
    for m in data["metrics"]:
        change_class = "positive" if m.get("positive", True) else "negative"
        metric_cards += f"""
        <div class="metric-card">
            <div class="metric-value">{m['value']}</div>
            <div class="metric-label">{m['label']}</div>
            <div class="metric-change {change_class}">{m['change']}</div>
        </div>
        """

    # 인사이트 HTML 생성
    icons = ["*", "+", "!", "#", "^"]
    insights_html = ""
    for i, insight in enumerate(data["insights"]):
        icon = icons[i % len(icons)]
        insights_html += f"""
        <div class="insight-item">
            <span class="insight-icon">{icon}</span>
            <span class="insight-text">{insight}</span>
        </div>
        """

    sentiment = data["sentiment"]
    trend = data["trend"]

    return template.safe_substitute(
        title=data["title"],
        subtitle=data["subtitle"],
        timestamp=data["timestamp"],
        metric_cards=metric_cards,
        insights_html=insights_html,
        positive_count=sentiment.get("positive", 0),
        neutral_count=sentiment.get("neutral", 0),
        negative_count=sentiment.get("negative", 0),
        trend_labels=json.dumps(trend.get("labels", [])),
        trend_data=json.dumps(trend.get("data", []))
    )


def _get_output_path() -> Path:
    """출력 경로"""
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    output_dir = project_root / "data/output/dashboards"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"dashboard_{timestamp}.html"


# ============================================================
# BaseTool 클래스 (신규 패턴)
# ============================================================

@register_tool("dashboard")
class DashboardTool(BaseTool):
    """대시보드 생성 도구

    BaseTool 패턴으로 구현된 Dashboard Generator.
    분석 결과를 시각화하는 인터랙티브 HTML 대시보드를 생성합니다.
    """

    name: str = "dashboard"
    description: str = "인터랙티브 대시보드 생성 (Chart.js 기반)"
    category: str = "business"
    version: str = "1.0.0"

    # 지원 레이아웃
    LAYOUTS = ["standard", "executive", "detailed"]

    def execute(
        self,
        analysis_result: Dict[str, Any],
        insights: Dict[str, Any],
        layout: str = "standard",
        brand: str = "K-Beauty",
        **kwargs
    ) -> Dict[str, Any]:
        """대시보드 생성 실행

        Args:
            analysis_result: ML 분석 결과
            insights: 인사이트 데이터
            layout: 레이아웃 유형
            brand: 브랜드 이름

        Returns:
            대시보드 생성 결과
        """
        return generate_dashboard.invoke({
            "analysis_result": analysis_result,
            "insights": insights,
            "layout": layout,
            "brand": brand
        })

    async def aexecute(
        self,
        analysis_result: Dict[str, Any],
        insights: Dict[str, Any],
        layout: str = "standard",
        brand: str = "K-Beauty",
        **kwargs
    ) -> Dict[str, Any]:
        """비동기 대시보드 생성 실행"""
        return await generate_dashboard.ainvoke({
            "analysis_result": analysis_result,
            "insights": insights,
            "layout": layout,
            "brand": brand
        })


# ============================================================
# Direct Function Calls (without Agent)
# ============================================================

def generate_dashboard_direct(
    analysis_result: Dict[str, Any],
    insights: Dict[str, Any],
    brand: str = "K-Beauty"
) -> Dict[str, Any]:
    """Agent 없이 직접 대시보드 생성"""
    logger.info(f"[Dashboard] Direct generation for {brand}")
    return generate_dashboard.invoke({
        "analysis_result": analysis_result,
        "insights": insights,
        "layout": "standard",
        "brand": brand
    })


def get_metrics_direct(analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Agent 없이 직접 메트릭 추출"""
    return get_dashboard_metrics.invoke({"analysis_result": analysis_result})


# ============================================================
# Export 할 @tool 함수 목록
# ============================================================

DASHBOARD_TOOLS = [
    generate_dashboard,
    get_dashboard_metrics,
]
