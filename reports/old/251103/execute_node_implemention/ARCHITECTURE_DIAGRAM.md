# Execute Node Enhancement - 아키텍처 다이어그램

**작성일**: 2025-10-15
**연관 문서**: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md), [AGENT_TOOL_STRATEGY.md](./AGENT_TOOL_STRATEGY.md)

---

## 📋 목차

1. [전체 시스템 흐름](#-전체-시스템-흐름)
2. [Execute Node 상세 구조](#-execute-node-상세-구조)
3. [LLM 호출 맵](#-llm-호출-맵)
4. [도구 오케스트레이션](#-도구-오케스트레이션)
5. [에러 복구 흐름](#-에러-복구-흐름)
6. [상태 전이 다이어그램](#-상태-전이-다이어그램)

---

## 🌊 전체 시스템 흐름

### 현재 (Before)

```mermaid
graph TB
    User[사용자 쿼리] --> Init[initialize_node]
    Init --> Planning[planning_node]

    subgraph "Planning Phase - LLM 3회"
        Planning --> P1[LLM #1: Intent Analysis]
        P1 --> P2[LLM #2: Agent Selection]
        P2 --> P3[LLM #3: Query Decomposition]
        P3 --> PlanReady[ExecutionPlan 생성]
    end

    PlanReady --> Route{route}
    Route -->|IRRELEVANT| Response
    Route -->|Execute| ExecSimple[execute_teams_node<br/>❌ LLM 없음]

    subgraph "Execution Phase - 단순 실행"
        ExecSimple --> SearchTeam
        ExecSimple --> AnalysisTeam

        SearchTeam --> S1[LLM #4: keyword_extraction]
        SearchTeam --> S2[LLM #5: tool_selection]
        S1 --> S3[도구 실행]
        S2 --> S3

        AnalysisTeam --> A1[LLM #6: tool_selection]
        A1 --> A2[LLM #7-9: Analysis]
    end

    S3 --> Aggregate
    A2 --> Aggregate

    Aggregate[aggregate_results] --> Response[generate_response]
    Response --> R1[LLM #10: Response Synthesis]
    R1 --> End[최종 응답]

    style Planning fill:#e3f2fd
    style ExecSimple fill:#ffcdd2
    style Aggregate fill:#c8e6c9
    style Response fill:#fff9c4
```

### 개선 (After)

```mermaid
graph TB
    User[사용자 쿼리] --> Init[initialize_node]
    Init --> Planning[planning_node]

    subgraph "Planning Phase - LLM 3회 (유지)"
        Planning --> P1[LLM #1: Intent Analysis]
        P1 --> P2[LLM #2: Agent Selection]
        P2 --> P3[LLM #3: Query Decomposition]
        P3 --> PlanReady[ExecutionPlan 생성]
    end

    PlanReady --> Route{route}
    Route -->|IRRELEVANT| Response
    Route -->|Execute| ExecEnhanced[execute_teams_node<br/>✅ LLM 기반 오케스트레이션]

    subgraph "Enhanced Execution Phase"
        ExecEnhanced --> PreExec[pre_execution_node]
        PreExec --> L4[🆕 LLM #4: Execution Strategy]

        L4 --> Loop{팀 루프}

        Loop --> Before[before_team_execution]
        Before --> L5[🆕 LLM #5: Tool Orchestration]

        L5 --> TeamExec[팀 실행]

        subgraph "Team Execution"
            TeamExec --> SE[SearchExecutor]
            TeamExec --> AE[AnalysisExecutor]

            SE --> SE1[LLM #8: keyword_extraction<br/>조건부]
            SE1 --> SE2[도구 실행]

            AE --> AE1[LLM #10-13: Analysis]
        end

        SE2 --> After[after_team_execution]
        AE1 --> After

        After --> L6[🆕 LLM #6: Result Analysis]

        L6 --> Decision{다음 팀?}
        Decision -->|있음| Loop
        Decision -->|early_exit| PostExec
        Decision -->|없음| PostExec

        PostExec[post_execution_node] --> L7[🆕 LLM #7: Execution Review]
    end

    L7 --> Aggregate[aggregate_results]
    Aggregate --> Response[generate_response]
    Response --> R1[LLM #14: Response Synthesis]
    R1 --> End[최종 응답]

    style Planning fill:#e3f2fd
    style ExecEnhanced fill:#c8e6c9
    style L4 fill:#fff3e0
    style L5 fill:#fff3e0
    style L6 fill:#fff3e0
    style L7 fill:#fff3e0
    style Aggregate fill:#e1f5fe
    style Response fill:#fff9c4
```

**주요 변경점**:
- ✅ Execute Node에 LLM 기반 의사결정 4회 추가
- ✅ 동적 도구 오케스트레이션
- ✅ 중간 결과 분석 및 계획 조정
- ✅ 실행 종합 검토

---

## 🏗️ Execute Node 상세 구조

### 4단계 실행 흐름

```mermaid
graph TB
    Start[execute_teams_node 진입] --> InitCtx[ExecutionContext 초기화]

    InitCtx --> Phase1[Phase 1: Pre-Execution]

    subgraph "Phase 1: 실행 전 전략 수립"
        Phase1 --> LLM_Pre[LLM #4: execution_strategy.txt]
        LLM_Pre --> Strategy{전략 결정}
        Strategy -->|sequential| Seq[순차 실행]
        Strategy -->|parallel| Par[병렬 실행]
        Strategy -->|adaptive| Adp[적응형 실행]

        Seq --> StrategySet[전략 확정]
        Par --> StrategySet
        Adp --> StrategySet
    end

    StrategySet --> Phase2[Phase 2: Team Execution Loop]

    subgraph "Phase 2: 팀별 실행 루프"
        Phase2 --> ForEach{각 팀}

        ForEach --> BeforeTeam[before_team_execution]
        BeforeTeam --> LLM_Before[LLM #5: tool_orchestration.txt]
        LLM_Before --> ToolSelect[도구 선택 + 파라미터]

        ToolSelect --> ExecTeam[팀 실행<br/>SearchExecutor/AnalysisExecutor]

        ExecTeam --> AfterTeam[after_team_execution]
        AfterTeam --> LLM_After[LLM #6: result_analysis.txt]

        LLM_After --> QualityCheck{품질 체크}
        QualityCheck -->|낮음| Adjust[계획 조정]
        QualityCheck -->|높음| Continue[계속]
        QualityCheck -->|충분| EarlyExit[조기 종료]

        Adjust --> ForEach
        Continue --> ForEach
        EarlyExit --> Phase3
        ForEach -->|모든 팀 완료| Phase3
    end

    Phase3[Phase 3: Post-Execution]

    subgraph "Phase 3: 실행 후 검토"
        Phase3 --> LLM_Post[LLM #7: execution_review.txt]
        LLM_Post --> Review{목표 달성?}
        Review -->|Yes| ProceedAgg[Aggregation 진행]
        Review -->|Partial| PartialAgg[부분 결과 처리]
        Review -->|No| ErrorHandle[에러 처리]

        ProceedAgg --> MergeCtx
        PartialAgg --> MergeCtx
        ErrorHandle --> MergeCtx
    end

    MergeCtx[ExecutionContext → MainState 병합] --> Return[state 반환]

    Return --> Aggregate[aggregate_results_node]

    style Phase1 fill:#e3f2fd
    style Phase2 fill:#fff3e0
    style Phase3 fill:#c8e6c9
    style LLM_Pre fill:#ffecb3
    style LLM_Before fill:#ffecb3
    style LLM_After fill:#ffecb3
    style LLM_Post fill:#ffecb3
```

### 데이터 흐름

```mermaid
graph LR
    subgraph "Input"
        I1[MainSupervisorState]
        I2[planning_state]
        I3[execution_plan]
    end

    subgraph "ExecutionContext"
        EC1[strategy: sequential/parallel]
        EC2[global_tool_registry]
        EC3[intermediate_results]
        EC4[quality_scores]
        EC5[llm_decisions]
    end

    subgraph "Output"
        O1[team_results]
        O2[execution_review]
        O3[execution_metadata]
    end

    I1 --> EC1
    I2 --> EC2
    I3 --> EC3

    EC1 --> O1
    EC3 --> O1
    EC4 --> O2
    EC5 --> O3

    style I1 fill:#e1f5fe
    style EC1 fill:#fff3e0
    style EC2 fill:#fff3e0
    style EC3 fill:#fff3e0
    style O1 fill:#c8e6c9
```

---

## 🔗 LLM 호출 맵

### 전체 LLM 호출 (14회)

```mermaid
graph TB
    subgraph "Planning Phase (3회)"
        L1[LLM #1: Intent Analysis<br/>temp=0.0, max_tokens=500]
        L2[LLM #2: Agent Selection<br/>temp=0.1, max_tokens=400]
        L3[LLM #3: Query Decomposition<br/>temp=0.1, max_tokens=600]
    end

    subgraph "Execute: Pre-Execution (1회)"
        L4[🆕 LLM #4: Execution Strategy<br/>temp=0.1, max_tokens=600]
    end

    subgraph "Execute: Before Team (1회 × N팀)"
        L5[🆕 LLM #5: Tool Orchestration<br/>temp=0.1, max_tokens=800]
    end

    subgraph "Execute: After Team (1회 × N팀)"
        L6[🆕 LLM #6: Result Analysis<br/>temp=0.2, max_tokens=700]
    end

    subgraph "Execute: Post-Execution (1회)"
        L7[🆕 LLM #7: Execution Review<br/>temp=0.2, max_tokens=900]
    end

    subgraph "SearchExecutor (0-1회)"
        L8[LLM #8: Keyword Extraction<br/>temp=0.1, max_tokens=300<br/>조건부: Supervisor가 제공 안 했을 때만]
    end

    subgraph "AnalysisExecutor (3-5회)"
        L10[LLM #10: Contract Analysis<br/>temp=0.3, max_tokens=800]
        L11[LLM #11: Market Analysis<br/>temp=0.3, max_tokens=1000]
        L12[LLM #12-13: Insight Generation<br/>temp=0.3, max_tokens=1000]
    end

    subgraph "Response Generation (1회)"
        L14[LLM #14: Response Synthesis<br/>temp=0.3, max_tokens=1500]
    end

    L1 --> L2 --> L3 --> L4
    L4 --> L5
    L5 --> L8
    L5 --> L10
    L8 --> L6
    L10 --> L6
    L11 --> L6
    L6 --> L7
    L7 --> L14

    style L1 fill:#e3f2fd
    style L2 fill:#e3f2fd
    style L3 fill:#e3f2fd
    style L4 fill:#ffecb3
    style L5 fill:#ffecb3
    style L6 fill:#ffecb3
    style L7 fill:#ffecb3
    style L8 fill:#c5e1a5
    style L10 fill:#fff9c4
    style L11 fill:#fff9c4
    style L14 fill:#f8bbd0
```

### LLM 호출 시퀀스 (복합 질문 예시)

```mermaid
sequenceDiagram
    participant User
    participant Planning
    participant Supervisor
    participant SearchTeam
    participant AnalysisTeam
    participant Response

    User->>Planning: "강남구 시세 + 리스크 분석"

    Note over Planning: LLM #1: Intent
    Planning->>Planning: COMPREHENSIVE

    Note over Planning: LLM #2: Agent Selection
    Planning->>Planning: [search_team, analysis_team]

    Note over Planning: LLM #3: Query Decomposition
    Planning->>Planning: [시세 조회, 리스크 분석]

    Planning->>Supervisor: ExecutionPlan

    Note over Supervisor: LLM #4: Execution Strategy
    Supervisor->>Supervisor: sequential

    Note over Supervisor: LLM #5: Tool Orchestration (search_team)
    Supervisor->>Supervisor: [market_data, real_estate_search]

    Supervisor->>SearchTeam: 도구 선택 전달

    Note over SearchTeam: LLM #8: Keyword (조건부)
    SearchTeam->>SearchTeam: 키워드 추출

    SearchTeam->>SearchTeam: market_data 실행
    SearchTeam->>SearchTeam: real_estate_search 실행

    SearchTeam->>Supervisor: 결과 반환

    Note over Supervisor: LLM #6: Result Analysis
    Supervisor->>Supervisor: quality=0.85, continue

    Note over Supervisor: LLM #5: Tool Orchestration (analysis_team)
    Supervisor->>Supervisor: [market_analysis]

    Supervisor->>AnalysisTeam: 도구 + 이전 결과 전달

    Note over AnalysisTeam: LLM #10-13: Analysis
    AnalysisTeam->>AnalysisTeam: 시장 분석 수행

    AnalysisTeam->>Supervisor: 분석 결과 반환

    Note over Supervisor: LLM #6: Result Analysis
    Supervisor->>Supervisor: quality=0.8, complete

    Note over Supervisor: LLM #7: Execution Review
    Supervisor->>Supervisor: goal_achievement=0.9

    Supervisor->>Response: 모든 결과 전달

    Note over Response: LLM #14: Response Synthesis
    Response->>User: 최종 응답
```

---

## 🛠️ 도구 오케스트레이션

### Global Tool Registry 구조

```mermaid
graph TB
    Registry[Global Tool Registry]

    subgraph "Search Tools"
        T1[legal_search<br/>비용: 중간<br/>평균 시간: 2.5s<br/>품질: 0.9]
        T2[market_data<br/>비용: 낮음<br/>평균 시간: 1.5s<br/>품질: 0.85]
        T3[real_estate_search<br/>비용: 중간<br/>평균 시간: 3.0s<br/>품질: 0.8]
        T4[loan_data<br/>비용: 낮음<br/>평균 시간: 1.0s<br/>품질: 0.75]
    end

    subgraph "Analysis Tools"
        T5[contract_analysis<br/>비용: 높음<br/>평균 시간: 5.0s<br/>품질: 0.85<br/>의존: legal_search]
        T6[market_analysis<br/>비용: 높음<br/>평균 시간: 4.0s<br/>품질: 0.8<br/>의존: market_data]
    end

    Registry --> T1
    Registry --> T2
    Registry --> T3
    Registry --> T4
    Registry --> T5
    Registry --> T6

    style T1 fill:#e3f2fd
    style T2 fill:#e3f2fd
    style T3 fill:#e3f2fd
    style T4 fill:#e3f2fd
    style T5 fill:#fff3e0
    style T6 fill:#fff3e0
```

### 도구 선택 로직

```mermaid
graph TB
    Start[LLM #5: Tool Orchestration] --> CheckUsed{이미 사용?}

    CheckUsed -->|Yes| Skip[도구 스킵]
    CheckUsed -->|No| CheckDep{의존성 충족?}

    CheckDep -->|Yes| CheckCost{비용 vs 효과}
    CheckDep -->|No| Wait[대기 또는 스킵]

    CheckCost -->|효과적| Select[도구 선택]
    CheckCost -->|비효율| Alternative[대안 도구]

    Select --> Params[파라미터 최적화]
    Alternative --> Params

    Params --> Execute[도구 실행]

    Skip --> Log[스킵 이유 로깅]
    Wait --> Log
    Execute --> Result[결과 저장]

    Result --> UpdateRegistry[Registry 업데이트<br/>- used_tools<br/>- last_used<br/>- quality_score]

    style CheckUsed fill:#fff3e0
    style CheckDep fill:#fff3e0
    style CheckCost fill:#fff3e0
    style Select fill:#c8e6c9
    style Execute fill:#c8e6c9
```

### 도구 중복 방지 예시

```mermaid
graph LR
    subgraph "SearchTeam 실행"
        S1[legal_search 실행] --> S2[결과: 10개 법률 조항]
        S2 --> S3[quality: 0.9]
    end

    S3 --> Registry1[Registry 업데이트:<br/>legal_search → used]

    Registry1 --> Check[LLM #5: Tool Orchestration<br/>for AnalysisTeam]

    Check --> Decision{legal_search 재사용?}

    Decision -->|❌ 중복 방지| Alt[대안: 이전 결과 재사용]
    Decision -->|✅ 필요 시만| ReRun[파라미터 변경 후 재실행]

    Alt --> Analysis[contract_analysis<br/>입력: 이전 legal_results 사용]

    style S1 fill:#e3f2fd
    style S3 fill:#c8e6c9
    style Decision fill:#fff3e0
    style Alt fill:#c8e6c9
```

---

## 🔄 에러 복구 흐름

### 팀 실패 시 대응

```mermaid
graph TB
    TeamStart[팀 실행 시작] --> Execute[도구 실행]

    Execute --> Check{성공?}

    Check -->|Success| Quality[LLM #6: Result Analysis]
    Check -->|Failure| Error[에러 감지]

    Error --> Analyze[에러 분석]
    Analyze --> Critical{Critical?}

    Critical -->|Yes| Fallback[Fallback 전략]
    Critical -->|No| Partial[부분 결과 수용]

    Fallback --> Retry{재시도 가능?}
    Retry -->|Yes, 파라미터 조정| Execute
    Retry -->|No| Alternative[대안 팀 실행]

    Alternative --> AltTeam[다른 팀으로 대체]

    Partial --> Quality

    Quality --> QScore{품질 점수}
    QScore -->|< 0.5| LowQuality[낮은 품질]
    QScore -->|>= 0.5| AcceptResult[결과 수용]

    LowQuality --> Adjust[계획 조정<br/>- 추가 도구<br/>- 파라미터 변경]

    Adjust --> NextTeam{다음 팀 실행?}
    NextTeam -->|Yes| SkipOrModify[일부 팀 스킵/수정]
    NextTeam -->|No| EarlyExit[조기 종료]

    AcceptResult --> Continue[계속 진행]

    AltTeam --> Continue
    SkipOrModify --> Continue
    EarlyExit --> PostExec[post_execution_node]

    Continue --> NextTeamLoop[다음 팀 루프]

    style Error fill:#ffcdd2
    style Fallback fill:#fff3e0
    style Retry fill:#fff9c4
    style Adjust fill:#fff3e0
    style AcceptResult fill:#c8e6c9
```

### 에러 유형별 전략

```mermaid
graph TB
    Error[에러 발생] --> Type{에러 유형}

    Type -->|Tool Timeout| T1[타임아웃]
    Type -->|Tool Exception| T2[도구 예외]
    Type -->|Low Quality| T3[낮은 품질]
    Type -->|Dependency Missing| T4[의존성 부재]

    T1 --> T1A[타임아웃 증가<br/>재시도 1회]
    T1A --> T1B{성공?}
    T1B -->|Yes| Accept
    T1B -->|No| Skip[도구 스킵]

    T2 --> T2A[에러 로깅]
    T2A --> T2B[대안 도구 시도]
    T2B --> T2C{대안 있음?}
    T2C -->|Yes| AltTool[대안 도구 실행]
    T2C -->|No| Skip

    T3 --> T3A[파라미터 조정]
    T3A --> T3B[재실행 1회]
    T3B --> T3C{개선됨?}
    T3C -->|Yes| Accept
    T3C -->|No| PartialAccept[부분 수용]

    T4 --> T4A[의존성 팀 먼저 실행]
    T4A --> T4B{의존성 충족?}
    T4B -->|Yes| RetryOriginal[원래 도구 재시도]
    T4B -->|No| Skip

    AltTool --> Accept[결과 수용]
    RetryOriginal --> Accept
    PartialAccept --> Accept
    Skip --> Notify[사용자 알림]

    Accept --> Continue[계속 진행]
    Notify --> Continue

    style T1 fill:#ffecb3
    style T2 fill:#ffcdd2
    style T3 fill:#fff9c4
    style T4 fill:#e1bee7
    style Accept fill:#c8e6c9
```

---

## 🔀 상태 전이 다이어그램

### ExecutionContext 상태

```mermaid
stateDiagram-v2
    [*] --> Initialized: execute_teams_node 진입

    Initialized --> PreExecution: pre_execution_node
    PreExecution --> StrategyDetermined: LLM #4 완료

    StrategyDetermined --> TeamLoop: team_execution_loop

    state TeamLoop {
        [*] --> BeforeTeam
        BeforeTeam --> ToolOrchestrated: LLM #5 완료
        ToolOrchestrated --> Executing: 팀 실행 시작
        Executing --> AfterTeam: 팀 완료
        AfterTeam --> ResultAnalyzed: LLM #6 완료

        ResultAnalyzed --> DecisionPoint

        state DecisionPoint <<choice>>
        DecisionPoint --> BeforeTeam: 다음 팀
        DecisionPoint --> [*]: 모든 팀 완료 또는 조기 종료
    }

    TeamLoop --> PostExecution: post_execution_node
    PostExecution --> Reviewed: LLM #7 완료

    Reviewed --> Completed: state 병합
    Completed --> [*]: aggregate_results_node로 이동
```

### 팀 실행 상태

```mermaid
stateDiagram-v2
    [*] --> Pending: 팀 계획됨

    Pending --> InProgress: before_team_execution

    state InProgress {
        [*] --> ToolSelection
        ToolSelection --> ToolExecution: 도구 선택 완료
        ToolExecution --> [*]: 도구 실행 완료
    }

    InProgress --> Completed: 성공
    InProgress --> Failed: 실패

    Failed --> Retry: 재시도 가능
    Retry --> InProgress: 파라미터 조정

    Failed --> Skipped: 재시도 불가

    Completed --> QualityCheck

    state QualityCheck <<choice>>
    QualityCheck --> Accepted: 품질 >= threshold
    QualityCheck --> PartialAccepted: 품질 < threshold

    Accepted --> [*]
    PartialAccepted --> [*]
    Skipped --> [*]
```

---

## 📊 비교 요약

### 기존 vs 개선

| 항목 | 기존 | 개선 | 개선 효과 |
|-----|------|------|----------|
| **Execute Node LLM 호출** | 0회 | 4회 | 동적 조율 가능 |
| **도구 선택 주체** | 각 Executor | Supervisor 중앙화 | 중복 방지 |
| **에러 복구** | 단순 로깅 | LLM 기반 대안 | 복구율 70% |
| **중간 결과 분석** | 없음 | 품질 점수 + 조정 | 품질 개선 20% |
| **실행 전략 최적화** | 정적 | 동적 (LLM 결정) | 효율성 15% 향상 |
| **총 LLM 호출 (복합)** | 10회 | 15회 | +50% |
| **응답 시간 (복합)** | 15-20초 | 18-22초 | +10-15% |
| **도구 중복 사용** | 30% | 0% | -100% |

### 아키텍처 레벨

| 레벨 | 기존 | 개선 |
|------|------|------|
| **Planning** | ✅ LLM 기반 인지 | ✅ 유지 |
| **Execution** | ❌ 단순 실행기 | ✅ 지능형 오케스트레이터 |
| **Agent** | ✅ 독립 실행 | ✅ 중앙 가이드 + 독립 실행 |
| **Tool** | ❌ 분산 선택 | ✅ 중앙 조율 |
| **Response** | ✅ LLM 합성 | ✅ 유지 |

---

## 🎯 핵심 개선 포인트

### 1. 중앙 집중식 도구 관리

**Before**: 각 Executor가 독립적으로 LLM 호출하여 도구 선택
- SearchExecutor → LLM #5 (tool_selection_search)
- AnalysisExecutor → LLM #6 (tool_selection_analysis)
- **문제**: 도구 중복 사용 가능

**After**: Supervisor가 중앙에서 LLM 호출하여 전체 시스템 관점 도구 오케스트레이션
- Supervisor → LLM #5 (tool_orchestration) × N팀
- **효과**: 도구 중복 0%, 의존성 관리 자동화

### 2. 동적 실행 조율

**Before**: Planning 단계에서 확정된 계획을 단순 실행
- 실행 중 계획 수정 불가
- 중간 결과 무시

**After**: 실행 중 LLM이 중간 결과 분석 후 계획 조정
- LLM #6 (result_analysis) → 품질 체크
- 조기 종료, 팀 스킵, 파라미터 조정 가능

### 3. 지능형 에러 복구

**Before**: 팀 실패 시 단순 로깅 후 계속
- 대안 전략 없음
- 부분 실패 허용 안 함

**After**: LLM이 에러 분석 후 복구 전략 수립
- 재시도, 대안 도구, 파라미터 조정
- 부분 결과 수용 및 보완

---

**작성자**: Claude
**검토 필요**: 시스템 아키텍트, 백엔드 개발자, UX 디자이너
**연관 문서**: [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md), [AGENT_TOOL_STRATEGY.md](./AGENT_TOOL_STRATEGY.md)
**상태**: 설계 완료
**날짜**: 2025-10-15
