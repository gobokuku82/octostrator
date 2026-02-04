"""LLM Manager - LLM 클라이언트 및 설정 관리"""

# Client (독립적)
from .client import LLMClient, LLMConfig, get_llm_client

# Config FIRST (prompts.py에서 사용하므로 먼저 import)
from .config_loader import AgentConfigLoader, agent_config, get_agent_config

# Prompts SECOND (agent_config 사용)
from .prompts import (
    COGNITIVE_SYSTEM_PROMPT,
    PLANNING_SYSTEM_PROMPT,
    RESPONSE_SYSTEM_PROMPT,
    REPLAN_SYSTEM_PROMPT,
    format_cognitive_prompt,
    format_planning_prompt,
    format_response_prompt,
    format_replan_prompt,
)

__all__ = [
    # Client
    "LLMClient",
    "LLMConfig",
    "get_llm_client",
    # Config
    "AgentConfigLoader",
    "agent_config",
    "get_agent_config",
    # Prompts
    "COGNITIVE_SYSTEM_PROMPT",
    "PLANNING_SYSTEM_PROMPT",
    "RESPONSE_SYSTEM_PROMPT",
    "REPLAN_SYSTEM_PROMPT",
    "format_cognitive_prompt",
    "format_planning_prompt",
    "format_response_prompt",
    "format_replan_prompt",
]
