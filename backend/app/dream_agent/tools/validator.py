"""Tool Validator - 도구 스펙 검증 및 유효성 검사

Phase 3: ToolSpec 검증, 의존성 검사, 스키마 유효성 검증.
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
import logging

from ..models.tool import ToolSpec, ToolType, ToolParameter, ToolParameterType
from .discovery import get_tool_discovery

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """검증 결과"""
    valid: bool
    errors: List[str]
    warnings: List[str]

    @classmethod
    def success(cls, warnings: Optional[List[str]] = None) -> "ValidationResult":
        return cls(valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(cls, errors: List[str], warnings: Optional[List[str]] = None) -> "ValidationResult":
        return cls(valid=False, errors=errors, warnings=warnings or [])


class ToolValidator:
    """도구 스펙 검증기

    ToolSpec의 유효성, 의존성, 파라미터를 검증합니다.

    Example:
        ```python
        validator = ToolValidator()

        # 단일 ToolSpec 검증
        result = validator.validate_spec(spec)
        if not result.valid:
            print(f"Errors: {result.errors}")

        # 전체 Discovery 검증
        result = validator.validate_all()
        ```
    """

    # 유효한 레이어 목록
    VALID_LAYERS = {"ml_execution", "biz_execution", "data_collection"}

    # 유효한 도구 타입
    VALID_TOOL_TYPES = {t.value for t in ToolType}

    # 유효한 파라미터 타입
    VALID_PARAM_TYPES = {t.value for t in ToolParameterType}

    def __init__(self):
        self._discovery = get_tool_discovery

    def validate_spec(self, spec: ToolSpec) -> ValidationResult:
        """단일 ToolSpec 검증

        Args:
            spec: 검증할 ToolSpec

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        # 1. 필수 필드 검증
        if not spec.name:
            errors.append("name is required")
        if not spec.description:
            warnings.append("description is empty")
        if not spec.executor:
            warnings.append("executor is not specified")

        # 2. 이름 규칙 검증
        if spec.name and not self._is_valid_name(spec.name):
            errors.append(f"Invalid name format: {spec.name}. Use lowercase with underscores.")

        # 3. 레이어 검증
        if spec.layer and spec.layer not in self.VALID_LAYERS:
            warnings.append(f"Unknown layer: {spec.layer}. Valid: {self.VALID_LAYERS}")

        # 4. 파라미터 검증
        param_errors = self._validate_parameters(spec.parameters)
        errors.extend(param_errors)

        # 5. 의존성 검증
        dep_errors, dep_warnings = self._validate_dependencies(spec)
        errors.extend(dep_errors)
        warnings.extend(dep_warnings)

        # 6. 비용 정보 검증
        if spec.has_cost and spec.estimated_cost is None:
            warnings.append("has_cost=True but estimated_cost is not specified")

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult.success(warnings)

    def validate_all(self) -> ValidationResult:
        """전체 Discovery의 모든 ToolSpec 검증

        Returns:
            ValidationResult (전체 결과 통합)
        """
        discovery = self._discovery()
        all_errors = []
        all_warnings = []

        specs = discovery.list_all_specs()
        for spec in specs:
            result = self.validate_spec(spec)
            if result.errors:
                all_errors.extend([f"[{spec.name}] {e}" for e in result.errors])
            if result.warnings:
                all_warnings.extend([f"[{spec.name}] {w}" for w in result.warnings])

        # 글로벌 검증
        global_errors, global_warnings = self._validate_global(specs)
        all_errors.extend(global_errors)
        all_warnings.extend(global_warnings)

        if all_errors:
            return ValidationResult.failure(all_errors, all_warnings)
        return ValidationResult.success(all_warnings)

    def validate_dependencies(self) -> ValidationResult:
        """의존성 그래프 전체 검증

        순환 의존성, 누락된 의존성 등을 검사합니다.

        Returns:
            ValidationResult
        """
        discovery = self._discovery()
        errors = []
        warnings = []

        specs = discovery.list_all_specs()
        spec_names = {s.name for s in specs}

        # 1. 누락된 의존성 확인
        for spec in specs:
            for dep in spec.dependencies:
                if dep not in spec_names:
                    errors.append(f"[{spec.name}] Missing dependency: {dep}")

        # 2. 순환 의존성 확인
        cycles = self._find_cycles(specs)
        if cycles:
            for cycle in cycles:
                errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult.success(warnings)

    def validate_input(self, spec: ToolSpec, input_data: Dict[str, Any]) -> ValidationResult:
        """도구 입력 데이터 검증

        Args:
            spec: ToolSpec
            input_data: 입력 딕셔너리

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        # 필수 파라미터 확인
        for param in spec.get_required_params():
            if param.name not in input_data:
                errors.append(f"Missing required parameter: {param.name}")

        # 파라미터 타입 확인
        for param in spec.parameters:
            if param.name in input_data:
                value = input_data[param.name]
                type_error = self._check_param_type(param, value)
                if type_error:
                    errors.append(type_error)

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult.success(warnings)

    def _is_valid_name(self, name: str) -> bool:
        """이름 형식 검증 (소문자, 언더스코어만)"""
        import re
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))

    def _validate_parameters(self, parameters: List[ToolParameter]) -> List[str]:
        """파라미터 검증"""
        errors = []
        seen_names = set()

        for param in parameters:
            # 중복 이름 확인
            if param.name in seen_names:
                errors.append(f"Duplicate parameter name: {param.name}")
            seen_names.add(param.name)

            # 이름 형식 확인
            if not param.name or not self._is_valid_name(param.name):
                errors.append(f"Invalid parameter name: {param.name}")

        return errors

    def _validate_dependencies(self, spec: ToolSpec) -> tuple:
        """의존성 검증"""
        errors = []
        warnings = []

        discovery = self._discovery()

        for dep_name in spec.dependencies:
            dep_spec = discovery.get(dep_name)
            if dep_spec is None:
                warnings.append(f"Dependency not found in discovery: {dep_name}")

        return errors, warnings

    def _validate_global(self, specs: List[ToolSpec]) -> tuple:
        """글로벌 검증 (중복 이름 등)"""
        errors = []
        warnings = []

        # 중복 이름 확인
        names = [s.name for s in specs]
        duplicates = [n for n in names if names.count(n) > 1]
        if duplicates:
            errors.append(f"Duplicate tool names: {set(duplicates)}")

        return errors, warnings

    def _find_cycles(self, specs: List[ToolSpec]) -> List[List[str]]:
        """순환 의존성 탐지"""
        graph = {s.name: set(s.dependencies) for s in specs}
        cycles = []

        def dfs(node: str, path: List[str], visited: Set[str]):
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                dfs(neighbor, path.copy(), visited)

        visited = set()
        for node in graph:
            if node not in visited:
                dfs(node, [], visited)

        return cycles

    def _check_param_type(self, param: ToolParameter, value: Any) -> Optional[str]:
        """파라미터 타입 확인"""
        type_map = {
            ToolParameterType.STRING: str,
            ToolParameterType.INTEGER: int,
            ToolParameterType.NUMBER: (int, float),
            ToolParameterType.BOOLEAN: bool,
            ToolParameterType.ARRAY: (list, tuple),
            ToolParameterType.OBJECT: dict,
        }

        expected = type_map.get(param.type)
        if expected and not isinstance(value, expected):
            return f"Parameter '{param.name}' expected {param.type.value}, got {type(value).__name__}"

        return None


# 싱글톤 인스턴스
_validator_instance: Optional[ToolValidator] = None


def get_tool_validator() -> ToolValidator:
    """ToolValidator 싱글톤 인스턴스 반환"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ToolValidator()
    return _validator_instance


def validate_tool_spec(spec: ToolSpec) -> ValidationResult:
    """ToolSpec 검증 (헬퍼 함수)"""
    return get_tool_validator().validate_spec(spec)


def validate_all_tools() -> ValidationResult:
    """전체 도구 검증 (헬퍼 함수)"""
    return get_tool_validator().validate_all()
