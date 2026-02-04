"""Tool Catalog - ML/Biz 도구 카탈로그

사용 가능한 모든 도구의 메타데이터를 정의하고 관리합니다.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ============================================================
# Tool Category
# ============================================================

class ToolCategory(str, Enum):
    """도구 카테고리"""
    ML = "ml"           # ML 실행 도구
    BIZ = "biz"         # 비즈니스 실행 도구
    UTILITY = "utility" # 유틸리티 도구


class ToolPhase(str, Enum):
    """도구 실행 단계"""
    COLLECTION = "collection"       # 데이터 수집
    PREPROCESSING = "preprocessing" # 전처리
    ANALYSIS = "analysis"           # 분석
    INSIGHT = "insight"             # 인사이트 생성
    OUTPUT = "output"               # 산출물 생성


# ============================================================
# Tool Metadata
# ============================================================

class ToolParameter(BaseModel):
    """도구 파라미터 정의"""
    name: str
    type: str  # string, int, float, bool, list, dict
    required: bool = False
    default: Optional[Any] = None
    description: str = ""
    enum_values: Optional[List[str]] = None


class ToolDependency(BaseModel):
    """도구 의존성 정의"""
    tool_name: str
    required: bool = True  # True: 필수, False: 선택
    output_key: Optional[str] = None  # 의존하는 출력 키


class ToolMetadata(BaseModel):
    """도구 메타데이터"""
    name: str
    display_name: str
    description: str
    category: ToolCategory
    phase: ToolPhase
    version: str = "1.0.0"

    # 실행 관련
    is_async: bool = False
    estimated_duration_sec: int = 60
    max_retries: int = 3

    # 승인 관련
    requires_approval: bool = False
    approval_type: Optional[str] = None  # preview, execute, result, cost

    # 비용 관련
    has_cost: bool = False
    cost_per_call: float = 0.0

    # 파라미터
    parameters: List[ToolParameter] = Field(default_factory=list)

    # 의존성
    dependencies: List[ToolDependency] = Field(default_factory=list)

    # 입출력
    input_types: List[str] = Field(default_factory=list)
    output_type: str = "generic"

    # 태그 (검색/필터링용)
    tags: List[str] = Field(default_factory=list)


# ============================================================
# Tool Catalog - 도구 카탈로그 정의
# ============================================================

# ML 도구 카탈로그
ML_TOOLS: Dict[str, ToolMetadata] = {
    "collector": ToolMetadata(
        name="collector",
        display_name="데이터 수집기",
        description="다양한 소스에서 데이터를 수집합니다 (올리브영, 쿠팡, Sephora 등)",
        category=ToolCategory.ML,
        phase=ToolPhase.COLLECTION,
        is_async=False,
        estimated_duration_sec=30,
        parameters=[
            ToolParameter(name="source", type="string", required=True,
                         description="데이터 소스 (oliveyoung, coupang, sephora 등)"),
            ToolParameter(name="brand", type="string", required=False,
                         description="브랜드 필터"),
            ToolParameter(name="date_range", type="dict", required=False,
                         description="날짜 범위 {'start': '2024-01-01', 'end': '2024-12-31'}"),
        ],
        input_types=[],
        output_type="raw_data",
        tags=["data", "collection", "source"]
    ),

    "preprocessor": ToolMetadata(
        name="preprocessor",
        display_name="데이터 전처리기",
        description="수집된 데이터를 정제하고 표준화합니다",
        category=ToolCategory.ML,
        phase=ToolPhase.PREPROCESSING,
        is_async=False,
        estimated_duration_sec=20,
        dependencies=[
            ToolDependency(tool_name="collector", required=True, output_key="raw_data")
        ],
        input_types=["raw_data"],
        output_type="preprocessed_data",
        tags=["data", "preprocessing", "cleaning"]
    ),

    "analyzer": ToolMetadata(
        name="analyzer",
        display_name="데이터 분석기",
        description="전처리된 데이터를 분석하여 통계와 패턴을 추출합니다",
        category=ToolCategory.ML,
        phase=ToolPhase.ANALYSIS,
        is_async=False,
        estimated_duration_sec=45,
        dependencies=[
            ToolDependency(tool_name="preprocessor", required=True, output_key="preprocessed_data")
        ],
        parameters=[
            ToolParameter(name="analysis_type", type="string", required=False,
                         default="comprehensive",
                         enum_values=["comprehensive", "sentiment", "trend", "comparison"]),
        ],
        input_types=["preprocessed_data"],
        output_type="analysis_result",
        tags=["analysis", "statistics", "pattern"]
    ),

    "insight": ToolMetadata(
        name="insight",
        display_name="인사이트 생성기",
        description="분석 결과에서 비즈니스 인사이트를 도출합니다",
        category=ToolCategory.ML,
        phase=ToolPhase.INSIGHT,
        is_async=False,
        estimated_duration_sec=30,
        dependencies=[
            ToolDependency(tool_name="analyzer", required=True, output_key="analysis_result")
        ],
        input_types=["analysis_result"],
        output_type="insights",
        tags=["insight", "recommendation", "summary"]
    ),
}

# Biz 도구 카탈로그
BIZ_TOOLS: Dict[str, ToolMetadata] = {
    "report_agent": ToolMetadata(
        name="report_agent",
        display_name="리포트 에이전트",
        description="분석 결과를 기반으로 리포트를 생성합니다 (Markdown, PDF, PPTX, HTML)",
        category=ToolCategory.BIZ,
        phase=ToolPhase.OUTPUT,
        is_async=False,
        estimated_duration_sec=60,
        requires_approval=False,
        dependencies=[
            ToolDependency(tool_name="analyzer", required=False, output_key="analysis_result"),
            ToolDependency(tool_name="insight", required=False, output_key="insights"),
        ],
        parameters=[
            ToolParameter(name="format", type="string", required=False,
                         default="markdown",
                         enum_values=["markdown", "pdf", "pptx", "html"]),
            ToolParameter(name="template", type="string", required=False,
                         description="리포트 템플릿 이름"),
        ],
        input_types=["analysis_result", "insights"],
        output_type="report",
        tags=["report", "document", "output"]
    ),

    "dashboard_agent": ToolMetadata(
        name="dashboard_agent",
        display_name="대시보드 에이전트",
        description="인터랙티브 대시보드를 생성합니다",
        category=ToolCategory.BIZ,
        phase=ToolPhase.OUTPUT,
        is_async=False,
        estimated_duration_sec=90,
        requires_approval=True,
        approval_type="preview",
        dependencies=[
            ToolDependency(tool_name="analyzer", required=True, output_key="analysis_result"),
        ],
        parameters=[
            ToolParameter(name="layout", type="string", required=False,
                         default="standard",
                         enum_values=["standard", "executive", "detailed"]),
        ],
        input_types=["analysis_result"],
        output_type="dashboard",
        tags=["dashboard", "visualization", "interactive"]
    ),

    "storyboard_agent": ToolMetadata(
        name="storyboard_agent",
        display_name="스토리보드 에이전트",
        description="광고/마케팅 콘텐츠의 스토리보드를 생성합니다",
        category=ToolCategory.BIZ,
        phase=ToolPhase.OUTPUT,
        is_async=False,
        estimated_duration_sec=120,
        requires_approval=True,
        approval_type="preview",
        parameters=[
            ToolParameter(name="content_type", type="string", required=True,
                         enum_values=["instagram", "youtube", "tiktok", "tv_ad"]),
            ToolParameter(name="duration_sec", type="int", required=False,
                         default=30),
            ToolParameter(name="style", type="string", required=False,
                         enum_values=["modern", "classic", "playful", "luxury"]),
        ],
        input_types=["insights", "brand_context"],
        output_type="storyboard",
        tags=["creative", "storyboard", "marketing"]
    ),

    "video_agent": ToolMetadata(
        name="video_agent",
        display_name="비디오 에이전트",
        description="스토리보드 기반 비디오를 생성합니다 (RunPod/ComfyUI 연동)",
        category=ToolCategory.BIZ,
        phase=ToolPhase.OUTPUT,
        is_async=True,  # 장시간 실행
        estimated_duration_sec=600,  # 10분
        requires_approval=True,
        approval_type="cost",
        has_cost=True,
        cost_per_call=2.5,  # USD
        dependencies=[
            ToolDependency(tool_name="storyboard_agent", required=True, output_key="storyboard"),
        ],
        parameters=[
            ToolParameter(name="resolution", type="string", required=False,
                         default="1080p",
                         enum_values=["720p", "1080p", "4k"]),
            ToolParameter(name="fps", type="int", required=False, default=30),
        ],
        input_types=["storyboard"],
        output_type="video",
        tags=["video", "creative", "generation", "async"]
    ),

    "ad_creative_agent": ToolMetadata(
        name="ad_creative_agent",
        display_name="광고 크리에이티브 에이전트",
        description="광고 카피, 해시태그, 캡션을 생성합니다",
        category=ToolCategory.BIZ,
        phase=ToolPhase.OUTPUT,
        is_async=False,
        estimated_duration_sec=30,
        requires_approval=True,
        approval_type="result",
        parameters=[
            ToolParameter(name="platform", type="string", required=True,
                         enum_values=["instagram", "facebook", "tiktok", "youtube", "naver"]),
            ToolParameter(name="tone", type="string", required=False,
                         default="professional",
                         enum_values=["professional", "casual", "playful", "luxury"]),
            ToolParameter(name="language", type="string", required=False,
                         default="ko",
                         enum_values=["ko", "en", "ja", "zh"]),
        ],
        input_types=["insights", "brand_context"],
        output_type="ad_creative",
        tags=["creative", "copy", "advertising", "social"]
    ),
}


# ============================================================
# Tool Catalog Loader
# ============================================================

class ToolCatalogLoader:
    """
    도구 카탈로그 로더

    ML/Biz 도구의 메타데이터를 로드하고 조회합니다.
    """

    def __init__(self):
        self._ml_tools = ML_TOOLS.copy()
        self._biz_tools = BIZ_TOOLS.copy()
        self._all_tools: Dict[str, ToolMetadata] = {}
        self._refresh_all_tools()

    def _refresh_all_tools(self) -> None:
        """전체 도구 목록 갱신"""
        self._all_tools = {**self._ml_tools, **self._biz_tools}

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """도구 메타데이터 조회"""
        return self._all_tools.get(name)

    def get_ml_tools(self) -> Dict[str, ToolMetadata]:
        """ML 도구 목록 반환"""
        return self._ml_tools.copy()

    def get_biz_tools(self) -> Dict[str, ToolMetadata]:
        """Biz 도구 목록 반환"""
        return self._biz_tools.copy()

    def get_all_tools(self) -> Dict[str, ToolMetadata]:
        """전체 도구 목록 반환"""
        return self._all_tools.copy()

    def get_tools_by_phase(self, phase: ToolPhase) -> List[ToolMetadata]:
        """단계별 도구 필터링"""
        return [tool for tool in self._all_tools.values() if tool.phase == phase]

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolMetadata]:
        """카테고리별 도구 필터링"""
        return [tool for tool in self._all_tools.values() if tool.category == category]

    def get_tools_requiring_approval(self) -> List[ToolMetadata]:
        """승인 필요 도구 목록"""
        return [tool for tool in self._all_tools.values() if tool.requires_approval]

    def get_async_tools(self) -> List[ToolMetadata]:
        """비동기 도구 목록"""
        return [tool for tool in self._all_tools.values() if tool.is_async]

    def get_tools_with_cost(self) -> List[ToolMetadata]:
        """비용 발생 도구 목록"""
        return [tool for tool in self._all_tools.values() if tool.has_cost]

    def get_tool_dependencies(self, name: str) -> List[ToolDependency]:
        """도구 의존성 목록"""
        tool = self.get_tool(name)
        return tool.dependencies if tool else []

    def get_required_tools_chain(self, name: str) -> List[str]:
        """
        도구 실행에 필요한 전체 도구 체인 반환 (위상 정렬)

        예: "report_agent" -> ["collector", "preprocessor", "analyzer", "insight", "report_agent"]
        """
        tool = self.get_tool(name)
        if not tool:
            return []

        visited = set()
        chain = []

        def visit(tool_name: str) -> None:
            if tool_name in visited:
                return
            visited.add(tool_name)

            current_tool = self.get_tool(tool_name)
            if current_tool:
                for dep in current_tool.dependencies:
                    if dep.required:
                        visit(dep.tool_name)
                chain.append(tool_name)

        visit(name)
        return chain

    def get_tools_by_tags(self, tags: List[str]) -> List[ToolMetadata]:
        """태그로 도구 검색"""
        result = []
        for tool in self._all_tools.values():
            if any(tag in tool.tags for tag in tags):
                result.append(tool)
        return result

    def get_output_tools_for_input(self, input_type: str) -> List[ToolMetadata]:
        """특정 입력 타입을 처리할 수 있는 도구 목록"""
        return [
            tool for tool in self._all_tools.values()
            if input_type in tool.input_types
        ]

    def get_tools_producing_output(self, output_type: str) -> List[ToolMetadata]:
        """특정 출력 타입을 생성하는 도구 목록"""
        return [
            tool for tool in self._all_tools.values()
            if tool.output_type == output_type
        ]

    def validate_tool_chain(self, tool_names: List[str]) -> Dict[str, Any]:
        """
        도구 체인 유효성 검증

        Returns:
            {
                "is_valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        errors = []
        warnings = []
        seen_outputs = set()

        for name in tool_names:
            tool = self.get_tool(name)
            if not tool:
                errors.append(f"Unknown tool: {name}")
                continue

            # 의존성 체크
            for dep in tool.dependencies:
                if dep.required and dep.tool_name not in tool_names:
                    errors.append(f"Tool '{name}' requires '{dep.tool_name}' but it's not in the chain")

            # 입력 타입 체크
            for input_type in tool.input_types:
                if input_type not in seen_outputs and tool.dependencies:
                    # 의존성이 있는데 입력 타입이 아직 생성되지 않음
                    pass  # 의존성 체크에서 이미 처리됨

            seen_outputs.add(tool.output_type)

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def get_tool_summary(self, name: str) -> Optional[Dict[str, Any]]:
        """도구 요약 정보"""
        tool = self.get_tool(name)
        if not tool:
            return None

        return {
            "name": tool.name,
            "display_name": tool.display_name,
            "description": tool.description,
            "category": tool.category.value,
            "phase": tool.phase.value,
            "requires_approval": tool.requires_approval,
            "is_async": tool.is_async,
            "has_cost": tool.has_cost,
            "estimated_duration_sec": tool.estimated_duration_sec
        }

    def to_llm_prompt(self) -> str:
        """LLM 프롬프트용 도구 설명 생성"""
        lines = ["# Available Tools\n"]

        lines.append("## ML Tools")
        for name, tool in self._ml_tools.items():
            lines.append(f"- **{tool.display_name}** (`{name}`): {tool.description}")

        lines.append("\n## Business Tools")
        for name, tool in self._biz_tools.items():
            approval = " [승인 필요]" if tool.requires_approval else ""
            async_tag = " [비동기]" if tool.is_async else ""
            cost_tag = f" [비용: ${tool.cost_per_call}]" if tool.has_cost else ""
            lines.append(f"- **{tool.display_name}** (`{name}`): {tool.description}{approval}{async_tag}{cost_tag}")

        return "\n".join(lines)


# ============================================================
# Global Instance
# ============================================================

_catalog: Optional[ToolCatalogLoader] = None


def get_catalog() -> ToolCatalogLoader:
    """전역 카탈로그 인스턴스 반환"""
    global _catalog
    if _catalog is None:
        _catalog = ToolCatalogLoader()
    return _catalog
