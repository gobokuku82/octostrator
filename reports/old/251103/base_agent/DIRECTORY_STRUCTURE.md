# Base Agent Framework - 디렉토리 구조 상세 설계

**작성일**: 2025-10-31
**버전**: 1.0
**목적**: Base Agent Framework의 디렉토리 구조 및 파일 구성 상세 설계

---

## 📁 전체 디렉토리 트리

```
base_agent_framework/
│
├── 📦 core/                                # 핵심 프레임워크 (도메인 독립)
│   ├── __init__.py
│   │
│   ├── 🎯 supervisor/                      # Supervisor 계층
│   │   ├── __init__.py
│   │   ├── base_supervisor.py             # 범용 Supervisor 기본 클래스
│   │   ├── workflow_builder.py            # Graph 구성 유틸리티
│   │   ├── node_manager.py                # 노드 관리 및 라우팅
│   │   └── progress_tracker.py            # 진행 상황 추적 (WebSocket)
│   │
│   ├── 🧠 cognitive/                       # 인지 계층
│   │   ├── __init__.py
│   │   ├── intent_analyzer.py             # 의도 분석 (범용)
│   │   ├── plan_generator.py              # 실행 계획 생성
│   │   ├── query_decomposer.py            # 복합 질문 분해
│   │   └── strategy_selector.py           # 실행 전략 선택
│   │
│   ├── ⚙️ execution/                       # 실행 계층
│   │   ├── __init__.py
│   │   ├── base_executor.py               # 범용 Executor 기본 클래스
│   │   ├── result_aggregator.py           # 결과 집계
│   │   ├── team_manager.py                # 팀 관리 및 조정
│   │   └── hitl/                          # Human-in-the-Loop 지원
│   │       ├── __init__.py
│   │       ├── interrupt_handler.py       # Interrupt 처리
│   │       └── approval_manager.py        # 승인 관리
│   │
│   ├── 🏗️ foundation/                      # 기반 계층
│   │   ├── __init__.py
│   │   │
│   │   ├── state/                         # State 관리
│   │   │   ├── __init__.py
│   │   │   ├── state_manager.py           # State 관리 유틸리티
│   │   │   ├── state_schema.py            # 기본 State 스키마
│   │   │   ├── state_validator.py         # State 검증
│   │   │   └── state_transition.py        # State 전환 헬퍼
│   │   │
│   │   ├── memory/                        # 메모리 시스템
│   │   │   ├── __init__.py
│   │   │   ├── memory_service.py          # 3-Tier Memory 서비스
│   │   │   ├── short_term_memory.py       # 단기 메모리 (1-5 sessions)
│   │   │   ├── mid_term_memory.py         # 중기 메모리 (6-10 sessions)
│   │   │   ├── long_term_memory.py        # 장기 메모리 (11-20 sessions)
│   │   │   └── memory_summarizer.py       # LLM 기반 요약
│   │   │
│   │   ├── checkpoint/                    # Checkpointing
│   │   │   ├── __init__.py
│   │   │   ├── checkpointer.py            # LangGraph 0.6 Checkpointer
│   │   │   └── checkpoint_manager.py      # Checkpoint 관리
│   │   │
│   │   └── registry/                      # 플러그인 레지스트리
│   │       ├── __init__.py
│   │       ├── intent_registry.py         # Intent 동적 등록
│   │       ├── tool_registry.py           # Tool 동적 등록
│   │       ├── agent_registry.py          # Agent 등록 및 관리
│   │       └── plugin_loader.py           # 플러그인 로더
│   │
│   ├── 🤖 llm/                             # LLM 통합
│   │   ├── __init__.py
│   │   ├── llm_service.py                 # LLM 호출 추상화
│   │   ├── prompt_manager.py              # 프롬프트 관리
│   │   ├── providers/                     # LLM Provider 구현
│   │   │   ├── __init__.py
│   │   │   ├── openai_provider.py         # OpenAI
│   │   │   ├── anthropic_provider.py      # Anthropic
│   │   │   └── base_provider.py           # Provider 기본 클래스
│   │   └── streaming/                     # 스트리밍 지원
│   │       ├── __init__.py
│   │       └── stream_handler.py
│   │
│   └── 🛠️ utils/                           # 유틸리티
│       ├── __init__.py
│       ├── config_loader.py               # 설정 파일 로더 (YAML/JSON)
│       ├── logger.py                      # 로깅 유틸리티
│       ├── validation.py                  # 검증 유틸리티
│       └── serialization.py               # 직렬화 유틸리티
│
├── 🔌 plugins/                             # 도메인별 플러그인
│   ├── __init__.py
│   ├── plugin_template/                   # 플러그인 템플릿
│   │   ├── __init__.py
│   │   ├── domain_config.yaml             # 도메인 설정 템플릿
│   │   ├── intents.py                     # Intent 정의 템플릿
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   └── example_tool.py
│   │   ├── prompts/
│   │   │   ├── cognitive/
│   │   │   │   └── intent_analysis.txt
│   │   │   ├── execution/
│   │   │   │   └── task_execution.txt
│   │   │   └── common/
│   │   │       └── response_generation.txt
│   │   └── executors/
│   │       ├── __init__.py
│   │       └── custom_executor.py
│   │
│   ├── 🏠 real_estate/                     # 부동산 플러그인
│   │   ├── __init__.py
│   │   ├── domain_config.yaml             # 부동산 도메인 설정
│   │   ├── intents.py                     # 부동산 Intent 정의
│   │   │
│   │   ├── tools/                         # 부동산 Tools
│   │   │   ├── __init__.py
│   │   │   ├── legal_search_tool.py       # 법률 검색
│   │   │   ├── market_data_tool.py        # 시세 조회
│   │   │   ├── real_estate_search_tool.py # 매물 검색
│   │   │   ├── loan_data_tool.py          # 대출 정보
│   │   │   ├── building_registry_tool.py  # 건축물 대장
│   │   │   ├── infrastructure_tool.py     # 인프라 정보
│   │   │   ├── policy_matcher_tool.py     # 정책 매칭
│   │   │   ├── contract_analysis_tool.py  # 계약서 분석
│   │   │   ├── market_analysis_tool.py    # 시장 분석
│   │   │   ├── roi_calculator_tool.py     # ROI 계산
│   │   │   ├── loan_simulator_tool.py     # 대출 시뮬레이션
│   │   │   ├── lease_contract_generator.py # 계약서 생성
│   │   │   └── realestate_terminology.py  # 용어 사전
│   │   │
│   │   ├── prompts/                       # 부동산 프롬프트
│   │   │   ├── cognitive/
│   │   │   │   ├── intent_analysis.txt
│   │   │   │   ├── agent_selection.txt
│   │   │   │   └── agent_selection_simple.txt
│   │   │   ├── execution/
│   │   │   │   ├── search_query.txt
│   │   │   │   ├── result_filtering.txt
│   │   │   │   ├── analysis.txt
│   │   │   │   ├── document_draft.txt
│   │   │   │   ├── document_review.txt
│   │   │   │   └── response_generation.txt
│   │   │   └── common/
│   │   │       ├── conversation_summary.txt
│   │   │       └── response_validation.txt
│   │   │
│   │   └── executors/                     # 부동산 Executors
│   │       ├── __init__.py
│   │       ├── search_executor.py         # 검색 팀
│   │       ├── analysis_executor.py       # 분석 팀
│   │       └── document_executor.py       # 문서 팀 (HITL)
│   │
│   ├── 🏥 medical/                         # 의료 플러그인 (예시)
│   │   ├── __init__.py
│   │   ├── domain_config.yaml
│   │   ├── intents.py
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── symptom_checker_tool.py
│   │   │   ├── medication_search_tool.py
│   │   │   ├── hospital_finder_tool.py
│   │   │   └── appointment_scheduler_tool.py
│   │   ├── prompts/
│   │   │   ├── cognitive/
│   │   │   ├── execution/
│   │   │   └── common/
│   │   └── executors/
│   │       ├── __init__.py
│   │       ├── diagnostic_executor.py
│   │       └── booking_executor.py
│   │
│   └── ⚖️ legal/                           # 법률 플러그인 (예시)
│       ├── __init__.py
│       ├── domain_config.yaml
│       ├── intents.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── case_law_tool.py
│       │   ├── statute_search_tool.py
│       │   ├── contract_analyzer_tool.py
│       │   └── risk_detector_tool.py
│       ├── prompts/
│       └── executors/
│
├── 🌐 application/                         # 애플리케이션 레이어
│   ├── __init__.py
│   │
│   ├── api/                               # API 레이어
│   │   ├── __init__.py
│   │   ├── chat_api.py                    # WebSocket Chat API
│   │   ├── ws_manager.py                  # WebSocket Connection Manager
│   │   ├── rest_api.py                    # REST API (선택)
│   │   └── schemas.py                     # API 스키마
│   │
│   ├── models/                            # 데이터 모델
│   │   ├── __init__.py
│   │   ├── chat.py                        # Chat 모델
│   │   ├── session.py                     # Session 모델
│   │   └── memory.py                      # Memory 모델
│   │
│   ├── db/                                # 데이터베이스
│   │   ├── __init__.py
│   │   ├── postgre_db.py                  # PostgreSQL 연결
│   │   ├── mongo_db.py                    # MongoDB 연결 (선택)
│   │   └── migrations/                    # DB 마이그레이션
│   │       ├── __init__.py
│   │       └── versions/
│   │
│   └── middleware/                        # 미들웨어
│       ├── __init__.py
│       ├── auth.py                        # 인증
│       ├── rate_limiter.py                # Rate Limiting
│       └── error_handler.py               # 에러 핸들링
│
├── 🧪 tests/                               # 테스트
│   ├── __init__.py
│   │
│   ├── unit/                              # 단위 테스트
│   │   ├── __init__.py
│   │   ├── test_supervisor/
│   │   ├── test_cognitive/
│   │   ├── test_execution/
│   │   ├── test_foundation/
│   │   └── test_llm/
│   │
│   ├── integration/                       # 통합 테스트
│   │   ├── __init__.py
│   │   ├── test_workflow/
│   │   ├── test_plugins/
│   │   └── test_memory/
│   │
│   ├── e2e/                               # E2E 테스트
│   │   ├── __init__.py
│   │   ├── test_real_estate/
│   │   ├── test_medical/
│   │   └── test_legal/
│   │
│   └── fixtures/                          # 테스트 Fixtures
│       ├── __init__.py
│       ├── sample_queries.json
│       └── mock_responses.json
│
├── 📚 docs/                                # 문서
│   ├── index.md                           # 문서 홈
│   ├── getting_started.md                 # 시작 가이드
│   ├── architecture.md                    # 아키텍처 설명
│   ├── plugin_development.md              # 플러그인 개발 가이드
│   ├── api_reference.md                   # API 레퍼런스
│   ├── configuration.md                   # 설정 가이드
│   ├── deployment.md                      # 배포 가이드
│   └── examples/                          # 예제
│       ├── basic_usage.md
│       ├── custom_domain.md
│       └── advanced_features.md
│
├── 📖 examples/                            # 예제 애플리케이션
│   ├── __init__.py
│   ├── real_estate_app.py                 # 부동산 예제
│   ├── medical_app.py                     # 의료 예제
│   ├── legal_app.py                       # 법률 예제
│   ├── minimal_custom_domain.py           # 최소 커스텀 도메인
│   └── advanced_custom_domain.py          # 고급 커스텀 도메인
│
├── 🔧 scripts/                             # 유틸리티 스크립트
│   ├── create_plugin.py                   # 플러그인 생성 스크립트
│   ├── migrate_domain.py                  # 도메인 마이그레이션 스크립트
│   ├── benchmark.py                       # 성능 벤치마크
│   └── validate_config.py                 # 설정 검증 스크립트
│
├── 🐳 docker/                              # Docker 설정
│   ├── Dockerfile                         # 메인 Dockerfile
│   ├── docker-compose.yml                 # Docker Compose
│   └── .dockerignore
│
├── ⚙️ config/                              # 설정 파일
│   ├── default.yaml                       # 기본 설정
│   ├── development.yaml                   # 개발 환경
│   ├── production.yaml                    # 프로덕션 환경
│   └── test.yaml                          # 테스트 환경
│
├── 📄 pyproject.toml                       # 프로젝트 설정 (Poetry)
├── 📄 setup.py                             # 설치 스크립트
├── 📄 requirements.txt                     # 의존성 (pip)
├── 📄 README.md                            # 프로젝트 README
├── 📄 LICENSE                              # 라이선스
├── 📄 CHANGELOG.md                         # 변경 이력
├── 📄 CONTRIBUTING.md                      # 기여 가이드
└── 📄 .env.example                         # 환경 변수 예시
```

---

## 📋 주요 파일 설명

### Core 레이어

#### 1. `core/supervisor/base_supervisor.py`

```python
"""
범용 Supervisor 기본 클래스

모든 도메인에서 재사용 가능한 워크플로우 오케스트레이션 로직
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseSupervisor(ABC):
    """
    범용 Supervisor

    Features:
    - 도메인 독립적 워크플로우
    - 플러그인 기반 확장
    - LangGraph 0.6 통합
    - Progress Callback 시스템
    - Checkpointing 지원
    """

    def __init__(
        self,
        llm_context: Any = None,
        enable_checkpointing: bool = True,
        config_path: Optional[str] = None
    ):
        pass

    @abstractmethod
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """도메인 설정 로드"""
        pass

    @abstractmethod
    def _load_domain_plugins(self):
        """도메인별 플러그인 로드"""
        pass

    async def process_query_streaming(
        self,
        query: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """쿼리 처리 (스트리밍)"""
        pass
```

#### 2. `core/cognitive/intent_analyzer.py`

```python
"""
범용 의도 분석기

도메인 독립적 의도 분석 로직
IntentRegistry를 통한 플러그인 지원
"""

class IntentAnalyzer:
    """
    의도 분석기

    Features:
    - LLM 기반 분석
    - 패턴 매칭 Fallback
    - 도메인별 Intent 지원
    - 다층 Fallback 전략
    """

    def __init__(self, intent_registry, llm_service):
        self.intent_registry = intent_registry
        self.llm_service = llm_service

    async def analyze(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> IntentResult:
        """의도 분석 실행"""
        pass
```

#### 3. `core/foundation/registry/intent_registry.py`

```python
"""
Intent 플러그인 레지스트리

도메인별 Intent 동적 등록 및 관리
"""

class IntentRegistry:
    """
    Intent 동적 등록 시스템

    Features:
    - 도메인별 Intent 격리
    - Hot-reload 지원
    - Pattern 매칭
    - Agent 매핑
    """

    def register_domain(
        self,
        domain_name: str,
        intents: Dict[str, str],
        patterns: Dict[str, List[str]],
        agent_mapping: Dict[str, List[str]]
    ):
        """도메인 Intent 등록"""
        pass
```

#### 4. `core/foundation/registry/tool_registry.py`

```python
"""
Tool 플러그인 레지스트리

도메인별 Tool 동적 등록 및 관리
"""

class ToolRegistry:
    """
    Tool 동적 등록 시스템

    Features:
    - 도메인별 Tool 격리
    - Function Calling 스키마 관리
    - 실행 추상화
    """

    def register_tool(
        self,
        tool_name: str,
        tool_instance: BaseTool,
        domain: str
    ):
        """Tool 등록"""
        pass

    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Tool 실행"""
        pass
```

### Plugin 레이어

#### 5. `plugins/real_estate/domain_config.yaml`

```yaml
# 부동산 도메인 설정

domain:
  name: "real_estate"
  display_name: "부동산 전문 상담"
  version: "1.0.0"
  description: "한국 부동산 전세/매매 전문 AI 상담 서비스"

intents:
  LEGAL_INQUIRY:
    name: "법률해설"
    patterns:
      - "법"
      - "계약"
      - "전세"
    suggested_agents:
      - "search_team"
    llm_prompt: "cognitive/legal_inquiry.txt"

  # ... (15개 Intent)

teams:
  search_team:
    type: "SearchExecutor"
    tools:
      - "legal_search"
      - "market_data"
    config:
      max_results: 10

  # ... (3개 Team)

tools:
  legal_search:
    module: "plugins.real_estate.tools.legal_search_tool"
    class: "LegalSearchTool"
    config:
      database: "faiss_legal_db"

  # ... (14개 Tool)
```

#### 6. `plugins/real_estate/intents.py`

```python
"""
부동산 도메인 Intent 정의
"""

from enum import Enum

class RealEstateIntent(Enum):
    """부동산 의도 타입"""
    TERM_DEFINITION = "용어설명"
    LEGAL_INQUIRY = "법률해설"
    LOAN_SEARCH = "대출상품검색"
    # ... (15개)

# Intent Patterns
INTENT_PATTERNS = {
    RealEstateIntent.LEGAL_INQUIRY: [
        "법", "계약", "전세", "임대", "보증금"
    ],
    # ...
}

# Agent Mapping
AGENT_MAPPING = {
    RealEstateIntent.LEGAL_INQUIRY: ["search_team"],
    # ...
}
```

#### 7. `plugins/real_estate/tools/legal_search_tool.py`

```python
"""
법률 검색 Tool
"""

from core.foundation.registry.tool_registry import BaseTool

class LegalSearchTool(BaseTool):
    """
    법률 검색 Tool

    Features:
    - FAISS 기반 Vector Search
    - Hybrid Search (Vector + Keyword)
    - Top-K 결과 반환
    """

    async def execute(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """법률 정보 검색"""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Function Calling 스키마"""
        return {
            "name": "legal_search",
            "description": "법률 관련 정보를 검색합니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5}
                }
            }
        }
```

### Application 레이어

#### 8. `application/api/chat_api.py`

```python
"""
WebSocket Chat API

Features:
- 실시간 채팅
- Progress Streaming
- HITL 지원
"""

from fastapi import WebSocket, APIRouter

router = APIRouter()

@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket 엔드포인트"""
    pass
```

#### 9. `application/models/chat.py`

```python
"""
Chat 데이터 모델
"""

from sqlalchemy import Column, String, Text, DateTime

class ChatMessage(Base):
    """채팅 메시지 모델"""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    role = Column(String)  # "user" or "assistant"
    content = Column(Text)
    created_at = Column(DateTime)
```

---

## 🔧 설정 파일

### `config/default.yaml`

```yaml
# 기본 설정

framework:
  name: "base_agent_framework"
  version: "1.0.0"

llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 2000

database:
  type: "postgresql"
  host: "${DB_HOST}"
  port: 5432
  name: "${DB_NAME}"

checkpointing:
  enabled: true
  backend: "postgresql"

memory:
  enabled: true
  tiers:
    short_term:
      sessions: 5
      mode: "full"
    mid_term:
      sessions: 5
      mode: "summary"
    long_term:
      sessions: 10
      mode: "summary"

plugins:
  auto_load: true
  default_domain: "real_estate"
  search_paths:
    - "plugins/"

logging:
  level: "INFO"
  format: "json"
```

---

## 📦 패키징

### `pyproject.toml`

```toml
[tool.poetry]
name = "base-agent-framework"
version = "1.0.0"
description = "Domain-agnostic AI Agent Framework based on LangGraph"
authors = ["Your Name <you@example.com>"]
license = "MIT"

[tool.poetry.dependencies]
python = "^3.11"
langgraph = "^0.6.0"
langchain = "^0.1.0"
fastapi = "^0.109.0"
uvicorn = "^0.27.0"
sqlalchemy = "^2.0.0"
psycopg2-binary = "^2.9.9"
pydantic = "^2.5.0"
pyyaml = "^6.0"
openai = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
black = "^23.12.0"
ruff = "^0.1.0"
mypy = "^1.7.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## 🚀 다음 단계

1. **Phase 1**: Core 레이어 구현
2. **Phase 2**: Plugin 시스템 구현
3. **Phase 3**: Real Estate 플러그인 마이그레이션
4. **Phase 4**: 문서화 및 예제 작성

---

**문서 버전**: 1.0
**최종 수정**: 2025-10-31
**작성자**: Claude Code
