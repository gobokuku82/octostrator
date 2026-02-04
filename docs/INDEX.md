# Dream Agent 문서 인덱스

> 마지막 업데이트: 2026-02-03
> 문서 버전: 1.2.0

---

## 기존 상세 문서 (README/)

> **중요**: `README/` 폴더에 상세한 개발 문서가 이미 존재합니다.

| 문서 | 설명 |
|------|------|
| [README/00_INDEX.md](../README/00_INDEX.md) | 전체 문서 색인 |
| [README/01_ARCHITECTURE.md](../README/01_ARCHITECTURE.md) | 전체 아키텍처 |
| [README/02_BACKEND.md](../README/02_BACKEND.md) | FastAPI 백엔드 & WebSocket |
| [README/03_AGENT_LAYERS.md](../README/03_AGENT_LAYERS.md) | **4-Layer 상세 설명** |
| [README/04_FRONTEND.md](../README/04_FRONTEND.md) | HTML 대시보드 |
| [README/05_DATA_STRUCTURE.md](../README/05_DATA_STRUCTURE.md) | 데이터 구조 |
| [README/06_QUICKSTART.md](../README/06_QUICKSTART.md) | 빠른 시작 가이드 |

---

## 문서 상태 범례

| 아이콘 | 의미 |
|--------|------|
| ✅ | 구현 완료 / 검증됨 |
| ⚠️ | 부분 구현 / 검토 필요 |
| ❌ | 미구현 |
| 🔧 | 사용자 결정 필요 |

---

## docs/ 문서 목록

### 1. [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) ✅
**시스템 아키텍처 문서**

| 섹션 | 내용 | 상태 |
|------|------|------|
| 4-Layer 아키텍처 | Cognitive → Planning → Execution → Response | ✅ |
| Executor 매핑 | DataExecutor, InsightExecutor, ContentExecutor, OpsExecutor | ✅ |
| 이중 Intent 시스템 | Legacy dict vs Pydantic 공존 | ⚠️ |
| 스키마 사용 현황 | I/O 스키마 문서화 목적 (런타임 미사용) | ⚠️ |
| 디렉토리 구조 | 전체 파일 구조 (179개 Python 파일) | ✅ |
| Domain Agents | 17개 구현, 1개 미구현 | ⚠️ |

### 2. [INTERFACE_CONTRACT.md](./INTERFACE_CONTRACT.md) ✅
**인터페이스 계약 문서**

| 섹션 | 내용 | 상태 |
|------|------|------|
| Layer I/O 스키마 | Cognitive, Planning, Execution, Response (문서화 목적) | ⚠️ |
| 스키마 사용 현황 알림 | 런타임 미사용 명시, 이중 Intent 시스템 설명 | ✅ |
| 데이터 모델 | Intent, TodoItem, Plan, ExecutionResult | ✅ |
| REST API | /api/agent/*, /health | ✅ |
| WebSocket API | /ws/* 실시간 업데이트 | ✅ |
| 에러 코드 | 표준 에러 코드 체계 | 🔧 |

### 3. [PLANNING.md](./PLANNING.md) ✅
**프로젝트 기획서**

| 섹션 | 내용 | 상태 |
|------|------|------|
| 기능 명세 | 레이어별 기능 현황 | ✅ |
| 도구 현황 | 18개 YAML, 17개 Agent | ✅ |
| 마일스톤 | Phase 0.5-4 대부분 완료 | ✅ |
| 보안 요구사항 | 인증, 암호화 등 | 🔧 |

### 4. [TOOL_SPECIFICATION.md](./TOOL_SPECIFICATION.md) ✅
**도구 스펙 문서**

| 섹션 | 내용 | 상태 |
|------|------|------|
| YAML 형식 | parameters 배열 형식 | ✅ |
| 도구 목록 | 18개 도구 정의 | ✅ |
| 의존성 그래프 | 도구 간 의존 관계 | ✅ |
| Agent 매핑 | 17개 구현, 1개 미구현 | ⚠️ |

### 5. [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) ⚠️
**개발 가이드**

| 섹션 | 내용 | 상태 |
|------|------|------|
| 환경 설정 | Python, 의존성, 환경변수 | ✅ |
| 코딩 컨벤션 | 스타일, 명명 규칙 | ✅ |
| 테스트 가이드 | pytest 사용법 | ⚠️ |
| 배포 체크리스트 | 배포 전 확인 사항 | 🔧 |

---

## 빠른 참조

### 서버 실행

```bash
cd backend
uvicorn api.main:app --reload --port 8000
# http://localhost:8000
```

### 핵심 경로

```
backend/
├── api/main.py            # FastAPI 엔트리포인트
└── app/dream_agent/
    ├── cognitive/         # Layer 1: 의도 파악
    ├── planning/          # Layer 2: 작업 계획
    ├── execution/         # Layer 3: 실행
    │   ├── *_executor.py  # 4개 Executor
    │   └── domain/        # 18개 Domain Agent
    ├── response/          # Layer 4: 응답 생성
    ├── orchestrator/      # LangGraph
    ├── tools/definitions/ # YAML (18개)
    ├── models/            # Pydantic 모델
    ├── schemas/           # I/O 스키마
    └── workflow_manager/  # 워크플로우 관리
```

### 주요 클래스

| 클래스 | 위치 | 용도 |
|--------|------|------|
| `Intent` | models/intent.py | 의도 분류 결과 |
| `TodoItem` | models/todo.py | 실행 작업 단위 |
| `Plan` | models/plan.py | 실행 계획 |
| `ExecutionResult` | models/execution.py | 실행 결과 |
| `BaseDomainAgent` | execution/domain/base_agent.py | Agent 기본 클래스 |
| `ToolSpec` | models/tool.py | YAML 도구 스펙 |

### Workflow Manager 구조

```
workflow_manager/
├── planning_manager/     # 계획 관리
│   ├── plan_manager.py
│   ├── execution_graph_builder.py
│   ├── resource_planner.py
│   └── sync_manager.py
├── todo_manager/         # Todo 관리
│   ├── todo_manager.py
│   ├── todo_creator.py
│   ├── todo_updater.py
│   ├── todo_store.py
│   └── todo_failure_recovery.py
├── hitl_manager/         # Human-in-the-Loop
│   ├── decision_manager.py
│   ├── plan_editor.py
│   └── nl_plan_modifier.py
├── feedback_manager/     # 피드백 관리
│   └── feedback_manager.py
└── approval_manager.py   # 승인 관리
```

---

## 🔧 사용자 결정 필요 항목

### 즉시 필요

| 항목 | 현재 | 옵션 |
|------|------|------|
| **inventory_agent** | 유일하게 미구현 | 구현 / YAML 제거 |
| **sales_agent 이름** | YAML↔Agent 불일치 | 통일 필요 |
| **에러 코드 체계** | 미정의 | 표준 코드 적용 |

### 기술 결정

| 항목 | 현재 | 옵션 |
|------|------|------|
| 세션 저장소 | In-memory | Redis / PostgreSQL |
| 테스트 커버리지 | 미측정 | 목표 설정 |
| CI/CD | 없음 | GitHub Actions |
| 인증 시스템 | 없음 | JWT / OAuth |
| frontend/ | 비어있음 | React 개발 / 제거 |

---

## 다음 단계

### 즉시

1. `inventory_agent` 구현 또는 YAML 제거
2. `sales_agent` ↔ `sales_material_generator.py` 이름 통일
3. 에러 코드 체계 확정

### 중기

1. CI/CD 파이프라인 구축
2. 테스트 커버리지 측정 및 목표 설정
3. Redis 캐시 도입

### 장기

1. 운영 환경 배포
2. 모니터링 시스템
3. 보안 강화

---

## 문서 기여

```bash
# 커밋 메시지 형식
docs(<문서명>): <변경 내용>

# 예시
docs(PLANNING): inventory_agent 구현 완료 표시
docs(INDEX): 문서 버전 업데이트
```
