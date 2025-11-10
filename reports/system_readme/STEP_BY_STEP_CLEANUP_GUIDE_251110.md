# Agent 삭제 작업 가이드
**작성일**: 2025-11-10
**목표**: 안전하게 기존 Agent 삭제 후 재설계 준비

---

## ⚠️ 시작하기 전에

### 1. Git 커밋 상태 확인
```bash
cd C:\kdy\Projects\AI_PTmanager\beta_v001
git status
```

**현재 상태**:
- Staged: `assessor_tools.py`, `frontdesk_crud.py`, `assessor_crud.py`, 등
- Modified: `frontdesk_tools.py`, `frontdesk_state.py`, 등
- Untracked: 테스트 파일들

### 2. 백업 생성 (선택)
기존 작업을 보관하고 싶다면:
```bash
# 백업 디렉토리 생성
mkdir -p C:\kdy\Projects\AI_PTmanager\beta_v001\backup\agents_backup_251110

# Agent 파일 백업
xcopy "C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\agents" ^
      "C:\kdy\Projects\AI_PTmanager\beta_v001\backup\agents_backup_251110\agents" /E /I /Y

# Supervisor 파일 백업
xcopy "C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\supervisors\cognitive" ^
      "C:\kdy\Projects\AI_PTmanager\beta_v001\backup\agents_backup_251110\cognitive" /E /I /Y

xcopy "C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\supervisors\todo" ^
      "C:\kdy\Projects\AI_PTmanager\beta_v001\backup\agents_backup_251110\todo" /E /I /Y
```

---

## 🗑️ Step 1: Agent 파일 삭제

### 삭제할 파일 목록

#### 1. Frontdesk Agent (버그 多)
```bash
# 삭제할 파일들
backend/app/octostrator/agents/frontdesk/
├── frontdesk_agent.py           ❌ 삭제
├── frontdesk_graph.py           ❌ 삭제
├── frontdesk_nodes.py           ❌ 삭제 (버그 많음)
├── frontdesk_tools.py           ❌ 삭제 (버그 많음)
├── frontdesk_prompts.py         ❌ 삭제
└── __init__.py                  ❌ 삭제 (재작성)
```

**삭제 명령**:
```bash
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\agents\frontdesk
del /Q *.py
```

#### 2. Assessor Agent (TODO만)
```bash
# 삭제할 파일들
backend/app/octostrator/agents/assessor/
├── assessor_agent.py            ❌ 삭제
├── assessor_graph.py            ❌ 삭제
├── assessor_nodes.py            ❌ 삭제 (TODO만)
├── assessor_tools.py            ❌ 삭제
└── __init__.py                  ❌ 삭제 (재작성)
```

**삭제 명령**:
```bash
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\agents\assessor
del /Q *.py
```

#### 3. 나머지 5개 Agent (미완성/TODO)
```bash
# 삭제 대상
backend/app/octostrator/agents/
├── nutrition/                   ❌ 전체 삭제
├── program_designer/            ❌ 전체 삭제
├── manager/                     ❌ 전체 삭제
├── marketing/                   ❌ 전체 삭제
└── owner_assistant/             ❌ 전체 삭제
```

**삭제 명령**:
```bash
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\agents

# 각 디렉토리 내 Python 파일만 삭제 (디렉토리는 유지)
cd nutrition && del /Q *.py && cd ..
cd program_designer && del /Q *.py && cd ..
cd manager && del /Q *.py && cd ..
cd marketing && del /Q *.py && cd ..
cd owner_assistant && del /Q *.py && cd ..
```

**또는 디렉토리까지 전체 삭제**:
```bash
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\agents
rmdir /S /Q nutrition
rmdir /S /Q program_designer
rmdir /S /Q manager
rmdir /S /Q marketing
rmdir /S /Q owner_assistant
rmdir /S /Q trainer_education
```

#### 4. Cognitive Layer (TODO만)
```bash
# 삭제할 파일들
backend/app/octostrator/supervisors/cognitive/
├── cognitive_graph.py           ❌ 삭제
├── cognitive_nodes.py           ❌ 삭제 (TODO만)
├── cognitive_helpers.py         ❌ 삭제
├── cognitive_prompts.py         ❌ 삭제
└── __init__.py                  ❌ 삭제 (재작성)
```

**삭제 명령**:
```bash
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\supervisors\cognitive
del /Q *.py
```

#### 5. Todo Manager (TODO만)
```bash
# 삭제할 파일들
backend/app/octostrator/supervisors/todo/
├── todo_manager.py              ❌ 삭제
└── __init__.py                  ❌ 삭제 (재작성)
```

**삭제 명령**:
```bash
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\supervisors\todo
del /Q *.py
```

---

## ✅ 유지할 파일 (절대 삭제 금지)

### 1. Agent Base 클래스
```
backend/app/octostrator/agents/base/
├── base_agent.py                ✅ 유지
├── agent_registry.py            ✅ 유지
├── capabilities.py              ✅ 유지
├── checkpoint_strategy.py       ✅ 유지
├── dependency_resolver.py       ✅ 유지
└── __init__.py                  ✅ 유지
```

### 2. Supervisor Core
```
backend/app/octostrator/supervisors/
├── octostrator/                 ✅ 유지 (전체)
│   ├── octostrator_graph.py
│   ├── octostrator_nodes.py
│   └── ...
├── execute/                     ✅ 유지 (전체)
│   ├── execute_graph.py
│   ├── execute_nodes.py
│   └── ...
└── response/                    ✅ 유지 (전체)
    ├── response_graph.py
    ├── response_nodes.py
    └── ...
```

### 3. States
```
backend/app/octostrator/states/
├── base.py                      ✅ 유지
├── octostrator_state.py         ✅ 유지
├── reducers.py                  ✅ 유지
├── frontdesk_state.py           ⚠️ 재정리 (삭제 안 함)
├── assessor_state.py            ⚠️ 재정리 (삭제 안 함)
└── ... (나머지 State 파일들)   ⚠️ 재정리
```

### 4. Contexts
```
backend/app/octostrator/contexts/
└── app_context.py               ✅ 유지
```

### 5. Database 레이어 (전체 유지)
```
backend/database/
├── session.py                   ✅ 유지 (타입 힌트만 수정)
├── frontdesk_crud.py            ✅ 유지
├── assessor_crud.py             ✅ 유지
├── utils.py                     ✅ 유지
└── ...
```

### 6. ORM Models (전체 유지)
```
backend/app/models/              ✅ 유지 (전체)
```

---

## 📝 Step 2: 필수 수정 사항

### 1. Database session.py 타입 힌트 수정
**파일**: `backend/database/session.py`

**수정 전**:
```python
async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

**수정 후**:
```python
from typing import AsyncGenerator

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### 2. agents/__init__.py 초기화
**파일**: `backend/app/octostrator/agents/__init__.py`

**새로 작성**:
```python
"""
Octostrator Agents Package

Agent Registry will be populated as agents are implemented.
"""

# Agent Registry (빈 상태로 시작)
agent_registry = {}

__all__ = ["agent_registry"]
```

---

## 🎯 Step 3: 삭제 후 상태 확인

### 확인 체크리스트
```bash
# 1. Agent 디렉토리 확인
ls C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\agents\

# 예상 결과:
# base/          ✅ (유지됨)
# frontdesk/     (비어있거나 삭제됨)
# assessor/      (비어있거나 삭제됨)
# ...

# 2. Supervisor 디렉토리 확인
ls C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\supervisors\

# 예상 결과:
# octostrator/   ✅ (유지됨)
# execute/       ✅ (유지됨)
# response/      ✅ (유지됨)
# cognitive/     (비어있음)
# todo/          (비어있음)

# 3. Database 레이어 확인
ls C:\kdy\Projects\AI_PTmanager\beta_v001\backend\database\

# 예상 결과:
# session.py           ✅
# frontdesk_crud.py    ✅
# assessor_crud.py     ✅
# utils.py             ✅

# 4. ORM Models 확인
ls C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\models\

# 예상 결과:
# __init__.py    ✅
# core.py        ✅
# frontdesk.py   ✅
# assessor.py    ✅
# ... (11개 파일 모두 존재)
```

---

## 🚀 Step 4: 다음 단계 준비

### 삭제 완료 후 할 일

#### 1. 코딩 컨벤션 문서 작성
**파일**: `C:\kdy\Projects\AI_PTmanager\beta_v001\docs\CODING_CONVENTIONS.md`

**내용**:
- Import 경로 규칙
- 타입 힌트 규칙
- Docstring 규칙
- LLM 호출 규칙 (Structured Output)
- Database 세션 사용 규칙
- 에러 처리 규칙
- 로깅 규칙

#### 2. Agent Template 파일 생성
**디렉토리**: `C:\kdy\Projects\AI_PTmanager\beta_v001\templates\agent_template\`

**파일**:
```
templates/agent_template/
├── {agent_name}_agent.py.template
├── {agent_name}_nodes.py.template
├── {agent_name}_tools.py.template
├── {agent_name}_prompts.py.template
├── {agent_name}_state.py.template
└── __init__.py.template
```

#### 3. Reference Agent 구현 시작
**대상**: Frontdesk Agent
**디렉토리**: `backend/app/octostrator/agents/frontdesk/`

**순서**:
1. State 재정의 (`backend/app/octostrator/states/frontdesk_state.py` 정리)
2. Prompts 작성 (`frontdesk_prompts.py`)
3. Tools 구현 (`frontdesk_tools.py` - 올바른 세션 사용)
4. Nodes 구현 (`frontdesk_nodes.py` - Structured Output)
5. Agent 클래스 (`frontdesk_agent.py` - BaseAgent 상속)
6. Graph 빌드 (`frontdesk_graph.py`)
7. 통합 테스트

---

## ✅ 삭제 명령 요약 (한 번에 실행)

```bash
# 1. 백업 생성 (선택)
mkdir C:\kdy\Projects\AI_PTmanager\beta_v001\backup\agents_backup_251110

# 2. Agent 파일 삭제
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend\app\octostrator\agents
cd frontdesk && del /Q *.py && cd ..
cd assessor && del /Q *.py && cd ..

# 3. 나머지 Agent 디렉토리 전체 삭제
rmdir /S /Q nutrition
rmdir /S /Q program_designer
rmdir /S /Q manager
rmdir /S /Q marketing
rmdir /S /Q owner_assistant
rmdir /S /Q trainer_education

# 4. Cognitive Layer 삭제
cd ..\supervisors\cognitive
del /Q *.py

# 5. Todo Manager 삭제
cd ..\todo
del /Q *.py

# 6. agents/__init__.py 초기화는 수동으로 편집
# 7. database/session.py 타입 힌트 수정은 수동으로 편집
```

---

## 🎯 삭제 후 다음 단계

### Phase 1 완료 후
- [x] 백업 생성 (선택)
- [x] Agent 파일 삭제
- [x] Cognitive/Todo 삭제
- [x] agents/__init__.py 초기화
- [x] database/session.py 타입 수정

### Phase 2 시작 (Reference Agent)
- [ ] 코딩 컨벤션 문서 작성
- [ ] Agent Template 생성
- [ ] Frontdesk State 재정의
- [ ] Frontdesk Prompts 작성
- [ ] Frontdesk Tools 구현
- [ ] Frontdesk Nodes 구현
- [ ] Frontdesk Agent 클래스 구현
- [ ] Frontdesk Graph 빌드
- [ ] 통합 테스트 작성
- [ ] E2E 테스트 통과

---

## ❓ 질문 체크리스트

삭제 전에 확인:
- [ ] Git 상태 확인했는가?
- [ ] 백업이 필요한가?
- [ ] 어떤 파일을 삭제할지 명확한가?
- [ ] 어떤 파일을 유지할지 명확한가?
- [ ] 삭제 후 다음 단계가 명확한가?

---

## 🚨 주의사항

### 절대 삭제하면 안 되는 것
- ❌ `backend/app/models/` (ORM 모델)
- ❌ `backend/database/` (CRUD - session.py만 수정)
- ❌ `backend/alembic/` (마이그레이션)
- ❌ `backend/app/octostrator/agents/base/` (BaseAgent)
- ❌ `backend/app/octostrator/supervisors/octostrator/` (메인 그래프)
- ❌ `backend/app/octostrator/supervisors/execute/` (Execute Layer)
- ❌ `backend/app/octostrator/supervisors/response/` (Response Layer)
- ❌ `backend/app/octostrator/states/base.py` (Base State)
- ❌ `backend/app/octostrator/states/octostrator_state.py` (Main State)
- ❌ `backend/app/octostrator/states/reducers.py` (Reducers)
- ❌ `backend/app/octostrator/contexts/` (Context API)

---

**작성자**: Claude Code
**최종 업데이트**: 2025-11-10
**중요**: 삭제 전 반드시 백업 권장!
