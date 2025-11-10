"""WebSocket 엔드포인트

Phase 4.3: 실시간 스트리밍 구현
Phase 3: Context API 지원 추가
"""
import asyncio
import json
from typing import Dict, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph as build_supervisor_graph
from backend.app.octostrator.checkpointer import create_checkpointer
from backend.app.octostrator.session import create_session, get_session_config
from backend.app.octostrator.contexts.app_context import create_app_context, UserTier
from backend.app.config.llm_settings import get_llm_settings_for_user


router = APIRouter()


def log_with_timestamp(message: str, start_time: Optional[datetime] = None):
    """타임스탬프와 경과시간을 포함한 로그 출력

    Args:
        message: 로그 메시지
        start_time: 실행 시작 시간 (경과시간 계산용)
    """
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S.%f")[:-3]  # 밀리초까지만

    if start_time:
        elapsed = (now - start_time).total_seconds()
        print(f"{timestamp} [{elapsed:6.3f}s] | {message}")
    else:
        print(f"{timestamp} | {message}")


class ConnectionManager:
    """WebSocket 연결 관리자"""

    def __init__(self):
        """초기화"""
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """클라이언트 연결

        Args:
            session_id: 세션 ID
            websocket: WebSocket 객체
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        log_with_timestamp(f"[WebSocket] Client connected: {session_id}")

    def disconnect(self, session_id: str):
        """클라이언트 연결 해제

        Args:
            session_id: 세션 ID
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            log_with_timestamp(f"[WebSocket] Client disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        """메시지 전송

        Args:
            session_id: 세션 ID
            message: 전송할 메시지 (dict)
        """
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                log_with_timestamp(f"[WebSocket] Failed to send message to {session_id}: {e}")
                self.disconnect(session_id)


# 전역 ConnectionManager 인스턴스
manager = ConnectionManager()


async def create_progress_callback(session_id: str):
    """Progress callback 생성

    Args:
        session_id: 세션 ID

    Returns:
        async callback 함수
    """
    async def progress_callback(event_type: str, event_data: dict):
        """진행 상황 콜백

        Args:
            event_type: 이벤트 타입
            event_data: 이벤트 데이터
        """
        message = {
            "type": event_type,
            "data": event_data,
            "session_id": session_id
        }
        await manager.send_message(session_id, message)

    return progress_callback


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket 채팅 엔드포인트

    Phase 4.3: 실시간 스트리밍
    Phase 3: Context API 지원 추가

    클라이언트는 다음 형식으로 메시지를 전송합니다:
    {
        "message": "사용자 메시지",
        "output_format": "chat",  # optional
        "debug": false,           # optional (Phase 3: 디버그 모드)
        "trace_id": "...",        # optional (Phase 3: 분산 추적 ID)
        "user_id": "..."          # optional (Phase 3: 사용자 ID, Tier 자동 추출)
    }

    서버는 다음 형식으로 이벤트를 전송합니다:
    {
        "type": "node_started" | "node_completed" | "hitl_waiting" | "final_result" | "error",
        "data": { ... },
        "session_id": "..."
    }

    Phase 3 Features:
    - debug: true로 설정 시 상세 로깅 활성화
    - trace_id: 분산 추적을 위한 고유 ID (미제공 시 자동 생성)
    - user_id: 사용자 ID (prefix로 Tier 자동 추출: premium_, trial_, 기타)
      - premium_user123 -> UserTier.PREMIUM (gpt-4o, 높은 tokens)
      - trial_user456 -> UserTier.TRIAL (gpt-4o-mini, 낮은 tokens)
      - user789 -> UserTier.STANDARD (균형잡힌 설정)

    Args:
        websocket: WebSocket 연결
        session_id: 세션 ID
    """
    # 연결 수락
    await manager.connect(session_id, websocket)

    # Checkpointer 및 Graph 초기화
    checkpointer = None
    graph = None

    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()
        log_with_timestamp(f"[WebSocket] Checkpointer 생성 완료: {session_id}")

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)
        log_with_timestamp(f"[WebSocket] Graph 빌드 완료: {session_id}")

        # 연결 성공 메시지
        await manager.send_message(session_id, {
            "type": "connected",
            "data": {"message": "WebSocket 연결 성공"},
            "session_id": session_id
        })

        # 메시지 수신 루프
        while True:
            # 클라이언트 메시지 대기
            data = await websocket.receive_json()

            # 메시지 검증
            if "message" not in data:
                await manager.send_message(session_id, {
                    "type": "error",
                    "data": {"error": "Message field is required"},
                    "session_id": session_id
                })
                continue

            user_message = data["message"]
            output_format = data.get("output_format", "chat")

            # Phase 3: Context API - 디버그 옵션 추출
            debug = data.get("debug", False)
            trace_id = data.get("trace_id", None)
            user_id = data.get("user_id", f"user_{session_id}")

            # 실행 시작 시간 기록
            start_time = datetime.now()
            log_with_timestamp(f"[WebSocket] Received message from {session_id}: {user_message[:50]}...")

            # Phase 3: AppContext 생성
            # user_id로부터 자동으로 UserTier 추출
            llm_settings = get_llm_settings_for_user()  # 기본값: STANDARD
            app_context = create_app_context(
                user_id=user_id,
                session_id=session_id,
                llm_settings=llm_settings,
                debug=debug,
                trace_id=trace_id
            )

            if debug:
                log_with_timestamp(f"[WebSocket] Debug mode enabled | Trace ID: {app_context.trace_id} | User Tier: {app_context.user_tier.value}")

            # thread_id로 config 생성 (Phase 3: context 포함)
            config = get_session_config(session_id, context=app_context)

            # 그래프 실행
            try:
                log_with_timestamp(f"[WebSocket] ===== 그래프 실행 시작 =====", start_time)

                # 실행 시작 알림
                await manager.send_message(session_id, {
                    "type": "execution_started",
                    "data": {"message": "처리 중..."},
                    "session_id": session_id
                })
                log_with_timestamp(f"[WebSocket] execution_started 메시지 전송 완료", start_time)

                # 초기 입력 생성 (Octostrator format)
                # 주의: State에는 직렬화 가능한 데이터만 포함
                initial_input = {
                    # User input
                    "user_query": user_message,
                    "session_id": session_id,
                    "output_format": output_format,

                    # State tracking
                    "plan": {},
                    "todos": [],
                    "execution_results": {},
                    "final_response": "",

                    # Flags
                    "plan_valid": False,
                    "requires_approval": False,
                    "error": None
                }
                log_with_timestamp(f"[WebSocket] Initial input 생성 완료", start_time)

                # 실시간 스트리밍
                log_with_timestamp(f"[WebSocket] astream_events 시작...", start_time)
                async for event in graph.astream_events(initial_input, config=config, version="v2"):
                    # 이벤트 타입별 처리
                    event_type = event.get("event")
                    event_name = event.get("name")
                    event_data = event.get("data", {})

                    # on_chat_model_stream은 너무 많아서 로그 제외 (토큰 단위 스트리밍)
                    if event_type != "on_chat_model_stream":
                        log_with_timestamp(f"[WebSocket] Event: {event_type} | {event_name}", start_time)

                    # 노드 시작
                    if event_type == "on_chain_start":
                        if event_name and not event_name.startswith("__"):
                            await manager.send_message(session_id, {
                                "type": "node_started",
                                "data": {
                                    "node": event_name,
                                    "run_id": event.get("run_id")
                                },
                                "session_id": session_id
                            })

                    # 노드 완료
                    elif event_type == "on_chain_end":
                        if event_name and not event_name.startswith("__"):
                            await manager.send_message(session_id, {
                                "type": "node_completed",
                                "data": {
                                    "node": event_name,
                                    "run_id": event.get("run_id")
                                },
                                "session_id": session_id
                            })

                            # Cognitive Layer 완료 후 plan 전송
                            if event_name == "cognitive":
                                state = await graph.aget_state(config)
                                if state.values:
                                    await manager.send_message(session_id, {
                                        "type": "plan_update",
                                        "data": {
                                            "plan": state.values.get("plan", {}),
                                            "plan_valid": state.values.get("plan_valid", False)
                                        },
                                        "session_id": session_id
                                    })
                                    log_with_timestamp(f"[WebSocket] plan_update 전송 완료", start_time)

                            # Todo Layer 완료 후 todos 전송
                            if event_name == "todo":
                                state = await graph.aget_state(config)
                                if state.values:
                                    await manager.send_message(session_id, {
                                        "type": "todos_update",
                                        "data": {
                                            "todos": state.values.get("todos", []),
                                            "total_todos": state.values.get("total_todos", 0)
                                        },
                                        "session_id": session_id
                                    })
                                    log_with_timestamp(f"[WebSocket] todos_update 전송 완료", start_time)

                            # Execute Layer 완료 후 execution results 전송
                            if event_name == "execute":
                                state = await graph.aget_state(config)
                                if state.values:
                                    await manager.send_message(session_id, {
                                        "type": "execution_update",
                                        "data": {
                                            "completed": state.values.get("completed", 0),
                                            "failed": state.values.get("failed", 0),
                                            "success_rate": state.values.get("success_rate", 0)
                                        },
                                        "session_id": session_id
                                    })
                                    log_with_timestamp(f"[WebSocket] execution_update 전송 완료", start_time)

                # 최종 결과 조회
                log_with_timestamp(f"[WebSocket] astream_events 완료. 최종 상태 조회 중...", start_time)
                final_state = await graph.aget_state(config)
                log_with_timestamp(f"[WebSocket] Final state 조회 완료", start_time)

                # 정상 완료 시 최종 결과 전송
                if final_state.values:
                    final_response = final_state.values.get("final_response", "")
                    completed = final_state.values.get("completed", 0)
                    total_todos = final_state.values.get("total_todos", 0)
                    error = final_state.values.get("error")

                    log_with_timestamp(f"[WebSocket] Final response: {final_response[:100] if final_response else 'None'}...", start_time)
                    log_with_timestamp(f"[WebSocket] Todos: {completed}/{total_todos}", start_time)

                    if error:
                        log_with_timestamp(f"[WebSocket] ⚠️ Error in execution: {error}", start_time)

                    await manager.send_message(session_id, {
                        "type": "final_result",
                        "data": {
                            "result": final_response or f"처리 중 오류가 발생했습니다: {error}" if error else "응답을 생성할 수 없습니다.",
                            "completed": completed,
                            "total_todos": total_todos,
                            "success_rate": final_state.values.get("success_rate", 0)
                        },
                        "session_id": session_id
                    })
                else:
                    log_with_timestamp(f"[WebSocket] ⚠️ Final state has no values!", start_time)

                # 완료 알림
                log_with_timestamp(f"[WebSocket] execution_completed 메시지 전송", start_time)
                await manager.send_message(session_id, {
                    "type": "execution_completed",
                    "data": {"message": "처리 완료"},
                    "session_id": session_id
                })
                log_with_timestamp(f"[WebSocket] ===== 그래프 실행 완료 =====", start_time)

            except Exception as e:
                log_with_timestamp(f"[WebSocket] ❌ ERROR during execution: {e}", start_time)
                import traceback
                log_with_timestamp(f"[WebSocket] ===== Full Traceback =====", start_time)
                traceback.print_exc()
                log_with_timestamp(f"[WebSocket] ===== End Traceback =====", start_time)

                await manager.send_message(session_id, {
                    "type": "error",
                    "data": {
                        "error": str(e),
                        "message": "처리 중 오류가 발생했습니다"
                    },
                    "session_id": session_id
                })
                log_with_timestamp(f"[WebSocket] Error 메시지 전송 완료", start_time)

    except WebSocketDisconnect:
        log_with_timestamp(f"[WebSocket] Client disconnected: {session_id}")
        manager.disconnect(session_id)

    except Exception as e:
        log_with_timestamp(f"[WebSocket] Error: {e}")
        import traceback
        traceback.print_exc()

        try:
            await manager.send_message(session_id, {
                "type": "error",
                "data": {"error": str(e)},
                "session_id": session_id
            })
        except:
            pass

        manager.disconnect(session_id)

    finally:
        # 연결 정리
        manager.disconnect(session_id)
