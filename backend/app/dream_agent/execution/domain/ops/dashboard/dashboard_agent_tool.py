"""Dashboard Agent Tool - 인터랙티브 대시보드 생성

HTML/JavaScript 기반의 인터랙티브 대시보드를 생성합니다.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from string import Template

from backend.app.dream_agent.biz_execution.base_tool import (
    BaseBizTool,
    BizResult,
    BizResultStatus,
    BizResultMetadata,
    ApprovalType,
    ValidationResult
)
from backend.app.dream_agent.biz_execution.tool_registry import register_tool
from backend.app.dream_agent.models.todo import TodoItem


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
        .insight-icon {
            font-size: 1.5em;
            margin-right: 15px;
        }
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
            <h1>📊 ${title}</h1>
            <p class="subtitle">${subtitle} | 업데이트: ${timestamp}</p>
        </div>

        <div class="metrics">
            ${metric_cards}
        </div>

        <div class="charts">
            <div class="chart-card">
                <h3>📈 감성 분포</h3>
                <div class="chart-container">
                    <canvas id="sentimentChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>📊 트렌드 분석</h3>
                <div class="chart-container">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </div>

        <div class="insights-section">
            <h3>💡 핵심 인사이트</h3>
            ${insights_html}
        </div>

        <div class="footer">
            <p>moaDREAM AI Dashboard | Powered by K-Beauty Intelligence</p>
        </div>
    </div>

    <script>
        // 감성 분포 차트
        const sentimentCtx = document.getElementById('sentimentChart').getContext('2d');
        new Chart(sentimentCtx, {
            type: 'doughnut',
            data: {
                labels: ['긍정', '중립', '부정'],
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

        // 트렌드 차트
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: ${trend_labels},
                datasets: [{
                    label: '리뷰 수',
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


@register_tool
class DashboardAgentTool(BaseBizTool):
    """
    대시보드 생성 도구

    분석 결과를 시각화하는 인터랙티브 HTML 대시보드를 생성합니다.
    """

    name = "dashboard_agent"
    description = "인터랙티브 대시보드 생성 (Chart.js 기반)"
    version = "1.0.0"

    requires_approval = True
    approval_type = ApprovalType.PREVIEW

    is_async = False
    estimated_duration_sec = 45

    required_input_types = ["analysis_result"]
    output_type = "dashboard"

    has_cost = False

    def __init__(self):
        super().__init__()
        self.layouts = ["standard", "executive", "detailed"]

    def validate_input(self, todo: TodoItem, context: Dict[str, Any]) -> ValidationResult:
        """입력 검증"""
        errors = []
        warnings = []

        layout = todo.metadata.execution.tool_params.get("layout", "standard")
        if layout not in self.layouts:
            warnings.append(f"Unknown layout '{layout}', using 'standard'")

        return ValidationResult(is_valid=True, errors=errors, warnings=warnings)

    async def execute(
        self,
        todo: TodoItem,
        context: Dict[str, Any],
        log: Any
    ) -> BizResult:
        """대시보드 생성 실행"""
        start_time = datetime.now()

        try:
            params = todo.metadata.execution.tool_params
            layout = params.get("layout", "standard")

            # 데이터 로드
            analysis = self._load_analysis_data(context)
            insights = self._load_insights_data(context)

            # 대시보드 데이터 준비
            dashboard_data = self._prepare_dashboard_data(analysis, insights, context)

            # HTML 생성
            html_content = self._generate_dashboard_html(dashboard_data, layout)

            # 파일 저장
            output_path = self._get_output_path()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_content, encoding="utf-8")

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return self.create_result(
                todo=todo,
                status=BizResultStatus.SUCCESS,
                result_type="dashboard",
                output_path=str(output_path),
                output_data={
                    "layout": layout,
                    "metrics": dashboard_data["metrics"],
                    "charts": ["sentiment", "trend"]
                },
                summary=f"대시보드 생성 완료 ({layout} 레이아웃)",
                preview=f"Dashboard URL: file://{output_path}",
                metadata=BizResultMetadata(
                    processing_time_ms=processing_time,
                    output_size_bytes=len(html_content.encode('utf-8'))
                )
            )

        except Exception as e:
            return self.create_error_result(
                todo=todo,
                error_message=str(e),
                error_code="DASHBOARD_GENERATION_ERROR"
            )

    def _load_analysis_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """분석 데이터 로드"""
        if "analysis_result" not in context:
            raise ValueError("analysis_result is required in context")
        return context["analysis_result"]

    def _load_insights_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """인사이트 로드"""
        if "insights" not in context:
            raise ValueError("insights is required in context")
        return context["insights"]

    def _prepare_dashboard_data(
        self,
        analysis: Dict[str, Any],
        insights: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """대시보드 데이터 준비"""
        sentiment = analysis.get("sentiment", {})
        trend = analysis.get("trend", {"labels": [], "data": []})

        return {
            "title": f"{context.get('brand', 'K-Beauty')} 분석 대시보드",
            "subtitle": context.get("source", "올리브영"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "metrics": [
                {"label": "총 리뷰", "value": f"{analysis.get('total_reviews', 0):,}", "change": "+12%", "positive": True},
                {"label": "평균 평점", "value": str(analysis.get("average_rating", 0)), "change": "+0.2", "positive": True},
                {"label": "긍정 비율", "value": f"{sentiment.get('positive_ratio', 0)}%", "change": "+5%", "positive": True},
                {"label": "리뷰 증가율", "value": "+23%", "change": "MoM", "positive": True}
            ],
            "sentiment": sentiment,
            "trend": trend,
            "insights": insights.get("insights", [])
        }

    def _generate_dashboard_html(self, data: Dict[str, Any], layout: str) -> str:
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
        icons = ["💡", "📈", "🎯", "⭐", "🔥"]
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

    def _get_output_path(self) -> Path:
        """출력 경로"""
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        output_dir = project_root / "data/output/dashboards"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return output_dir / f"dashboard_{timestamp}.html"
