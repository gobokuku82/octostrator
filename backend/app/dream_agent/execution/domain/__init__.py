"""Domain Agents - 도메인별 실행 Agent

실제 비즈니스 로직을 수행하는 Agent들입니다.
Phase 2: BaseDomainAgent 기반 표준화.

구조:
- base_agent.py: BaseDomainAgent 추상 클래스 (Phase 2)
- collection/: 데이터 수집 (collector, preprocessor)
- analysis/: 분석 (sentiment, keyword, problem, hashtag, competitor, trends)
- insight/: 인사이트 생성
- content/: 콘텐츠 생성 (ad_creative, storyboard, video)
- report/: 리포트 생성
- ops/: 운영 (dashboard, sales, inventory)
- toolkit/: 공용 유틸리티
"""

# Phase 2: BaseDomainAgent
from .base_agent import (
    BaseDomainAgent,
    DomainAgentRegistry,
    get_domain_agent_registry,
    register_domain_agent,
    get_domain_agent,
)

__all__ = [
    # Phase 2: Base classes
    "BaseDomainAgent",
    "DomainAgentRegistry",
    "get_domain_agent_registry",
    "register_domain_agent",
    "get_domain_agent",
    # Sub-packages
    "collection",
    "analysis",
    "insight",
    "content",
    "report",
    "ops",
    "toolkit",
]
