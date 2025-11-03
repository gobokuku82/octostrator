# State/Context 설계 계획서 v1.0

**작성일**: 2025-10-13
**버전**: v1.0
**작성자**: Claude Code
**목적**: property_search_results 집계 문제 해결을 위한 State/Context 재설계

---

## 📊 현재 상황 분석

### 발견된 문제

**로그 분석 결과** (2025-10-13 17:53:05):
```
[SearchTeam] Property search completed: 10 results  ✅ 도구 실행 성공
[SearchTeam] Aggregated 0 results from 0 sources  ❌ 집계 실패
```

**근본 원인**:
1. `SearchTeamState` TypedDict에 `property_search_results` 필드 정의 누락
2. `aggregate_results_node`가 `property_search_results` 집계 로직 없음
3. `finalize_node`가 `property_search_results`를 team_results에 포함 안함
4. Supervisor가 `property_search_results`를 응답 생성 시 전달 안함

### 데이터 모델 분석

**PostgreSQL 모델** (`backend/app/models/real_estate.py`):
- `RealEstate`: 부동산 물리적 정보 (건물, 위치, 면적 등)
- `Transaction`: 거래 정보 (매매가, 전세가, 월세)
- `Region`: 지역 정보 (법정동 코드)
- `NearbyFacility`: 주변 시설 (지하철, 학교)
- `RealEstateAgent`: 중개사 정보

**Pydantic Schemas** (`backend/app/schemas/real_estate.py`):
- `RealEstateResponse`: API 응답 스키마
- `TransactionResponse`: 거래 응답 스키마
- `RealEstateWithTransactions`: 조인된 데이터
- `RealEstateWithRegion`: 지역 정보 포함

### 현재 Agent State 구조

**SearchTeamState** (`backend/app/service_agent/foundation/separated_states.py:76-108`):
```python
class SearchTeamState(TypedDict):
    # Search results
    legal_results: List[Dict[str, Any]]          # 법률 검색 결과
    real_estate_results: List[Dict[str, Any]]    # MarketDataTool (시세 데이터)
    loan_results: List[Dict[str, Any]]            # 대출 상품 검색
    # ❌ property_search_results 필드 없음!
    aggregated_results: Dict[str, Any]
```

---

## 🎯 설계 원칙

### 1. DB 모델과 Agent State의 역할 분리

**DB Models (SQLAlchemy)**: 데이터 영속성
- PostgreSQL 테이블 스키마 정의
- ORM 관계 매핑 (relationships)
- 데이터 검증 (constraints)

**Pydantic Schemas**: API 계층
- FastAPI 요청/응답 검증
- 타입 힌트 및 문서화
- 직렬화/역직렬화

**Agent States (TypedDict)**: LangGraph 실행 상태
- 에이전트 실행 흐름 관리
- 팀 간 데이터 전달
- 중간 결과 저장

**원칙**: **DB 모델 → Schemas → Agent State 변환**
- Tool이 DB 쿼리 → Pydantic 모델로 검증 → Dict로 State에 저장
- State는 "실행 컨텍스트"이지 "데이터 모델"이 아님

### 2. State 네이밍 규칙

**도구별 State 키 명명**:
- `legal_results`: HybridLegalSearch 결과
- `real_estate_results`: MarketDataTool 결과 (시세 통계)
- `property_search_results`: RealEstateSearchTool 결과 (개별 매물)
- `loan_results`: LoanDataTool 결과

**이유**:
- `real_estate`는 도메인(부동산), `property_search`는 기능(매물 검색)
- MarketDataTool과 RealEstateSearchTool 구분 명확

### 3. Context 전달 전략

**Shared Context** (모든 팀 공유):
```python
{
    "query": str,           # 사용자 쿼리
    "session_id": str,      # 세션 ID
    "user_id": int,         # 사용자 ID (optional)
    "timestamp": datetime
}
```

**Team-specific Context** (팀 내부):
```python
{
    "search_params": {...},  # 검색 파라미터
    "filters": {...},        # 필터 조건
    "pagination": {...}      # 페이징 정보
}
```

---

## 📋 수정 계획

### Phase 1: SearchTeamState 확장 (Critical)

**파일**: `backend/app/service_agent/foundation/separated_states.py`
**위치**: Lines 76-108

**수정 내용**:
```python
class SearchTeamState(TypedDict):
    # ... 기존 필드들 ...

    # Search results
    legal_results: List[Dict[str, Any]]
    real_estate_results: List[Dict[str, Any]]    # 시세 데이터 (MarketDataTool)
    loan_results: List[Dict[str, Any]]
    property_search_results: List[Dict[str, Any]]  # ✅ 개별 매물 (RealEstateSearchTool)
    aggregated_results: Dict[str, Any]
```

**근거**:
- RealEstateSearchTool이 Line 677에서 `state["property_search_results"]` 저장
- TypedDict 정의 없으면 LangGraph state 업데이트 실패

---

### Phase 2: aggregate_results_node 수정 (Critical)

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`
**위치**: Lines 785-824

**현재 코드**:
```python
async def aggregate_results_node(self, state: SearchTeamState) -> SearchTeamState:
    logger.info("[SearchTeam] Aggregating results")

    total_results = 0
    sources = []

    if state.get("legal_results"):
        total_results += len(state["legal_results"])
        sources.append("legal_db")

    if state.get("real_estate_results"):
        total_results += len(state["real_estate_results"])
        sources.append("real_estate_api")

    if state.get("loan_results"):
        total_results += len(state["loan_results"])
        sources.append("loan_service")

    # ❌ property_search_results 집계 없음!

    state["total_results"] = total_results
    state["sources_used"] = sources

    state["aggregated_results"] = {
        "total_count": total_results,
        "by_type": {
            "legal": len(state.get("legal_results", [])),
            "real_estate": len(state.get("real_estate_results", [])),
            "loan": len(state.get("loan_results", []))
            # ❌ property_search 없음!
        },
        "sources": sources,
        "keywords_used": state.get("keywords", {})
    }

    logger.info(f"[SearchTeam] Aggregated {total_results} results from {len(sources)} sources")
    return state
```

**수정 후 코드**:
```python
async def aggregate_results_node(self, state: SearchTeamState) -> SearchTeamState:
    logger.info("[SearchTeam] Aggregating results")

    total_results = 0
    sources = []

    if state.get("legal_results"):
        total_results += len(state["legal_results"])
        sources.append("legal_db")

    if state.get("real_estate_results"):
        total_results += len(state["real_estate_results"])
        sources.append("market_data_api")

    if state.get("loan_results"):
        total_results += len(state["loan_results"])
        sources.append("loan_service")

    # ✅ 개별 매물 검색 결과 집계 추가
    if state.get("property_search_results"):
        total_results += len(state["property_search_results"])
        sources.append("property_db")

    state["total_results"] = total_results
    state["sources_used"] = sources

    # aggregated_results 업데이트
    state["aggregated_results"] = {
        "total_count": total_results,
        "by_type": {
            "legal": len(state.get("legal_results", [])),
            "market_data": len(state.get("real_estate_results", [])),     # 시세
            "loan": len(state.get("loan_results", [])),
            "property_search": len(state.get("property_search_results", []))  # ✅ 매물
        },
        "sources": sources,
        "keywords_used": state.get("keywords", {})
    }

    logger.info(f"[SearchTeam] Aggregated {total_results} results from {len(sources)} sources")
    return state
```

**근거**:
- 로그에서 "Aggregated 0 results" → 집계 로직 누락
- `by_type`에 `property_search` 추가로 LLM이 매물 데이터 존재 인지

---

### Phase 3: finalize_node team_results 포함 확인 (Medium)

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`
**위치**: Lines 826-848

**현재 상태**:
- finalize_node는 상태만 정리, team_results 반환 없음

**조사 필요사항**:
- Supervisor가 SearchTeam 결과를 어떻게 가져가는지 확인
- `separated_states.py`의 StateManager가 team_results 병합하는지 확인

**현재 코드**:
```python
async def finalize_node(self, state: SearchTeamState) -> SearchTeamState:
    logger.info("[SearchTeam] Finalizing")

    state["end_time"] = datetime.now()

    if state.get("start_time"):
        elapsed = (state["end_time"] - state["start_time"]).total_seconds()
        state["search_time"] = elapsed

    # 상태 결정
    if state.get("error"):
        state["status"] = "failed"
    elif state.get("total_results", 0) > 0:
        state["status"] = "completed"
    else:
        state["status"] = "completed"

    logger.info(f"[SearchTeam] Completed with status: {state['status']}")
    return state
```

**예상 수정 (필요 시)**:
```python
async def finalize_node(self, state: SearchTeamState) -> SearchTeamState:
    logger.info("[SearchTeam] Finalizing")

    state["end_time"] = datetime.now()

    if state.get("start_time"):
        elapsed = (state["end_time"] - state["start_time"]).total_seconds()
        state["search_time"] = elapsed

    # 상태 결정
    if state.get("error"):
        state["status"] = "failed"
    elif state.get("total_results", 0) > 0:
        state["status"] = "completed"
    else:
        state["status"] = "completed"

    # ✅ team_results 구성 (Supervisor로 전달할 데이터)
    # Note: Supervisor가 state에서 직접 읽어가는지 확인 필요
    state["team_results"] = {
        "legal": state.get("legal_results", []),
        "market_data": state.get("real_estate_results", []),
        "loan": state.get("loan_results", []),
        "property_search": state.get("property_search_results", []),  # ✅ 추가
        "aggregated": state.get("aggregated_results", {})
    }

    logger.info(f"[SearchTeam] Completed with status: {state['status']}")
    return state
```

---

### Phase 4: execute() 메서드 initial_state 수정 (Low)

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`
**위치**: Lines 850-898

**현재 코드**:
```python
initial_state = SearchTeamState(
    team_name=self.team_name,
    status="pending",
    shared_context=shared_state,
    keywords=keywords or SearchKeywords(legal=[], real_estate=[], loan=[], general=[]),
    search_scope=search_scope or [],
    filters={},
    legal_results=[],
    real_estate_results=[],
    loan_results=[],
    # ❌ property_search_results 없음!
    aggregated_results={},
    total_results=0,
    search_time=0.0,
    sources_used=[],
    search_progress={},
    start_time=None,
    end_time=None,
    error=None,
    current_search=None
)
```

**수정 후 코드**:
```python
initial_state = SearchTeamState(
    team_name=self.team_name,
    status="pending",
    shared_context=shared_state,
    keywords=keywords or SearchKeywords(legal=[], real_estate=[], loan=[], general=[]),
    search_scope=search_scope or [],
    filters={},
    legal_results=[],
    real_estate_results=[],
    loan_results=[],
    property_search_results=[],  # ✅ 추가
    aggregated_results={},
    total_results=0,
    search_time=0.0,
    sources_used=[],
    search_progress={},
    start_time=None,
    end_time=None,
    error=None,
    current_search=None,
    execution_strategy=None
)
```

---

## 🔄 데이터 흐름도

```
User Query: "강남구 5억미만 아파트"
    ↓
TeamSupervisor (Planning)
    ↓ selected_tools: ["real_estate_search"]
SearchExecutor
    ↓
execute_search_node
    ↓ Line 671: real_estate_search_tool.search()
RealEstateSearchTool
    ↓ PostgreSQL Query
    ├─ RealEstate.query().filter(region='강남구', max_price=50000만원)
    ├─ JOIN Region
    ├─ JOIN Transaction (가격 필터)
    └─ Eager Load (joinedload)
    ↓
    ├─ 10 results found
    └─ Line 677: state["property_search_results"] = property_data  ✅
    ↓
aggregate_results_node
    ↓ ❌ property_search_results 집계 안함 (현재)
    └─ ✅ property_search_results 집계 (수정 후)
    ↓
finalize_node
    ↓ team_results 구성
    └─ property_search 포함
    ↓
TeamSupervisor (aggregate_results_node)
    ↓ team_results['search'] 병합
    └─ property_search 데이터 포함
    ↓
TeamSupervisor (generate_response_node)
    ↓ LLM에게 전달
    └─ aggregated_results에 property_search 있음
    ↓
LLM Response
    └─ "강남구에서 5억 미만 아파트 10건을 찾았습니다..."
```

---

## 📝 State Schema 표준화 제안

### 향후 확장을 위한 표준 포맷

**Tool Result 표준 구조**:
```python
{
    "status": "success" | "error",
    "data": [...],           # 실제 결과 리스트
    "result_count": int,
    "metadata": {
        "data_source": str,  # "PostgreSQL", "ChromaDB", "API"
        "query_params": {},
        "execution_time_ms": int,
        "filters_applied": {}
    },
    "error": Optional[str]
}
```

**State 저장 시**:
```python
# Tool에서 반환한 표준 포맷
result = await tool.search(query, params)

# State에는 data만 저장 (메타데이터는 로그)
if result["status"] == "success":
    state["property_search_results"] = result["data"]
    state["property_search_metadata"] = result["metadata"]  # Optional
```

**이점**:
- 모든 Tool이 동일한 응답 포맷 사용
- 에러 처리 일관성
- 메타데이터 추적 가능

---

## ✅ 검증 계획

### 1. Unit Test

**테스트 파일**: `backend/tests/test_search_executor.py`

```python
import pytest
from app.service_agent.execution_agents.search_executor import SearchExecutor
from app.service_agent.foundation.separated_states import SearchTeamState

@pytest.mark.asyncio
async def test_property_search_aggregation():
    """property_search_results가 정상적으로 집계되는지 테스트"""
    executor = SearchExecutor()

    # 테스트 state 생성
    state = SearchTeamState(
        team_name="search",
        status="in_progress",
        shared_context={},
        keywords={},
        search_scope=[],
        filters={},
        legal_results=[],
        real_estate_results=[],
        loan_results=[],
        property_search_results=[
            {"id": 1, "name": "강남 아파트 A"},
            {"id": 2, "name": "강남 아파트 B"}
        ],
        aggregated_results={},
        total_results=0,
        search_time=0.0,
        sources_used=[],
        search_progress={},
        start_time=None,
        end_time=None,
        error=None,
        current_search=None,
        execution_strategy=None
    )

    # aggregate_results_node 실행
    result = await executor.aggregate_results_node(state)

    # 검증
    assert result["total_results"] == 2, "총 결과 수가 2여야 함"
    assert "property_db" in result["sources_used"], "property_db가 sources에 포함되어야 함"
    assert result["aggregated_results"]["by_type"]["property_search"] == 2, "property_search 카운트가 2여야 함"
    assert result["aggregated_results"]["total_count"] == 2, "total_count가 2여야 함"


@pytest.mark.asyncio
async def test_mixed_results_aggregation():
    """여러 도구 결과가 함께 집계되는지 테스트"""
    executor = SearchExecutor()

    state = SearchTeamState(
        team_name="search",
        status="in_progress",
        shared_context={},
        keywords={},
        search_scope=[],
        filters={},
        legal_results=[{"law": "test1"}],
        real_estate_results=[{"market": "test2"}],
        loan_results=[{"loan": "test3"}],
        property_search_results=[{"property": "test4"}, {"property": "test5"}],
        aggregated_results={},
        total_results=0,
        search_time=0.0,
        sources_used=[],
        search_progress={},
        start_time=None,
        end_time=None,
        error=None,
        current_search=None,
        execution_strategy=None
    )

    result = await executor.aggregate_results_node(state)

    # 검증
    assert result["total_results"] == 5, "총 결과 수가 5여야 함 (1+1+1+2)"
    assert len(result["sources_used"]) == 4, "4개 소스가 사용되어야 함"
    assert result["aggregated_results"]["by_type"]["legal"] == 1
    assert result["aggregated_results"]["by_type"]["market_data"] == 1
    assert result["aggregated_results"]["by_type"]["loan"] == 1
    assert result["aggregated_results"]["by_type"]["property_search"] == 2
```

---

### 2. Integration Test

**테스트 시나리오**: 실제 쿼리 실행

```python
import pytest
from app.service_agent.execution_agents.search_executor import SearchExecutor
from app.service_agent.foundation.separated_states import SharedState

@pytest.mark.asyncio
async def test_property_search_end_to_end():
    """실제 쿼리로 property_search가 동작하는지 테스트"""

    executor = SearchExecutor()

    # 공유 상태 생성
    shared_state = SharedState(
        user_query="강남구 5억미만 아파트 찾아줘",
        session_id="test-session-123",
        timestamp=datetime.now().isoformat(),
        language="ko",
        status="processing",
        error_message=None
    )

    # SearchExecutor 실행
    result = await executor.execute(
        shared_state=shared_state,
        search_scope=["real_estate"],
        keywords=None
    )

    # 검증
    assert result["status"] == "completed", "실행이 완료되어야 함"
    assert "property_search_results" in result, "property_search_results 키가 있어야 함"
    assert len(result.get("property_search_results", [])) > 0, "최소 1개 이상의 결과가 있어야 함"
    assert result["total_results"] > 0, "total_results가 0보다 커야 함"
    assert "property_db" in result["sources_used"], "property_db가 사용되어야 함"
```

---

### 3. E2E Test

**테스트 환경**:
- 프론트엔드 → WebSocket → Supervisor → SearchExecutor → RealEstateSearchTool

**테스트 절차**:
1. 프론트엔드에서 "강남구 5억미만 아파트 찾아줘" 입력
2. WebSocket을 통해 쿼리 전송
3. Supervisor가 Planning Agent 호출
4. SearchExecutor가 RealEstateSearchTool 실행
5. aggregate_results_node에서 결과 집계
6. Supervisor가 LLM에게 aggregated_results 전달
7. LLM이 매물 정보 기반 응답 생성
8. 프론트엔드에서 최종 응답 표시

**검증 항목**:
- [ ] 로그에 "Property search completed: N results" 출력
- [ ] 로그에 "Aggregated N results from M sources" 출력 (N > 0)
- [ ] 로그에 "property_db" 소스 포함
- [ ] LLM 응답에 매물 정보 포함 (예: "강남구에서 5억 미만 아파트 10건 발견")
- [ ] 프론트엔드에서 매물 목록 표시

---

## 🎯 우선순위 및 예상 효과

### Priority 1 (Critical - 즉시 수정)

#### ✅ SearchTeamState에 property_search_results 필드 추가
- **파일**: `backend/app/service_agent/foundation/separated_states.py`
- **영향**: TypedDict 정의 누락으로 state 업데이트 실패
- **예상 시간**: 2분
- **난이도**: 낮음

#### ✅ aggregate_results_node에 property_search_results 집계 로직 추가
- **파일**: `backend/app/service_agent/execution_agents/search_executor.py`
- **영향**: 10개 결과 → 0개 집계 문제 해결
- **예상 시간**: 5분
- **난이도**: 낮음

---

### Priority 2 (High - 당일 완료)

#### ⚠️ finalize_node에 team_results 구성 확인/추가
- **파일**: `backend/app/service_agent/execution_agents/search_executor.py`
- **영향**: Supervisor로 데이터 전달
- **예상 시간**: 10분 (조사 포함)
- **난이도**: 중간
- **조사 필요**: Supervisor의 state 읽기 방식 확인

---

### Priority 3 (Medium - 향후 개선)

#### 📝 Tool Result 표준화
- **파일**: 모든 Tool 파일
- **영향**: 코드 일관성, 유지보수성
- **예상 시간**: 1시간
- **난이도**: 중간

#### 📝 Unit Test 작성
- **파일**: `backend/tests/test_search_executor.py`
- **영향**: 회귀 테스트 방지
- **예상 시간**: 30분
- **난이도**: 낮음

---

### 예상 효과

#### 즉시 효과 (Priority 1 완료 후)
- ✅ "강남구 5억미만 아파트" 쿼리 → 10개 매물 정상 표시
- ✅ MarketDataTool (시세) vs RealEstateSearchTool (개별 매물) 구분 명확
- ✅ LLM이 매물 정보를 받아 상세 응답 생성
- ✅ 로그: "Aggregated 10 results from 1 sources" (property_db)

#### 로그 개선 (Before → After)
**Before**:
```
[SearchTeam] Property search completed: 10 results
[SearchTeam] Aggregated 0 results from 0 sources  ❌
```

**After**:
```
[SearchTeam] Property search completed: 10 results
[SearchTeam] Aggregated 10 results from 1 sources  ✅
[TeamSupervisor] Aggregated search: 12345 bytes
[TeamSupervisor] Using LLM for response generation
```

#### 사용자 경험 개선
**Before**: "죄송합니다. 해당 조건에 맞는 매물을 찾지 못했습니다."
**After**: "강남구에서 5억 미만 아파트 10건을 찾았습니다. [매물 정보 상세]"

---

## 📌 다음 단계

### 1. 계획서 검토 및 승인 ✅

### 2. Phase 1-2 수정 실행 (Critical 우선)
1. `separated_states.py`: SearchTeamState 필드 추가
2. `search_executor.py`: aggregate_results_node 수정
3. 코드 검증 (syntax check)

### 3. 서버 재시작 및 테스트
```bash
# 서버 재시작
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*"
cd backend
venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 로그 확인
- [ ] "Property search completed: N results" 출력
- [ ] "Aggregated N results from M sources" 출력 (N > 0)
- [ ] "property_db" 소스 포함
- [ ] "Aggregated search: XXXX bytes" (TeamSupervisor)

### 5. 실제 응답 확인
- [ ] 프론트엔드에서 "강남구 5억미만 아파트" 쿼리 실행
- [ ] LLM 응답에 매물 정보 포함 확인
- [ ] WebSocket 메시지에 property_search 데이터 포함 확인

### 6. Phase 3-4 후속 작업 (필요 시)
- finalize_node team_results 구성 (Supervisor 조사 후 결정)
- execute() initial_state 수정

### 7. 문서화
- README 업데이트 (새로운 Tool 사용법)
- API 문서 업데이트

---

## ❓ 질문사항 및 결정 필요 사항

### Q1. finalize_node에서 team_results 구성이 필요한가?
**상황**:
- 현재 finalize_node는 state만 정리하고 반환
- Supervisor가 state에서 직접 읽는지, team_results를 통해 읽는지 불명확

**조사 필요**:
- `team_supervisor.py`의 aggregate_results_node 확인
- `separated_states.py`의 StateManager 확인

**결정 기준**:
- Supervisor가 `state["legal_results"]` 직접 읽기 → team_results 불필요
- Supervisor가 `state["team_results"]["legal"]` 읽기 → team_results 필수

---

### Q2. property_search_metadata도 State에 저장할까?
**장점**:
- 디버깅 용이 (쿼리 파라미터, 실행 시간 추적)
- 성능 분석 가능

**단점**:
- State 크기 증가
- 복잡도 증가

**권장**:
- Phase 1에서는 제외
- 향후 필요 시 추가 (Priority 3)

---

### Q3. Tool Result 표준화를 지금 할까, 나중에 할까?
**지금 하는 경우**:
- 모든 Tool이 일관된 포맷 사용
- 에러 처리 통일
- **단점**: 수정 범위 증가 (4개 Tool 모두 수정)

**나중에 하는 경우**:
- 빠른 버그 수정 가능
- 점진적 개선
- **단점**: 기술 부채 증가

**권장**:
- Phase 1-2에서는 property_search만 수정
- Phase 3에서 표준화 진행 (Priority 3)

---

## 📊 리스크 분석

### High Risk
**없음** - 단순한 필드 추가 및 집계 로직 추가

### Medium Risk
**Phase 3 (finalize_node)** - Supervisor와의 연동 방식 확인 필요
- **완화책**: Supervisor 코드 조사 후 결정

### Low Risk
**Phase 1-2** - 단순한 코드 추가, 기존 로직에 영향 없음

---

## 📚 참고 자료

### 관련 파일
- `backend/app/service_agent/foundation/separated_states.py`: State 정의
- `backend/app/service_agent/execution_agents/search_executor.py`: SearchExecutor
- `backend/app/service_agent/tools/real_estate_search_tool.py`: RealEstateSearchTool
- `backend/app/models/real_estate.py`: PostgreSQL 모델
- `backend/app/schemas/real_estate.py`: Pydantic 스키마
- `backend/app/service_agent/supervisor/team_supervisor.py`: Supervisor

### 로그 예시
```
2025-10-13 17:53:04 - [SearchTeam] Executing individual real estate property search
2025-10-13 17:53:04 - Real estate search - region: 강남구, type: APARTMENT, price: None-None
2025-10-13 17:53:05 - [SearchTeam] Property search completed: 10 results
2025-10-13 17:53:05 - [SearchTeam] Aggregating results
2025-10-13 17:53:05 - [SearchTeam] Aggregated 0 results from 0 sources  ❌ 문제!
```

---

## ✅ 승인 체크리스트

수정 전 확인사항:
- [ ] 계획서 내용 이해
- [ ] 수정 범위 확인 (Phase 1-2만 우선 진행)
- [ ] 백업 불필요 (Git으로 버전 관리)
- [ ] 테스트 계획 이해

수정 후 확인사항:
- [ ] 서버 정상 시작
- [ ] 로그에 "Aggregated N results" (N > 0)
- [ ] 실제 쿼리 정상 동작
- [ ] LLM 응답에 매물 정보 포함

---

**승인자**: _______________
**승인일**: 2025-10-13
**다음 검토일**: Phase 1-2 완료 후
