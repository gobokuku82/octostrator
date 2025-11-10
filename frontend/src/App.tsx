import React, { useState, useRef, useEffect } from 'react';
import './App.css';
import { Dashboard } from './components/Dashboard';
import { PlanStep, ExecutionEvent, ErrorLog, DashboardState } from './types/dashboard';

interface Message {
  id: string;
  type: 'user' | 'bot' | 'system';
  content: string;
  timestamp: Date;
}

interface HITLState {
  isWaiting: boolean;
  question: string;
  plan: any[];
  currentStep: number;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'bot',
      content: '안녕하세요! 스페셜 에이전트입니다.\n무엇을 도와드릴까요?',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [hitlState, setHitlState] = useState<HITLState>({
    isWaiting: false,
    question: '',
    plan: [],
    currentStep: 0,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string>(`session_${Date.now()}`);
  const messageCounterRef = useRef<number>(0);

  // Dashboard state
  const [currentNode, setCurrentNode] = useState<string | null>(null);
  const [planSteps, setPlanSteps] = useState<PlanStep[]>([]);
  const [currentStepDash, setCurrentStepDash] = useState<number>(0);
  const [stateValues, setStateValues] = useState<DashboardState>({
    current_step: 0,
    plan: [],
    messages: 0,
    output_format: 'chat',
  });
  const [errors, setErrors] = useState<ErrorLog[]>([]);
  const [executionHistory, setExecutionHistory] = useState<ExecutionEvent[]>([]);

  const quickQuestions = [
    '에이전트기능1',
    '에이전트기능2',
    '에이전트기능3',
  ];

  // 스크롤 자동 이동
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // WebSocket 연결
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    const sessionId = sessionIdRef.current;
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}`);

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      setIsConnected(true);

      addSystemMessage('✅ WebSocket 연결 성공');
    };

    ws.onclose = () => {
      console.log('[WebSocket] Disconnected');
      setIsConnected(false);

      addSystemMessage('❌ WebSocket 연결 해제됨. 재연결 시도 중...');

      // 3초 후 재연결 시도
      setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      addSystemMessage('⚠️ WebSocket 오류 발생');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };

    wsRef.current = ws;
  };

  const handleWebSocketMessage = (data: any) => {
    const { type, data: eventData } = data;

    switch (type) {
      case 'connected':
        // 연결 성공 메시지는 이미 onopen에서 처리
        break;

      case 'execution_started':
        setIsLoading(true);
        addSystemMessage('🔄 처리 중...');
        break;

      case 'node_started':
        const nodeNameMap: { [key: string]: string } = {
          intent: '의도 파악',
          planning: '작업 계획 수립',
          executor: '실행기',
          diet: '식단 에이전트',
          workout: '운동 에이전트',
          schedule: '스케줄 에이전트',
          member_care: '회원 관리 에이전트',
          coaching: '코칭 에이전트',
          aggregator: '결과 종합',
          chat_generator: '답변 생성',
        };
        const nodeName = nodeNameMap[eventData.node] || eventData.node;
        addSystemMessage(`▶️ ${nodeName} 시작`);

        // Dashboard 업데이트
        setCurrentNode(eventData.node);
        setExecutionHistory(prev => [...prev, {
          timestamp: new Date().toISOString(),
          node: eventData.node,
          eventType: 'started'
        }]);
        break;

      case 'node_completed':
        // 노드 완료 메시지는 생략 (너무 많아서)

        // Dashboard 업데이트
        setCurrentNode(null);
        setExecutionHistory(prev => {
          const lastEvent = prev[prev.length - 1];
          if (lastEvent && lastEvent.node === eventData.node && lastEvent.eventType === 'started') {
            const duration = (new Date().getTime() - new Date(lastEvent.timestamp).getTime()) / 1000;
            return [...prev, {
              timestamp: new Date().toISOString(),
              node: eventData.node,
              eventType: 'completed',
              duration
            }];
          }
          return prev;
        });
        break;

      case 'hitl_waiting':
        // HITL 대기 상태
        setIsLoading(false);
        setHitlState({
          isWaiting: true,
          question: eventData.question,
          plan: eventData.plan || [],
          currentStep: eventData.current_step || 0,
        });

        addSystemMessage(`⏸️ 사용자 승인 대기 중`);

        // HITL 질문을 봇 메시지로 추가
        const hitlMessage: Message = {
          id: Date.now().toString(),
          type: 'bot',
          content: `[승인 필요]\n${eventData.question}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, hitlMessage]);
        break;

      case 'final_result':
        setIsLoading(false);

        if (eventData.result) {
          const botMessage: Message = {
            id: Date.now().toString(),
            type: 'bot',
            content: eventData.result,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, botMessage]);
        }
        break;

      case 'execution_completed':
        setIsLoading(false);
        addSystemMessage('✅ 처리 완료');
        break;

      case 'plan_update':
        // Dashboard plan 업데이트
        // plan이 객체일 수 있으므로 배열로 변환
        const planData = eventData.plan || {};
        const steps = Array.isArray(planData)
          ? planData
          : (planData.steps || []);
        setPlanSteps(steps);
        setCurrentStepDash(eventData.current_step || 0);
        break;

      case 'state_update':
        // Dashboard state 업데이트
        setStateValues(eventData.state || {
          current_step: 0,
          plan: [],
          messages: 0,
          output_format: 'chat',
        });
        break;

      case 'error':
        setIsLoading(false);

        const errorMessage: Message = {
          id: Date.now().toString(),
          type: 'bot',
          content: `❌ 오류 발생: ${eventData.error || eventData.message}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);

        // Dashboard 에러 추가
        setErrors(prev => [...prev, {
          timestamp: new Date().toISOString(),
          node: eventData.node || 'unknown',
          message: eventData.error || eventData.message
        }]);
        break;

      default:
        console.log('[WebSocket] Unknown message type:', type);
    }
  };

  const addSystemMessage = (content: string) => {
    messageCounterRef.current += 1;
    const systemMessage: Message = {
      id: `system_${Date.now()}_${messageCounterRef.current}`,
      type: 'system',
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, systemMessage]);
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading || !isConnected) return;

    // 사용자 메시지 추가
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // WebSocket으로 메시지 전송
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          message: content,
          output_format: 'chat',
        })
      );
    } else {
      setIsLoading(false);
      addSystemMessage('❌ WebSocket 연결이 없습니다. 재연결 중...');
      connectWebSocket();
    }
  };

  const handleHITLApprove = () => {
    if (!hitlState.isWaiting) return;

    // 승인 메시지 전송
    const approvalMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: '[승인] 네, 진행해주세요',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, approvalMessage]);

    // HITL 상태 해제
    setHitlState({
      isWaiting: false,
      question: '',
      plan: [],
      currentStep: 0,
    });

    setIsLoading(true);

    // WebSocket으로 승인 전송 (None으로 재개)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          message: '승인',
          hitl_response: 'approved',
        })
      );
    }
  };

  const handleHITLReject = () => {
    if (!hitlState.isWaiting) return;

    // 거부 메시지 전송
    const rejectionMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: '[거부] 아니요, 취소해주세요',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, rejectionMessage]);

    // HITL 상태 해제
    setHitlState({
      isWaiting: false,
      question: '',
      plan: [],
      currentStep: 0,
    });

    setIsLoading(false);

    // WebSocket으로 거부 전송
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          message: '거부',
          hitl_response: 'rejected',
        })
      );
    }

    addSystemMessage('❌ 작업이 취소되었습니다');
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const handleQuickQuestion = (question: string) => {
    sendMessage(question);
  };

  return (
    <div className="app-container">
      {/* Dashboard 영역 (왼쪽) */}
      <Dashboard
        currentNode={currentNode}
        planSteps={planSteps}
        currentStep={currentStepDash}
        stateValues={stateValues}
        errors={errors}
        executionHistory={executionHistory}
      />

      {/* Chatbot 영역 (오른쪽) */}
      <div className="chatbot-area">
        <div className="chat-container">
        <div className="chat-header">
          <h1>Fitness PT Manager</h1>
          <p>
            운동용 챗봇 테스트
            {isConnected ? (
              <span style={{ color: '#4caf50', marginLeft: '10px' }}>● 연결됨</span>
            ) : (
              <span style={{ color: '#f44336', marginLeft: '10px' }}>● 연결 끊김</span>
            )}
          </p>
        </div>

        <div className="quick-actions">
          {quickQuestions.map((question, index) => (
            <button
              key={index}
              className="quick-action-btn"
              onClick={() => handleQuickQuestion(question)}
              disabled={isLoading || !isConnected}
            >
              {question}
            </button>
          ))}
        </div>

        <div className="messages">
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              <div className="message-content">
                {message.content}
              </div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString('ko-KR', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message bot">
              <div className="message-content typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* HITL 승인 UI */}
        {hitlState.isWaiting && (
          <div className="hitl-container">
            <div className="hitl-question">
              <p><strong>승인 필요:</strong> {hitlState.question}</p>
            </div>
            <div className="hitl-actions">
              <button
                className="hitl-btn approve"
                onClick={handleHITLApprove}
              >
                ✓ 승인
              </button>
              <button
                className="hitl-btn reject"
                onClick={handleHITLReject}
              >
                ✗ 거부
              </button>
            </div>
          </div>
        )}

        <div className="input-container">
          <input
            type="text"
            className="chat-input"
            placeholder={
              !isConnected
                ? 'WebSocket 연결 중...'
                : hitlState.isWaiting
                ? '승인/거부를 선택해주세요'
                : '메시지를 입력하세요...'
            }
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading || !isConnected || hitlState.isWaiting}
          />
          <button
            className="send-button"
            onClick={() => sendMessage(inputValue)}
            disabled={isLoading || !inputValue.trim() || !isConnected || hitlState.isWaiting}
          >
            전송
          </button>
        </div>
        </div>
      </div>
    </div>
  );
}

export default App;
