# 로깅 및 대시보드 구현 계획서 (2025-11-05)

## 📋 Executive Summary

**목표**: 전체 시스템 흐름을 실시간으로 모니터링하고, 문제 발생 지점을 즉각 파악할 수 있는 로깅 시스템과 시각적 대시보드 구현

**현재 상태**:
- ✅ HITL 기능 비활성화 완료
- ✅ 기본 순차 실행 플로우 단순화 완료
- ✅ 시스템 아키텍처 문서화 완료 (system_flow.md, agent_flow.md)
- ⚠️ 실행 과정 가시성 부족 - 어디서 문제가 발생하는지 파악 어려움

**최종 목표**: 기본 순차 실행이 정상 작동하는지 확인 → HITL 재구현 준비

---

## 🎯 Phase 1: 현재 시스템 상태 평가

### 1.1 작동 중인 기능
✅ **WebSocket 연결**: `ws://localhost:8000/ws/chat/{session_id}`
✅ **LangGraph 그래프 빌드**: Checkpointer 포함 정상 컴파일
✅ **Intent Understanding**: 사용자 의도 파악
✅ **Planning**: Task 리스트 생성 (HITL 제외)
✅ **Executor**: Command 기반 동적 라우팅
✅ **Agents**: 5개 Fitness Agents 정의됨 (diet, workout, schedule, member_care, coaching)
✅ **Aggregator**: 결과 집계 및 인사이트 생성
✅ **Output Router & Generators**: Chat/Graph/Report 생성

### 1.2 검증 필요 사항
⚠️ **순차 실행 완전성**: Intent → Planning → Executor → Agents(순차) → Aggregator → Generator → END 전체 플로우
⚠️ **State 관리**: current_step 증가, plan 상태 업데이트 정상 작동 여부
⚠️ **에러 핸들링**: Agent 실패 시 복구 로직
⚠️ **최종 결과 생성**: final_result 필드 정상 출력 여부

### 1.3 부족한 가시성
❌ **노드 실행 순서**: 어떤 노드가 언제 실행되는지 알 수 없음
❌ **State 변화**: current_step이 제대로 증가하는지 확인 불가
❌ **에러 지점**: 어떤 Agent에서 실패했는지 추적 어려움
❌ **실행 시간**: 각 노드/Agent 실행 시간 측정 안 됨

---

## 🔧 Phase 2: Backend 로깅 구현

### 2.1 로깅 전략

#### A. 노드 단위 로깅
**위치**: 각 cognitive_nodes.py, response_nodes.py, agents/*.py
**형식**:
```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def {node_name}_node(state: SupervisorState, llm=None) -> dict:
    start_time = datetime.now()
    session_id = state.get("session_id", "unknown")

    logger.info(f"[{node_name.upper()}] 🚀 Node started | Session: {session_id}")
    logger.debug(f"[{node_name.upper()}] Input state: current_step={state.get('current_step')}, plan_length={len(state.get('plan', []))}")

    try:
        # ... node logic ...
        result = await some_operation()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[{node_name.upper()}] ✅ Node completed | Elapsed: {elapsed:.2f}s")
        logger.debug(f"[{node_name.upper()}] Output: {result}")

        return result
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"[{node_name.upper()}] ❌ Node failed | Elapsed: {elapsed:.2f}s | Error: {e}")
        logger.exception(f"[{node_name.upper()}] Full traceback:")
        raise
```

#### B. Executor 상세 로깅
**위치**: `cognitive_nodes.py` - executor_node
**추가 로그**:
```python
async def executor_node(state: SupervisorState) -> Command:
    plan = state["plan"]
    current_step = state["current_step"]

    logger.info(f"[EXECUTOR] 📍 Current Step: {current_step}/{len(plan)}")

    if current_step < len(plan):
        step = plan[current_step]
        logger.info(f"[EXECUTOR] 🎯 Executing Step {step['step_id']}: {step['agent']} - {step['description']}")
        logger.debug(f"[EXECUTOR] Step details: {step}")

        return Command(goto=step["agent"])
    else:
        logger.info(f"[EXECUTOR] ✨ All steps completed. Moving to Aggregator.")
        return Command(goto="aggregator")
```

#### C. Agent 실행 로깅
**위치**: `agents/*.py` - 각 agent_node
**추가 로그**:
```python
async def {agent}_agent_node(state: SupervisorState) -> Dict:
    plan = state["plan"]
    current_step = state["current_step"]
    step = plan[current_step]

    logger.info(f"[{AGENT}] 🔄 Agent started | Step: {step['step_id']} | Task: {step['description']}")

    try:
        # Tool 호출 전
        logger.debug(f"[{AGENT}] Calling tool with params: ...")

        result_data = {tool_function}(...)

        # Tool 호출 후
        logger.info(f"[{AGENT}] ✅ Tool execution successful")
        logger.debug(f"[{AGENT}] Tool result: {result_data}")

        # State 업데이트
        plan[current_step]["status"] = "completed"
        plan[current_step]["result"] = result_text

        logger.info(f"[{AGENT}] 📈 Moving to next step: {current_step} → {current_step + 1}")

        return {
            "plan": plan,
            "current_step": current_step + 1,
            "messages": [AIMessage(content=result_text)]
        }
    except Exception as e:
        logger.error(f"[{AGENT}] ❌ Tool execution failed: {e}")
        plan[current_step]["status"] = "failed"
        plan[current_step]["error"] = str(e)
        return {"plan": plan, "current_step": current_step + 1}
```

#### D. WebSocket 이벤트 로깅
**위치**: `backend/app/api/websocket.py`
**추가 로그**:
```python
async for event in graph.astream_events(initial_input, config=config, version="v2"):
    event_type = event.get("event")
    event_name = event.get("name")

    # 기존 로직에 추가
    if event_type == "on_chain_start":
        logger.info(f"[WS] 🟢 Event: {event_type} | Node: {event_name} | RunID: {event.get('run_id')}")
    elif event_type == "on_chain_end":
        logger.info(f"[WS] 🔵 Event: {event_type} | Node: {event_name} | RunID: {event.get('run_id')}")
    elif event_type == "on_chain_error":
        logger.error(f"[WS] 🔴 Event: {event_type} | Node: {event_name} | Error: {event.get('data')}")
```

### 2.2 로깅 설정 파일
**파일**: `backend/app/config/logging_config.py` (신규 생성)
```python
import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """로깅 설정

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        log_file: 로그 파일 경로 (None이면 콘솔만 출력)
    """
    # 루트 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # 포맷 정의
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (선택적)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
```

**적용**: `backend/app/main.py`에 추가
```python
from backend.app.config.logging_config import setup_logging

# FastAPI app 생성 전
setup_logging(
    log_level="DEBUG",  # 개발 시 DEBUG, 운영 시 INFO
    log_file="C:/kdy/Projects/AI_PTmanager/beta_v001/logs/backend.log"
)
```

---

## 🖥️ Phase 3: Frontend 로깅 구현

### 3.1 Console 로깅 전략

#### A. WebSocket 이벤트 로깅
**위치**: `frontend/src/App.tsx`
**추가 로그**:
```typescript
useEffect(() => {
  const ws = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}`);

  ws.onopen = () => {
    console.log('[WS] ✅ WebSocket 연결 성공', { sessionId, timestamp: new Date().toISOString() });
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`[WS] 📨 메시지 수신: ${data.type}`, data);

    switch (data.type) {
      case 'node_started':
        console.log(`[WS] 🟢 노드 시작: ${data.data.node}`, { runId: data.data.run_id });
        break;
      case 'node_completed':
        console.log(`[WS] 🔵 노드 완료: ${data.data.node}`, { runId: data.data.run_id });
        break;
      case 'final_result':
        console.log('[WS] ✨ 최종 결과 수신', { resultLength: data.data.result.length });
        break;
      case 'error':
        console.error('[WS] ❌ 에러 발생', data.data);
        break;
    }
  };

  ws.onerror = (error) => {
    console.error('[WS] 🔴 WebSocket 에러', error);
  };

  ws.onclose = () => {
    console.log('[WS] 🔌 WebSocket 연결 종료');
  };

}, [sessionId]);
```

#### B. 사용자 액션 로깅
```typescript
const sendMessage = () => {
  console.log('[USER] 💬 메시지 전송 시도', {
    message: input.substring(0, 50) + '...',
    outputFormat,
    timestamp: new Date().toISOString()
  });

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ message: input, output_format: outputFormat }));
    console.log('[USER] ✅ 메시지 전송 완료');
  } else {
    console.error('[USER] ❌ WebSocket 연결 없음', { readyState: ws?.readyState });
  }
};
```

#### C. State 변화 로깅
```typescript
useEffect(() => {
  console.log('[STATE] 메시지 배열 업데이트', {
    messageCount: messages.length,
    lastMessage: messages[messages.length - 1]
  });
}, [messages]);
```

---

## 📊 Phase 4: Dashboard 구현

### 4.1 Dashboard 레이아웃

**위치**: 챗봇 오른쪽에 사이드 패널로 배치

```
┌─────────────────────┬──────────────────────┐
│                     │                      │
│   Chatbot Area      │   Dashboard Panel    │
│   (기존)            │   (신규)             │
│                     │                      │
│   - Input           │   - Execution Status │
│   - Messages        │   - Plan Steps       │
│   - Send Button     │   - State Viewer     │
│                     │   - Error Log        │
│                     │                      │
└─────────────────────┴──────────────────────┘
        60%                    40%
```

### 4.2 Dashboard 컴포넌트

#### A. 파일 구조
```
frontend/src/
├── components/
│   ├── Dashboard.tsx          # 메인 대시보드
│   ├── ExecutionTimeline.tsx  # 실행 타임라인
│   ├── PlanStepsList.tsx      # 계획 단계 목록
│   ├── StateViewer.tsx        # State 뷰어
│   └── ErrorDisplay.tsx       # 에러 표시
├── hooks/
│   └── useDashboardData.ts    # Dashboard 데이터 관리
└── types/
    └── dashboard.ts           # 타입 정의
```

#### B. Dashboard.tsx (신규 파일)
```typescript
import React from 'react';
import './Dashboard.css';

interface DashboardProps {
  currentNode: string | null;
  planSteps: PlanStep[];
  currentStep: number;
  stateValues: any;
  errors: ErrorLog[];
  executionHistory: ExecutionEvent[];
}

interface PlanStep {
  step_id: number;
  agent: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: string;
  error?: string;
}

interface ExecutionEvent {
  timestamp: string;
  node: string;
  eventType: 'started' | 'completed' | 'error';
  duration?: number;
}

interface ErrorLog {
  timestamp: string;
  node: string;
  message: string;
}

export const Dashboard: React.FC<DashboardProps> = ({
  currentNode,
  planSteps,
  currentStep,
  stateValues,
  errors,
  executionHistory
}) => {
  return (
    <div className="dashboard-panel">
      {/* 헤더 */}
      <div className="dashboard-header">
        <h2>🔍 Execution Monitor</h2>
        <div className="status-badge">
          {currentNode ? `Running: ${currentNode}` : 'Idle'}
        </div>
      </div>

      {/* 실행 타임라인 */}
      <div className="dashboard-section">
        <h3>📈 Execution Timeline</h3>
        <ExecutionTimeline events={executionHistory} />
      </div>

      {/* 계획 단계 */}
      <div className="dashboard-section">
        <h3>📋 Plan Steps</h3>
        <PlanStepsList
          steps={planSteps}
          currentStep={currentStep}
        />
      </div>

      {/* State 뷰어 */}
      <div className="dashboard-section">
        <h3>💾 Current State</h3>
        <StateViewer state={stateValues} />
      </div>

      {/* 에러 로그 */}
      {errors.length > 0 && (
        <div className="dashboard-section error-section">
          <h3>❌ Errors</h3>
          <ErrorDisplay errors={errors} />
        </div>
      )}
    </div>
  );
};
```

#### C. ExecutionTimeline.tsx
```typescript
import React from 'react';

interface ExecutionEvent {
  timestamp: string;
  node: string;
  eventType: 'started' | 'completed' | 'error';
  duration?: number;
}

export const ExecutionTimeline: React.FC<{ events: ExecutionEvent[] }> = ({ events }) => {
  return (
    <div className="execution-timeline">
      {events.map((event, index) => (
        <div key={index} className={`timeline-event ${event.eventType}`}>
          <div className="event-icon">
            {event.eventType === 'started' && '🟢'}
            {event.eventType === 'completed' && '🔵'}
            {event.eventType === 'error' && '🔴'}
          </div>
          <div className="event-details">
            <div className="event-node">{event.node}</div>
            <div className="event-time">{new Date(event.timestamp).toLocaleTimeString()}</div>
            {event.duration && <div className="event-duration">{event.duration.toFixed(2)}s</div>}
          </div>
        </div>
      ))}
    </div>
  );
};
```

#### D. PlanStepsList.tsx
```typescript
import React from 'react';

interface PlanStep {
  step_id: number;
  agent: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: string;
  error?: string;
}

export const PlanStepsList: React.FC<{
  steps: PlanStep[];
  currentStep: number;
}> = ({ steps, currentStep }) => {
  return (
    <div className="plan-steps-list">
      {steps.map((step, index) => (
        <div
          key={step.step_id}
          className={`plan-step ${step.status} ${index === currentStep ? 'current' : ''}`}
        >
          <div className="step-header">
            <span className="step-number">#{step.step_id}</span>
            <span className="step-agent">{step.agent}</span>
            <span className={`step-status-badge ${step.status}`}>
              {step.status === 'pending' && '⏳'}
              {step.status === 'running' && '▶️'}
              {step.status === 'completed' && '✅'}
              {step.status === 'failed' && '❌'}
              {step.status}
            </span>
          </div>
          <div className="step-description">{step.description}</div>
          {step.result && (
            <div className="step-result">
              <strong>Result:</strong> {step.result.substring(0, 100)}...
            </div>
          )}
          {step.error && (
            <div className="step-error">
              <strong>Error:</strong> {step.error}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
```

#### E. StateViewer.tsx
```typescript
import React, { useState } from 'react';

export const StateViewer: React.FC<{ state: any }> = ({ state }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="state-viewer">
      <div className="state-summary">
        <div className="state-item">
          <strong>Current Step:</strong> {state.current_step ?? 'N/A'}
        </div>
        <div className="state-item">
          <strong>Plan Length:</strong> {state.plan?.length ?? 0}
        </div>
        <div className="state-item">
          <strong>Messages:</strong> {state.messages?.length ?? 0}
        </div>
        <div className="state-item">
          <strong>Output Format:</strong> {state.output_format ?? 'chat'}
        </div>
      </div>

      <button
        className="expand-button"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? '▼ Hide Full State' : '▶ Show Full State'}
      </button>

      {expanded && (
        <pre className="state-json">
          {JSON.stringify(state, null, 2)}
        </pre>
      )}
    </div>
  );
};
```

#### F. Dashboard.css
```css
.dashboard-panel {
  width: 40%;
  height: 100vh;
  padding: 20px;
  background: #f5f5f5;
  border-left: 2px solid #ddd;
  overflow-y: auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #333;
}

.dashboard-header h2 {
  margin: 0;
  font-size: 20px;
}

.status-badge {
  padding: 5px 12px;
  background: #4CAF50;
  color: white;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.dashboard-section {
  margin-bottom: 25px;
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.dashboard-section h3 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 16px;
  color: #333;
}

/* Execution Timeline */
.execution-timeline {
  max-height: 200px;
  overflow-y: auto;
}

.timeline-event {
  display: flex;
  align-items: center;
  padding: 8px;
  margin-bottom: 8px;
  border-left: 3px solid #ddd;
  background: #fafafa;
  border-radius: 4px;
}

.timeline-event.started {
  border-left-color: #4CAF50;
}

.timeline-event.completed {
  border-left-color: #2196F3;
}

.timeline-event.error {
  border-left-color: #f44336;
}

.event-icon {
  font-size: 18px;
  margin-right: 10px;
}

.event-details {
  flex: 1;
}

.event-node {
  font-weight: bold;
  font-size: 14px;
}

.event-time {
  font-size: 12px;
  color: #666;
}

.event-duration {
  font-size: 12px;
  color: #999;
  font-style: italic;
}

/* Plan Steps List */
.plan-steps-list {
  max-height: 300px;
  overflow-y: auto;
}

.plan-step {
  padding: 12px;
  margin-bottom: 10px;
  border-radius: 6px;
  border: 2px solid #ddd;
  background: #fafafa;
  transition: all 0.2s;
}

.plan-step.current {
  border-color: #FF9800;
  background: #FFF3E0;
  box-shadow: 0 0 10px rgba(255, 152, 0, 0.3);
}

.plan-step.completed {
  border-color: #4CAF50;
  background: #E8F5E9;
}

.plan-step.failed {
  border-color: #f44336;
  background: #FFEBEE;
}

.plan-step.running {
  border-color: #2196F3;
  background: #E3F2FD;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.step-number {
  font-weight: bold;
  color: #666;
}

.step-agent {
  font-weight: bold;
  color: #333;
  text-transform: uppercase;
  font-size: 12px;
}

.step-status-badge {
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: bold;
}

.step-status-badge.pending {
  background: #FFF3E0;
  color: #F57C00;
}

.step-status-badge.running {
  background: #E3F2FD;
  color: #1976D2;
}

.step-status-badge.completed {
  background: #E8F5E9;
  color: #388E3C;
}

.step-status-badge.failed {
  background: #FFEBEE;
  color: #D32F2F;
}

.step-description {
  font-size: 13px;
  color: #555;
  margin-bottom: 5px;
}

.step-result, .step-error {
  font-size: 12px;
  padding: 8px;
  border-radius: 4px;
  margin-top: 8px;
}

.step-result {
  background: #E8F5E9;
  color: #2E7D32;
}

.step-error {
  background: #FFEBEE;
  color: #C62828;
}

/* State Viewer */
.state-viewer {
  font-size: 13px;
}

.state-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 10px;
}

.state-item {
  padding: 8px;
  background: #fafafa;
  border-radius: 4px;
}

.state-item strong {
  color: #333;
  margin-right: 5px;
}

.expand-button {
  width: 100%;
  padding: 8px;
  background: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.expand-button:hover {
  background: #1976D2;
}

.state-json {
  margin-top: 10px;
  padding: 10px;
  background: #263238;
  color: #A5D6A7;
  border-radius: 4px;
  font-size: 11px;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
}

/* Error Display */
.error-section {
  border-left: 4px solid #f44336;
}

.error-display {
  max-height: 150px;
  overflow-y: auto;
}

.error-item {
  padding: 10px;
  margin-bottom: 8px;
  background: #FFEBEE;
  border-left: 3px solid #D32F2F;
  border-radius: 4px;
}

.error-timestamp {
  font-size: 11px;
  color: #666;
  margin-bottom: 5px;
}

.error-node {
  font-weight: bold;
  color: #D32F2F;
  margin-bottom: 5px;
}

.error-message {
  font-size: 12px;
  color: #333;
}
```

### 4.3 App.tsx 통합

**수정 위치**: `frontend/src/App.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import './App.css';

function App() {
  // ... 기존 state ...

  // Dashboard state 추가
  const [currentNode, setCurrentNode] = useState<string | null>(null);
  const [planSteps, setPlanSteps] = useState<PlanStep[]>([]);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [stateValues, setStateValues] = useState<any>({});
  const [errors, setErrors] = useState<ErrorLog[]>([]);
  const [executionHistory, setExecutionHistory] = useState<ExecutionEvent[]>([]);

  useEffect(() => {
    // WebSocket 메시지 핸들러 수정
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'node_started':
          setCurrentNode(data.data.node);
          setExecutionHistory(prev => [...prev, {
            timestamp: new Date().toISOString(),
            node: data.data.node,
            eventType: 'started'
          }]);
          break;

        case 'node_completed':
          setCurrentNode(null);
          setExecutionHistory(prev => {
            const lastEvent = prev[prev.length - 1];
            if (lastEvent && lastEvent.node === data.data.node) {
              const duration = (new Date().getTime() - new Date(lastEvent.timestamp).getTime()) / 1000;
              return [...prev, {
                timestamp: new Date().toISOString(),
                node: data.data.node,
                eventType: 'completed',
                duration
              }];
            }
            return prev;
          });
          break;

        case 'plan_update':
          // 새로운 이벤트 타입 (백엔드에서 추가 필요)
          setPlanSteps(data.data.plan);
          setCurrentStep(data.data.current_step);
          break;

        case 'state_update':
          // 새로운 이벤트 타입 (백엔드에서 추가 필요)
          setStateValues(data.data.state);
          break;

        case 'error':
          setErrors(prev => [...prev, {
            timestamp: new Date().toISOString(),
            node: data.data.node || 'unknown',
            message: data.data.error
          }]);
          break;
      }
    };
  }, [sessionId]);

  return (
    <div className="app-container">
      {/* 기존 챗봇 영역 */}
      <div className="chatbot-area">
        {/* ... 기존 코드 ... */}
      </div>

      {/* 새로운 대시보드 영역 */}
      <Dashboard
        currentNode={currentNode}
        planSteps={planSteps}
        currentStep={currentStep}
        stateValues={stateValues}
        errors={errors}
        executionHistory={executionHistory}
      />
    </div>
  );
}
```

### 4.4 Backend에서 Dashboard 이벤트 전송

**수정 위치**: `backend/app/api/websocket.py`

```python
async for event in graph.astream_events(initial_input, config=config, version="v2"):
    # ... 기존 코드 ...

    # Plan/State 업데이트 이벤트 추가
    if event_type == "on_chain_end" and event_name == "planning":
        # Planning 노드 완료 후 Plan 전송
        state = await graph.aget_state(config)
        if state.values:
            await manager.send_message(session_id, {
                "type": "plan_update",
                "data": {
                    "plan": state.values.get("plan", []),
                    "current_step": state.values.get("current_step", 0)
                },
                "session_id": session_id
            })

    # Executor 또는 Agent 완료 후 State 업데이트
    if event_type == "on_chain_end" and event_name in ["executor", "diet", "workout", "schedule", "member_care", "coaching"]:
        state = await graph.aget_state(config)
        if state.values:
            await manager.send_message(session_id, {
                "type": "state_update",
                "data": {
                    "state": {
                        "current_step": state.values.get("current_step"),
                        "plan": state.values.get("plan"),
                        "messages": len(state.values.get("messages", [])),
                        "output_format": state.values.get("output_format")
                    }
                },
                "session_id": session_id
            })
```

---

## 🧪 Phase 5: 테스트 전략

### 5.1 테스트 시나리오

#### Test Case 1: Simple Query (1-2 steps)
**Query**: "최근 식단 기록 보여줘"

**Expected Flow**:
```
Intent → Planning → Executor → diet → Executor → Aggregator → Chat Generator → END
```

**Expected Plan**:
```json
[
  {"step_id": 1, "agent": "diet", "description": "최근 식단 기록 조회"}
]
```

**Success Criteria**:
- ✅ Planning에서 1개 step 생성
- ✅ Executor가 diet로 라우팅
- ✅ Diet agent 성공 실행
- ✅ current_step이 0 → 1로 증가
- ✅ Executor가 Aggregator로 라우팅
- ✅ Final result 정상 출력

#### Test Case 2: Medium Query (2-3 steps)
**Query**: "하체 운동 루틴 추천하고 자세 영상 찾아줘"

**Expected Flow**:
```
Intent → Planning → Executor → workout → Executor → coaching → Executor → Aggregator → Chat Generator → END
```

**Expected Plan**:
```json
[
  {"step_id": 1, "agent": "workout", "description": "하체 운동 루틴 생성"},
  {"step_id": 2, "agent": "coaching", "description": "하체 운동 자세 영상 검색"}
]
```

**Success Criteria**:
- ✅ Planning에서 2개 steps 생성
- ✅ Executor가 순차적으로 workout → coaching 실행
- ✅ current_step이 0 → 1 → 2로 증가
- ✅ 모든 step의 status가 "completed"
- ✅ Final result에 두 agent 결과 모두 포함

#### Test Case 3: Complex Query (3-5 steps)
**Query**: "김철수 회원의 운동과 식단을 확인하고 PT예약해줘"

**Expected Flow**:
```
Intent → Planning → Executor → member_care → Executor → workout → Executor → diet → Executor → schedule → Executor → Aggregator → Chat Generator → END
```

**Expected Plan**:
```json
[
  {"step_id": 1, "agent": "member_care", "description": "김철수 회원 정보 조회"},
  {"step_id": 2, "agent": "workout", "description": "김철수 회원의 운동 기록 조회"},
  {"step_id": 3, "agent": "diet", "description": "김철수 회원의 식단 기록 조회"},
  {"step_id": 4, "agent": "schedule", "description": "PT 스케줄 예약"}
]
```

**Success Criteria**:
- ✅ Planning에서 4개 steps 생성
- ✅ Executor가 순차적으로 모든 agent 실행
- ✅ current_step이 0 → 1 → 2 → 3 → 4로 증가
- ✅ 모든 step의 status가 "completed"
- ✅ Final result에 모든 agent 결과 포함

### 5.2 수집할 로그 정보

#### A. Frontend Logs (F12 Console)
**수집 방법**: Chrome DevTools Console → 전체 복사
**필요 정보**:
- `[WS]` 태그 모든 로그
- `[USER]` 태그 모든 로그
- `[STATE]` 태그 모든 로그
- 에러 스택 트레이스

**예시 로그**:
```
[WS] ✅ WebSocket 연결 성공 { sessionId: 'xxx', timestamp: '2025-11-05T...' }
[USER] 💬 메시지 전송 시도 { message: '김철수 회원의 운동과 식단을...', outputFormat: 'chat' }
[WS] 📨 메시지 수신: node_started { node: 'intent', run_id: '...' }
[WS] 🟢 노드 시작: intent { runId: '...' }
...
```

#### B. Backend Logs (Terminal)
**수집 방법**: Backend 터미널 출력 전체 복사
**필요 정보**:
- `[INTENT]`, `[PLANNING]`, `[EXECUTOR]` 등 모든 노드 로그
- `[{AGENT}]` (DIET, WORKOUT, 등) 모든 Agent 로그
- `[WS]` WebSocket 이벤트 로그
- 에러 트레이스백

**예시 로그**:
```
2025-11-05 14:30:15 | INFO     | backend.app.octostrator.supervisor.cognitive_nodes | [INTENT] 🚀 Node started | Session: xxx
2025-11-05 14:30:15 | DEBUG    | backend.app.octostrator.supervisor.cognitive_nodes | [INTENT] Input state: current_step=0, plan_length=0
2025-11-05 14:30:16 | INFO     | backend.app.octostrator.supervisor.cognitive_nodes | [INTENT] ✅ Node completed | Elapsed: 0.82s
2025-11-05 14:30:16 | INFO     | backend.app.octostrator.supervisor.cognitive_nodes | [PLANNING] 🚀 Node started | Session: xxx
...
```

#### C. Dashboard 상태 (Screenshot)
**수집 방법**: 대시보드 스크린샷 캡처
**필요 정보**:
- Execution Timeline 전체
- Plan Steps List (모든 step 상태)
- Current State 값
- Error Display (있을 경우)

### 5.3 테스트 체크리스트

**사전 준비**:
- [ ] Backend 서버 실행 (`uv run uvicorn backend.app.main:app --reload`)
- [ ] Frontend 서버 실행 (`npm start`)
- [ ] PostgreSQL 서버 실행 확인
- [ ] Browser DevTools 콘솔 열기 (F12)
- [ ] Backend 터미널 로그 확인 준비

**실행 단계**:
- [ ] Test Case 1 (Simple) 실행
- [ ] Frontend 콘솔 로그 복사
- [ ] Backend 터미널 로그 복사
- [ ] Dashboard 스크린샷 캡처
- [ ] 최종 결과 확인

- [ ] Test Case 2 (Medium) 실행
- [ ] (동일한 로그 수집)

- [ ] Test Case 3 (Complex) 실행
- [ ] (동일한 로그 수집)

**검증 항목**:
- [ ] 모든 노드가 예상 순서대로 실행되었는가?
- [ ] current_step이 올바르게 증가하는가?
- [ ] Plan의 모든 step이 "completed" 상태인가?
- [ ] Final result가 정상적으로 출력되는가?
- [ ] 에러가 발생했는가? (발생 시 어느 노드에서?)

---

## 📅 Phase 6: 구현 일정

### Week 1: Backend 로깅 (1-2일)
- [ ] Day 1: `logging_config.py` 생성 및 적용
- [ ] Day 1: cognitive_nodes.py 로깅 추가
- [ ] Day 2: response_nodes.py 로깅 추가
- [ ] Day 2: agents/*.py 로깅 추가
- [ ] Day 2: websocket.py 로깅 추가
- [ ] Day 2: 로그 파일 생성 확인 및 테스트

### Week 1: Frontend 로깅 (0.5일)
- [ ] Day 3: App.tsx WebSocket 로깅 추가
- [ ] Day 3: 사용자 액션 로깅 추가
- [ ] Day 3: State 변화 로깅 추가

### Week 2: Dashboard 구현 (2-3일)
- [ ] Day 4: Dashboard 컴포넌트 구조 생성
- [ ] Day 4: ExecutionTimeline.tsx 구현
- [ ] Day 5: PlanStepsList.tsx 구현
- [ ] Day 5: StateViewer.tsx 구현
- [ ] Day 5: ErrorDisplay.tsx 구현
- [ ] Day 6: Dashboard.css 스타일링
- [ ] Day 6: App.tsx 통합 및 레이아웃 조정

### Week 2: Backend Dashboard 이벤트 (0.5일)
- [ ] Day 6: websocket.py에 plan_update 이벤트 추가
- [ ] Day 6: websocket.py에 state_update 이벤트 추가

### Week 2: 테스트 및 검증 (1일)
- [ ] Day 7: Test Case 1 실행 및 로그 수집
- [ ] Day 7: Test Case 2 실행 및 로그 수집
- [ ] Day 7: Test Case 3 실행 및 로그 수집
- [ ] Day 7: 문제 진단 및 수정
- [ ] Day 7: 최종 검증

**총 예상 기간**: 약 7일 (1주일)

---

## ✅ Phase 7: 성공 기준

### 7.1 기능적 성공 기준
- ✅ **완전한 순차 실행**: Intent → Planning → Executor → Agents → Aggregator → Generator → END 전체 플로우 정상 작동
- ✅ **State 관리**: current_step 올바르게 증가, plan 상태 정상 업데이트
- ✅ **에러 없음**: 전체 실행 과정에서 에러 발생하지 않음
- ✅ **최종 결과 출력**: final_result 필드에 정상적인 답변 생성

### 7.2 로깅 성공 기준
- ✅ **노드 단위 로깅**: 모든 노드의 시작/완료/에러 로그 정상 출력
- ✅ **타임스탬프**: 모든 로그에 정확한 시간 기록
- ✅ **실행 시간 측정**: 각 노드의 실행 시간 측정 및 기록
- ✅ **에러 트레이스**: 에러 발생 시 상세한 스택 트레이스 출력

### 7.3 Dashboard 성공 기준
- ✅ **실시간 업데이트**: WebSocket 이벤트 수신 시 즉시 UI 업데이트
- ✅ **Plan 시각화**: 모든 step의 상태(pending/running/completed/failed) 정확히 표시
- ✅ **Current Node 표시**: 현재 실행 중인 노드 실시간 표시
- ✅ **State 확인**: current_step, plan 등 주요 state 값 확인 가능
- ✅ **에러 표시**: 에러 발생 시 대시보드에서 즉시 확인 가능

### 7.4 사용자 경험 성공 기준
- ✅ **투명성**: 사용자가 전체 실행 과정을 명확히 볼 수 있음
- ✅ **디버깅 용이성**: 문제 발생 시 로그만으로 원인 파악 가능
- ✅ **성능 모니터링**: 각 노드/Agent 실행 시간 확인 가능
- ✅ **신뢰성**: 예상대로 동작하며, 예외 상황 없음

---

## 🔄 Phase 8: Rollback Plan

### 만약 구현 중 문제 발생 시

#### A. 로깅으로 인한 성능 저하
**증상**: 로그가 너무 많아서 실행 속도 저하
**해결책**:
1. `logging_config.py`에서 log_level을 `DEBUG` → `INFO`로 변경
2. 불필요한 DEBUG 로그 제거
3. 로그 파일 rotation 설정 (일일/주간 rotation)

#### B. Dashboard가 프론트엔드 성능 저하
**증상**: Dashboard 렌더링으로 인한 UI 느려짐
**해결책**:
1. Dashboard를 별도 페이지로 분리 (탭 전환)
2. executionHistory 최대 개수 제한 (최근 50개만 유지)
3. State Viewer의 Full State를 기본적으로 접기

#### C. 기본 순차 실행이 여전히 실패
**증상**: 로깅/대시보드 추가 후에도 순차 실행 실패
**우선순위 변경**:
1. 로깅/대시보드 구현 일시 중단
2. 코드 리뷰 및 근본 원인 분석
3. 최소한의 동작 가능한 버전으로 축소
4. 단계별 재구축

#### D. WebSocket 이벤트 과다로 인한 네트워크 부하
**증상**: 너무 많은 이벤트 전송으로 WebSocket 연결 불안정
**해결책**:
1. `plan_update`, `state_update` 이벤트 전송 빈도 제한
2. 특정 노드 완료 시에만 전송 (planning, executor, aggregator)
3. 이벤트 배치 처리 (0.5초마다 모아서 전송)

---

## 📝 Phase 9: 다음 단계 (HITL 재구현)

로깅 및 대시보드 구현 후, 기본 순차 실행이 완벽하게 작동하면:

### HITL 재구현 계획
1. **올바른 Resume 메커니즘 사용**:
   - `astream()` 또는 `ainvoke(None, config)` 사용
   - `astream_events()`는 모니터링만 사용

2. **HITL 노드 재활성화**:
   - `cognitive_prompts.py`에 HITL agent 다시 추가
   - HITL handler 노드 재검증

3. **Frontend HITL UI 활성화**:
   - 이미 구현된 HITL UI 컴포넌트 사용
   - 백엔드와 연동 테스트

4. **Interrupt 처리 검증**:
   - `interrupt()` 호출 정상 작동
   - `final_state.next` 감지 정상 작동
   - Resume 후 이어서 실행 정상 작동

**HITL 구현 문서**: 별도로 `HITL_IMPLEMENTATION_PLAN.md` 작성 예정

---

## 📌 요약

### 핵심 목표
1. **가시성 확보**: 로깅 시스템으로 전체 실행 과정 추적
2. **실시간 모니터링**: 대시보드로 현재 상태 시각화
3. **빠른 디버깅**: 문제 발생 시 로그로 즉시 원인 파악
4. **정상 작동 검증**: Test Case 실행으로 기본 순차 실행 확인

### 주요 구현 사항
- ✅ Backend: 노드/Agent/WebSocket 로깅 추가
- ✅ Frontend: Console 로깅 추가
- ✅ Dashboard: 실시간 실행 모니터링 UI
- ✅ Testing: 3개 난이도별 Test Case

### 사용자 요청 정보
실행 후 다음 정보를 제공해주세요:
1. **Frontend Logs**: F12 DevTools Console 전체 복사
2. **Backend Logs**: Terminal 출력 전체 복사
3. **Dashboard Screenshot**: 실행 완료 후 대시보드 캡처
4. **최종 결과**: 챗봇에 표시된 final_result

### 기대 효과
- 🎯 문제 발생 지점 즉시 파악 가능
- 🎯 실행 과정 완전히 투명하게 확인
- 🎯 성능 병목 구간 식별 가능
- 🎯 HITL 재구현을 위한 안정적인 기반 마련

---

**문서 작성일**: 2025-11-05
**작성자**: Claude (AI Assistant)
**상태**: 구현 대기 중
**우선순위**: HIGH
