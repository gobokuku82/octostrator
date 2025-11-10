# AI Multi-Agent System (Domain-Agnostic)

LangGraph 1.0 Supervisor Pattern을 사용한 **범용 멀티 에이전트 시스템**

> **Current State**: 모든 레이어가 도메인 독립적으로 범용화 완료 (Fitness, Medical, Legal, Education 등 모든 도메인 지원)

## 📋 Overview

도메인 독립적인 **범용 멀티 에이전트 프레임워크**입니다.
6개의 핵심 레이어가 모두 도메인 독립적으로 설계되어, 어떤 산업 분야(Fitness, Medical, Legal, Education 등)에서도 사용할 수 있는 확장 가능한 아키텍처를 제공합니다.

### System Generalization Status (6/6 Complete)

- ✅ **Supervisor Layer** - Domain-agnostic orchestration
- ✅ **Model Layer** - Generic Pydantic models
- ✅ **Cognitive Layer** - Generic AI agent framework
- ✅ **CRUD Layer** - Generic database operations
- ✅ **State Layer** - Generic state management
- ✅ **Tools Layer** - Generic tools registry

## 🏗️ Architecture

### 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                        │
│  - Supervisor (LangGraph)                                    │
│  - Agent Registry & Discovery                                │
│  - Execution Flow Control                                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    COGNITIVE LAYER                           │
│  - Specialist Agents (BaseAgent)                             │
│  - Tools Integration                                         │
│  - State Management                                          │
│  - LLM Integration                                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  - Generic Models (Pydantic)                                 │
│  - Generic CRUD Operations                                   │
│  - Database Session Management                               │
│  - Migration System (Alembic)                                │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
beta_v001/
├── backend/
│   ├── app/
│   │   └── octostrator/              # 멀티 에이전트 오케스트레이션 시스템
│   │       ├── supervisor/           # Supervisor Layer (도메인 독립적)
│   │       │   ├── __init__.py       # 범용 supervisor 그래프 (297 lines)
│   │       │   └── supervisor_flow_diagram.md
│   │       │
│   │       ├── models/               # Model Layer (도메인 독립적)
│   │       │   ├── __init__.py       # 범용 Pydantic 모델 진입점 (245 lines)
│   │       │   ├── base_models.py    # 기본 모델 (User, Organization 등)
│   │       │   ├── models_guide.md   # 모델 작성 가이드 (1000+ lines)
│   │       │   └── archive/          # 참고용 구현 예시
│   │       │       └── fitness/      # Fitness 도메인 예시
│   │       │
│   │       ├── execution_agents/     # Cognitive Layer (도메인 독립적)
│   │       │   └── base/
│   │       │       ├── base_agent.py          # 확장 가능한 기본 Agent 클래스
│   │       │       ├── agent_registry.py      # Agent 등록/관리
│   │       │       ├── checkpoint_strategy.py # 체크포인트 전략
│   │       │       └── dependency_resolver.py # Agent 의존성 해결
│   │       │
│   │       ├── tools/                # Tools Layer (도메인 독립적)
│   │       │   ├── __init__.py       # 범용 tools 레지스트리 (321 lines)
│   │       │   ├── TOOLS_GUIDE.md    # 도구 작성 가이드 (1046 lines, 4개 도메인 예시)
│   │       │   └── archive_fitness/  # 참고용 구현 예시 (Fitness 도메인, 62 tools)
│   │       │       ├── frontdesk_tools.py       # 문의/예약 관리
│   │       │       ├── assessor_tools.py        # 체력 평가/분석
│   │       │       ├── program_designer_tools.py # 프로그램 설계
│   │       │       ├── manager_tools.py          # 회원 관리
│   │       │       ├── marketing_tools.py        # 마케팅
│   │       │       ├── owner_assistant_tools.py  # 매출 분석
│   │       │       └── trainer_education_tools.py # 트레이너 교육
│   │       │
│   │       └── states/               # State Layer (도메인 독립적)
│   │           ├── __init__.py       # 범용 state 관리 (265 lines)
│   │           └── STATE_GUIDE.md    # State 작성 가이드 (1500+ lines)
│   │
│   └── database/                     # Data Layer (도메인 독립적)
│       ├── __init__.py               # 데이터베이스 패키지 진입점 (261 lines)
│       ├── session.py                # 비동기 세션 관리 (84 lines)
│       ├── utils.py                  # CRUD 헬퍼 함수 (350+ lines)
│       ├── CRUD_PATTERNS_GUIDE.md    # CRUD 패턴 가이드 (1800+ lines)
│       └── relation_db/              # Alembic 마이그레이션
│           ├── alembic.ini
│           ├── env.py
│           └── versions/
│
├── reports/                          # 프로젝트 문서 및 리포트
│   ├── TOOLS_LAYER_GENERALIZATION_COMPLETION_REPORT_251110.md
│   ├── STATE_SCHEMA_UPDATE_REPORT.md
│   ├── PHASE5_ALL_AGENTS_DB_INTEGRATION_PLAN.md
│   ├── PHASE5_FRONTDESK_DB_INTEGRATION_REPORT.md
│   └── FRONTDESK_DB_INTEGRATION_TEST_REPORT.md
│
├── .claude/
│   └── settings.local.json           # Claude Code 권한 설정
│
├── alembic.ini                       # Alembic 설정
├── pyproject.toml                    # 프로젝트 의존성
└── README.md                         # 이 파일
```

## 🔑 Key Files Description

### Core System Files

#### `backend/app/octostrator/supervisor/__init__.py` (297 lines)
**Supervisor Layer** - 도메인 독립적인 멀티 에이전트 오케스트레이션
- LangGraph 기반 supervisor 그래프
- Agent 등록 및 라우팅
- 실행 흐름 제어
- 체크포인트 관리

#### `backend/app/octostrator/models/__init__.py` (245 lines)
**Model Layer** - 범용 Pydantic 모델 시스템
- 도메인 독립적 기본 모델 (User, Organization, Session 등)
- 모델 작성 가이드 및 예시
- 4개 도메인 예시 (Fitness, Medical, Legal, Education)
- Fitness 도메인 참고 구현은 `archive/fitness/`에 보관

**Guide**: `backend/app/octostrator/models/models_guide.md` (1000+ lines)

#### `backend/app/octostrator/execution_agents/base/`
**Cognitive Layer** - 확장 가능한 Agent 프레임워크
- `base_agent.py`: BaseAgent 추상 클래스, 모든 agent의 기반
- `agent_registry.py`: Agent 등록/관리/동적 로딩
- `checkpoint_strategy.py`: 체크포인트 전략 (None, AfterEach, Manual)
- `dependency_resolver.py`: Agent 간 의존성 해결 및 실행 순서 결정

#### `backend/app/octostrator/tools/__init__.py` (321 lines)
**Tools Layer** - 범용 도구 레지스트리
- 도메인 독립적 tools registry (Dict 기반)
- 3가지 구현 패턴 제공:
  - Option A: Separate Tool Modules (복잡한 도메인)
  - Option B: Inline Tools in Agent Nodes (간단한 도메인)
  - Option C: LangChain Tool Decorators (고급)
- Fitness 도메인 참고 구현 62개는 `archive_fitness/`에 보관

**Guide**: `backend/app/octostrator/tools/TOOLS_GUIDE.md` (1046 lines, 4개 도메인 예시)

#### `backend/app/octostrator/states/__init__.py` (265 lines)
**State Layer** - 범용 상태 관리
- LangGraph TypedDict 기반 state 스키마
- 도메인 독립적 기본 state 구조
- 3가지 state 패턴:
  - Simple State (단순 대화)
  - Agent State (전문 작업)
  - Supervisor State (멀티 에이전트)

**Guide**: `backend/app/octostrator/states/STATE_GUIDE.md` (1500+ lines)

#### `backend/database/__init__.py` (261 lines)
**CRUD Layer** - 범용 데이터베이스 레이어
- 도메인 독립적 CRUD 인터페이스
- 비동기 세션 관리
- Generic CRUD 헬퍼 함수
- 5가지 CRUD 패턴:
  - Simple CRUD (기본 CRUD)
  - Transaction CRUD (트랜잭션)
  - Bulk CRUD (대량 작업)
  - Async CRUD (비동기)
  - Repository Pattern (복잡한 로직)

**Session Management**: `backend/database/session.py` (84 lines)
**CRUD Utilities**: `backend/database/utils.py` (350+ lines)
**Guide**: `backend/database/CRUD_PATTERNS_GUIDE.md` (1800+ lines)

### Archive Directories (참고용 구현 예시)

#### `backend/app/octostrator/tools/archive_fitness/` (7 files, 62 tools)
Fitness 도메인 구현 예시 - 새로운 도메인 개발 시 참고:
- `frontdesk_tools.py` (12 tools): 문의, 예약, 리드 관리
- `assessor_tools.py` (7 tools): 인바디 분석, 체력 평가
- `program_designer_tools.py` (10 tools): 운동 프로그램 설계
- `manager_tools.py` (8 tools): 출석, 갱신, 이탈 관리
- `marketing_tools.py` (9 tools): SNS, 이벤트 마케팅
- `owner_assistant_tools.py` (8 tools): 매출, ROI 분석
- `trainer_education_tools.py` (8 tools): 트레이너 교육 관리

#### `backend/app/octostrator/models/archive/fitness/`
Fitness 도메인 모델 예시 - 새로운 도메인 개발 시 참고:
- 회원, 트레이너, 프로그램, 인바디, 출석 등 Fitness 관련 모델

## 🚀 Quick Start

### Installation

```bash
# 의존성 설치
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY, DATABASE_URL 등을 설정
```

### Running the System

```bash
# 개발 서버 실행
uv run uvicorn backend.app.main:app --reload

# 데이터베이스 마이그레이션
python -m alembic upgrade head
```

### Testing

```bash
# 전체 테스트 실행
pytest

# 특정 모듈 테스트
pytest backend/test_frontdesk_integration.py
pytest backend/test_assessor_integration.py

# 사용자 확인 테스트
python backend/test_check_users.py
```

## 📚 Implementation Guides

### 1. Adding Domain-Specific Models
**Guide**: [backend/app/octostrator/models/models_guide.md](backend/app/octostrator/models/models_guide.md)

```python
# Example: Fitness Domain
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from backend.database.base import Base

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False)
```

### 2. Creating Domain-Specific Tools
**Guide**: [backend/app/octostrator/tools/TOOLS_GUIDE.md](backend/app/octostrator/tools/TOOLS_GUIDE.md)

**Option A: Separate Tool Module** (복잡한 도메인)
```python
# backend/app/octostrator/tools/fitness_tools.py
from backend.database.session import get_db_session
from typing import Dict

async def create_workout_program(
    user_id: int,
    program_name: str,
    exercises: List[Dict],
    duration_weeks: int
) -> Dict:
    """Create a new workout program for a user"""
    try:
        async with get_db_session() as db:
            program = WorkoutProgram(...)
            db.add(program)
            await db.commit()
            return {"status": "success", "program_id": program.id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# backend/app/octostrator/tools/__init__.py
from .fitness_tools import create_workout_program

TOOLS = {
    "create_workout_program": create_workout_program,
}
```

**Option B: Inline Tools** (간단한 도메인)
```python
from langchain.tools import tool

@tool
async def simple_tool(param: str) -> str:
    """Tool description"""
    return f"Result: {param}"

# Pass to agent
tools = [simple_tool]
agent = BaseAgent(tools=tools, ...)
```

### 3. Writing Domain-Specific CRUD
**Guide**: [backend/database/CRUD_PATTERNS_GUIDE.md](backend/database/CRUD_PATTERNS_GUIDE.md)

```python
# backend/database/fitness_crud.py
from .utils import create_record, get_by_id, update_record
from backend.app.octostrator.models.fitness import Member

async def create_member(db, member_data: dict):
    return await create_record(db, Member, member_data)

async def get_member(db, member_id: int):
    return await get_by_id(db, Member, member_id)
```

### 4. Defining Domain-Specific States
**Guide**: [backend/app/octostrator/states/STATE_GUIDE.md](backend/app/octostrator/states/STATE_GUIDE.md)

```python
from typing import TypedDict, Optional

class FitnessAssessmentState(TypedDict, total=False):
    user_id: int
    member_name: str
    inbody_data: dict
    fitness_level: str
    recommendations: list
    next_action: str
```

### 5. Creating Specialist Agents
**Based on**: `backend/app/octostrator/execution_agents/base/base_agent.py`

```python
from backend.app.octostrator.execution_agents.base import BaseAgent

class FitnessAssessorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="fitness_assessor",
            description="체력 평가 및 분석 전문 Agent",
            tools=["analyze_inbody", "calculate_fitness_score"],
            dependencies=[]
        )

    async def execute(self, state: dict) -> dict:
        # Agent 로직 구현
        pass
```

## 🔧 Configuration

### Database Configuration
```python
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
```

### LLM Configuration
```python
# .env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4
```

### Checkpoint Configuration
```python
from backend.app.octostrator.execution_agents.base import CheckpointMode

# No checkpoints
agent = BaseAgent(checkpoint_mode=CheckpointMode.NONE)

# Checkpoint after each step
agent = BaseAgent(checkpoint_mode=CheckpointMode.AFTER_EACH)

# Manual checkpoints
agent = BaseAgent(checkpoint_mode=CheckpointMode.MANUAL)
```

## 🏛️ Architecture Principles

### 1. Domain-Agnostic Design
모든 레이어는 특정 도메인(PT, 의료, 법률 등)에 종속되지 않도록 설계되었습니다.

### 2. Clean Slate + Comprehensive Guide
각 레이어는 빈 레지스트리/스키마로 시작하며, 상세한 가이드 문서를 제공합니다.

### 3. LangGraph Philosophy
- **Stateless**: 함수는 상태를 저장하지 않음
- **Simple**: Dict 기반의 단순한 구조
- **Composable**: 작은 단위로 조합 가능

### 4. Archive Strategy
참고용 도메인 구현 예시는 archive 디렉토리에 보관하여 새로운 도메인 개발 시 참고할 수 있도록 합니다.

### 5. Multiple Patterns
각 레이어는 다양한 구현 패턴을 제공하여 도메인의 복잡도에 따라 선택 가능합니다.

## 📖 Technology Stack

- **LangChain 1.0**: LLM 애플리케이션 프레임워크
- **LangGraph 1.0**: 상태 기반 멀티 에이전트 오케스트레이션
- **FastAPI**: 비동기 웹 프레임워크
- **PostgreSQL**: 관계형 데이터베이스
- **SQLAlchemy 2.0**: ORM (Async 지원)
- **Alembic**: 데이터베이스 마이그레이션
- **Pydantic**: 데이터 검증 및 모델링
- **FAISS/ChromaDB**: 벡터 데이터베이스 (RAG)

## 📋 Reports & Documentation

### Generalization Reports
- [Tools Layer Generalization Report](reports/TOOLS_LAYER_GENERALIZATION_COMPLETION_REPORT_251110.md)
- [State Schema Update Report](reports/STATE_SCHEMA_UPDATE_REPORT.md)
- [Phase 5 All Agents DB Integration Plan](reports/PHASE5_ALL_AGENTS_DB_INTEGRATION_PLAN.md)
- [Frontdesk DB Integration Report](reports/PHASE5_FRONTDESK_DB_INTEGRATION_REPORT.md)

### Testing Reports
- [Frontdesk DB Integration Test Report](reports/FRONTDESK_DB_INTEGRATION_TEST_REPORT.md)

### Implementation Guides
- [Models Guide](backend/app/octostrator/models/models_guide.md) - 1000+ lines, 4 domains
- [Tools Guide](backend/app/octostrator/tools/TOOLS_GUIDE.md) - 1046 lines, 4 domains
- [State Guide](backend/app/octostrator/states/STATE_GUIDE.md) - 1500+ lines
- [CRUD Patterns Guide](backend/database/CRUD_PATTERNS_GUIDE.md) - 1800+ lines

## 🤝 Contributing

새로운 도메인을 추가하거나 기능을 확장하려면:

1. 해당 레이어의 가이드 문서를 읽어보세요 (TOOLS_GUIDE.md, STATE_GUIDE.md 등)
2. Archive 디렉토리의 참고 구현 예시를 참고하세요
3. 가이드에서 제공하는 패턴을 따라 구현하세요
4. 테스트를 작성하고 실행하세요

## 📞 Support

- Documentation: See `backend/app/octostrator/*/` for comprehensive guides
- Issues: Report issues in project repository
- Architecture Questions: See reports/ directory

---

**Author**: AI Multi-Agent Framework Team
**Last Updated**: 2025-11-10
**Version**: 2.0 (Domain-Agnostic Framework - All 6 Layers Complete)
