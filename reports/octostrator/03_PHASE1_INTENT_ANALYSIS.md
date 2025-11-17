# 03. Phase 1: Intent Analysis Agent

**문서 버전**: 1.0.0  
**작성일**: 2025-11-17  
**관련 문서**: [02_STATE_SCHEMA.md](./02_STATE_SCHEMA.md)

---

## 📋 목차

1. [Intent Analysis 개요](#1-intent-analysis-개요)
2. [의도 분류 체계](#2-의도-분류-체계)
3. [구현 전략](#3-구현-전략)
4. [LLM 프롬프트 설계](#4-llm-프롬프트-설계)
5. [라우팅 로직](#5-라우팅-로직)
6. [예외 처리](#6-예외-처리)
7. [테스트 케이스](#7-테스트-케이스)

---

## 1. Intent Analysis 개요

### 1.1 역할

**Intent Analysis Agent**는 사용자 쿼리를 분석하여 4가지 의도로 분류하는 첫 번째 노드입니다.

```
사용자 쿼리
    ↓
Intent Analysis Agent
    ↓
의도 분류 (4가지)
    ↓
적절한 다음 노드로 라우팅
```

### 1.2 입력/출력

| 항목 | 설명 |
|------|------|
| **입력** | `state["messages"][-1]`: 최신 사용자 메시지 |
| **분석 컨텍스트** | 대화 히스토리, 활성 TODO, 실행 상태 |
| **출력** | `current_intent`, `intent_confidence` |
| **라우팅** | Command API로 다음 노드 지정 |

### 1.3 처리 시간

- **목표**: 1-2초 이내
- **LLM 호출**: 1회
- **병목 없음**: 빠른 분류 후 즉시 라우팅

---

## 2. 의도 분류 체계

### 2.1 4가지 의도

| 의도 | 설명 | 다음 노드 | 예시 |
|------|------|----------|------|
| **new_task** | 새로운 복잡한 작업 요청 | `planning_agent` | "AI 보고서 만들어줘" |
| **modify_task** | 기존 작업 수정 | `planning_agent` | "거기에 한국 시장도 추가해줘" |
| **continue_task** | 작업 계속/재개 | `supervisor_agent` | "계속해줘", "다음 단계 진행" |
| **simple_qa** | 단순 질문 | `simple_qa_agent` | "GPT-5는 언제 나와?" |

### 2.2 분류 기준

#### new_task
**특징**:
- 여러 단계가 필요한 작업
- 복잡한 결과물 생성 (문서, 코드, 분석)
- 3개 이상의 하위 작업 필요
- 중간 검증이 필요

**키워드**:
- "만들어줘", "작성해줘", "분석해줘"
- "보고서", "문서", "코드", "프로젝트"

#### modify_task
**특징**:
- 기존 TODO 참조
- 지시대명사 사용 ("거기", "그거", "이거")
- 추가/수정/삭제 요청

**키워드**:
- "추가해줘", "수정해줘", "바꿔줘"
- "거기에", "그 보고서에"
- "대신", "말고"

#### continue_task
**특징**:
- 명시적 계속 요청
- 실행 중 TODO 존재
- 추가 지시 없음

**키워드**:
- "계속", "다음", "진행"
- "이어서", "끝까지"

#### simple_qa
**특징**:
- 단일 사실 질문
- 1-2단계로 답변 가능
- TODO 불필요

**키워드**:
- "뭐야", "언제", "어디", "누가"
- "설명해줘", "알려줘" (간단한)

### 2.3 애매한 경우

**확신도 (confidence) 활용**:
```python
if intent_confidence < 0.7:
    # 사용자에게 명확화 요청
    user_clarification = interrupt({
        "type": "intent_clarification",
        "message": "다음 중 어떤 작업을 원하시나요?",
        "data": {
            "options": [
                {"label": "새 작업 시작", "value": "new_task"},
                {"label": "기존 작업 수정", "value": "modify_task"},
                {"label": "단순 질문", "value": "simple_qa"}
            ]
        }
    })
```

---

## 3. 구현 전략

### 3.1 노드 구조

```python
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage
import json

def intent_analysis_agent(state: MainState) -> Command:
    """
    Intent Analysis Agent
    사용자 쿼리를 분석하여 의도를 분류
    """
    
    # 1. 컨텍스트 수집
    current_query = state["messages"][-1].content
    conversation_history = state["messages"][:-1]
    active_todos = state.get("todos", [])
    conversation_mode = state.get("conversation_mode", "idle")
    
    # 2. LLM으로 의도 분석
    analysis = analyze_intent_with_llm(
        query=current_query,
        history=conversation_history,
        todos=active_todos,
        mode=conversation_mode
    )
    
    # 3. 확신도 체크
    if analysis["confidence"] < 0.7:
        # 명확화 요청
        clarification = request_clarification(analysis)
        return Command(
            update={
                "current_intent": clarification["intent"],
                "intent_confidence": 1.0
            },
            goto=route_by_intent(clarification["intent"])
        )
    
    # 4. 라우팅
    return Command(
        update={
            "current_intent": analysis["intent"],
            "intent_confidence": analysis["confidence"]
        },
        goto=route_by_intent(analysis["intent"])
    )
```

### 3.2 LLM 호출 함수

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOpenAI(model="gpt-4", temperature=0)

def analyze_intent_with_llm(
    query: str,
    history: List[BaseMessage],
    todos: List[TodoItem],
    mode: str
) -> dict:
    """
    LLM으로 의도 분석
    """
    
    # 프롬프트 생성
    prompt = ChatPromptTemplate.from_messages([
        ("system", INTENT_ANALYSIS_SYSTEM_PROMPT),
        ("user", INTENT_ANALYSIS_USER_TEMPLATE)
    ])
    
    # 컨텍스트 준비
    history_str = format_conversation_history(history)
    todos_str = format_todos(todos)
    
    # LLM 호출
    response = llm.invoke(
        prompt.format_messages(
            query=query,
            history=history_str,
            todos=todos_str,
            mode=mode
        )
    )
    
    # JSON 파싱
    analysis = json.loads(response.content)
    
    return {
        "intent": analysis["intent"],
        "confidence": analysis["confidence"],
        "reasoning": analysis["reasoning"]
    }
```

### 3.3 라우팅 함수

```python
def route_by_intent(intent: str) -> str:
    """
    의도에 따라 다음 노드 결정
    """
    routing_map = {
        "new_task": "planning_agent",
        "modify_task": "planning_agent",
        "continue_task": "supervisor_agent",
        "simple_qa": "simple_qa_agent"
    }
    
    return routing_map.get(intent, "simple_qa_agent")  # 기본값
```

---

## 4. LLM 프롬프트 설계

### 4.1 System Prompt

```python
INTENT_ANALYSIS_SYSTEM_PROMPT = """
당신은 사용자의 의도를 정확하게 분류하는 전문가입니다.

사용자 쿼리를 분석하여 다음 4가지 의도 중 하나로 분류하세요:

1. **new_task**: 새로운 복잡한 작업 요청
   - 여러 단계가 필요한 작업
   - 복잡한 결과물 (문서, 코드, 분석)
   - 3개 이상의 하위 작업 필요
   
2. **modify_task**: 기존 작업 수정
   - 지시대명사 사용 ("거기", "그거", "이것")
   - 추가/수정/삭제 요청
   - 기존 TODO 참조
   
3. **continue_task**: 작업 계속/재개
   - "계속", "다음", "진행" 등
   - 추가 지시 없음
   
4. **simple_qa**: 단순 질문
   - 단일 사실 질문
   - 1-2단계로 답변 가능
   - TODO 불필요

분류 기준:
- **복잡도**: 필요한 단계 수
- **컨텍스트**: 대화 히스토리 및 기존 TODO 참조
- **키워드**: 특정 동사, 명사 패턴

JSON 형식으로 응답하세요:
{
    "intent": "new_task" | "modify_task" | "continue_task" | "simple_qa",
    "confidence": 0.0-1.0,
    "reasoning": "판단 근거 (한 문장)"
}
"""
```

### 4.2 User Template

```python
INTENT_ANALYSIS_USER_TEMPLATE = """
**사용자 쿼리**: {query}

**대화 히스토리** (최근 3턴):
{history}

**활성 TODO** ({num_todos}개):
{todos}

**현재 실행 상태**: {mode}

위 정보를 바탕으로 사용자의 의도를 분류하세요.

특히 다음을 고려하세요:
1. 활성 TODO가 있는가? → modify_task 또는 continue_task 가능성 높음
2. 지시대명사("거기", "그거")가 있는가? → modify_task
3. 복잡한 결과물을 요구하는가? → new_task
4. 단순 사실 질문인가? → simple_qa

JSON으로 응답하세요.
"""
```

### 4.3 포맷팅 함수

```python
def format_conversation_history(history: List[BaseMessage]) -> str:
    """대화 히스토리를 문자열로 포맷"""
    recent = history[-3:]  # 최근 3턴
    formatted = []
    
    for msg in recent:
        role = "User" if isinstance(msg, HumanMessage) else "AI"
        formatted.append(f"{role}: {msg.content[:100]}...")
    
    return "\n".join(formatted) if formatted else "없음"

def format_todos(todos: List[TodoItem]) -> str:
    """TODO 리스트를 문자열로 포맷"""
    if not todos:
        return "없음"
    
    formatted = []
    for i, todo in enumerate(todos, 1):
        status_emoji = {
            "pending": "⏸️",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(todo["status"], "❓")
        
        formatted.append(
            f"{i}. [{status_emoji}] {todo['title']} ({todo['status']})"
        )
    
    return "\n".join(formatted)
```

---

## 5. 라우팅 로직

### 5.1 조건부 엣지

```python
# Main Graph 정의 시
graph.add_conditional_edges(
    "intent_analysis",
    route_by_intent_state,  # 함수
    {
        "new_task": "planning_agent",
        "modify_task": "planning_agent",
        "continue_task": "supervisor_agent",
        "simple_qa": "simple_qa_agent"
    }
)

def route_by_intent_state(state: MainState) -> str:
    """State에서 intent를 읽어 라우팅"""
    return state["current_intent"]
```

### 5.2 Command API 활용 (권장)

```python
def intent_analysis_agent(state: MainState) -> Command:
    # ... 의도 분석 ...
    
    # Command로 직접 라우팅 (조건부 엣지 불필요)
    return Command(
        update={
            "current_intent": intent,
            "intent_confidence": confidence
        },
        goto=route_by_intent(intent)
    )
```

---

## 6. 예외 처리

### 6.1 LLM 파싱 실패

```python
def analyze_intent_with_llm(query, history, todos, mode):
    try:
        response = llm.invoke(...)
        analysis = json.loads(response.content)
        
        # 필수 필드 검증
        assert "intent" in analysis
        assert "confidence" in analysis
        assert analysis["intent"] in ["new_task", "modify_task", "continue_task", "simple_qa"]
        
        return analysis
        
    except (json.JSONDecodeError, AssertionError, KeyError) as e:
        # 파싱 실패 시 기본값
        logger.warning(f"Intent parsing failed: {e}")
        return {
            "intent": "simple_qa",  # 안전한 기본값
            "confidence": 0.5,
            "reasoning": "파싱 실패로 기본값 사용"
        }
```

### 6.2 LLM 호출 실패

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def analyze_intent_with_llm(query, history, todos, mode):
    # LLM 호출
    # 실패 시 자동 재시도 (최대 3회)
    ...
```

### 6.3 타임아웃

```python
import asyncio

async def analyze_intent_with_timeout(query, history, todos, mode, timeout=5):
    """타임아웃 설정"""
    try:
        return await asyncio.wait_for(
            analyze_intent_with_llm_async(query, history, todos, mode),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning("Intent analysis timeout")
        return {
            "intent": "simple_qa",
            "confidence": 0.5,
            "reasoning": "타임아웃"
        }
```

---

## 7. 테스트 케이스

### 7.1 new_task 테스트

```python
test_cases_new_task = [
    {
        "query": "2025년 AI 트렌드 보고서 만들어줘",
        "expected_intent": "new_task",
        "min_confidence": 0.8
    },
    {
        "query": "Python으로 TODO 관리 앱 만들어줘",
        "expected_intent": "new_task",
        "min_confidence": 0.8
    },
    {
        "query": "경쟁사 분석 자료를 만들어줘",
        "expected_intent": "new_task",
        "min_confidence": 0.8
    }
]
```

### 7.2 modify_task 테스트

```python
test_cases_modify_task = [
    {
        "query": "거기에 한국 시장 분석도 추가해줘",
        "context": {"todos": [{"id": "todo_1", "title": "AI 보고서"}]},
        "expected_intent": "modify_task",
        "min_confidence": 0.8
    },
    {
        "query": "대신 GPT-4 정보로 바꿔줘",
        "context": {"todos": [{"id": "todo_1"}]},
        "expected_intent": "modify_task",
        "min_confidence": 0.7
    }
]
```

### 7.3 continue_task 테스트

```python
test_cases_continue_task = [
    {
        "query": "계속해줘",
        "context": {
            "todos": [
                {"id": "todo_1", "status": "in_progress"}
            ],
            "conversation_mode": "executing"
        },
        "expected_intent": "continue_task",
        "min_confidence": 0.9
    },
    {
        "query": "다음 단계 진행해줘",
        "context": {"todos": [{"status": "completed"}]},
        "expected_intent": "continue_task",
        "min_confidence": 0.8
    }
]
```

### 7.4 simple_qa 테스트

```python
test_cases_simple_qa = [
    {
        "query": "GPT-5는 언제 나와?",
        "expected_intent": "simple_qa",
        "min_confidence": 0.9
    },
    {
        "query": "LangGraph가 뭐야?",
        "expected_intent": "simple_qa",
        "min_confidence": 0.9
    },
    {
        "query": "현재 진행 상황 알려줘",
        "context": {"todos": []},
        "expected_intent": "simple_qa",
        "min_confidence": 0.7
    }
]
```

### 7.5 테스트 실행

```python
import pytest

@pytest.mark.parametrize("test_case", test_cases_new_task)
def test_intent_analysis_new_task(test_case):
    state = create_test_state(
        query=test_case["query"],
        context=test_case.get("context", {})
    )
    
    result = intent_analysis_agent(state)
    
    assert result.update["current_intent"] == test_case["expected_intent"]
    assert result.update["intent_confidence"] >= test_case["min_confidence"]
```

---

## 8. 성능 최적화

### 8.1 캐싱 (선택)

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def analyze_intent_cached(query_hash: str, context_hash: str):
    """
    동일한 쿼리 + 컨텍스트에 대해 캐싱
    (개발 환경에서 유용)
    """
    # 실제 분석 로직
    ...
```

### 8.2 경량 모델 사용

```python
# 빠른 분류를 위해 경량 모델 사용
llm_fast = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def analyze_intent_with_llm(query, history, todos, mode):
    # Intent 분류는 gpt-3.5-turbo로도 충분
    response = llm_fast.invoke(...)
    ...
```

---

## 9. 다음 단계

Intent Analysis 후 각 의도별 처리를 위해 다음 문서를 참고하세요:

1. **[04_PHASE2_PLANNING.md](./04_PHASE2_PLANNING.md)**: new_task, modify_task 처리
2. **[05_PHASE3_SUPERVISOR.md](./05_PHASE3_SUPERVISOR.md)**: continue_task 처리
3. **Simple Q&A Agent**: 별도 문서 (간단한 구현)

---

**이전 문서**: [02_STATE_SCHEMA.md](./02_STATE_SCHEMA.md)  
**다음 문서**: [04_PHASE2_PLANNING.md](./04_PHASE2_PLANNING.md)
