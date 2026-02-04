"""Tool Models - Tool 명세 및 관련 모델

Phase 0: Tool Discovery 시스템의 핵심 모델.
YAML 기반 Tool 정의를 Pydantic 모델로 표현.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
from enum import Enum


class ToolType(str, Enum):
    """Tool 타입"""
    DATA = "data"           # 데이터 수집/처리
    ANALYSIS = "analysis"   # 분석/인사이트
    CONTENT = "content"     # 콘텐츠 생성
    BUSINESS = "business"   # 비즈니스 작업


class ToolParameterType(str, Enum):
    """파라미터 타입"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Tool 파라미터 정의"""
    name: str
    type: ToolParameterType
    required: bool = False
    default: Optional[Any] = None
    description: str = ""

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Parameter name cannot be empty")
        return v.strip()


class ToolSpec(BaseModel):
    """Tool 명세 (YAML에서 로드)"""
    name: str
    description: str
    tool_type: ToolType
    version: str = "1.0.0"

    # 파라미터
    parameters: List[ToolParameter] = Field(default_factory=list)

    # 실행 정보
    executor: str  # "ml_agent.sentiment", "biz_agent.report" 등
    timeout_sec: int = 300
    max_retries: int = 3

    # 의존성
    dependencies: List[str] = Field(default_factory=list)  # 이 tool이 의존하는 다른 tool 이름들
    produces: List[str] = Field(default_factory=list)      # 이 tool이 생성하는 출력 키

    # Layer 정보
    layer: str = "execution"  # cognitive, planning, ml_execution, biz_execution

    # 메타데이터
    tags: List[str] = Field(default_factory=list)
    examples: List[Dict[str, Any]] = Field(default_factory=list)

    # 비용 정보
    has_cost: bool = False
    estimated_cost: float = 0.0

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip().lower().replace(" ", "_")

    @field_validator('executor')
    @classmethod
    def validate_executor(cls, v):
        if not v or not v.strip():
            raise ValueError("Executor cannot be empty")
        return v.strip()

    def get_required_params(self) -> List[ToolParameter]:
        """필수 파라미터 목록"""
        return [p for p in self.parameters if p.required]

    def get_optional_params(self) -> List[ToolParameter]:
        """선택 파라미터 목록"""
        return [p for p in self.parameters if not p.required]

    def to_langchain_schema(self) -> Dict[str, Any]:
        """LangChain Tool 스키마로 변환"""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type.value,
                "description": param.description
            }
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class ToolRegistry(BaseModel):
    """Tool 레지스트리 메타데이터"""
    version: str = "1.0.0"
    tools: Dict[str, ToolSpec] = Field(default_factory=dict)
    last_updated: Optional[str] = None
