"""Agent Config Loader - YAML 설정 파일 로더

레이어별 설정을 YAML 파일에서 로드하고 캐싱합니다.
"""

import os
import yaml
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Any, Optional

from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class AgentConfigLoader:
    """
    Agent 설정 로더

    YAML 파일에서 설정을 로드하고 캐싱하여 제공합니다.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Args:
            config_dir: 설정 파일 디렉토리 경로 (기본: llm_manager/configs)
        """
        if config_dir is None:
            config_dir = Path(__file__).parent / "configs"
        self.config_dir = config_dir

        # 설정 캐시
        self._intent_config: Optional[Dict] = None
        self._data_sources_config: Optional[Dict] = None
        self._tool_settings_config: Optional[Dict] = None
        self._prompts_config: Dict[str, Dict] = {}

        # 초기 로드
        self._load_all_configs()

    def _load_yaml(self, filename: str, subdir: Optional[str] = None) -> Dict:
        """YAML 파일 로드"""
        if subdir:
            filepath = self.config_dir / subdir / filename
        else:
            filepath = self.config_dir / filename

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Config file not found: {filepath}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {filepath}: {e}")
            return {}

    def _load_all_configs(self) -> None:
        """모든 설정 파일 로드"""
        self._intent_config = self._load_yaml("intent_keywords.yaml")
        self._data_sources_config = self._load_yaml("data_sources.yaml")
        self._tool_settings_config = self._load_yaml("tool_settings.yaml")

        # 프롬프트 파일들 로드
        prompts_dir = self.config_dir / "prompts"
        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.yaml"):
                name = prompt_file.stem
                self._prompts_config[name] = self._load_yaml(prompt_file.name, "prompts")

        logger.info(f"Loaded configs: intent, data_sources, tool_settings, prompts={list(self._prompts_config.keys())}")

    def reload(self) -> None:
        """설정 다시 로드"""
        self._load_all_configs()
        logger.info("All configs reloaded")

    # ============================================================
    # Intent Keywords 관련
    # ============================================================

    def get_ml_keywords(self, language: str = "ko") -> List[str]:
        """ML 관련 키워드 반환"""
        if not self._intent_config:
            return []
        return self._intent_config.get("ml_keywords", {}).get(language, [])

    def get_biz_keywords(self, language: str = "ko") -> List[str]:
        """Biz 관련 키워드 반환"""
        if not self._intent_config:
            return []
        return self._intent_config.get("biz_keywords", {}).get(language, [])

    def get_source_keywords(self, source: str, language: str = "ko") -> List[str]:
        """특정 데이터 소스의 키워드 반환"""
        if not self._intent_config:
            return []
        sources = self._intent_config.get("data_sources", {})
        return sources.get(source, {}).get("keywords", {}).get(language, [])

    def get_all_source_keywords(self, language: str = "ko") -> Dict[str, List[str]]:
        """모든 데이터 소스의 키워드 반환"""
        if not self._intent_config:
            return {}
        result = {}
        for source, config in self._intent_config.get("data_sources", {}).items():
            keywords = config.get("keywords", {}).get(language, [])
            if keywords:
                result[source] = keywords
        return result

    def get_default_sources(self) -> List[str]:
        """기본 데이터 소스 목록 반환"""
        if not self._intent_config:
            return ["amazon", "oliveyoung", "youtube", "tiktok"]
        return self._intent_config.get("defaults", {}).get("default_sources", [])

    def get_confidence_threshold(self) -> float:
        """신뢰도 임계값 반환"""
        if not self._intent_config:
            return 0.7
        return self._intent_config.get("defaults", {}).get("confidence_threshold", 0.7)

    # ============================================================
    # Data Sources 관련
    # ============================================================

    def get_source_config(self, source: str) -> Dict[str, Any]:
        """데이터 소스 설정 반환"""
        if not self._data_sources_config:
            return {}
        return self._data_sources_config.get("sources", {}).get(source, {})

    def get_source_file_path(self, source: str) -> Optional[str]:
        """데이터 소스 파일 경로 반환"""
        config = self.get_source_config(source)
        return config.get("file_path")

    def get_enabled_sources(self) -> List[str]:
        """활성화된 데이터 소스 목록"""
        if not self._data_sources_config:
            return []
        sources = self._data_sources_config.get("sources", {})
        return [name for name, config in sources.items() if config.get("enabled", False)]

    def get_output_dir(self, output_type: str = "ml_results") -> str:
        """출력 디렉토리 경로 반환"""
        if not self._data_sources_config:
            return f"data/output/{output_type}"
        output_config = self._data_sources_config.get("output", {})
        return output_config.get(f"{output_type}_dir", f"data/output/{output_type}")

    def get_sentiment_keywords(self, sentiment: str, language: str = "ko") -> List[str]:
        """감성 분석 키워드 반환"""
        if not self._data_sources_config:
            return []
        sentiment_config = self._data_sources_config.get("sentiment", {})
        return sentiment_config.get(f"{sentiment}_keywords", {}).get(language, [])

    def get_analysis_settings(self) -> Dict[str, Any]:
        """분석 설정 반환"""
        if not self._data_sources_config:
            return {}
        return self._data_sources_config.get("analysis", {})

    # ============================================================
    # Tool Settings 관련
    # ============================================================

    def get_tool_config(self, category: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        카테고리별 도구 설정 반환

        Args:
            category: 도구 카테고리 (예: "biz_execution", "ml_execution")
            default: 기본값 (설정이 없을 때 반환)

        Returns:
            해당 카테고리의 설정 dict
        """
        if default is None:
            default = {}
        if not self._tool_settings_config:
            return default
        return self._tool_settings_config.get(category, default)

    def get_ml_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """ML 도구 설정 반환"""
        if not self._tool_settings_config:
            return {}
        return self._tool_settings_config.get("ml_tools", {}).get(tool_name, {})

    def get_biz_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Biz 도구 설정 반환"""
        if not self._tool_settings_config:
            return {}
        return self._tool_settings_config.get("biz_tools", {}).get(tool_name, {})

    def get_tool_timeout(self, tool_name: str) -> int:
        """도구 타임아웃 반환 (초)"""
        ml_config = self.get_ml_tool_config(tool_name)
        if ml_config:
            return ml_config.get("timeout_sec", 60)
        biz_config = self.get_biz_tool_config(tool_name)
        return biz_config.get("timeout_sec", 60)

    def get_tool_requires_approval(self, tool_name: str) -> bool:
        """도구 승인 필요 여부 반환"""
        biz_config = self.get_biz_tool_config(tool_name)
        return biz_config.get("requires_approval", False)

    def get_llm_settings(self) -> Dict[str, Any]:
        """LLM 설정 반환"""
        if not self._tool_settings_config:
            return {}
        return self._tool_settings_config.get("common", {}).get("llm", {})

    def get_llm_max_tokens(self, layer: str) -> int:
        """레이어별 LLM max_tokens 반환"""
        llm_settings = self.get_llm_settings()
        max_tokens = llm_settings.get("max_tokens", {})
        return max_tokens.get(layer, 500)

    def get_approval_settings(self) -> Dict[str, Any]:
        """승인 설정 반환"""
        if not self._tool_settings_config:
            return {}
        return self._tool_settings_config.get("approval", {})

    # ============================================================
    # Prompts 관련
    # ============================================================

    def get_prompt(self, layer: str, prompt_type: str = "system_prompt") -> str:
        """프롬프트 반환"""
        if layer not in self._prompts_config:
            logger.warning(f"Prompt config not found for layer: {layer}")
            return ""
        return self._prompts_config[layer].get(prompt_type, "")

    def get_prompt_template(self, layer: str) -> str:
        """사용자 프롬프트 템플릿 반환"""
        return self.get_prompt(layer, "user_template")

    def get_language_instruction(self, layer: str, language: str = "KOR") -> str:
        """언어별 지시문 반환"""
        if layer not in self._prompts_config:
            return ""
        instructions = self._prompts_config[layer].get("language_instructions", {})
        return instructions.get(language, "")

    def get_fallback_response(self, language: str = "KOR") -> str:
        """Fallback 응답 반환"""
        if "response" not in self._prompts_config:
            return "요청을 처리했습니다."
        fallbacks = self._prompts_config["response"].get("fallback_responses", {})
        return fallbacks.get(language, "요청을 처리했습니다.")

    def get_prompt_examples(self, layer: str) -> List[Dict[str, Any]]:
        """프롬프트 예시 반환"""
        if layer not in self._prompts_config:
            return []
        return self._prompts_config[layer].get("examples", [])

    def get_section_headers(self, language: str = "KOR") -> Dict[str, str]:
        """응답 섹션 헤더 반환"""
        if "response" not in self._prompts_config:
            return {}
        headers = self._prompts_config["response"].get("section_headers", {})
        return headers.get(language, {})

    # ============================================================
    # 유틸리티 메서드
    # ============================================================

    def detect_sources_from_text(self, text: str, language: str = "ko") -> List[str]:
        """텍스트에서 데이터 소스 감지"""
        detected = []
        text_lower = text.lower()

        for source, keywords in self.get_all_source_keywords(language).items():
            if any(kw.lower() in text_lower for kw in keywords):
                detected.append(source)

        return detected

    def detect_intent_type(self, text: str, language: str = "ko") -> Dict[str, Any]:
        """텍스트에서 intent 타입 감지 (키워드 기반)"""
        text_lower = text.lower()

        ml_keywords = self.get_ml_keywords(language)
        biz_keywords = self.get_biz_keywords(language)

        requires_ml = any(kw.lower() in text_lower for kw in ml_keywords)
        requires_biz = any(kw.lower() in text_lower for kw in biz_keywords)

        if requires_ml and requires_biz:
            intent_type = "full_pipeline"
        elif requires_ml:
            intent_type = "ml_analysis"
        elif requires_biz:
            intent_type = "report_generation"
        else:
            intent_type = "simple_question"

        return {
            "intent_type": intent_type,
            "requires_ml": requires_ml,
            "requires_biz": requires_biz
        }

    def get_full_config(self) -> Dict[str, Any]:
        """전체 설정 반환 (디버깅용)"""
        return {
            "intent": self._intent_config,
            "data_sources": self._data_sources_config,
            "tool_settings": self._tool_settings_config,
            "prompts": self._prompts_config
        }


# ============================================================
# Global Instance
# ============================================================

_agent_config: Optional[AgentConfigLoader] = None


def get_agent_config() -> AgentConfigLoader:
    """전역 설정 로더 인스턴스 반환"""
    global _agent_config
    if _agent_config is None:
        _agent_config = AgentConfigLoader()
    return _agent_config


# 편의를 위한 전역 인스턴스
agent_config = get_agent_config()
