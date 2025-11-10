# 올바른 프로젝트 구조 분석
**작성일**: 2025-11-10
**중요**: 이전 보고서의 구조 분석이 잘못되었습니다. 이 문서가 정확한 구조입니다.

---

## 🏢 전체 애플리케이션 구조

### 핵심 이해
- **메인 애플리케이션**: FastAPI 기반 PT 관리 시스템
- **Octostrator (챗봇)**: 애플리케이션의 **일부 기능** (전체가 아님)
- **Database 레이어**: 별도 분리된 데이터 접근 계층

---

## 📁 올바른 디렉토리 구조

```
backend/
├── app/                                    # ⭐ 메인 FastAPI 애플리케이션
│   ├── main.py                             # FastAPI 엔트리포인트
│   │                                       # - Octostrator Graph 초기화
│   │                                       # - API 라우터 등록
│   │                                       # - /chat 엔드포인트
│   │
│   ├── api/                                # REST API 엔드포인트
│   │   ├── websocket.py                    # WebSocket 실시간 스트리밍
│   │   ├── sessions.py                     # Session Management API
│   │   ├── todos.py                        # Todo Management API
│   │   └── agents.py                       # Agent Management API
│   │
│   ├── models/                             # ⭐ ORM 모델 (실제 위치)
│   │   ├── __init__.py                     # Base, engine export
│   │   ├── base.py                         # SQLAlchemy Base
│   │   ├── core.py                         # User 모델
│   │   ├── frontdesk.py                    # Lead, Inquiry, Appointment
│   │   ├── assessor.py                     # InBodyData, PostureAnalysis
│   │   ├── program_designer.py             # Program, WorkoutRoutine, MealLog
│   │   ├── manager.py                      # Attendance, ChurnRisk, Schedule
│   │   ├── marketing.py                    # SocialMediaPost, Event
│   │   ├── owner.py                        # Revenue, MemberProgress
│   │   ├── trainer.py                      # TrainerSkill
│   │   └── shared.py                       # ExerciseDB, Bookmark
│   │                                       # ⭐ 총 11개 파일, 23개 테이블
│   │
│   ├── octostrator/                        # ⭐ 챗봇 (일부 기능)
│   │   ├── supervisors/                    # 3계층 슈퍼바이저
│   │   │   ├── octostrator/                # 메인 오케스트레이터
│   │   │   ├── cognitive/                  # Layer 1: 의도 파악
│   │   │   ├── todo/                       # Layer 1.5: Todo 관리
│   │   │   ├── execute/                    # Layer 3: Agent 실행
│   │   │   └── response/                   # Layer 4: 응답 생성
│   │   ├── agents/                         # 7개 Worker Agent
│   │   │   ├── base/                       # BaseAgent 클래스
│   │   │   ├── frontdesk/                  # 신규 회원 응대
│   │   │   ├── assessor/                   # 체형 평가
│   │   │   ├── nutrition/                  # 식단 관리
│   │   │   ├── program_designer/           # 운동 프로그램
│   │   │   ├── manager/                    # 회원 관리
│   │   │   ├── marketing/                  # 마케팅
│   │   │   └── owner_assistant/            # 원장 보조
│   │   ├── states/                         # State 관리
│   │   ├── contexts/                       # Context API
│   │   └── tools/                          # 공유 도구
│   │
│   ├── config/                             # 애플리케이션 설정
│   ├── schemas/                            # Pydantic 스키마
│   ├── core/                               # 핵심 로직
│   ├── utils/                              # 유틸리티
│   ├── db/                                 # (비어있음 - 사용 안 함)
│   └── registry/                           # 레지스트리
│
├── database/                               # ⭐ 데이터베이스 레이어 (별도)
│   ├── session.py                          # PostgreSQL 비동기 세션 관리
│   ├── utils.py                            # JSON/DateTime 변환 유틸
│   ├── assessor_crud.py                    # Assessor CRUD (완성)
│   ├── frontdesk_crud.py                   # Frontdesk CRUD (완성)
│   ├── create_all_mocks.py                 # Mock 데이터 생성
│   ├── verify_data.py                      # 데이터 검증
│   │
│   ├── relation_db/                        # 관계형 DB (레거시?)
│   │   ├── models.py                       # (사용 여부 불명)
│   │   ├── session.py                      # SQLite 세션 (레거시)
│   │   └── ...
│   │
│   ├── vector_db/                          # 벡터 DB (FAISS)
│   │   ├── exercise_index/
│   │   ├── member_index/
│   │   └── faiss_manager.py
│   │
│   └── unstructured_db/                    # 비정형 데이터
│       ├── documents/
│       ├── images/
│       └── videos/
│
├── alembic/                                # ⭐ DB 마이그레이션
│   ├── alembic.ini                         # Alembic 설정
│   ├── env.py                              # 마이그레이션 환경
│   └── versions/                           # 마이그레이션 파일
│       ├── c8dd4d782b94_initial.py         # 초기 마이그레이션 (23개 테이블)
│       └── d9e84f691c25_nutrition.py       # Nutrition 테이블 추가
│
└── tests/                                  # 테스트 파일
```

---

## 🔑 핵심 경로 정리

### 1. ORM 모델 정의
**올바른 경로**: `backend/app/models/`

```python
# backend/app/models/__init__.py
from .core import User
from .frontdesk import Lead, Inquiry, Appointment
from .assessor import InBodyData, PostureAnalysis
# ...

# ⭐ 여기가 실제 ORM 모델 위치
```

**잘못된 경로** (사용 안 함):
- `backend/database/relation_db/models.py` ❌ (레거시?)

---

### 2. Database CRUD 레이어
**올바른 경로**: `backend/database/`

```python
# backend/database/frontdesk_crud.py
from app.models import Lead, Inquiry, Appointment  # ⭐ app/models에서 import

async def create_lead(session: AsyncSession, lead_data: Dict) -> Optional[Lead]:
    lead = Lead(...)  # app/models.frontdesk.Lead 사용
    ...
```

**구조**:
```
backend/database/
├── session.py              # 세션 관리
├── assessor_crud.py        # Assessor CRUD
├── frontdesk_crud.py       # Frontdesk CRUD
└── utils.py                # 변환 유틸리티
```

---

### 3. Octostrator (챗봇)
**올바른 경로**: `backend/app/octostrator/`

**역할**: FastAPI 애플리케이션의 **일부 기능** (전체가 아님)
- `/chat` 엔드포인트에서 호출됨
- 7개 Agent를 통한 업무 자동화
- WebSocket을 통한 실시간 스트리밍

```python
# backend/app/main.py
from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph

supervisor_graph = build_octostrator_graph()

@app.post("/chat")
async def chat(request: ChatRequest):
    result = await supervisor_graph.ainvoke({
        "user_query": request.message,
        ...
    })
```

---

### 4. FastAPI 엔드포인트
**경로**: `backend/app/api/`

```
backend/app/api/
├── websocket.py        # WebSocket: /ws/chat
├── sessions.py         # Session: /api/sessions
├── todos.py            # Todo: /api/todos
└── agents.py           # Agent: /api/agents
```

---

## 🔄 데이터 흐름

### 전체 애플리케이션 흐름
```
1. 사용자 요청
   ↓
2. FastAPI Endpoint (/chat, /ws/chat)
   backend/app/main.py
   backend/app/api/websocket.py
   ↓
3. Octostrator Graph 실행 (챗봇 기능)
   backend/app/octostrator/supervisors/octostrator/
   ↓
4. Cognitive Layer (의도 파악)
   backend/app/octostrator/supervisors/cognitive/
   ↓
5. Execute Layer (Agent 실행)
   backend/app/octostrator/supervisors/execute/
   ├─ Agent 선택 (agent_registry)
   └─ Agent 실행
      backend/app/octostrator/agents/{agent_name}/
      ↓
6. Agent Tools (DB 접근)
   backend/app/octostrator/agents/{agent_name}/{agent_name}_tools.py
   ↓
7. Database CRUD
   backend/database/{agent_name}_crud.py
   ├─ Session 생성 (backend/database/session.py)
   └─ ORM 모델 사용 (backend/app/models/)
      ↓
8. PostgreSQL Database
   ↓
9. Response Layer (응답 생성)
   backend/app/octostrator/supervisors/response/
   ↓
10. FastAPI 응답
```

---

## 📊 계층 구조

### Layer 0: 인프라
```
PostgreSQL Database
└── Alembic Migrations (backend/alembic/)
```

### Layer 1: 데이터 모델
```
ORM Models (backend/app/models/)
├── core.py (User)
├── frontdesk.py (Lead, Inquiry, Appointment)
├── assessor.py (InBodyData, PostureAnalysis)
└── ... (11개 파일, 23개 테이블)
```

### Layer 2: 데이터 접근
```
Database CRUD (backend/database/)
├── session.py (세션 관리)
├── frontdesk_crud.py
├── assessor_crud.py
└── utils.py
```

### Layer 3: 비즈니스 로직 (Octostrator)
```
Chatbot Logic (backend/app/octostrator/)
├── Supervisors (3계층)
│   ├── Cognitive (의도 파악)
│   ├── Execute (Agent 실행)
│   └── Response (응답 생성)
└── Agents (7개)
    ├── Frontdesk
    ├── Assessor
    ├── Nutrition
    └── ... (4개 더)
```

### Layer 4: API 인터페이스
```
FastAPI Endpoints (backend/app/)
├── main.py (/chat)
└── api/
    ├── websocket.py (/ws/chat)
    ├── sessions.py (/api/sessions)
    ├── todos.py (/api/todos)
    └── agents.py (/api/agents)
```

---

## 🚨 이전 보고서의 오류

### 잘못 표시한 내용 (수정 전)
```
❌ backend/database/relation_db/models.py (23개 테이블)
   → 실제로는 backend/app/models/ (11개 파일)

❌ Database 레이어 = 독립적
   → 실제로는 FastAPI 애플리케이션의 일부

❌ Octostrator = 전체 시스템
   → 실제로는 챗봇 기능 (일부)
```

### 올바른 이해
```
✅ ORM 모델: backend/app/models/ (11개 파일, 23개 테이블)
✅ CRUD 레이어: backend/database/ (별도 레이어)
✅ 챗봇: backend/app/octostrator/ (일부 기능)
✅ 메인: backend/app/main.py (FastAPI 앱)
```

---

## 🎯 재설계 시 영향 범위

### 삭제 대상 (Octostrator만)
```
backend/app/octostrator/
├── agents/                  ❌ 전체 삭제 (base 제외)
├── supervisors/cognitive/   ❌ 재구현
└── supervisors/todo/        ❌ 재구현
```

### 유지 대상 (건드리지 않음)
```
backend/app/
├── models/                  ✅ 유지 (ORM 모델)
├── api/                     ✅ 유지 (REST API)
├── main.py                  ✅ 유지 (엔트리포인트)
├── config/                  ✅ 유지
└── schemas/                 ✅ 유지

backend/database/
├── session.py               ✅ 유지 (타입 힌트만 수정)
├── frontdesk_crud.py        ✅ 유지
├── assessor_crud.py         ✅ 유지
└── utils.py                 ✅ 유지

backend/alembic/             ✅ 유지 (마이그레이션)

backend/app/octostrator/
├── supervisors/
│   ├── octostrator/         ✅ 유지 (메인 그래프)
│   ├── execute/             ✅ 유지 (Agent 실행)
│   └── response/            ✅ 유지 (응답 생성)
├── states/                  ✅ 유지 (State 관리)
└── contexts/                ✅ 유지 (Context API)
```

---

## 📝 수정된 Import 경로 규칙

### 올바른 Import
```python
# ORM 모델 import
from backend.app.models import Lead, Inquiry, Appointment
from backend.app.models.frontdesk import Lead
from backend.app.models.assessor import InBodyData, PostureAnalysis

# CRUD import
from backend.database import frontdesk_crud, assessor_crud
from backend.database.session import get_db_session, get_db
from backend.database.utils import parse_json_list, datetime_to_str

# Agent import
from backend.app.octostrator.agents.frontdesk.frontdesk_agent import FrontdeskAgent
from backend.app.octostrator.states.frontdesk_state import FrontdeskState

# Config import
from backend.app.config.system import config
```

### 잘못된 Import (절대 사용 금지)
```python
# ❌ 상대 경로
from database import frontdesk_crud
from models import Lead

# ❌ 잘못된 경로
from backend.database.relation_db.models import Lead  # 레거시
from app.models import Lead  # backend. 누락
```

---

## 🔍 주요 파일 경로 요약표

| 항목 | 올바른 경로 | 설명 |
|------|------------|------|
| **ORM 모델** | `backend/app/models/` | 11개 파일, 23개 테이블 |
| **CRUD 함수** | `backend/database/` | frontdesk_crud, assessor_crud |
| **세션 관리** | `backend/database/session.py` | PostgreSQL 비동기 세션 |
| **Agent 구현** | `backend/app/octostrator/agents/` | 7개 에이전트 |
| **Supervisor** | `backend/app/octostrator/supervisors/` | 3계층 슈퍼바이저 |
| **State 관리** | `backend/app/octostrator/states/` | Annotated Reducers |
| **API 엔드포인트** | `backend/app/api/` | WebSocket, REST |
| **메인 엔트리** | `backend/app/main.py` | FastAPI 앱 |
| **마이그레이션** | `backend/alembic/` | Alembic |

---

## ✅ 다음 단계

1. **기존 재설계 계획서 수정** ✅ (이 문서로 대체)
2. **Agent 재설계 시작** (올바른 경로 기반)
3. **Import 경로 컨벤션 확정** (위 규칙 따름)

---

**작성자**: Claude Code
**최종 업데이트**: 2025-11-10
**중요도**: ⭐⭐⭐⭐⭐ (이전 보고서 무시, 이 문서가 정확함)
