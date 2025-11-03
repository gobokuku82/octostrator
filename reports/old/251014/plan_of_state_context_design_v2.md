# State/Context 설계 계획서 v2.0

**작성일**: 2025-10-13
**버전**: v2.0 (v1.0 개정판)
**작성자**: Claude Code
**목적**: property_search_results 집계 문제 해결 및 DB 모델 기반 State/Context 재설계

**주요 변경사항 (v1.0 → v2.0)**:
- schemas/models 전체 분석 결과 반영
- 즉시 구현 vs 추후 구현 우선순위 구분
- SharedState에 user_id 추가 (Optional)
- property_search_results 데이터 구조 명세 추가
- trust_score, nearby_facilities, agent_info 조건부 포함 전략
- 향후 확장 로드맵 추가

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

### 데이터 모델 전체 분석 (v2.0 추가)

**PostgreSQL 모델 구조** (전체 확인 완료):

1. **부동산 관련** (`backend/app/models/real_estate.py`):
   - `Region`: 지역 정보 (법정동 코드)
   - `RealEstate`: 부동산 물리적 정보 (건물, 위치, 면적)
   - `Transaction`: 거래 정보 (매매가, 전세가, 월세, 매물번호)
   - `NearbyFacility`: 주변 시설 (지하철, 학교) ✅ 조건부 포함
   - `RealEstateAgent`: 중개사 정보 ✅ 조건부 포함
   - `TrustScore`: 신뢰도 점수 (0-100) ✅ 포함

2. **사용자 관련** (`backend/app/models/users.py`):
   - `User`: 통합 사용자 (email, type, is_active)
   - `UserProfile`: 프로필 (nickname, gender, birth_date)
   - `LocalAuth`: 로컬 로그인
   - `SocialAuth`: 소셜 로그인 (Google, Kakao, Naver, Apple)
   - `UserFavorite`: 찜 목록 🔄 추후 구현

3. **채팅 관련** (`backend/app/models/chat.py`):
   - `ChatSession`: 세션 (user_id 필수, title)
   - `ChatMessage`: 메시지 (sender_type, content)

**Pydantic Schemas** (API 계층):
- `RealEstateResponse`, `TransactionResponse`, `RegionResponse`
- `RealEstateWithTransactions`, `RealEstateWithRegion`
- `UserResponse`, `UserProfileResponse`, `UserWithProfile`
- `ChatSessionResponse`, `ChatMessageResponse`
- `TrustScoreResponse`

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
- `property_search_results`: RealEstateSearchTool 결과 (개별 매물) ✅ 추가
- `loan_results`: LoanDataTool 결과

**이유**:
- `real_estate`는 도메인(부동산), `property_search`는 기능(매물 검색)
- MarketDataTool과 RealEstateSearchTool 구분 명확

### 3. Context 전달 전략

**Shared Context** (모든 팀 공유) - v2.0 개정:
```python
{
    "query": str,                    # 사용자 쿼리
    "session_id": str,               # 세션 ID (UUID)
    "user_id": Optional[int],        # ✅ v2.0 추가: 사용자 ID (로그인 시)
    "timestamp": datetime,           # 요청 시간
    "language": str                  # 언어 (ko/en)
}
```

**Team-specific Context** (팀 내부):
```python
{
    "search_params": {...},          # 검색 파라미터
    "filters": {...},                # 필터 조건
    "pagination": {...},             # 페이징 정보
    "include_nearby": bool,          # ✅ 주변 시설 포함 여부 (Q4)
    "include_transactions": bool     # 거래 내역 포함 여부
}
```

---

## 📋 수정 계획 (우선순위별)

### ⚡ Phase 1: 즉시 구현 (Critical - 버그 수정)

#### 1-1. SearchTeamState 확장

**파일**: `backend/app/service_agent/foundation/separated_states.py`
**위치**: Lines 76-108

**현재 코드**:
```python
class SearchTeamState(TypedDict):
    # ... 기존 필드들 ...

    # Search results
    legal_results: List[Dict[str, Any]]
    real_estate_results: List[Dict[str, Any]]
    loan_results: List[Dict[str, Any]]
    # ❌ property_search_results 없음!
    aggregated_results: Dict[str, Any]
```

**수정 후 코드**:
```python
class SearchTeamState(TypedDict):
    # Team identification
    team_name: str
    status: str

    # Shared context
    shared_context: Dict[str, Any]

    # Search specific
    keywords: Optional[SearchKeywords]
    search_scope: List[str]  # ["legal", "real_estate", "loan"]
    filters: Dict[str, Any]

    # Search results
    legal_results: List[Dict[str, Any]]                  # 법률 검색 결과
    real_estate_results: List[Dict[str, Any]]            # 시세 데이터 (MarketDataTool)
    loan_results: List[Dict[str, Any]]                   # 대출 상품 검색
    property_search_results: List[Dict[str, Any]]        # ✅ 개별 매물 (RealEstateSearchTool)
    aggregated_results: Dict[str, Any]

    # Metadata
    total_results: int
    search_time: float
    sources_used: List[str]
    search_progress: Dict[str, str]

    # Execution tracking
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]
    current_search: Optional[str]
    execution_strategy: Optional[str]
```

**근거**:
- RealEstateSearchTool이 Line 677에서 `state["property_search_results"]` 저장
- TypedDict 정의 없으면 LangGraph state 업데이트 실패

---

#### 1-2. SharedState 확장 (user_id 추가)

**파일**: `backend/app/service_agent/foundation/separated_states.py`
**위치**: Lines 59-70

**현재 코드**:
```python
class SharedState(TypedDict):
    user_query: str
    session_id: str
    timestamp: str
    language: str
    status: Literal["pending", "processing", "completed", "error"]
    error_message: Optional[str]
    # ❌ user_id 없음!
```

**수정 후 코드**:
```python
class SharedState(TypedDict):
    """
    모든 팀이 공유하는 최소한의 상태
    - 필수 필드만 포함
    - 팀 간 통신의 기본 단위
    """
    user_query: str
    session_id: str
    user_id: Optional[int]        # ✅ v2.0 추가: 사용자 ID (로그인 시, 없으면 None)
    timestamp: str
    language: str
    status: Literal["pending", "processing", "completed", "error"]
    error_message: Optional[str]
```

**근거**:
- `ChatSession.user_id` 필수 필드 (nullable=False)
- 세션 저장 시 user_id 필요
- 로그인 안한 사용자는 None 처리
- 추후 찜 기능, 맞춤 추천 구현 시 필수

---

#### 1-3. aggregate_results_node 수정

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
    """
    결과 집계 노드
    여러 검색 결과를 통합
    """
    logger.info("[SearchTeam] Aggregating results")

    # 결과 집계
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

    # 통합 결과 생성
    state["aggregated_results"] = {
        "total_count": total_results,
        "by_type": {
            "legal": len(state.get("legal_results", [])),
            "market_data": len(state.get("real_estate_results", [])),         # 시세 통계
            "loan": len(state.get("loan_results", [])),
            "property_search": len(state.get("property_search_results", []))  # ✅ 개별 매물
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

#### 1-4. execute() 메서드 initial_state 수정

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`
**위치**: Lines 850-898 (대략)

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

#### 1-5. StateManager.create_initial_team_state 수정

**파일**: `backend/app/service_agent/foundation/separated_states.py`
**위치**: Lines 510-526

**현재 코드**:
```python
if team_type == "search":
    state = {
        **base_fields,
        "keywords": None,
        "search_scope": ["legal", "real_estate", "loan"],
        "filters": {},
        "legal_results": [],
        "real_estate_results": [],
        "loan_results": [],
        # ❌ property_search_results 없음!
        "aggregated_results": {},
        "total_results": 0,
        "search_time": 0.0,
        "sources_used": [],
        "search_progress": {},
        "current_search": None,
        "execution_strategy": None
    }
```

**수정 후 코드**:
```python
if team_type == "search":
    state = {
        **base_fields,
        "keywords": None,
        "search_scope": ["legal", "real_estate", "loan"],
        "filters": {},
        "legal_results": [],
        "real_estate_results": [],
        "loan_results": [],
        "property_search_results": [],  # ✅ 추가
        "aggregated_results": {},
        "total_results": 0,
        "search_time": 0.0,
        "sources_used": [],
        "search_progress": {},
        "current_search": None,
        "execution_strategy": None
    }
```

---

### 🔧 Phase 2: property_search_results 데이터 구조 명세 (High)

#### 2-1. property_search_results 항목 구조 정의

**파일**: 계획서 / 문서화
**목적**: RealEstateSearchTool 반환 데이터 표준화

**데이터 저장 방식** (Q9 답변):
- **Option A 채택**: `result["data"]`만 저장 (매물 리스트만)
- **Option B 대비**: metadata를 별도 필드로 저장 가능하도록 설계

**현재 RealEstateSearchTool 반환 포맷**:
```python
{
    "status": "success" | "error",
    "data": [...],              # 매물 리스트 (이 부분만 state에 저장)
    "result_count": 10,
    "metadata": {
        "region": str,
        "property_type": str,
        "filters": {...},
        "pagination": {...},
        "data_source": "PostgreSQL"
    }
}
```

**state["property_search_results"]에 저장되는 각 항목 구조**:
```python
{
    # 기본 정보 (RealEstate)
    "id": int,                              # RealEstate.id
    "name": str,                            # 단지명/건물명
    "property_type": str,                   # "APARTMENT" | "OFFICETEL" | "VILLA" | "ONEROOM" | "HOUSE"
    "code": str,                            # 단지코드/매물코드

    # 위치 정보 (RealEstate + Region)
    "region_id": int,                       # Region.id
    "region_name": str,                     # 지역명 (예: "강남구")
    "address": str,                         # 도로명 주소
    "address_detail": Optional[str],        # 상세주소
    "latitude": Optional[float],            # 위도
    "longitude": Optional[float],           # 경도

    # 가격 정보 (Transaction) - 개별 거래 단위
    "transaction_type": Optional[str],      # "SALE" | "JEONSE" | "RENT"
    "sale_price": Optional[int],            # 매매가 (만원)
    "deposit": Optional[int],               # 보증금 (만원)
    "monthly_rent": Optional[int],          # 월세 (만원)
    "article_no": Optional[str],            # 매물번호
    "article_confirm_ymd": Optional[str],   # 매물확인일자
    "transaction_date": Optional[str],      # 거래일

    # 가격 범위 정보 (Transaction) - 단지/건물 통계
    "min_sale_price": Optional[int],        # 최소 매매가 (만원)
    "max_sale_price": Optional[int],        # 최대 매매가 (만원)
    "min_deposit": Optional[int],           # 최소 보증금 (만원)
    "max_deposit": Optional[int],           # 최대 보증금 (만원)
    "min_monthly_rent": Optional[int],      # 최소 월세 (만원)
    "max_monthly_rent": Optional[int],      # 최대 월세 (만원)

    # 면적 정보 (RealEstate)
    "exclusive_area": Optional[float],      # 전용면적 (㎡)
    "supply_area": Optional[float],         # 공급면적 (㎡)
    "exclusive_area_pyeong": Optional[float],  # 전용면적 (평)
    "supply_area_pyeong": Optional[float],     # 공급면적 (평)
    "min_exclusive_area": Optional[float],  # 최소 전용면적 (단지)
    "max_exclusive_area": Optional[float],  # 최대 전용면적 (단지)
    "representative_area": Optional[float], # 대표 전용면적 (단지)

    # 건물 정보 (RealEstate)
    "total_households": Optional[int],      # 총 세대수
    "total_buildings": Optional[int],       # 총 동수
    "completion_date": Optional[str],       # 준공년월 (YYYYMM)
    "floor_area_ratio": Optional[float],    # 용적률 (%)
    "floor_info": Optional[str],            # 층 정보
    "direction": Optional[str],             # 방향
    "building_description": Optional[str],  # 건물 설명
    "tag_list": Optional[List[str]],        # 태그 리스트

    # 매물 통계 (RealEstate)
    "deal_count": Optional[int],            # 매매 매물 수
    "lease_count": Optional[int],           # 전세 매물 수
    "rent_count": Optional[int],            # 월세 매물 수
    "short_term_rent_count": Optional[int], # 단기임대 매물 수

    # ✅ 추가 정보 (조건부 포함)
    "trust_score": Optional[float],         # Q3: 신뢰도 점수 (0-100) - 있으면 표시
    "nearby_facilities": Optional[Dict],    # Q4: 주변 시설 - 사용자 질문 시만
    "agent_info": Optional[Dict],           # Q5: 중개사 정보 - 데이터 있으면 포함

    # 메타데이터
    "created_at": str,                      # ISO format datetime
    "updated_at": Optional[str]             # ISO format datetime
}
```

**nearby_facilities 구조** (Q4: 조건부 포함):
```python
{
    "subway_line": Optional[str],           # 지하철 노선 (예: "2호선")
    "subway_distance": Optional[int],       # 지하철역까지 거리 (m)
    "subway_walking_time": Optional[int],   # 도보 시간 (분)
    "elementary_schools": Optional[str],    # 초등학교 목록
    "middle_schools": Optional[str],        # 중학교 목록
    "high_schools": Optional[str]           # 고등학교 목록
}
```

**agent_info 구조** (Q5: 조건부 포함):
```python
{
    "agent_name": Optional[str],            # 중개사명
    "company_name": Optional[str],          # 메인 중개사명
    "is_direct_trade": bool                 # 직거래 여부
}
```

**포함 조건**:
- **trust_score**: 항상 JOIN, 데이터 있으면 표시 (없어도 에러 안남)
- **nearby_facilities**: 사용자 쿼리에 "지하철", "역", "학교", "편의시설" 포함 시만 JOIN
- **agent_info**: 데이터 있으면 포함, 없으면 제외 (LEFT JOIN 사용)

---

#### 2-2. RealEstateSearchTool 수정 (조건부 JOIN)

**파일**: `backend/app/service_agent/tools/real_estate_search_tool.py`

**현재 상태**:
- trust_scores JOIN 안함
- nearby_facilities LEFT JOIN 구현됨 (`include_nearby` 파라미터)
- agent_info JOIN 안함

**수정 필요**:

1. **trust_scores JOIN 추가**:
```python
def _query_real_estates(self, db, region, property_type, ...):
    query = db.query(RealEstate).options(
        joinedload(RealEstate.region),
        joinedload(RealEstate.transactions),
        joinedload(RealEstate.trust_scores)  # ✅ 추가
    )
    # ... 필터링 로직
```

2. **agent_info LEFT JOIN 추가** (조건부):
```python
# search_executor.py에서 이미 구현된 include_nearby 로직 참고
if any(term in query for term in ["중개사", "agent", "직거래"]):
    search_params["include_agent"] = True

# real_estate_search_tool.py
if include_agent:
    query = query.options(joinedload(RealEstate.agent))
```

3. **응답 데이터 구성**:
```python
result_item = {
    "id": property.id,
    "name": property.name,
    # ... 기본 필드들

    # trust_score 추가
    "trust_score": property.trust_scores[0].score if property.trust_scores else None,

    # nearby_facilities (조건부)
    "nearby_facilities": {
        "subway_line": facility.subway_line,
        # ...
    } if include_nearby and property.nearby_facilities else None,

    # agent_info (조건부)
    "agent_info": {
        "agent_name": agent.agent_name,
        # ...
    } if property.agent else None
}
```

---

### 🔍 Phase 3: finalize_node team_results 구성 확인 (Medium)

**파일**: `backend/app/service_agent/execution_agents/search_executor.py`
**위치**: Lines 826-848

**현재 상태**:
- finalize_node는 상태만 정리, team_results 반환 없음

**조사 필요사항**:
- Supervisor가 SearchTeam 결과를 어떻게 가져가는지 확인
- `separated_states.py`의 `StateManager.merge_team_results` 확인 (Lines 442-484)

**현재 코드 분석**:
```python
# separated_states.py:442-484
@staticmethod
def merge_team_results(
    main_state: MainSupervisorState,
    team_name: str,
    team_result: Dict[str, Any]
) -> MainSupervisorState:
    """팀 결과를 메인 State에 병합"""
    logger.info(f"Merging results from team: {team_name}")

    if "team_results" not in main_state:
        main_state["team_results"] = {}
    main_state["team_results"][team_name] = team_result  # ✅ 전체 state 저장
    # ...
```

**결론**: Supervisor가 **team_result (전체 state)를 그대로 저장**하므로, finalize_node에서 별도로 team_results 구성 불필요!

**검증 필요**:
- team_supervisor.py의 aggregate_results_node에서 어떻게 데이터를 읽는지 확인
- `state["team_results"]["search"]["property_search_results"]` 형태로 접근하는지 확인

**예상 수정** (필요 시):
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

    # ✅ 명시적으로 결과 요약 (Supervisor가 쉽게 읽을 수 있도록)
    # Note: 이미 StateManager.merge_team_results가 전체 state를 저장하므로 선택사항
    state["summary"] = {
        "legal_count": len(state.get("legal_results", [])),
        "market_data_count": len(state.get("real_estate_results", [])),
        "loan_count": len(state.get("loan_results", [])),
        "property_count": len(state.get("property_search_results", [])),  # ✅
        "total_count": state.get("total_results", 0),
        "execution_time": state.get("search_time", 0.0)
    }

    logger.info(f"[SearchTeam] Completed with status: {state['status']}")
    return state
```

---

## 🔄 데이터 흐름도

```
User Query: "강남구 5억미만 아파트 찾아줘"
    ↓
TeamSupervisor (Planning)
    ↓ selected_tools: ["real_estate_search"]
SearchExecutor
    ↓
execute_search_node
    ↓ Line 671: real_estate_search_tool.search(query, search_params)
RealEstateSearchTool
    ↓ PostgreSQL Query with JOINs
    ├─ RealEstate.query().filter(region='강남구', max_price=50000만원)
    ├─ JOIN Region (지역명)
    ├─ JOIN Transaction (가격 필터)
    ├─ LEFT JOIN TrustScore (신뢰도 점수) ✅ Q3
    ├─ LEFT JOIN NearbyFacility (조건부) ✅ Q4
    └─ LEFT JOIN RealEstateAgent (조건부) ✅ Q5
    ↓
    ├─ 10 results found
    ├─ result = {"status": "success", "data": [...], "metadata": {...}}
    └─ Line 677: state["property_search_results"] = result["data"]  ✅ Option A
    ↓
aggregate_results_node
    ↓ ✅ property_search_results 집계 (수정 후)
    ├─ total_results = 10
    ├─ sources = ["property_db"]
    └─ by_type["property_search"] = 10
    ↓
finalize_node
    ↓ state 정리 및 완료 처리
    └─ status = "completed"
    ↓
StateManager.merge_team_results
    ↓ main_state["team_results"]["search"] = SearchTeamState (전체)
    └─ property_search_results 포함 ✅
    ↓
TeamSupervisor (aggregate_results_node)
    ↓ team_results['search'] 읽기
    ├─ legal_results: []
    ├─ real_estate_results: []
    ├─ loan_results: []
    └─ property_search_results: [10개 매물] ✅
    ↓
TeamSupervisor (generate_response_node)
    ↓ LLM에게 전달
    ├─ aggregated_results: {"by_type": {"property_search": 10}}
    └─ property_search_results: [매물 상세 정보]
    ↓
LLM Response
    └─ "강남구에서 5억 미만 아파트 10건을 찾았습니다. [매물 정보 상세 + trust_score 표시]"
```

---

## 🚀 향후 확장 로드맵 (Phase 4+)

### 추후 구현 기능 (우선순위순)

#### 1. 사용자 인증 및 세션 관리 (Q1)
**상태**: 개발 초기 단계, 구현 계획 있음

**구현 필요 사항**:
- FastAPI 인증 미들웨어
- JWT 토큰 발급/검증
- WebSocket 연결 시 user_id 추출
- `SharedState.user_id` 자동 채우기

**현재 대비**:
- ✅ SharedState에 `user_id: Optional[int]` 이미 추가 (v2.0)
- 로그인 없으면 None 처리

**DB 모델**: 준비 완료
- `User`, `LocalAuth`, `SocialAuth` 테이블 존재

---

#### 2. 찜 기능 (User Favorites) (Q2)
**상태**: 추후 구현

**구현 필요 사항**:
1. **SearchTeamState 확장**:
```python
class SearchTeamState(TypedDict):
    # ... 기존 필드들 ...
    user_favorites: Optional[List[int]]  # 찜한 매물 ID 리스트 (추후 추가)
```

2. **property_search_results에 is_favorited 추가**:
```python
{
    "id": 123,
    "name": "강남 아파트",
    # ... 기본 필드들
    "is_favorited": bool,  # ✅ 사용자가 찜한 매물인지 여부
}
```

3. **RealEstateSearchTool 수정**:
```python
def _query_real_estates(self, db, user_id, ...):
    # user_id로 UserFavorite 조회
    user_favorites = db.query(UserFavorite).filter(
        UserFavorite.user_id == user_id
    ).all()
    favorite_ids = [f.real_estate_id for f in user_favorites]

    # 검색 결과에 is_favorited 추가
    for result in results:
        result["is_favorited"] = result["id"] in favorite_ids
```

4. **API 엔드포인트 추가**:
- `POST /api/favorites`: 매물 찜하기
- `DELETE /api/favorites/{real_estate_id}`: 찜 취소
- `GET /api/favorites`: 찜한 매물 목록

**DB 모델**: 준비 완료
- `UserFavorite` 테이블 존재

---

#### 3. 계약서 자동 입력 (Q6)
**상태**: 구현 계획 있음, Human-in-the-loop 필요

**LeaseContractGeneratorTool**: 임대차 계약서 생성 도구 (개발 중)

**구현 필요 사항**:

1. **MainSupervisorState에 선택된 매물 추가**:
```python
class MainSupervisorState(TypedDict, total=False):
    # ... 기존 필드들 ...

    # Document generation context
    selected_property: Optional[Dict[str, Any]]  # SearchTeam에서 선택한 매물
    contract_parties: Optional[Dict[str, Any]]   # 임대인/임차인 정보 (사용자 입력)
```

2. **Human-in-the-loop 플로우**:
```
User: "전월세 계약서 작성해줘"
    ↓
PlanningAgent: [search_team, document_team] 선택
    ↓
SearchTeam: 매물 목록 검색 (10개)
    ↓
TeamSupervisor: LLM이 매물 목록 제시
    ↓
User: "2번 매물로 해줘" (Human input)  ← Human-in-the-loop
    ↓
TeamSupervisor: selected_property 저장
    ↓
User: 임대인/임차인 정보 입력 (이름, 주민번호 등)  ← Human input
    ↓
DocumentTeam: LeaseContractGeneratorTool 실행
    ↓ selected_property + contract_parties 전달
    ↓ 계약서 생성 (Docx)
    ↓
User: 계약서 다운로드
```

3. **WebSocket 메시지 타입 추가**:
```python
# 사용자 입력 요청
{
    "type": "input_request",
    "input_type": "property_selection",
    "options": [...],  # 매물 목록
    "prompt": "계약서를 작성할 매물을 선택해주세요"
}

# 사용자 응답
{
    "type": "user_input",
    "input_type": "property_selection",
    "value": 2  # 선택한 매물 번호
}
```

**DB 모델**: 준비 완료
- `UserProfile`: 사용자 기본 정보 (이름, 생년월일)
- 추가 필요: 주민등록번호 (암호화 저장)

---

#### 4. Tool Result 표준화 (Phase 3)
**상태**: 향후 개선

**목적**: 모든 Tool이 일관된 응답 포맷 사용

**표준 포맷**:
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

**적용 대상 Tool**:
- HybridLegalSearch
- MarketDataTool
- RealEstateSearchTool ✅ 이미 적용됨
- LoanDataTool

**State 저장 방식 (Option B로 확장)**:
```python
# Option A (현재): data만 저장
state["property_search_results"] = result["data"]

# Option B (확장 시): metadata도 저장
state["property_search_results"] = result["data"]
state["property_search_metadata"] = result["metadata"]  # 디버깅용
```

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
        shared_context={
            "user_query": "강남구 5억미만 아파트",
            "session_id": "test-123",
            "user_id": None,  # v2.0 추가
            "timestamp": "2025-10-13T00:00:00",
            "language": "ko",
            "status": "processing",
            "error_message": None
        },
        keywords={},
        search_scope=[],
        filters={},
        legal_results=[],
        real_estate_results=[],
        loan_results=[],
        property_search_results=[
            {"id": 1, "name": "강남 아파트 A", "trust_score": 85.5},
            {"id": 2, "name": "강남 아파트 B", "trust_score": 90.0}
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
async def test_property_search_with_trust_score():
    """trust_score가 포함된 매물이 정상 처리되는지 테스트 (Q3)"""
    executor = SearchExecutor()

    property_with_trust = {
        "id": 1,
        "name": "테스트 아파트",
        "trust_score": 85.5,  # 신뢰도 점수 있음
        "price": 45000
    }

    property_without_trust = {
        "id": 2,
        "name": "테스트 빌라",
        "trust_score": None,  # 신뢰도 점수 없음
        "price": 30000
    }

    state = SearchTeamState(
        # ... 기본 필드들
        property_search_results=[property_with_trust, property_without_trust],
        # ...
    )

    result = await executor.aggregate_results_node(state)

    # 검증: trust_score 유무와 관계없이 모두 집계
    assert result["total_results"] == 2
    assert result["property_search_results"][0]["trust_score"] == 85.5
    assert result["property_search_results"][1]["trust_score"] is None
```

---

### 2. Integration Test

**테스트 시나리오**: 실제 쿼리 실행

```python
import pytest
from app.service_agent.execution_agents.search_executor import SearchExecutor
from app.service_agent.foundation.separated_states import SharedState, StateManager

@pytest.mark.asyncio
async def test_property_search_end_to_end():
    """실제 쿼리로 property_search가 동작하는지 테스트"""

    executor = SearchExecutor()

    # 공유 상태 생성 (v2.0: user_id 포함)
    shared_state = StateManager.create_shared_state(
        query="강남구 5억미만 아파트 찾아줘",
        session_id="test-session-123",
        language="ko"
    )
    # user_id는 None (로그인 안한 사용자)

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

    # v2.0 검증: trust_score 포함 확인 (Q3)
    first_property = result["property_search_results"][0]
    assert "trust_score" in first_property, "trust_score 필드가 있어야 함 (None 가능)"


@pytest.mark.asyncio
async def test_property_search_with_nearby_facilities():
    """주변 시설 정보 포함 쿼리 테스트 (Q4)"""
    executor = SearchExecutor()

    # "지하철" 키워드 포함 쿼리
    shared_state = StateManager.create_shared_state(
        query="강남구 5억미만 아파트, 지하철역 근처",
        session_id="test-session-456"
    )

    result = await executor.execute(shared_state=shared_state)

    # 검증: nearby_facilities 포함 확인
    assert result["status"] == "completed"
    first_property = result["property_search_results"][0]

    # nearby_facilities가 있거나 None이어야 함
    if "nearby_facilities" in first_property and first_property["nearby_facilities"]:
        assert "subway_line" in first_property["nearby_facilities"]
        assert "subway_distance" in first_property["nearby_facilities"]


@pytest.mark.asyncio
async def test_property_search_with_agent_info():
    """중개사 정보 포함 확인 테스트 (Q5)"""
    executor = SearchExecutor()

    shared_state = StateManager.create_shared_state(
        query="강남구 아파트 중개사 정보",
        session_id="test-session-789"
    )

    result = await executor.execute(shared_state=shared_state)

    # 검증: agent_info가 데이터 있으면 포함
    assert result["status"] == "completed"

    # 최소 한 개 매물은 agent_info 있어야 함 (데이터 있다고 가정)
    has_agent_info = any(
        p.get("agent_info") is not None
        for p in result["property_search_results"]
    )
    # Note: 데이터 없으면 실패할 수 있음 (테스트 데이터 준비 필요)
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
- [ ] **v2.0**: trust_score 표시 (있는 경우)
- [ ] **v2.0**: nearby_facilities 표시 ("지하철" 키워드 포함 시)
- [ ] **v2.0**: agent_info 표시 (데이터 있는 경우)

---

## 🎯 우선순위 및 예상 효과

### Priority 1 (Critical - 즉시 수정) ⚡

#### ✅ SearchTeamState에 property_search_results 필드 추가
- **파일**: `separated_states.py:76-108`
- **영향**: TypedDict 정의 누락으로 state 업데이트 실패
- **예상 시간**: 2분
- **난이도**: 낮음

#### ✅ SharedState에 user_id 필드 추가 (v2.0)
- **파일**: `separated_states.py:59-70`
- **영향**: 향후 찜 기능, 맞춤 추천 대비
- **예상 시간**: 2분
- **난이도**: 낮음

#### ✅ aggregate_results_node에 property_search_results 집계 로직 추가
- **파일**: `search_executor.py:785-824`
- **영향**: 10개 결과 → 0개 집계 문제 해결
- **예상 시간**: 5분
- **난이도**: 낮음

#### ✅ execute() 메서드 initial_state 수정
- **파일**: `search_executor.py:850-898`
- **영향**: 초기화 시 property_search_results 포함
- **예상 시간**: 2분
- **난이도**: 낮음

#### ✅ StateManager.create_initial_team_state 수정
- **파일**: `separated_states.py:510-526`
- **영향**: 헬퍼 함수 일관성 유지
- **예상 시간**: 2분
- **난이도**: 낮음

**Phase 1 총 예상 시간**: **13분**

---

### Priority 2 (High - 당일 완료) 🔧

#### ⚠️ RealEstateSearchTool에 trust_score JOIN 추가 (Q3)
- **파일**: `real_estate_search_tool.py`
- **영향**: 신뢰도 점수 표시
- **예상 시간**: 15분
- **난이도**: 중간

#### ⚠️ RealEstateSearchTool에 agent_info LEFT JOIN 추가 (Q5)
- **파일**: `real_estate_search_tool.py`, `search_executor.py`
- **영향**: 중개사 정보 표시 (데이터 있을 때만)
- **예상 시간**: 20분
- **난이도**: 중간

#### ⚠️ property_search_results 데이터 구조 문서화
- **파일**: 계획서, README
- **영향**: 프론트엔드 개발자가 데이터 구조 파악
- **예상 시간**: 10분
- **난이도**: 낮음

**Phase 2 총 예상 시간**: **45분**

---

### Priority 3 (Medium - 주간 완료) 📝

#### 📝 finalize_node에 summary 추가 (선택사항)
- **파일**: `search_executor.py:826-848`
- **영향**: Supervisor가 결과 요약 쉽게 읽기
- **예상 시간**: 10분
- **난이도**: 낮음

#### 📝 Unit Test 작성
- **파일**: `backend/tests/test_search_executor.py`
- **영향**: 회귀 테스트 방지
- **예상 시간**: 30분
- **난이도**: 낮음

#### 📝 Integration Test 작성
- **파일**: `backend/tests/test_search_integration.py`
- **영향**: 전체 플로우 검증
- **예상 시간**: 45분
- **난이도**: 중간

**Phase 3 총 예상 시간**: **1시간 25분**

---

### 예상 효과

#### 즉시 효과 (Priority 1 완료 후)
- ✅ "강남구 5억미만 아파트" 쿼리 → 10개 매물 정상 표시
- ✅ MarketDataTool (시세) vs RealEstateSearchTool (개별 매물) 구분 명확
- ✅ LLM이 매물 정보를 받아 상세 응답 생성
- ✅ 로그: "Aggregated 10 results from 1 sources" (property_db)
- ✅ user_id 추가로 향후 확장 대비 완료

#### Priority 2 완료 후 추가 효과
- ✅ 신뢰도 점수 표시 (Q3)
- ✅ 중개사 정보 표시 (Q5)
- ✅ 주변 시설 정보 조건부 표시 (Q4, 이미 구현됨)

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

**After**:
```
강남구에서 5억 미만 아파트 10건을 찾았습니다.

1. 강남 아파트 A
   - 가격: 4억 5천만원
   - 면적: 84㎡ (25평)
   - 신뢰도: ⭐ 85.5점
   - 중개사: ABC공인중개사

2. 강남 아파트 B
   - 가격: 4억 8천만원
   - 면적: 95㎡ (29평)
   - 신뢰도: ⭐ 90.0점
   - 지하철: 2호선 강남역 도보 5분

...
```

---

## 📌 다음 단계

### 1. Phase 1 실행 (즉시)

**수정 순서**:
1. `separated_states.py`: SearchTeamState + SharedState 필드 추가
2. `separated_states.py`: StateManager.create_initial_team_state 수정
3. `search_executor.py`: aggregate_results_node 수정
4. `search_executor.py`: execute() initial_state 수정
5. 코드 검증 (syntax check)

### 2. 서버 재시작 및 테스트
```bash
# 서버 재시작
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*"
cd backend
venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 로그 확인 (Phase 1 검증)
- [ ] "Property search completed: N results" 출력
- [ ] "Aggregated N results from M sources" 출력 (N > 0)
- [ ] "property_db" 소스 포함
- [ ] "Aggregated search: XXXX bytes" (TeamSupervisor)

### 4. 실제 응답 확인
- [ ] 프론트엔드에서 "강남구 5억미만 아파트" 쿼리 실행
- [ ] LLM 응답에 매물 정보 포함 확인
- [ ] WebSocket 메시지에 property_search 데이터 포함 확인

### 5. Phase 2 실행 (당일)
- RealEstateSearchTool에 trust_score JOIN 추가
- RealEstateSearchTool에 agent_info JOIN 추가
- 데이터 구조 문서화

### 6. Phase 3 실행 (주간)
- Unit Test 작성
- Integration Test 작성
- 문서화 완료

### 7. 향후 확장 (Phase 4+)
- 사용자 인증 구현 (Q1)
- 찜 기능 구현 (Q2)
- 계약서 자동 입력 (Q6)

---

## 📚 참고 자료

### 관련 파일 (전체 확인 완료)

**State/Context 정의**:
- `backend/app/service_agent/foundation/separated_states.py`: State 정의

**Executor**:
- `backend/app/service_agent/execution_agents/search_executor.py`: SearchExecutor

**Tools**:
- `backend/app/service_agent/tools/real_estate_search_tool.py`: RealEstateSearchTool
- `backend/app/service_agent/tools/market_data_tool.py`: MarketDataTool
- `backend/app/service_agent/tools/hybrid_legal_search.py`: HybridLegalSearch
- `backend/app/service_agent/tools/loan_data_tool.py`: LoanDataTool
- `backend/app/service_agent/tools/lease_contract_generator_tool.py`: 임대차 계약서 생성

**DB Models**:
- `backend/app/models/real_estate.py`: PostgreSQL 부동산 모델
- `backend/app/models/users.py`: PostgreSQL 사용자 모델
- `backend/app/models/chat.py`: PostgreSQL 채팅 모델
- `backend/app/models/trust.py`: PostgreSQL 신뢰도 점수 모델

**Pydantic Schemas**:
- `backend/app/schemas/real_estate.py`: 부동산 스키마
- `backend/app/schemas/users.py`: 사용자 스키마
- `backend/app/schemas/chat.py`: 채팅 스키마
- `backend/app/schemas/trust.py`: 신뢰도 점수 스키마

**Supervisor**:
- `backend/app/service_agent/supervisor/team_supervisor.py`: TeamSupervisor

---

## ❓ 미결 사항 및 확인 필요 (v2.0)

### ✅ 해결된 사항 (답변 완료)
- Q1: 사용자 인증 → **Yes, user_id를 SharedState에 Optional로 추가**
- Q2: 찜 기능 → **추후 구현**
- Q3: 신뢰도 점수 → **Yes, 포함 (없어도 에러 안남)**
- Q4: 주변 시설 → **Yes, 조건부 포함 (사용자 질문 시만)**
- Q5: 중개사 정보 → **Yes, 조건부 포함 (데이터 있으면)**
- Q6: 계약서 자동 입력 → **추후 구현 (Human-in-the-loop)**
- Q7: LeaseContractGeneratorTool → **사용함 (개발 중)**
- Q8: user_id 포함 여부 → **Yes, Optional[int]로 추가**
- Q9: 데이터 저장 방식 → **Option A 채택 (data만 저장)**

### ⚠️ 확인 필요 (실제 코드 테스트 후)
- team_supervisor.py가 property_search_results를 어떻게 읽는지 확인
- WebSocket 메시지에 property_search_results 포함되는지 확인
- nearby_facilities가 이미 구현되어 있는지 확인 (search_executor.py:663에 include_nearby 있음)

---

## ✅ 승인 체크리스트

수정 전 확인사항:
- [x] 계획서 v2.0 내용 이해
- [x] schemas/models 전체 분석 완료
- [x] 즉시 구현 vs 추후 구현 구분 명확
- [x] 수정 범위 확인 (Phase 1-2 우선 진행)
- [ ] 백업 불필요 (Git으로 버전 관리)
- [ ] 테스트 계획 이해

수정 후 확인사항:
- [ ] 서버 정상 시작
- [ ] 로그에 "Aggregated N results" (N > 0)
- [ ] 실제 쿼리 정상 동작
- [ ] LLM 응답에 매물 정보 포함
- [ ] trust_score 표시 (Priority 2)
- [ ] agent_info 표시 (Priority 2)

---

**승인자**: _______________
**승인일**: 2025-10-13
**다음 검토일**: Phase 1 완료 후

---

## 📊 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0 | 2025-10-13 | 초안 작성 | Claude Code |
| v2.0 | 2025-10-13 | schemas/models 전체 분석 반영, 즉시/추후 구분, user_id 추가, 조건부 포함 전략 | Claude Code |
