# Execution Dashboard 수정 계획서

**작성일**: 2025-11-02
**대상**: `frontend/components/dashboards/execution-dashboard.tsx`
**목적**: 테스트/디버깅을 위한 상세 정보 표시 기능 추가
**작성자**: Claude Code

---

## 📋 목차

1. [현재 상태 분석](#1-현재-상태-분석)
2. [수정 목표](#2-수정-목표)
3. [백엔드 수정 사항](#3-백엔드-수정-사항)
4. [프론트엔드 수정 사항](#4-프론트엔드-수정-사항)
5. [타입 정의 수정](#5-타입-정의-수정)
6. [단계별 구현 계획](#6-단계별-구현-계획)
7. [예상 결과](#7-예상-결과)

---

## 1. 현재 상태 분석

### 1.1 현재 기능

**Execution Dashboard**는 에이전트 실행 과정을 실시간으로 모니터링하는 도구입니다.

#### 표시 정보

| 영역 | 현재 표시 내용 | 한계 |
|------|---------------|------|
| **Query Input** | 사용자 질문 입력 | ✅ 정상 작동 |
| **Team Overview** | 팀별 실행 상태 (search, analysis, document) | ✅ 정상 작동 |
| **Team Steps** | 각 팀의 서브그래프 Step 진행률 | ✅ 정상 작동 |
| **Response Generation** | 답변 생성 단계 | ✅ 정상 작동 |
| **Performance Metrics** | 실행 시간, LLM 호출, 토큰 | ⚠️ 백엔드 미구현 (0으로 표시) |

#### WebSocket 메시지 처리

**현재 처리하는 메시지** (8개):

```typescript
✅ connected
✅ execution_start
✅ agent_steps_initialized
✅ agent_step_progress
✅ todo_updated
✅ response_generating_start
✅ response_generating_progress
✅ final_response
```

### 1.2 부족한 기능 (테스트/디버깅 관점)

| 필요 기능 | 현재 | 문제점 |
|----------|------|--------|
| **파라미터 추출 확인** | ❌ 없음 | 지역, 매물타입, 가격이 제대로 추출되었는지 확인 불가 |
| **검색 결과 개수** | ❌ 없음 | 각 툴이 몇 개의 결과를 반환했는지 확인 불가 |
| **툴 실행 시간** | ❌ 없음 | 어느 툴이 느린지 확인 불가 |
| **에러 상세 정보** | △ 부분 | "실패"만 표시, 구체적 에러 메시지 없음 |
| **SQL 쿼리 로그** | ❌ 없음 | 실제 실행된 쿼리 확인 불가 |
| **LLM 의사결정** | ❌ 없음 | 어떤 툴을 선택했는지, confidence는 얼마인지 확인 불가 |

---

## 2. 수정 목표

### 2.1 핵심 목표

> **"로그 파일을 뒤적이지 않고, UI로 모든 디버깅 정보를 확인"**

### 2.2 구체적 목표

#### Phase 1: 검색 파라미터 및 결과 추적 (우선순위 높음)

- [x] 사용자 쿼리에서 추출된 파라미터 표시
- [x] 각 툴의 검색 결과 개수 표시
- [x] 툴별 실행 시간 표시
- [x] 에러 메시지 상세 표시

#### Phase 2: LLM 의사결정 추적 (우선순위 중간)

- [x] LLM이 선택한 툴 목록
- [x] 선택 이유 (reasoning)
- [x] Confidence score
- [x] Fallback 여부

#### Phase 3: SQL 쿼리 로그 (선택사항, 개발 모드 전용)

- [x] 실행된 SQL 쿼리 요약
- [x] WHERE 절 조건
- [x] 결과 행 개수

---

## 3. 백엔드 수정 사항

### 3.1 새로운 WebSocket 메시지 추가

#### Message 1: `search_params_extracted` (파라미터 추출)

**위치**: `backend/app/service_agent/execution_agents/search_executor.py:584`

**추가 코드**:

```python
# execute_search_node 메서드 내부
async def execute_search_node(self, state: SearchTeamState) -> SearchTeamState:
    # ... (기존 코드)

    # 쿼리 추출
    query = shared_context.get("user_query", "") or shared_context.get("query", "")

    # 파라미터 추출 (기존 로직)
    region = self._extract_region(query)
    property_type = self._extract_property_type(query)
    min_price, max_price = self._extract_price_range(query)

    # 🆕 프론트엔드로 파라미터 전송
    if self.progress_callback:
        await self.progress_callback("search_params_extracted", {
            "agentName": "search",
            "params": {
                "region": region,
                "property_type": property_type,
                "min_price": min_price,
                "max_price": max_price,
                "query": query
            }
        })

    # ... (기존 검색 로직 계속)
```

**메시지 형식**:

```json
{
    "type": "search_params_extracted",
    "agentName": "search",
    "params": {
        "region": "강남구",
        "property_type": "APARTMENT",
        "min_price": null,
        "max_price": 500000000,
        "query": "강남구 5억 이하 아파트"
    }
}
```

#### Message 2: `tool_execution_result` (툴 실행 결과)

**위치**: `backend/app/service_agent/execution_agents/search_executor.py:638`

**추가 코드**:

```python
# 법률 검색 완료 후
if result.get("status") == "success":
    legal_data = result.get("data", [])

    state["legal_results"] = [...]  # 기존 코드

    # 🆕 프론트엔드로 결과 전송
    if self.progress_callback:
        await self.progress_callback("tool_execution_result", {
            "agentName": "search",
            "tool": "legal_search",
            "result_count": len(legal_data),
            "execution_time_ms": int((time.time() - tool_start_time) * 1000),
            "status": "success"
        })
```

**메시지 형식**:

```json
{
    "type": "tool_execution_result",
    "agentName": "search",
    "tool": "legal_search",
    "result_count": 5,
    "execution_time_ms": 1200,
    "status": "success"
}
```

#### Message 3: `tool_selection_decision` (LLM 툴 선택)

**위치**: `backend/app/service_agent/execution_agents/search_executor.py:456`

**추가 코드**:

```python
# _select_tools_with_llm 메서드 내부
async def _select_tools_with_llm(self, query: str, keywords: SearchKeywords = None):
    # ... (기존 LLM 호출 로직)

    selected_tools = result.get("selected_tools", [])
    reasoning = result.get("reasoning", "")
    confidence = result.get("confidence", 0.0)

    # 🆕 프론트엔드로 의사결정 정보 전송
    if self.progress_callback:
        await self.progress_callback("tool_selection_decision", {
            "agentName": "search",
            "selected_tools": selected_tools,
            "reasoning": reasoning,
            "confidence": confidence,
            "is_fallback": False
        })

    # ... (기존 코드 계속)
```

**메시지 형식**:

```json
{
    "type": "tool_selection_decision",
    "agentName": "search",
    "selected_tools": ["legal_search", "market_data"],
    "reasoning": "전세금 인상률은 법률 정보가 필요하고, 강남구 시세는 부동산 시세 정보가 필요합니다.",
    "confidence": 0.95,
    "is_fallback": false
}
```

#### Message 4: `sql_query_executed` (개발 모드 전용)

**위치**: `backend/app/service_agent/tools/market_data_tool.py:196`

**추가 코드**:

```python
# _query_market_data 메서드 내부
def _query_market_data(self, db: Session, region: str, ...):
    # ... (기존 쿼리 구성)

    results = query.all()

    # 🆕 개발 모드에서만 SQL 로그 전송
    if settings.DEBUG and hasattr(self, 'progress_callback') and self.progress_callback:
        await self.progress_callback("sql_query_executed", {
            "tool": "market_data",
            "query_summary": f"SELECT ... WHERE region LIKE '%{region}%' GROUP BY ...",
            "result_count": len(results),
            "filters": {
                "region": region,
                "property_type": property_type
            }
        })

    return results
```

**메시지 형식**:

```json
{
    "type": "sql_query_executed",
    "tool": "market_data",
    "query_summary": "SELECT ... WHERE region LIKE '%강남구%' GROUP BY region, property_type",
    "result_count": 3,
    "filters": {
        "region": "강남구",
        "property_type": "APARTMENT"
    }
}
```

### 3.2 백엔드 수정 파일 목록

| 파일 | 수정 내용 | 우선순위 |
|------|----------|---------|
| `search_executor.py` | `search_params_extracted`, `tool_selection_decision` 메시지 추가 | 높음 |
| `search_executor.py` | `tool_execution_result` 메시지 추가 (각 툴마다) | 높음 |
| `market_data_tool.py` | `sql_query_executed` 메시지 추가 (개발 모드) | 낮음 |
| `real_estate_search_tool.py` | `sql_query_executed` 메시지 추가 (개발 모드) | 낮음 |

---

## 4. 프론트엔드 수정 사항

### 4.1 새로운 카드 컴포넌트

#### Component 1: `SearchParamsCard` (검색 파라미터)

**파일**: `frontend/components/dashboards/execution-dashboard.tsx`

**위치**: Line 408 이후 (Sub Components 섹션)

**코드**:

```tsx
function SearchParamsCard({ data }: { data: SearchParams }) {
  return (
    <Card className="p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🔍</span>
          <h3 className="text-lg font-semibold">추출된 검색 파라미터</h3>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="p-2 bg-background rounded border border-border">
            <div className="text-xs text-muted-foreground mb-1">원본 쿼리</div>
            <div className="text-sm font-medium">{data.query}</div>
          </div>

          <div className="p-2 bg-background rounded border border-border">
            <div className="text-xs text-muted-foreground mb-1">지역</div>
            <div className="text-sm font-medium">
              {data.region || <span className="text-red-500">추출 실패 ❌</span>}
            </div>
          </div>

          <div className="p-2 bg-background rounded border border-border">
            <div className="text-xs text-muted-foreground mb-1">매물 타입</div>
            <div className="text-sm font-medium">
              {data.property_type || <span className="text-gray-500">없음</span>}
            </div>
          </div>

          <div className="p-2 bg-background rounded border border-border">
            <div className="text-xs text-muted-foreground mb-1">가격 범위</div>
            <div className="text-sm font-medium">
              {data.min_price && `${(data.min_price / 10000).toLocaleString()}만원 ~`}
              {data.max_price && `${(data.max_price / 10000).toLocaleString()}만원`}
              {!data.min_price && !data.max_price && <span className="text-gray-500">제한 없음</span>}
            </div>
          </div>
        </div>

        {/* 경고: 지역 추출 실패 시 */}
        {!data.region && (
          <div className="p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
            <div className="text-xs text-red-600 flex items-center gap-2">
              ⚠️ 지역이 추출되지 않았습니다. 검색 결과가 부정확할 수 있습니다.
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}
```

#### Component 2: `ToolResultsCard` (툴별 결과)

**코드**:

```tsx
function ToolResultsCard({ data }: { data: Record<string, ToolExecutionResult> }) {
  const toolLabels: Record<string, string> = {
    legal_search: "법률 검색",
    market_data: "시세 조회",
    real_estate_search: "매물 검색",
    loan_data: "대출 정보"
  }

  return (
    <Card className="p-4">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">📊</span>
          <h3 className="text-lg font-semibold">툴 실행 결과</h3>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {Object.entries(data).map(([tool, result]) => (
            <div
              key={tool}
              className={`
                p-3 rounded-lg border
                ${result.status === "success"
                  ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                  : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"}
              `}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold">
                  {toolLabels[tool] || tool}
                </div>
                <div className="text-xs text-muted-foreground">
                  {result.execution_time_ms}ms
                </div>
              </div>

              <div className="flex items-center gap-2">
                {result.status === "success" ? (
                  <>
                    <span className="text-green-600">✓</span>
                    <span className="text-sm font-bold">{result.result_count}개</span>
                  </>
                ) : (
                  <>
                    <span className="text-red-600">✗</span>
                    <span className="text-sm text-red-600">실패</span>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}
```

#### Component 3: `ToolSelectionCard` (LLM 툴 선택)

**코드**:

```tsx
function ToolSelectionCard({ data }: { data: ToolSelectionDecision }) {
  return (
    <Card className="p-4 bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          <h3 className="text-lg font-semibold">LLM 툴 선택</h3>
          {data.is_fallback && (
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
              Fallback
            </span>
          )}
        </div>

        <div className="space-y-2">
          {/* 선택된 툴 */}
          <div className="p-2 bg-background rounded border border-border">
            <div className="text-xs text-muted-foreground mb-1">선택된 툴</div>
            <div className="flex flex-wrap gap-1">
              {data.selected_tools.map(tool => (
                <span key={tool} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                  {tool}
                </span>
              ))}
            </div>
          </div>

          {/* Confidence */}
          <div className="p-2 bg-background rounded border border-border">
            <div className="text-xs text-muted-foreground mb-1">Confidence</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    data.confidence >= 0.8 ? "bg-green-500" :
                    data.confidence >= 0.6 ? "bg-yellow-500" : "bg-red-500"
                  }`}
                  style={{ width: `${data.confidence * 100}%` }}
                />
              </div>
              <span className="text-sm font-semibold">
                {(data.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Reasoning */}
          <div className="p-2 bg-background rounded border border-border">
            <div className="text-xs text-muted-foreground mb-1">선택 이유</div>
            <div className="text-sm">{data.reasoning}</div>
          </div>
        </div>
      </div>
    </Card>
  )
}
```

#### Component 4: `SQLQueryLogCard` (SQL 쿼리 로그, 개발 모드)

**코드**:

```tsx
function SQLQueryLogCard({ data }: { data: SQLQueryLog[] }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <Card className="p-4 bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">💾</span>
            <h3 className="text-lg font-semibold">SQL 쿼리 로그</h3>
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
              Dev Only
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? "숨기기" : "펼치기"}
          </Button>
        </div>

        {isExpanded && (
          <div className="space-y-2">
            {data.map((log, idx) => (
              <div key={idx} className="p-2 bg-background rounded border border-border">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold">{log.tool}</span>
                  <span className="text-xs text-muted-foreground">
                    {log.result_count}행
                  </span>
                </div>
                <div className="text-xs font-mono text-muted-foreground">
                  {log.query_summary}
                </div>
                {log.filters && (
                  <div className="text-xs text-muted-foreground mt-1">
                    필터: {JSON.stringify(log.filters)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}
```

### 4.2 WebSocket 메시지 핸들러 추가

**위치**: `execution-dashboard.tsx:37` (handleWSMessage 함수 내부)

**추가 코드**:

```tsx
const handleWSMessage = useCallback((message: WSMessage) => {
  console.log("[ExecutionDashboard] Received:", message.type)

  switch (message.type) {
    // ... (기존 케이스들)

    case "search_params_extracted":
      setDashboardState((prev) => ({
        ...prev,
        search_params: message.params
      }))
      break

    case "tool_execution_result":
      setDashboardState((prev) => ({
        ...prev,
        tool_results: {
          ...prev.tool_results,
          [message.tool]: {
            result_count: message.result_count,
            execution_time_ms: message.execution_time_ms,
            status: message.status
          }
        }
      }))
      break

    case "tool_selection_decision":
      setDashboardState((prev) => ({
        ...prev,
        tool_selection: {
          selected_tools: message.selected_tools,
          reasoning: message.reasoning,
          confidence: message.confidence,
          is_fallback: message.is_fallback
        }
      }))
      break

    case "sql_query_executed":
      setDashboardState((prev) => ({
        ...prev,
        sql_logs: [
          ...(prev.sql_logs || []),
          {
            tool: message.tool,
            query_summary: message.query_summary,
            result_count: message.result_count,
            filters: message.filters
          }
        ]
      }))
      break
  }
}, [])
```

### 4.3 UI에 카드 추가

**위치**: `execution-dashboard.tsx:272` (Content 섹션)

**추가 코드**:

```tsx
{/* Content */}
<div className="flex-1 overflow-y-auto px-6 py-4">
  <div className="max-w-6xl mx-auto space-y-4">
    {/* ... (기존 카드들) */}

    {/* 🆕 Search Params Card */}
    {dashboardState.search_params && (
      <SearchParamsCard data={dashboardState.search_params} />
    )}

    {/* 🆕 Tool Selection Card */}
    {dashboardState.tool_selection && (
      <ToolSelectionCard data={dashboardState.tool_selection} />
    )}

    {/* Team Overview (기존) */}
    {dashboardState.active_teams.length > 0 && (
      <Card className="p-4">...</Card>
    )}

    {/* 🆕 Tool Results Card */}
    {dashboardState.tool_results && Object.keys(dashboardState.tool_results).length > 0 && (
      <ToolResultsCard data={dashboardState.tool_results} />
    )}

    {/* 🆕 SQL Query Log Card (개발 모드) */}
    {process.env.NODE_ENV === "development" && dashboardState.sql_logs && dashboardState.sql_logs.length > 0 && (
      <SQLQueryLogCard data={dashboardState.sql_logs} />
    )}

    {/* ... (기존 카드들) */}
  </div>
</div>
```

---

## 5. 타입 정의 수정

### 5.1 파일 위치

**파일**: `frontend/types/execution.ts`

### 5.2 추가할 타입

**위치**: Line 115 이후

**코드**:

```typescript
// ============================================================================
// 🆕 Debugging & Testing Types
// ============================================================================

export interface SearchParams {
  query: string
  region?: string | null
  property_type?: string | null
  min_price?: number | null
  max_price?: number | null
  min_area?: number | null
  max_area?: number | null
}

export interface ToolExecutionResult {
  result_count: number
  execution_time_ms: number
  status: "success" | "failed" | "error"
  error?: string
}

export interface ToolSelectionDecision {
  selected_tools: string[]
  reasoning: string
  confidence: number
  is_fallback: boolean
}

export interface SQLQueryLog {
  tool: string
  query_summary: string
  result_count: number
  filters?: Record<string, any>
}

// ============================================================================
// 🆕 Extended ExecutionDashboardState
// ============================================================================

export interface ExecutionDashboardState {
  query?: string
  active_teams: TeamExecutionState[]
  response_generation?: ResponseGenerationState
  performance_metrics?: PerformanceMetrics
  status: "idle" | "executing" | "generating" | "completed" | "error"

  // 🆕 Debugging 정보
  search_params?: SearchParams
  tool_results?: Record<string, ToolExecutionResult>
  tool_selection?: ToolSelectionDecision
  sql_logs?: SQLQueryLog[]
}
```

---

## 6. 단계별 구현 계획

### Phase 1: 검색 파라미터 추적 (1-2일)

#### Step 1.1: 백엔드 메시지 추가

**우선순위**: 높음
**예상 시간**: 2시간

- [ ] `search_executor.py`에 `search_params_extracted` 메시지 추가
- [ ] 파라미터 추출 후 WebSocket으로 전송
- [ ] 테스트: WebSocket 메시지 수신 확인

**검증 방법**:
```bash
# 브라우저 개발자 도구 Console
WebSocket 메시지: search_params_extracted 수신 확인
```

#### Step 1.2: 프론트엔드 타입 추가

**우선순위**: 높음
**예상 시간**: 30분

- [ ] `types/execution.ts`에 `SearchParams` 타입 추가
- [ ] `ExecutionDashboardState`에 `search_params` 필드 추가

#### Step 1.3: 프론트엔드 UI 구현

**우선순위**: 높음
**예상 시간**: 1시간

- [ ] `SearchParamsCard` 컴포넌트 구현
- [ ] WebSocket 핸들러에 `search_params_extracted` 케이스 추가
- [ ] UI에 카드 추가

**검증 방법**:
```
1. 질문 입력: "강남구 5억 이하 아파트"
2. SearchParamsCard 확인:
   - 지역: 강남구 ✓
   - 매물타입: APARTMENT ✓
   - 최대가격: 500000000 ✓
```

---

### Phase 2: 툴 실행 결과 추적 (1-2일)

#### Step 2.1: 백엔드 메시지 추가

**우선순위**: 높음
**예상 시간**: 3시간

- [ ] `search_executor.py`에 `tool_execution_result` 메시지 추가
- [ ] 각 툴 실행 후 결과 전송 (legal_search, market_data, loan_data, real_estate_search)
- [ ] 실행 시간 측정 추가

**검증 방법**:
```bash
# 로그 확인
[INFO] Tool execution result sent: legal_search, 5 results, 1200ms
```

#### Step 2.2: 프론트엔드 UI 구현

**우선순위**: 높음
**예상 시간**: 1.5시간

- [ ] `ToolResultsCard` 컴포넌트 구현
- [ ] WebSocket 핸들러에 `tool_execution_result` 케이스 추가
- [ ] UI에 카드 추가

**검증 방법**:
```
ToolResultsCard 확인:
- 법률 검색: ✓ 5개 (1200ms)
- 시세 조회: ✓ 3개 (800ms)
- 매물 검색: ✓ 12개 (2100ms)
```

---

### Phase 3: LLM 툴 선택 추적 (1일)

#### Step 3.1: 백엔드 메시지 추가

**우선순위**: 중간
**예상 시간**: 1시간

- [ ] `search_executor.py`의 `_select_tools_with_llm` 메서드 수정
- [ ] `tool_selection_decision` 메시지 추가
- [ ] Fallback 여부 포함

#### Step 3.2: 프론트엔드 UI 구현

**우선순위**: 중간
**예상 시간**: 1.5시간

- [ ] `ToolSelectionCard` 컴포넌트 구현
- [ ] Confidence 진행바 추가
- [ ] Fallback 표시

**검증 방법**:
```
ToolSelectionCard 확인:
- 선택된 툴: legal_search, market_data
- Confidence: 95%
- 선택 이유: "전세금 인상률은 법률 정보가 필요하고..."
```

---

### Phase 4: SQL 쿼리 로그 (선택사항, 1일)

#### Step 4.1: 백엔드 메시지 추가

**우선순위**: 낮음
**예상 시간**: 2시간

- [ ] `market_data_tool.py`에 `sql_query_executed` 메시지 추가
- [ ] `real_estate_search_tool.py`에 `sql_query_executed` 메시지 추가
- [ ] 개발 모드에서만 활성화 (`if settings.DEBUG`)

#### Step 4.2: 프론트엔드 UI 구현

**우선순위**: 낮음
**예상 시간**: 1시간

- [ ] `SQLQueryLogCard` 컴포넌트 구현
- [ ] 펼치기/숨기기 토글 추가
- [ ] 개발 모드에서만 표시

---

### 전체 일정

| Phase | 내용 | 예상 시간 | 우선순위 |
|-------|------|----------|---------|
| Phase 1 | 검색 파라미터 추적 | 3.5시간 | 높음 |
| Phase 2 | 툴 실행 결과 추적 | 4.5시간 | 높음 |
| Phase 3 | LLM 툴 선택 추적 | 2.5시간 | 중간 |
| Phase 4 | SQL 쿼리 로그 | 3시간 | 낮음 |
| **합계** | | **13.5시간** | **약 2일** |

---

## 7. 예상 결과

### 7.1 테스트 시나리오

**쿼리**: "강남구 5억 이하 아파트 전세금 인상률"

### 7.2 대시보드 UI (수정 후)

```
┌─────────────────────────────────────────────────────────────┐
│  ⚙️ Execution Test Dashboard                                │
│  에이전트 실행 및 성능 테스트 모니터링                        │
│                                           [🟢 연결됨] [초기화] │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  실행 중인 질문: 강남구 5억 이하 아파트 전세금 인상률         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🔍 추출된 검색 파라미터                                      │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │ 원본 쿼리    │ 지역         │ 매물 타입    │ 가격 범위│  │
│  │ 강남구 5억..  │ 강남구 ✓    │ APARTMENT ✓ │ ~5억 ✓  │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🤖 LLM 툴 선택                                               │
│  선택된 툴: [legal_search] [market_data] [real_estate_search]│
│  Confidence: ████████████████░░░░ 95%                        │
│  선택 이유: 전세금 인상률은 법률 정보가 필요하고, 강남구...  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  팀 현황                                          2/3 완료    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 🔍 검색 팀 (search)                    Step 4/4  [완료] ││
│  │ 전체 진행률: ████████████████████████ 100%              ││
│  │ ✓ Step 1: 쿼리 생성                                     ││
│  │ ✓ Step 2: 데이터 검색                                   ││
│  │ ✓ Step 3: 결과 필터링                                   ││
│  │ ✓ Step 4: 결과 정리                                     ││
│  │ ⏱️ 소요 시간: 2.3초                                      ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  📊 툴 실행 결과                                              │
│  ┌──────────────────┬──────────────────┬──────────────────┐ │
│  │ 법률 검색 ✓      │ 시세 조회 ✓      │ 매물 검색 ✓      │ │
│  │ 5개 | 1200ms     │ 3개 | 800ms      │ 12개 | 2100ms    │ │
│  └──────────────────┴──────────────────┴──────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  💾 SQL 쿼리 로그 (Dev Only)                    [펼치기]     │
│  (숨김)                                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  📊 Performance Metrics                                      │
│  ┌─────────┬─────────┬─────────┬─────────┐                 │
│  │ 총 시간 │ LLM 호출│ 평균 시간│ 토큰   │                 │
│  │ 2.3s    │ 2       │ 0.8s    │ 1,234   │                 │
│  └─────────┴─────────┴─────────┴─────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 디버깅 시나리오

#### 시나리오 1: 지역 추출 실패

**문제 발견**:
```
🔍 추출된 검색 파라미터
- 지역: 추출 실패 ❌
⚠️ 지역이 추출되지 않았습니다. 검색 결과가 부정확할 수 있습니다.
```

**조치**:
1. 백엔드 로그 확인 (선택사항)
2. 파라미터 추출 로직 수정 (`_extract_region`)
3. 재테스트

#### 시나리오 2: 검색 결과 없음

**문제 발견**:
```
📊 툴 실행 결과
- 법률 검색 ✓: 0개 | 1200ms
- 시세 조회 ✗: 실패
- 매물 검색 ✓: 0개 | 2100ms
```

**조치**:
1. 시세 조회 실패 원인 확인 (에러 메시지)
2. SQL 쿼리 로그 확인 (개발 모드)
3. DB 데이터 확인

#### 시나리오 3: LLM Confidence 낮음

**문제 발견**:
```
🤖 LLM 툴 선택
Confidence: ████░░░░░░░░░░░░░░░░ 25%
[Fallback] 배지 표시
```

**조치**:
1. Fallback 원인 확인
2. LLM 프롬프트 개선
3. 재테스트

---

## 8. 체크리스트

### 백엔드 수정

- [ ] `search_executor.py`: `search_params_extracted` 메시지 추가
- [ ] `search_executor.py`: `tool_execution_result` 메시지 추가
- [ ] `search_executor.py`: `tool_selection_decision` 메시지 추가
- [ ] `market_data_tool.py`: `sql_query_executed` 메시지 추가 (선택)
- [ ] `real_estate_search_tool.py`: `sql_query_executed` 메시지 추가 (선택)

### 프론트엔드 수정

- [ ] `types/execution.ts`: 새로운 타입 정의 추가
- [ ] `execution-dashboard.tsx`: WebSocket 핸들러 추가
- [ ] `execution-dashboard.tsx`: `SearchParamsCard` 컴포넌트 구현
- [ ] `execution-dashboard.tsx`: `ToolResultsCard` 컴포넌트 구현
- [ ] `execution-dashboard.tsx`: `ToolSelectionCard` 컴포넌트 구현
- [ ] `execution-dashboard.tsx`: `SQLQueryLogCard` 컴포넌트 구현 (선택)
- [ ] `execution-dashboard.tsx`: UI에 카드 추가

### 테스트

- [ ] WebSocket 메시지 수신 확인
- [ ] 파라미터 추출 정확도 확인
- [ ] 검색 결과 개수 확인
- [ ] LLM 툴 선택 확인
- [ ] Performance Metrics 확인

---

## 9. 참고 자료

### 관련 파일

| 파일 | 경로 | 역할 |
|------|------|------|
| SearchExecutor | `backend/app/service_agent/execution_agents/search_executor.py` | 검색 에이전트 |
| MarketDataTool | `backend/app/service_agent/tools/market_data_tool.py` | 시세 조회 툴 |
| RealEstateSearchTool | `backend/app/service_agent/tools/real_estate_search_tool.py` | 매물 검색 툴 |
| Execution Dashboard | `frontend/components/dashboards/execution-dashboard.tsx` | 대시보드 UI |
| Execution Types | `frontend/types/execution.ts` | 타입 정의 |

### 기술 스택

- **백엔드**: Python, FastAPI, WebSocket, SQLAlchemy
- **프론트엔드**: Next.js, React, TypeScript, Tailwind CSS
- **통신**: WebSocket (JSON 메시지)

---

**계획서 작성 완료**
**예상 구현 기간**: 2일 (Phase 1-2 우선 구현, Phase 3-4 선택사항)
**최종 검증**: 실제 질문으로 E2E 테스트
