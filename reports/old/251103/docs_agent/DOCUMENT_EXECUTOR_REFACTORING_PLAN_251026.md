# Document Executor 통합 리팩토링 계획서

**날짜**: 2025-10-26
**버전**: Beta v0.01 - Document Executor Refactoring (Simplified)
**작성자**: Development Team
**목적**: Document Team 5개 파일을 단일 document_executor.py로 통합

---

## 📋 목차

1. [현재 상태 분석](#1-현재-상태-분석)
2. [목표 및 배경](#2-목표-및-배경)
3. [아키텍처 변경사항](#3-아키텍처-변경사항)
4. [구현 계획](#4-구현-계획)
5. [파일 변경 목록](#5-파일-변경-목록)
6. [위험 요소 및 대응 방안](#6-위험-요소-및-대응-방안)
7. [테스트 계획](#7-테스트-계획)
8. [롤백 계획](#8-롤백-계획)

---

## 1. 현재 상태 분석

### 1.1 Document Team 현황 (HITL 구현)

**위치**: `backend/app/service_agent/teams/document_team/`

```
document_team/
├── __init__.py              (12줄)   - build_document_workflow export
├── workflow.py              (66줄)   - build_document_workflow()
├── planning.py              (51줄)   - planning_node()
├── search.py                (47줄)   - search_node() + Mock search
├── aggregate.py            (111줄)   - aggregate_node() + interrupt() + helper functions
└── generate.py              (97줄)   - generate_node()
```

**총 라인 수**: ~384줄

**핵심 기능**:
- ✅ LangGraph 0.6 HITL 패턴 사용
- ✅ `interrupt()` 함수로 사용자 승인 대기
- ✅ `Command` API로 워크플로우 재개
- ✅ MainSupervisorState 사용
- ✅ team_results로 Parent Graph에 결과 전달
- ✅ 승인/수정/거부 기능 구현

**워크플로우**:
```
Planning → Search → Aggregate (⏸️ interrupt) → Generate
```

### 1.2 기존 Document Executor 현황

**위치**: `backend/app/service_agent/execution_agents/document_executor.py`

```python
class DocumentExecutor:
    - 570줄
    - ❌ HITL 기능 없음 (구식)
    - DocumentTeamState 사용 (다른 State)
    - Review 기능 있음
```

**상태**: ⚠️ **삭제 예정** (백업 후)
- 새로운 document_executor.py가 이를 대체
- 기존 파일은 참고하지 않음

### 1.3 Import 경로 영향 범위

**검색 결과**:
```bash
grep -r "from.*document_team" backend/
```

**결과**: ✅ **단 1곳만 영향**
```python
# backend/app/service_agent/supervisor/team_supervisor.py:38
from app.service_agent.teams.document_team import build_document_workflow
```

**변경 필요**:
- `team_supervisor.py` Line 38만 수정하면 끝

### 1.4 Helper 함수 분석

**search.py**:
- 30-40줄의 간단한 Mock 검색 로직
- 별도 Tool 클래스 불필요 → private 메서드로 충분

**aggregate.py**:
- `aggregate_results()`: 15줄 정도의 간단한 집계 함수
- `apply_user_feedback()`: 10줄 정도의 간단한 수정 함수
- 별도 Tool 클래스 불필요 → private 메서드로 충분

---

## 2. 목표 및 배경

### 2.1 리팩토링 목표

#### 주요 목표
1. ✅ **파일 통합**: 5개 파일 → 1개 파일 (`document_executor.py`)
2. ✅ **HITL 기능 유지**: interrupt() 및 Command API 완전 보존
3. ✅ **코드 간소화**: 별도 Tool 생성 없이 private 메서드로 처리
4. ✅ **기존 파일 정리**: 구 document_executor.py 삭제
5. ✅ **안전한 백업**: 삭제 전 모든 파일 백업

#### 간소화 결정
- ❌ 새 Tool 생성 안 함 (search, aggregator)
- ✅ Helper 함수들을 DocumentExecutor 내부 private 메서드로 포함
- ✅ Import 변경은 단 1곳만 (team_supervisor.py:38)

### 2.2 배경

**왜 통합이 필요한가?**

1. **파일 분산 문제**: 5개 파일로 분산되어 전체 흐름 파악 어려움
2. **일관성**: 다른 Executor들은 단일 파일인데 Document만 분산
3. **유지보수 부담**: 여러 파일 관리 부담
4. **중복 파일**: 기존 document_executor.py는 안 쓰는데 남아있음

**왜 새 Tool을 만들지 않나?**

- search.py, aggregate.py의 함수들이 매우 단순 (10-15줄)
- 다른 곳에서 재사용할 일 없음 (Document 전용)
- Tool 클래스 오버헤드 불필요

---

## 3. 아키텍처 변경사항

### 3.1 디렉토리 구조 변경

#### Before (현재)
```
backend/app/service_agent/
├── teams/
│   └── document_team/        ← 5개 파일 분산
│       ├── __init__.py
│       ├── workflow.py
│       ├── planning.py
│       ├── search.py
│       ├── aggregate.py
│       └── generate.py
├── execution_agents/
│   └── document_executor.py  ← 570줄, 안 쓰는 구식 파일
└── tools/
    └── lease_contract_generator_tool.py
```

#### After (변경 후)
```
backend/app/service_agent/
├── teams/
│   └── document_team_old/    ← 백업 폴더
│       └── ...
├── execution_agents/
│   ├── document_executor_old.py    ← 기존 파일 백업
│   └── document_executor.py        ← ✨ 새로운 통합 파일 (HITL 포함)
└── tools/
    └── lease_contract_generator_tool.py  ← 기존 그대로 유지
```

**변경 사항**:
- ✅ document_team 5개 파일 → 1개 파일로 통합
- ✅ 기존 파일들 _old로 백업
- ✅ 새 Tool 생성 없음 (간소화)

### 3.2 새로운 document_executor.py 구조

```python
"""
Document Executor - HITL-enabled Document Generation
LangGraph 0.6 Official Pattern with interrupt() function

통합 내용:
- document_team/workflow.py   → build_workflow()
- document_team/planning.py   → planning_node()
- document_team/search.py     → search_node() + _mock_search()
- document_team/aggregate.py  → aggregate_node() + helper methods
- document_team/generate.py   → generate_node()

Workflow: Planning → Search → Aggregate (⏸️ HITL) → Generate
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.service_agent.foundation.separated_states import MainSupervisorState

logger = logging.getLogger(__name__)


class DocumentExecutor:
    """
    Document Executor with HITL support
    Consolidates document_team workflow into single file
    """

    def __init__(self, llm_context=None, checkpointer=None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트 (선택)
            checkpointer: AsyncPostgresSaver (선택)
        """
        self.llm_context = llm_context
        self.checkpointer = checkpointer

    def build_workflow(self):
        """
        Build Document workflow with HITL

        Returns:
            Compiled StateGraph
        """
        logger.info("Building Document Executor workflow (HITL-enabled)")

        workflow = StateGraph(MainSupervisorState)

        # Add nodes
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("search", self.search_node)
        workflow.add_node("aggregate", self.aggregate_node)  # ⏸️ Contains interrupt()
        workflow.add_node("generate", self.generate_node)

        # Define edges
        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "search")
        workflow.add_edge("search", "aggregate")
        workflow.add_edge("aggregate", "generate")
        workflow.add_edge("generate", END)

        # Compile
        compiled = workflow.compile(checkpointer=self.checkpointer)
        logger.info("Document Executor workflow compiled successfully")

        return compiled

    # ==========================================
    # Node Methods (from document_team)
    # ==========================================

    def planning_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Planning node - Analyze requirements
        From: document_team/planning.py
        """
        logger.info("📋 Planning node: Analyzing document requirements")

        query = state.get("query", "")

        planning_result = {
            "document_type": "general",
            "sections": ["introduction", "main_content", "conclusion"],
            "estimated_length": "medium",
            "requires_search": True,
            "search_keywords": self._extract_keywords(query),
            "timestamp": "2025-10-26T00:00:00"
        }

        logger.info(f"Planning complete: {planning_result['document_type']} document")

        return {
            "planning_result": planning_result,
            "workflow_status": "running"
        }

    def search_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Search node - Gather information
        From: document_team/search.py
        """
        logger.info("🔍 Search node: Gathering information")

        planning_result = state.get("planning_result", {})
        keywords = planning_result.get("search_keywords", [])

        # Use mock search (from search.py)
        search_results = self._mock_search(keywords)

        logger.info(f"Search complete: Found {len(search_results)} results")

        return {
            "search_results": search_results,
            "workflow_status": "running"
        }

    def aggregate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Aggregate node - Consolidate results and request HITL approval
        From: document_team/aggregate.py

        ⚠️ CRITICAL: Uses interrupt() function for LangGraph 0.6 HITL
        """
        logger.info("📊 Aggregate node: Consolidating search results")

        search_results = state.get("search_results", [])

        # Aggregate results (from aggregate.py)
        aggregated_content = self._aggregate_results(search_results)

        logger.info(f"Aggregation complete: {len(aggregated_content)} characters")
        logger.info("⏸️  Requesting human approval via interrupt()")

        # Prepare interrupt value
        interrupt_value = {
            "aggregated_content": aggregated_content,
            "search_results_count": len(search_results),
            "message": "Please review the aggregated content before final document generation.",
            "options": {
                "approve": "Continue with document generation",
                "modify": "Provide feedback for modification",
                "reject": "Cancel document generation"
            },
            "_metadata": {
                "interrupted_by": "aggregate",
                "interrupt_type": "approval",
                "node_name": "document_team.aggregate"
            }
        }

        # ✅ LangGraph 0.6 Official Pattern
        user_feedback = interrupt(interrupt_value)

        # 🔄 Execution resumes here
        logger.info("▶️  Workflow resumed with user feedback")
        logger.info(f"User feedback: {user_feedback}")

        # Process user feedback (from aggregate.py)
        if user_feedback and user_feedback.get("action") == "modify":
            aggregated_content = self._apply_user_feedback(aggregated_content, user_feedback)
            logger.info("Content modified based on user feedback")

        return {
            "aggregated_content": aggregated_content,
            "collaboration_result": user_feedback,
            "workflow_status": "running",
            "interrupted_by": "aggregate",
            "interrupt_type": "approval"
        }

    def generate_node(self, state: MainSupervisorState) -> Dict[str, Any]:
        """
        Generate node - Create final document
        From: document_team/generate.py
        """
        logger.info("📝 Generate node: Creating final document")

        aggregated_content = state.get("aggregated_content", "")
        planning_result = state.get("planning_result", {})
        collaboration_result = state.get("collaboration_result", {})

        # Format document
        final_document = self._format_document(
            content=aggregated_content,
            planning=planning_result,
            feedback=collaboration_result
        )

        logger.info(f"Document generation complete: {len(final_document)} characters")

        # Build final_response
        doc_type = planning_result.get("document_type", "general")
        user_action = collaboration_result.get("action", "unknown") if collaboration_result else "unknown"

        final_response = {
            "answer": final_document,
            "document_type": doc_type,
            "user_approved": user_action == "approve",
            "user_action": user_action,
            "modifications_applied": user_action == "modify",
            "type": "document"
        }

        logger.info(f"✅ Final response created: type={doc_type}, action={user_action}")

        # Add to team_results for Parent Graph
        team_results = {
            "document": {
                "status": "success",
                "data": final_response
            }
        }

        logger.info("✅ Document Team results added to team_results")

        return {
            "final_document": final_document,
            "final_response": final_response,
            "workflow_status": "completed",
            "team_results": team_results
        }

    # ==========================================
    # Private Helper Methods
    # ==========================================

    def _extract_keywords(self, query: str) -> list:
        """
        Extract search keywords from query
        From: document_team/planning.py
        """
        # TODO: Use LLM for better extraction
        keywords = query.split()[:5]
        return keywords

    def _mock_search(self, keywords: list) -> list:
        """
        Mock search implementation
        From: document_team/search.py
        """
        search_results = []
        for keyword in keywords:
            result = {
                "keyword": keyword,
                "source": "mock_database",
                "content": f"Mock search result for: {keyword}",
                "relevance_score": 0.85,
                "timestamp": "2025-10-26T00:00:00"
            }
            search_results.append(result)
        return search_results

    def _aggregate_results(self, search_results: list) -> str:
        """
        Aggregate search results into coherent content
        From: document_team/aggregate.py:aggregate_results()
        """
        if not search_results:
            return "No search results to aggregate."

        # Simple aggregation
        # TODO: Use LLM for better aggregation
        aggregated = "\n\n".join([
            f"- {result.get('keyword', 'Unknown')}: {result.get('content', 'No content')}"
            for result in search_results
        ])

        return f"Aggregated Content:\n{aggregated}"

    def _apply_user_feedback(self, content: str, feedback: Dict[str, Any]) -> str:
        """
        Apply user modifications to content
        From: document_team/aggregate.py:apply_user_feedback()
        """
        modifications = feedback.get("modifications", "")
        if modifications:
            # TODO: Use LLM to intelligently apply modifications
            return f"{content}\n\n[User Feedback Applied]\n{modifications}"
        return content

    def _format_document(self, content: str, planning: Dict[str, Any], feedback: Dict[str, Any]) -> str:
        """
        Format the final document
        From: document_team/generate.py:format_document()
        """
        doc_type = planning.get("document_type", "general")
        sections = planning.get("sections", [])

        document = f"""
# Document: {doc_type.upper()}

## Generated Content

{content}

## Metadata
- Document Type: {doc_type}
- Sections: {', '.join(sections)}
- User Approved: {feedback.get('action') == 'approve' if feedback else False}
- Generation Time: 2025-10-26

---
Generated by Holmes AI Document Executor
"""
        return document.strip()


# ==========================================
# Standalone Function for TeamSupervisor
# ==========================================

def build_document_workflow(checkpointer: AsyncPostgresSaver):
    """
    Build Document workflow as compiled subgraph

    Used by TeamSupervisor to integrate Document Executor

    Args:
        checkpointer: AsyncPostgresSaver instance

    Returns:
        Compiled StateGraph ready to be added as node
    """
    executor = DocumentExecutor(checkpointer=checkpointer)
    return executor.build_workflow()
```

**예상 라인 수**: ~350-400줄

---

## 4. 구현 계획

### Phase 1: 백업 및 준비 (30분)

#### Step 1.1: 기존 파일 백업
```bash
# Document Team 폴더 백업
mv backend/app/service_agent/teams/document_team \
   backend/app/service_agent/teams/document_team_old

# Document Executor 백업
mv backend/app/service_agent/execution_agents/document_executor.py \
   backend/app/service_agent/execution_agents/document_executor_old.py
```

#### Step 1.2: Git 커밋 (백업 완료 시점)
```bash
git add .
git commit -m "Backup: Move document_team to _old and backup old document_executor"
```

**체크포인트**:
- [ ] document_team_old 폴더 존재
- [ ] document_executor_old.py 파일 존재
- [ ] Git 커밋 완료

---

### Phase 2: 새 document_executor.py 생성 (2.5시간)

#### Step 2.1: 기본 구조 작성
```python
# DocumentExecutor 클래스
# __init__()
# build_workflow()
```

#### Step 2.2: 노드 메서드 통합
1. **planning_node**: planning.py 복사
2. **search_node**: search.py 복사
3. **aggregate_node**: aggregate.py 복사 (interrupt() 유지)
4. **generate_node**: generate.py 복사

#### Step 2.3: Private Helper 메서드 추가
```python
# From planning.py
def _extract_keywords(self, query: str) -> list: ...

# From search.py
def _mock_search(self, keywords: list) -> list: ...

# From aggregate.py
def _aggregate_results(self, search_results: list) -> str: ...
def _apply_user_feedback(self, content: str, feedback: dict) -> str: ...

# From generate.py
def _format_document(self, content: str, planning: dict, feedback: dict) -> str: ...
```

#### Step 2.4: build_document_workflow() 함수 추가
```python
def build_document_workflow(checkpointer):
    """TeamSupervisor 통합용"""
    executor = DocumentExecutor(checkpointer=checkpointer)
    return executor.build_workflow()
```

**체크포인트**:
- [ ] document_executor.py 생성 완료
- [ ] 모든 노드 메서드 구현
- [ ] 모든 helper 메서드 구현
- [ ] 코드 컴파일 오류 없음
- [ ] interrupt() 함수 정상 포함

---

### Phase 3: TeamSupervisor 통합 업데이트 (30분)

#### Step 3.1: Import 경로 변경
```python
# team_supervisor.py Line 38

# Before
from app.service_agent.teams.document_team import build_document_workflow

# After
from app.service_agent.execution_agents.document_executor import build_document_workflow
```

#### Step 3.2: 다른 부분 확인
- Line 1446: `document_workflow = build_document_workflow(...)` - 동일 유지
- Line 1453: `workflow.add_node("document_team", ...)` - 동일 유지
- Line 1466: `"document": "document_team"` - 동일 유지

**체크포인트**:
- [ ] Import 경로 변경 완료 (Line 38)
- [ ] 다른 부분 수정 불필요 확인
- [ ] Backend 실행 오류 없음

---

### Phase 4: 테스트 (2시간)

#### Step 4.1: 기본 동작 확인
```bash
# Backend 실행
cd backend
uv run uvicorn app.main:app --reload

# 확인 사항:
- Backend 실행 정상
- document_executor import 정상
- TeamSupervisor build 정상
```

#### Step 4.2: 통합 테스트
```
1. "임대차계약서 작성해줘" 입력
2. Planning → document_team 라우팅 확인
3. Aggregate에서 interrupt 발생 확인
4. Frontend Lease Contract Page 표시 확인
```

#### Step 4.3: E2E 테스트
```bash
# Frontend 실행
cd frontend
npm run dev

# 시나리오 1: 승인
- "강남역 근처 아파트 임대차계약서 작성" 입력
- Lease Contract Page 팝업
- "승인" 클릭
- 문서 생성 확인

# 시나리오 2: 수정
- 동일 입력
- "수정" → "보증금 5억으로 올려주세요" 입력
- 수정 반영 확인

# 시나리오 3: 거부
- 동일 입력
- "거부" 클릭
- 거부 상태 확인
```

**체크포인트**:
- [ ] Backend 실행 정상
- [ ] HITL interrupt 정상 발생
- [ ] 승인/수정/거부 모두 정상 작동
- [ ] team_results 전달 정상
- [ ] 최종 응답 표시 정상

---

### Phase 5: 정리 및 문서화 (30분)

#### Step 5.1: Import 전역 검색
```bash
# document_team import 검색
grep -r "from.*document_team" backend/
grep -r "import.*document_team" backend/

# 결과: team_supervisor.py:38 만 나와야 함 (이미 수정됨)
```

#### Step 5.2: 파일 정리 확인
- [ ] document_team_old 폴더 존재
- [ ] document_executor_old.py 파일 존재
- [ ] 새 document_executor.py 정상 작동

#### Step 5.3: 문서 업데이트
- README 업데이트 (필요 시)
- 이 계획서에 "완료" 표시

**체크포인트**:
- [ ] 모든 Import 정상
- [ ] 백업 파일 보존
- [ ] 문서 최신화

---

### Phase 6: Git 커밋 및 배포 (30분)

#### Step 6.1: 최종 커밋
```bash
git add .
git commit -m "Refactor: Consolidate document_team into single document_executor.py

- Merge 5 files into execution_agents/document_executor.py (~380 lines)
- Maintain HITL pattern with interrupt() function
- Include all helper methods as private methods (no new tools)
- Update TeamSupervisor import path (single line change)
- Remove old document_executor.py (backed up as _old)
- All HITL tests passing (approve/modify/reject)

Files changed:
- NEW: backend/app/service_agent/execution_agents/document_executor.py
- BACKUP: backend/app/service_agent/teams/document_team_old/
- BACKUP: backend/app/service_agent/execution_agents/document_executor_old.py
- MODIFIED: backend/app/service_agent/supervisor/team_supervisor.py (import only)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
"
```

#### Step 6.2: 배포 전 체크리스트
- [ ] 모든 테스트 통과
- [ ] HITL 기능 정상 (승인/수정/거부)
- [ ] 백업 파일 존재
- [ ] 문서 업데이트 완료

**체크포인트**: 배포 준비 완료

---

## 5. 파일 변경 목록

### 5.1 신규 생성 파일

| 파일 경로 | 라인 수 | 설명 |
|----------|---------|------|
| `execution_agents/document_executor.py` | ~380 | Document Team 5개 파일 통합 (HITL 포함) |

**총 신규 라인 수**: ~380줄

### 5.2 백업 파일

| 원본 경로 | 백업 경로 | 비고 |
|----------|----------|------|
| `teams/document_team/` | `teams/document_team_old/` | 폴더 전체 백업 |
| `execution_agents/document_executor.py` | `execution_agents/document_executor_old.py` | 구 파일 백업 |

### 5.3 수정 파일

| 파일 경로 | 변경 사항 | 라인 번호 |
|----------|----------|-----------|
| `supervisor/team_supervisor.py` | Import 경로 변경 | Line 38 |

### 5.4 삭제 파일 (백업 완료 후)

| 파일 경로 | 삭제 시기 | 비고 |
|----------|----------|------|
| `teams/document_team/` | ✅ Phase 1에서 _old로 이동 | 백업 보존 |
| `execution_agents/document_executor.py` (구) | ✅ Phase 1에서 _old로 이동 | 백업 보존 |

**권장**: 백업 파일(_old)은 2주~1개월 안정화 기간 후 삭제 결정

---

## 6. 위험 요소 및 대응 방안

### 6.1 주요 위험 요소

| 위험 | 영향도 | 확률 | 대응 방안 |
|------|--------|------|-----------|
| **HITL 기능 손상** | 🔴 Critical | 저 | aggregate_node에서 interrupt() 정확히 복사 |
| **Import 경로 누락** | 🟠 High | 극저 | 전역 검색으로 확인 (단 1곳만) |
| **State 필드 누락** | 🟡 Medium | 저 | MainSupervisorState 그대로 사용 |
| **Helper 함수 누락** | 🟡 Medium | 저 | 모든 함수 라인별 복사 |
| **롤백 불가** | 🔴 Critical | 저 | _old 백업 + Git 커밋 |

### 6.2 세부 대응 방안

#### 6.2.1 HITL 기능 손상 방지
- **검증**: aggregate_node 코드 라인별 비교
- **테스트**: 승인/수정/거부 각각 E2E 테스트
- **로그 확인**: "⏸️ Requesting human approval" 로그 확인

#### 6.2.2 Import 경로 누락 방지
```bash
# 전역 검색
grep -r "document_team" backend/
grep -r "from app.service_agent.teams.document_team" backend/

# 결과: team_supervisor.py:38 만 나와야 함
```

#### 6.2.3 Helper 함수 누락 방지
**체크리스트**:
- [ ] `_extract_keywords()` (from planning.py)
- [ ] `_mock_search()` (from search.py)
- [ ] `_aggregate_results()` (from aggregate.py)
- [ ] `_apply_user_feedback()` (from aggregate.py)
- [ ] `_format_document()` (from generate.py)

---

## 7. 테스트 계획

### 7.1 단위 테스트

```python
# backend/tests/execution_agents/test_document_executor.py

import pytest
from app.service_agent.execution_agents.document_executor import (
    DocumentExecutor,
    build_document_workflow
)

class TestDocumentExecutor:

    @pytest.fixture
    def executor(self):
        return DocumentExecutor()

    def test_build_workflow(self, executor):
        """워크플로우 빌드 검증"""
        workflow = executor.build_workflow()
        assert workflow is not None

    def test_planning_node(self, executor):
        """Planning node 검증"""
        state = {"query": "임대차계약서 작성해줘"}
        result = executor.planning_node(state)

        assert "planning_result" in result
        assert result["workflow_status"] == "running"

    def test_search_node(self, executor):
        """Search node 검증"""
        state = {
            "planning_result": {
                "search_keywords": ["임대차", "계약서"]
            }
        }
        result = executor.search_node(state)

        assert "search_results" in result
        assert len(result["search_results"]) > 0

    def test_extract_keywords(self, executor):
        """Keyword 추출 검증"""
        keywords = executor._extract_keywords("임대차 계약서 작성")
        assert len(keywords) > 0

    def test_mock_search(self, executor):
        """Mock 검색 검증"""
        results = executor._mock_search(["임대차", "보증금"])
        assert len(results) == 2
        assert results[0]["keyword"] == "임대차"

    def test_aggregate_results(self, executor):
        """집계 함수 검증"""
        search_results = [
            {"keyword": "임대차", "content": "Content 1"},
            {"keyword": "보증금", "content": "Content 2"}
        ]
        aggregated = executor._aggregate_results(search_results)

        assert len(aggregated) > 0
        assert "임대차" in aggregated
        assert "보증금" in aggregated

    def test_apply_user_feedback(self, executor):
        """피드백 적용 검증"""
        content = "Original content"
        feedback = {"modifications": "보증금 5억으로 변경"}

        modified = executor._apply_user_feedback(content, feedback)

        assert "User Feedback Applied" in modified
        assert "보증금 5억으로 변경" in modified

    # NOTE: aggregate_node는 interrupt() 때문에 단위 테스트 어려움
    # E2E 테스트로 검증
```

### 7.2 E2E 테스트

#### 7.2.1 시나리오 1: 승인 플로우
```
1. User: "강남역 근처 아파트 임대차계약서 작성해줘"
2. Backend: Planning → Search → Aggregate → INTERRUPT
3. Frontend: Lease Contract Page 표시
4. User: "승인" 버튼 클릭
5. Backend: Generate → team_results 전달
6. Frontend: 최종 문서 표시

✅ Expected:
- Backend 로그: "⏸️ Requesting human approval"
- Backend 로그: "▶️ Workflow resumed"
- Backend 로그: "user_action: approve"
- Frontend: 문서 정상 표시
```

#### 7.2.2 시나리오 2: 수정 플로우
```
1-3. (동일)
4. User: "수정" → "보증금을 5억으로 올려주세요" 입력
5. Backend: Apply modifications → Generate
6. Frontend: 수정 반영된 문서 표시

✅ Expected:
- Backend 로그: "Content modified based on user feedback"
- Backend 로그: "user_action: modify"
- 문서 내용: "[User Feedback Applied]\n보증금을 5억으로 올려주세요" 포함
```

#### 7.2.3 시나리오 3: 거부 플로우
```
1-3. (동일)
4. User: "거부" 버튼 클릭
5. Backend: Generate (with rejected flag)
6. Frontend: 거부 상태 표시

✅ Expected:
- Backend 로그: "user_action: reject"
- 문서 metadata: user_action: "reject"
```

### 7.3 테스트 성공 기준

| 테스트 종류 | 성공 기준 |
|------------|----------|
| 단위 테스트 | Helper 메서드 100% 통과 |
| E2E 테스트 (승인) | ✅ 문서 생성 정상 |
| E2E 테스트 (수정) | ✅ 수정 반영 정상 |
| E2E 테스트 (거부) | ✅ 거부 상태 표시 |
| Performance | HITL 기존과 동일 (~17-48초) |

---

## 8. 롤백 계획

### 8.1 롤백 트리거

다음 상황 발생 시 즉시 롤백:

1. **HITL 기능 손상**: Interrupt 발생 안 함 또는 Resume 실패
2. **Critical Bug**: 문서 생성 완전 실패
3. **Data Loss**: team_results 전달 실패로 응답 없음
4. **Import Error**: TeamSupervisor build 실패

### 8.2 롤백 절차

#### Option A: Git Revert (권장)
```bash
# 1. 리팩토링 커밋 확인
git log --oneline | grep "Refactor: Consolidate document_team"

# 2. 해당 커밋 revert
git revert <commit-hash>

# 3. 백업 파일 복원
mv backend/app/service_agent/teams/document_team_old \
   backend/app/service_agent/teams/document_team

mv backend/app/service_agent/execution_agents/document_executor_old.py \
   backend/app/service_agent/execution_agents/document_executor.py

# 4. Import 경로 복원 (team_supervisor.py Line 38)
# from document_executor → from document_team

# 5. 재시작
cd backend && uv run uvicorn app.main:app --reload
```

#### Option B: 백업 파일 직접 복원
```bash
# 1. 새 파일 삭제
rm backend/app/service_agent/execution_agents/document_executor.py

# 2. 백업 복원
mv backend/app/service_agent/teams/document_team_old \
   backend/app/service_agent/teams/document_team

mv backend/app/service_agent/execution_agents/document_executor_old.py \
   backend/app/service_agent/execution_agents/document_executor.py

# 3. Import 경로 복원

# 4. Git 커밋
git add .
git commit -m "Rollback: Restore document_team and old document_executor"
```

### 8.3 롤백 검증

- [ ] Backend 실행 정상
- [ ] HITL 기능 정상 (승인/수정/거부)
- [ ] 문서 생성 정상
- [ ] E2E 테스트 통과

---

## 9. 타임라인

### 9.1 예상 소요 시간

| Phase | 작업 | 예상 시간 |
|-------|------|----------|
| Phase 1 | 백업 및 준비 | 30분 |
| Phase 2 | document_executor.py 생성 | 2.5시간 |
| Phase 3 | TeamSupervisor 통합 | 30분 |
| Phase 4 | 테스트 | 2시간 |
| Phase 5 | 정리 및 문서화 | 30분 |
| Phase 6 | Git 커밋 및 배포 | 30분 |
| **총합** | | **6.5시간** |

### 9.2 권장 일정

**Day 1 (3시간)**:
- Phase 1: 백업 (30분)
- Phase 2: document_executor.py 생성 (2.5시간)

**Day 2 (2.5시간)**:
- Phase 3: TeamSupervisor 통합 (30분)
- Phase 4: 테스트 (2시간)

**Day 3 (1시간)**:
- Phase 5: 정리 (30분)
- Phase 6: 배포 (30분)

**총 소요 기간**: 3일 (총 6.5시간)

---

## 10. 체크리스트

### 10.1 시작 전 체크리스트

- [ ] 현재 HITL 기능 정상 작동 확인
- [ ] Git 상태 Clean
- [ ] 백업 경로 확인
- [ ] Phase별 시간 확보

### 10.2 Phase별 체크리스트

**Phase 1: 백업**
- [ ] document_team → document_team_old 이동 완료
- [ ] document_executor.py → _old.py 이동 완료
- [ ] Git 커밋 완료
- [ ] 백업 파일 존재 확인

**Phase 2: Executor 생성**
- [ ] 기본 구조 작성
- [ ] planning_node 완성
- [ ] search_node 완성
- [ ] aggregate_node 완성 (interrupt 포함)
- [ ] generate_node 완성
- [ ] `_extract_keywords()` 추가
- [ ] `_mock_search()` 추가
- [ ] `_aggregate_results()` 추가
- [ ] `_apply_user_feedback()` 추가
- [ ] `_format_document()` 추가
- [ ] build_document_workflow() 함수 추가
- [ ] 코드 컴파일 오류 없음

**Phase 3: 통합**
- [ ] team_supervisor.py import 경로 변경 (Line 38)
- [ ] Backend 실행 오류 없음

**Phase 4: 테스트**
- [ ] 단위 테스트 작성 및 통과
- [ ] E2E 테스트 (승인) ✅
- [ ] E2E 테스트 (수정) ✅
- [ ] E2E 테스트 (거부) ✅

**Phase 5: 정리**
- [ ] Import 전역 검색 및 확인
- [ ] 백업 파일 보존 확인
- [ ] 문서 업데이트

**Phase 6: 배포**
- [ ] 최종 Git 커밋
- [ ] 배포 체크리스트 완료

### 10.3 완료 후 체크리스트

- [ ] HITL 기능 정상 (승인/수정/거부)
- [ ] 문서 생성 정상
- [ ] 성능 저하 없음
- [ ] 백업 파일 보존 (_old)
- [ ] 롤백 절차 검증 완료

---

## 11. 결론

### 11.1 요약

본 리팩토링은 **Document Team 5개 파일을 단일 document_executor.py로 통합**합니다:

1. ✅ **파일 통합**: 5개 파일 → 1개 파일 (~380줄)
2. ✅ **HITL 기능 유지**: interrupt() 및 Command API 완전 보존
3. ✅ **코드 간소화**: Helper 함수들을 private 메서드로 포함 (새 Tool 불필요)
4. ✅ **기존 파일 정리**: 구 document_executor.py 제거 (백업)
5. ✅ **안전한 백업**: 모든 파일 _old로 보존
6. ✅ **최소 변경**: Import 수정은 단 1곳만 (team_supervisor.py:38)

### 11.2 기대 효과

1. **유지보수성**: 전체 워크플로우를 한 파일에서 파악
2. **간결함**: 불필요한 파일 분산 및 Tool 오버헤드 제거
3. **일관성**: 다른 Executor들과 구조 통일
4. **시간 절약**: 9.5시간 → 6.5시간 (3시간 단축)

### 11.3 간소화 결정

**왜 새 Tool을 만들지 않았나?**
- search, aggregate의 helper 함수들이 매우 단순 (10-15줄)
- Document 전용 함수로 다른 곳에서 재사용 불가
- Tool 클래스 오버헤드 불필요
- Private 메서드로 충분

### 11.4 Next Steps

1. **Phase 1 시작**: 백업부터 안전하게 진행
2. **단계별 체크**: 체크리스트 확인하며 진행
3. **테스트 철저히**: HITL 기능 손상 방지
4. **모니터링**: 배포 후 안정성 확인

---

**작성일**: 2025-10-26 (Revised)
**예상 완료**: 3일 (6.5시간)
**다음 리뷰**: 리팩토링 완료 후
**문의**: Development Team
