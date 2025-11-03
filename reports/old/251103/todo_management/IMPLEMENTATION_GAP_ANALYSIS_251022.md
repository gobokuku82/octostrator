# Todo Management 구현 가이드

**작성일:** 2025-10-22
**목적:** Todo Management (Time Travel + HITL) 순차적 구현 가이드
**예상 소요 시간:** 11-17시간 (2-3일)

---

## 🎯 구현 개요

### 목표
LangGraph Checkpointer를 활용한 Time Travel 및 Human-in-the-Loop 기능 구현

### 핵심 기능
1. **Time Travel**: 이전 체크포인트로 되돌아가기
2. **State Rollback**: 특정 단계의 상태 복원
3. **실시간 UI**: WebSocket 기반 Checkpoint 선택 인터페이스

### 아키텍처
```
[Frontend]              [Backend]                [LangGraph]
chat-interface.tsx  →   chat_api.py          →   TeamBasedSupervisor
RollbackModal       →   WebSocket Handler    →   Checkpointer
useRollback hook    →   RollbackManager      →   get_state_history()
                                               →   update_state()
```

---

## 📋 Phase 1: Backend Core (필수)

**목표:** Rollback 핵심 로직 구현
**소요 시간:** 4-6시간 (1일)

### 1.1 State 필드 추가 (5분)

**파일:** `backend/app/service_agent/foundation/separated_states.py`
**위치:** 라인 287-349 (MainSupervisorState 클래스)

**추가할 필드:**
```python
class MainSupervisorState(TypedDict, total=False):
    # ========== 기존 필드들 (그대로 유지) ==========
    messages: List[BaseMessage]
    planning_state: Optional[PlanningState]
    execution_plan: Optional[Dict[str, Any]]
    current_step: Optional[str]
    # ... (기타 기존 필드들)

    # ========== Rollback 필드 추가 (새로 추가) ==========
    rollback_requested: bool                        # Rollback 요청 플래그
    rollback_target_checkpoint_id: Optional[str]    # 목표 Checkpoint ID
    rollback_target_step: Optional[str]             # 목표 단계명
    modification_data: Optional[Dict[str, Any]]     # 수정할 데이터
    available_checkpoints: List[Dict[str, Any]]     # 사용 가능한 Checkpoint 목록
```

**필요한 Import 추가:**
```python
from typing import List, Dict, Any, Optional
```

---

### 1.2 RollbackManager 생성 (2-3시간)

**파일:** `backend/app/service_agent/cognitive_agents/rollback_manager.py` (새 파일)
**크기:** 약 150 라인

**전체 코드:**
```python
"""
Rollback Manager - Time Travel 및 Checkpoint 관리

LangGraph의 Checkpointer를 활용하여 이전 상태로 되돌아가는 기능 제공
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from langgraph.checkpoint.base import BaseCheckpointSaver

logger = logging.getLogger(__name__)


class RollbackManager:
    """
    Rollback 및 Time Travel 관리자

    Attributes:
        checkpointer: LangGraph Checkpointer 인스턴스
    """

    def __init__(self, checkpointer: BaseCheckpointSaver):
        """
        Args:
            checkpointer: AsyncPostgresSaver 인스턴스
        """
        self.checkpointer = checkpointer
        logger.info("✅ RollbackManager initialized")

    async def get_available_checkpoints(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        사용 가능한 Checkpoint 목록 조회

        Args:
            session_id: 세션 ID (thread_id로 사용)
            limit: 최대 조회 개수

        Returns:
            Checkpoint 목록 (최신순)
            [
                {
                    "checkpoint_id": "1ef...",
                    "step_name": "planning",
                    "timestamp": "2025-10-22T10:30:00",
                    "summary": "계획 수립 완료",
                    "metadata": {...}
                },
                ...
            ]
        """
        try:
            config = {
                "configurable": {
                    "thread_id": session_id
                }
            }

            # Checkpoint 히스토리 조회
            checkpoints = []
            async for checkpoint_tuple in self.checkpointer.alist(config, limit=limit):
                checkpoint = checkpoint_tuple.checkpoint
                metadata = checkpoint_tuple.metadata
                config_data = checkpoint_tuple.config

                # Checkpoint ID 추출
                checkpoint_id = config_data.get("configurable", {}).get("checkpoint_id", "")

                # 단계명 추출 (metadata 또는 state에서)
                step_name = metadata.get("step", "unknown")

                # Timestamp 추출
                ts = checkpoint.get("ts")
                if ts:
                    timestamp = datetime.fromtimestamp(ts / 1000000).isoformat()
                else:
                    timestamp = datetime.now().isoformat()

                # Summary 생성
                summary = self._create_checkpoint_summary(checkpoint, metadata)

                checkpoints.append({
                    "checkpoint_id": checkpoint_id,
                    "step_name": step_name,
                    "timestamp": timestamp,
                    "summary": summary,
                    "metadata": metadata
                })

            logger.info(f"📋 Retrieved {len(checkpoints)} checkpoints for session {session_id}")
            return checkpoints

        except Exception as e:
            logger.error(f"❌ Failed to get checkpoints: {e}", exc_info=True)
            return []

    def _create_checkpoint_summary(
        self,
        checkpoint: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Checkpoint 요약 생성

        Args:
            checkpoint: Checkpoint 데이터
            metadata: Checkpoint 메타데이터

        Returns:
            요약 문자열
        """
        # State에서 execution_steps 추출
        channel_values = checkpoint.get("channel_values", {})
        execution_steps = channel_values.get("execution_steps", [])

        if execution_steps:
            completed = sum(1 for step in execution_steps if step.get("status") == "completed")
            total = len(execution_steps)
            return f"작업 진행: {completed}/{total} 완료"

        # Metadata에서 정보 추출
        step = metadata.get("step", "")
        if step == "planning":
            return "계획 수립 단계"
        elif step == "execute_teams":
            return "팀 실행 단계"
        elif step == "aggregate":
            return "결과 집계 단계"
        else:
            return f"{step} 단계"

    async def get_checkpoint_state(
        self,
        session_id: str,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        특정 Checkpoint의 State 조회

        Args:
            session_id: 세션 ID
            checkpoint_id: Checkpoint ID

        Returns:
            State 딕셔너리 또는 None
        """
        try:
            config = {
                "configurable": {
                    "thread_id": session_id,
                    "checkpoint_id": checkpoint_id
                }
            }

            checkpoint_tuple = await self.checkpointer.aget_tuple(config)
            if checkpoint_tuple:
                return checkpoint_tuple.checkpoint.get("channel_values", {})

            return None

        except Exception as e:
            logger.error(f"❌ Failed to get checkpoint state: {e}", exc_info=True)
            return None
```

**테스트 코드 (선택):**
```python
# tests/test_rollback_manager.py
import pytest
from app.service_agent.cognitive_agents.rollback_manager import RollbackManager

@pytest.mark.asyncio
async def test_get_checkpoints(checkpointer, test_session_id):
    """Checkpoint 조회 테스트"""
    manager = RollbackManager(checkpointer)
    checkpoints = await manager.get_available_checkpoints(test_session_id)

    assert isinstance(checkpoints, list)
    if checkpoints:
        assert "checkpoint_id" in checkpoints[0]
        assert "step_name" in checkpoints[0]
        assert "timestamp" in checkpoints[0]
```

---

### 1.3 TeamSupervisor에 Rollback 메서드 추가 (1-2시간)

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`
**위치:** 라인 1200 이후 (initialize_checkpointer 메서드 다음)

**추가할 메서드:**
```python
    async def execute_rollback(
        self,
        session_id: str,
        target_checkpoint_id: str,
        modifications: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Time Travel: 특정 Checkpoint로 되돌아가서 재실행

        Args:
            session_id: 세션 ID (thread_id)
            target_checkpoint_id: 되돌아갈 Checkpoint ID
            modifications: 수정할 State 값 (선택)

        Returns:
            실행 결과

        Raises:
            RuntimeError: Checkpointer 미초기화

        Example:
            >>> result = await supervisor.execute_rollback(
            ...     session_id="session-123",
            ...     target_checkpoint_id="1ef...",
            ...     modifications={"execution_steps": [...]}
            ... )
        """
        if not self.checkpointer:
            raise RuntimeError("Checkpointer not initialized. Call initialize_checkpointer() first.")

        logger.info(f"🔄 Starting rollback for session {session_id} to checkpoint {target_checkpoint_id}")

        # 1. Target Checkpoint Config 생성
        target_config = {
            "configurable": {
                "thread_id": session_id,
                "checkpoint_id": target_checkpoint_id
            }
        }

        # 2. State 수정 (옵션)
        if modifications:
            logger.info(f"🔧 Applying modifications: {list(modifications.keys())}")

            # update_state()를 사용하여 State 수정
            # 주의: update_state()는 새로운 checkpoint를 생성함
            updated_config = self.app.update_state(
                config=target_config,
                values=modifications,
                as_node="__start__"  # 시작 노드로 수정
            )

            # 수정된 config로 교체
            target_config = updated_config

        # 3. 해당 지점부터 다시 실행
        logger.info(f"▶️ Re-executing from checkpoint {target_checkpoint_id}")

        try:
            # ainvoke()로 그래프 재실행
            # None을 전달하면 현재 state에서 계속 진행
            result = await self.app.ainvoke(
                input=None,
                config=target_config
            )

            logger.info(f"✅ Rollback completed for session {session_id}")
            return result

        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}", exc_info=True)
            raise

    async def get_state_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        세션의 Checkpoint 히스토리 조회

        Args:
            session_id: 세션 ID
            limit: 최대 조회 개수

        Returns:
            Checkpoint 목록 (최신순)
        """
        if not self.checkpointer:
            raise RuntimeError("Checkpointer not initialized")

        from app.service_agent.cognitive_agents.rollback_manager import RollbackManager

        manager = RollbackManager(self.checkpointer)
        return await manager.get_available_checkpoints(session_id, limit)
```

**Import 추가 (파일 상단):**
```python
from typing import List, Dict, Any, Optional
```

---

### 1.4 Phase 1 테스트

**테스트 스크립트:** `tests/manual/test_rollback_phase1.py`

```python
"""
Phase 1 수동 테스트: Backend Core
"""
import asyncio
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

async def test_rollback_core():
    """Rollback 핵심 기능 테스트"""

    # 1. Supervisor 초기화
    supervisor = TeamBasedSupervisor()
    await supervisor.setup()

    # 2. 테스트 세션으로 쿼리 실행
    test_session_id = "test-rollback-001"
    result = await supervisor.process_query_streaming(
        query="서울 강남구 아파트 추천해줘",
        session_id=test_session_id,
        chat_session_id=test_session_id,
        user_id=1
    )

    print("✅ Initial query completed")

    # 3. Checkpoint 목록 조회
    checkpoints = await supervisor.get_state_history(test_session_id)
    print(f"\n📋 Found {len(checkpoints)} checkpoints:")
    for i, cp in enumerate(checkpoints[:5]):
        print(f"  {i+1}. {cp['step_name']} - {cp['summary']} ({cp['timestamp']})")

    # 4. 첫 번째 checkpoint로 rollback
    if checkpoints:
        target_cp = checkpoints[0]
        print(f"\n🔄 Rolling back to: {target_cp['step_name']}")

        rollback_result = await supervisor.execute_rollback(
            session_id=test_session_id,
            target_checkpoint_id=target_cp['checkpoint_id']
        )

        print("✅ Rollback completed")
        print(f"Result keys: {list(rollback_result.keys())}")

if __name__ == "__main__":
    asyncio.run(test_rollback_core())
```

**실행:**
```bash
cd backend
python -m tests.manual.test_rollback_phase1
```

**기대 결과:**
```
✅ Initial query completed

📋 Found 15 checkpoints:
  1. aggregate - 결과 집계 단계 (2025-10-22T10:30:45)
  2. execute_teams - 작업 진행: 3/3 완료 (2025-10-22T10:30:30)
  3. planning - 계획 수립 단계 (2025-10-22T10:30:15)

🔄 Rolling back to: aggregate
✅ Rollback completed
Result keys: ['messages', 'final_response', 'execution_steps', ...]
```

---

## 📋 Phase 2: WebSocket API (필수)

**목표:** Frontend와 통신할 WebSocket 핸들러 구현
**소요 시간:** 3-4시간 (0.5일)

### 2.1 WebSocket 핸들러 추가

**파일:** `backend/app/api/chat_api.py`
**위치:** 라인 700-720 (기존 message handler 부분)

**수정할 코드:**

```python
# ========== 기존 코드 (라인 700-706) 수정 ==========
elif message_type == "interrupt_response":
    # LangGraph interrupt 처리 구현
    action = data.get("action")  # "approve" or "modify"
    modified_todos = data.get("modified_todos", [])

    logger.info(f"📨 Interrupt response: {action}")

    # Command를 사용하여 그래프 재개
    from langgraph.types import Command

    if action == "approve":
        # 승인: 그대로 진행
        command = Command(resume=True)
        logger.info("✅ Plan approved, resuming execution")

    elif action == "modify":
        # 수정: 변경사항과 함께 진행
        command = Command(
            resume=True,
            update={"modified_todos": modified_todos}
        )
        logger.info(f"🔧 Plan modified with {len(modified_todos)} changes")

    # TODO: SessionManager를 통해 Command 전달
    # 현재는 로그만 출력 (추후 구현)
    await conn_mgr.send_message(session_id, {
        "type": "interrupt_acknowledged",
        "action": action,
        "timestamp": datetime.now().isoformat()
    })

# ========== 새로운 핸들러 추가 (라인 708+) ==========
# === Get Checkpoints (체크포인트 목록 조회) ===
elif message_type == "get_checkpoints":
    try:
        logger.info(f"📋 Getting checkpoints for session {session_id}")

        # Checkpoint 목록 조회
        checkpoints = await supervisor.get_state_history(
            session_id=session_id,
            limit=data.get("limit", 20)
        )

        # 결과 전송
        await conn_mgr.send_message(session_id, {
            "type": "checkpoints_list",
            "checkpoints": checkpoints,
            "count": len(checkpoints),
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"✅ Sent {len(checkpoints)} checkpoints")

    except Exception as e:
        logger.error(f"❌ Failed to get checkpoints: {e}", exc_info=True)
        await conn_mgr.send_message(session_id, {
            "type": "error",
            "error": f"Failed to get checkpoints: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

# === Rollback Request (롤백 실행) ===
elif message_type == "rollback_request":
    try:
        target_checkpoint_id = data.get("target_checkpoint_id")
        modifications = data.get("modifications")

        if not target_checkpoint_id:
            raise ValueError("target_checkpoint_id is required")

        logger.info(f"🔄 Rollback requested: {target_checkpoint_id}")

        # Rollback 진행 상황 전송
        await conn_mgr.send_message(session_id, {
            "type": "rollback_start",
            "target_checkpoint_id": target_checkpoint_id,
            "timestamp": datetime.now().isoformat()
        })

        # Rollback 실행
        result = await supervisor.execute_rollback(
            session_id=session_id,
            target_checkpoint_id=target_checkpoint_id,
            modifications=modifications
        )

        # 완료 메시지 전송
        await conn_mgr.send_message(session_id, {
            "type": "rollback_complete",
            "target_checkpoint_id": target_checkpoint_id,
            "result": {
                "final_response": result.get("final_response"),
                "execution_steps": result.get("execution_steps", [])
            },
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"✅ Rollback completed for session {session_id}")

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}", exc_info=True)
        await conn_mgr.send_message(session_id, {
            "type": "rollback_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
```

**Import 추가 (파일 상단):**
```python
from langgraph.types import Command
```

---

### 2.2 WebSocket Protocol 문서 업데이트

**파일:** `backend/app/api/chat_api.py`
**위치:** 라인 605-622 (WebSocket docstring)

**추가할 Protocol:**
```python
"""
실시간 채팅 WebSocket 엔드포인트

Protocol:
    Client → Server:
        - {"type": "query", "query": "...", "enable_checkpointing": true}
        - {"type": "interrupt_response", "action": "approve|modify", "modified_todos": [...]}
        - {"type": "get_checkpoints", "limit": 20}                              # 추가
        - {"type": "rollback_request", "target_checkpoint_id": "...", "modifications": {...}}  # 추가

    Server → Client:
        - {"type": "connected", "session_id": "..."}
        - {"type": "planning_start", ...}
        - {"type": "plan_ready", ...}
        - {"type": "checkpoints_list", "checkpoints": [...], "count": 10}       # 추가
        - {"type": "rollback_start", "target_checkpoint_id": "..."}             # 추가
        - {"type": "rollback_complete", "result": {...}}                        # 추가
        - {"type": "rollback_error", "error": "..."}                            # 추가
        - {"type": "final_response", "response": {...}}
        - {"type": "error", "error": "..."}
"""
```

---

### 2.3 Phase 2 테스트

**테스트 도구:** wscat 또는 Python WebSocket 클라이언트

**Option A: wscat 사용**
```bash
# wscat 설치 (Node.js 필요)
npm install -g wscat

# WebSocket 연결
wscat -c ws://localhost:8000/api/v1/chat/ws/test-session-001

# 1. Checkpoint 목록 조회
> {"type": "get_checkpoints", "data": {"limit": 10}}

# 2. Rollback 실행
> {"type": "rollback_request", "data": {"target_checkpoint_id": "1ef..."}}
```

**Option B: Python 클라이언트** (`tests/manual/test_websocket_phase2.py`)

```python
"""
Phase 2 수동 테스트: WebSocket API
"""
import asyncio
import websockets
import json

async def test_websocket_rollback():
    """WebSocket Rollback 테스트"""

    uri = "ws://localhost:8000/api/v1/chat/ws/test-session-001"

    async with websockets.connect(uri) as websocket:
        # 1. 연결 확인
        response = await websocket.recv()
        print(f"📡 Connected: {response}")

        # 2. Checkpoint 목록 요청
        await websocket.send(json.dumps({
            "type": "get_checkpoints",
            "data": {"limit": 5}
        }))

        response = await websocket.recv()
        data = json.loads(response)
        print(f"\n📋 Checkpoints: {data.get('count')} found")

        checkpoints = data.get("checkpoints", [])
        if checkpoints:
            for i, cp in enumerate(checkpoints):
                print(f"  {i+1}. {cp['step_name']} ({cp['checkpoint_id'][:8]}...)")

        # 3. Rollback 실행
        if checkpoints:
            target_cp = checkpoints[0]
            print(f"\n🔄 Requesting rollback to: {target_cp['step_name']}")

            await websocket.send(json.dumps({
                "type": "rollback_request",
                "data": {
                    "target_checkpoint_id": target_cp['checkpoint_id']
                }
            }))

            # 진행 상황 수신
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                msg_type = data.get("type")

                print(f"📨 Received: {msg_type}")

                if msg_type == "rollback_complete":
                    print("✅ Rollback completed!")
                    break
                elif msg_type == "rollback_error":
                    print(f"❌ Error: {data.get('error')}")
                    break

if __name__ == "__main__":
    asyncio.run(test_websocket_rollback())
```

**실행:**
```bash
# 1. Backend 서버 시작
cd backend
uvicorn app.main:app --reload

# 2. 테스트 실행
python -m tests.manual.test_websocket_phase2
```

**기대 결과:**
```
📡 Connected: {"type": "connected", "session_id": "test-session-001"}

📋 Checkpoints: 3 found
  1. aggregate (1ef45678...)
  2. execute_teams (1ef45677...)
  3. planning (1ef45676...)

🔄 Requesting rollback to: aggregate
📨 Received: rollback_start
📨 Received: rollback_complete
✅ Rollback completed!
```

---

## 📋 Phase 3: Frontend (필수)

**목표:** 사용자 친화적인 UI 구현
**소요 시간:** 4-7시간 (1일)

### 3.1 RollbackModal 컴포넌트 생성

**파일:** `frontend/components/ui/rollback-modal.tsx` (새 파일)
**크기:** 약 180 라인

**전체 코드:**
```typescript
"use client"

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Clock, CheckCircle, Circle, AlertCircle } from "lucide-react"

/**
 * Checkpoint 데이터 타입
 */
export interface Checkpoint {
  checkpoint_id: string
  step_name: string
  timestamp: string
  summary: string
  metadata?: Record<string, any>
}

/**
 * RollbackModal Props
 */
export interface RollbackModalProps {
  isOpen: boolean
  checkpoints: Checkpoint[]
  isLoading?: boolean
  onRollback: (checkpointId: string) => void
  onClose: () => void
}

/**
 * Rollback Modal 컴포넌트
 *
 * Checkpoint 목록을 표시하고 사용자가 되돌아갈 지점을 선택할 수 있는 모달
 */
export function RollbackModal({
  isOpen,
  checkpoints,
  isLoading = false,
  onRollback,
  onClose
}: RollbackModalProps) {
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string | null>(null)

  const handleRollback = () => {
    if (selectedCheckpointId) {
      onRollback(selectedCheckpointId)
      setSelectedCheckpointId(null)
    }
  }

  const handleClose = () => {
    setSelectedCheckpointId(null)
    onClose()
  }

  const getStepIcon = (stepName: string) => {
    switch (stepName.toLowerCase()) {
      case 'planning':
        return <Circle className="h-4 w-4" />
      case 'execute_teams':
        return <AlertCircle className="h-4 w-4" />
      case 'aggregate':
        return <CheckCircle className="h-4 w-4" />
      default:
        return <Circle className="h-4 w-4" />
    }
  }

  const getStepBadge = (stepName: string) => {
    switch (stepName.toLowerCase()) {
      case 'planning':
        return <Badge variant="outline">계획</Badge>
      case 'execute_teams':
        return <Badge variant="default">실행</Badge>
      case 'aggregate':
        return <Badge variant="secondary">집계</Badge>
      default:
        return <Badge variant="outline">{stepName}</Badge>
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return new Intl.DateTimeFormat('ko-KR', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }).format(date)
    } catch {
      return timestamp
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>이전 단계로 돌아가기</DialogTitle>
          <DialogDescription>
            되돌아갈 체크포인트를 선택하세요. 선택한 지점부터 다시 실행됩니다.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[400px] pr-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-40">
              <div className="text-muted-foreground">체크포인트를 불러오는 중...</div>
            </div>
          ) : checkpoints.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-center">
              <AlertCircle className="h-12 w-12 text-muted-foreground mb-2" />
              <div className="text-muted-foreground">사용 가능한 체크포인트가 없습니다.</div>
            </div>
          ) : (
            <div className="space-y-3">
              {checkpoints.map((checkpoint, index) => (
                <Card
                  key={checkpoint.checkpoint_id}
                  className={`cursor-pointer transition-all ${
                    selectedCheckpointId === checkpoint.checkpoint_id
                      ? 'ring-2 ring-primary'
                      : 'hover:bg-accent'
                  }`}
                  onClick={() => setSelectedCheckpointId(checkpoint.checkpoint_id)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        {getStepIcon(checkpoint.step_name)}
                        <CardTitle className="text-base">
                          {checkpoint.step_name}
                        </CardTitle>
                        {getStepBadge(checkpoint.step_name)}
                      </div>
                      {index === 0 && (
                        <Badge variant="outline" className="text-xs">최신</Badge>
                      )}
                    </div>
                    <CardDescription className="flex items-center gap-1 text-xs">
                      <Clock className="h-3 w-3" />
                      {formatTimestamp(checkpoint.timestamp)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="text-sm text-muted-foreground">
                      {checkpoint.summary}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            취소
          </Button>
          <Button
            onClick={handleRollback}
            disabled={!selectedCheckpointId || isLoading}
          >
            이 단계로 돌아가기
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

---

### 3.2 useRollback Hook 생성

**디렉토리 생성:**
```bash
mkdir -p frontend/hooks
```

**파일:** `frontend/hooks/useRollback.ts` (새 파일)
**크기:** 약 90 라인

**전체 코드:**
```typescript
"use client"

import { useState, useCallback, useEffect } from 'react'
import { Checkpoint } from '@/components/ui/rollback-modal'

/**
 * useRollback Hook
 *
 * Rollback 기능을 위한 상태 관리 및 WebSocket 통신
 */
export function useRollback(
  websocket: WebSocket | null,
  sessionId: string
) {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  /**
   * Checkpoint 목록 요청
   */
  const requestCheckpoints = useCallback(() => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not connected')
      return
    }

    setIsLoading(true)

    websocket.send(JSON.stringify({
      type: 'get_checkpoints',
      data: {
        limit: 20
      }
    }))

    console.log('📋 Requested checkpoints')
  }, [websocket])

  /**
   * Rollback 실행
   */
  const executeRollback = useCallback((checkpointId: string) => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not connected')
      return
    }

    console.log(`🔄 Executing rollback to checkpoint: ${checkpointId}`)

    websocket.send(JSON.stringify({
      type: 'rollback_request',
      data: {
        target_checkpoint_id: checkpointId
      }
    }))

    setIsModalOpen(false)
  }, [websocket])

  /**
   * Rollback Modal 열기
   */
  const openRollbackModal = useCallback(() => {
    setIsModalOpen(true)
    requestCheckpoints()
  }, [requestCheckpoints])

  /**
   * WebSocket 메시지 핸들러 등록
   */
  useEffect(() => {
    if (!websocket) return

    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data)

        if (message.type === 'checkpoints_list') {
          setCheckpoints(message.checkpoints || [])
          setIsLoading(false)
          console.log(`✅ Received ${message.count} checkpoints`)
        } else if (message.type === 'rollback_complete') {
          console.log('✅ Rollback completed')
          // 필요시 UI 업데이트
        } else if (message.type === 'rollback_error') {
          console.error('❌ Rollback error:', message.error)
          setIsLoading(false)
        }
      } catch (error) {
        console.error('❌ Failed to parse WebSocket message:', error)
      }
    }

    websocket.addEventListener('message', handleMessage)

    return () => {
      websocket.removeEventListener('message', handleMessage)
    }
  }, [websocket])

  return {
    checkpoints,
    isModalOpen,
    isLoading,
    openRollbackModal,
    executeRollback,
    closeModal: () => setIsModalOpen(false)
  }
}
```

---

### 3.3 ChatInterface 수정

**파일:** `frontend/components/chat-interface.tsx`
**수정 위치:** 기존 파일에 추가

**Import 추가 (파일 상단):**
```typescript
import { useRollback } from '@/hooks/useRollback'
import { RollbackModal } from '@/components/ui/rollback-modal'
import { RotateCcw } from 'lucide-react'
```

**Hook 사용 (컴포넌트 내부):**
```typescript
export function ChatInterface() {
  // ========== 기존 상태들 (그대로 유지) ==========
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [websocket, setWebsocket] = useState<WebSocket | null>(null)
  const sessionId = "session-xxx" // 실제 세션 ID 사용

  // ========== Rollback Hook 추가 ==========
  const {
    checkpoints,
    isModalOpen,
    isLoading,
    openRollbackModal,
    executeRollback,
    closeModal
  } = useRollback(websocket, sessionId)

  // ... 기존 코드 ...

  return (
    <div className="flex flex-col h-screen">
      {/* 헤더 영역에 Rollback 버튼 추가 */}
      <div className="flex items-center justify-between p-4 border-b">
        <h1 className="text-xl font-bold">HolmesNyangz</h1>

        <Button
          variant="outline"
          size="sm"
          onClick={openRollbackModal}
          className="gap-2"
        >
          <RotateCcw className="h-4 w-4" />
          이전 단계로
        </Button>
      </div>

      {/* 채팅 영역 (기존 코드 유지) */}
      <div className="flex-1 overflow-y-auto">
        {/* ... 기존 메시지 렌더링 코드 ... */}
      </div>

      {/* 입력 영역 (기존 코드 유지) */}
      <div className="p-4 border-t">
        {/* ... 기존 입력 필드 ... */}
      </div>

      {/* Rollback Modal 추가 */}
      <RollbackModal
        isOpen={isModalOpen}
        checkpoints={checkpoints}
        isLoading={isLoading}
        onRollback={executeRollback}
        onClose={closeModal}
      />
    </div>
  )
}
```

---

### 3.4 Phase 3 테스트

**브라우저 테스트:**

```bash
# Frontend 개발 서버 시작
cd frontend
npm run dev

# 브라우저에서 접속
# http://localhost:3000
```

**테스트 시나리오:**

1. **Rollback 버튼 확인**
   - [ ] 우측 상단에 "⏮️ 이전 단계로" 버튼 표시
   - [ ] 버튼 클릭 시 Modal 열림

2. **Checkpoint 목록 표시**
   - [ ] Modal에 Checkpoint 목록 표시
   - [ ] 각 항목에 단계명, 시간, 요약 표시
   - [ ] 최신 항목에 "최신" 배지 표시

3. **Checkpoint 선택**
   - [ ] Checkpoint 클릭 시 선택 강조 (ring-2)
   - [ ] "이 단계로 돌아가기" 버튼 활성화

4. **Rollback 실행**
   - [ ] 버튼 클릭 시 WebSocket 메시지 전송
   - [ ] Modal 자동 닫힘
   - [ ] 콘솔에 "Rollback completed" 로그 출력

5. **에러 처리**
   - [ ] Checkpoint 없을 때 "사용 가능한 체크포인트가 없습니다" 메시지
   - [ ] 로딩 중 "체크포인트를 불러오는 중..." 표시

---

## 📊 전체 구현 체크리스트

### Phase 1: Backend Core ✅
- [ ] `separated_states.py`: MainSupervisorState에 rollback 필드 추가 (5분)
- [ ] `rollback_manager.py`: RollbackManager 클래스 생성 (2-3시간)
- [ ] `team_supervisor.py`: execute_rollback(), get_state_history() 메서드 추가 (1-2시간)
- [ ] Phase 1 수동 테스트 실행 및 검증 (30분)

### Phase 2: WebSocket API ✅
- [ ] `chat_api.py`: interrupt_response 핸들러 완성 (30분)
- [ ] `chat_api.py`: get_checkpoints 핸들러 추가 (1시간)
- [ ] `chat_api.py`: rollback_request 핸들러 추가 (1시간)
- [ ] WebSocket Protocol 문서 업데이트 (10분)
- [ ] Phase 2 WebSocket 테스트 실행 및 검증 (30분)

### Phase 3: Frontend ✅
- [ ] `rollback-modal.tsx`: RollbackModal 컴포넌트 생성 (2-3시간)
- [ ] `useRollback.ts`: useRollback Hook 생성 (1-2시간)
- [ ] `chat-interface.tsx`: Rollback 버튼 + Modal 통합 (1시간)
- [ ] Phase 3 브라우저 UI 테스트 (1시간)

### 최종 통합 테스트 ✅
- [ ] End-to-End 테스트: 전체 Rollback 흐름 검증 (1시간)
- [ ] 문서화: API 문서 및 사용자 가이드 작성 (1시간)

---

## 🚀 구현 시작하기

### 준비 사항
- ✅ Checkpointer 인프라 완성 (AsyncPostgresSaver 연결됨)
- ✅ ExecutionStepState 존재 (TODO 추적 구조)
- ✅ WebSocket 기반 구축됨
- ✅ Frontend 프로젝트 존재 (Next.js + shadcn/ui)

### 시작 순서
1. **Phase 1 시작**: `separated_states.py` 파일 열기
2. **코드 작성**: 본 문서의 코드를 순서대로 복사/붙여넣기
3. **테스트**: 각 Phase 완료 후 반드시 테스트 실행
4. **다음 Phase**: 테스트 통과 후 다음 단계 진행

### 예상 일정
- **Day 1 (오전)**: Phase 1 완료 + 테스트
- **Day 1 (오후)**: Phase 2 완료 + 테스트
- **Day 2 (오전)**: Phase 3 완료
- **Day 2 (오후)**: 통합 테스트 + 문서화

---

## 📚 참고 문서

- **LangGraph Time Travel**: https://langchain-ai.github.io/langgraph/how-tos/time-travel/
- **Checkpointer 가이드**: `../human_in_the_loop/CHECKPOINTER_COMPLETE_GUIDE.md`
- **원본 계획**: `TODO_MANAGEMENT_IMPLEMENTATION_251022.md`
- **Schema 명확화**: `../database/CHECKPOINT_SCHEMA_CLARIFICATION_251022.md`

---

**작성 완료.** 이제 Phase 1부터 순차적으로 구현을 시작할 수 있습니다.
