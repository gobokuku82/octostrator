# 04. Phase 2: Planning Agent

**문서 버전**: 1.0.0  
**작성일**: 2025-11-17  
**관련 문서**: [03_PHASE1_INTENT_ANALYSIS.md](./03_PHASE1_INTENT_ANALYSIS.md)

---

## 📋 목차

1. [Planning Agent 개요](#1-planning-agent-개요)
2. [TODO 생성 전략](#2-todo-생성-전략)
3. [interrupt() 구현](#3-interrupt-구현)
4. [TODO 수정 모드](#4-todo-수정-모드)
5. [LLM 프롬프트 설계](#5-llm-프롬프트-설계)
6. [사용자 응답 처리](#6-사용자-응답-처리)
7. [의존성 관리](#7-의존성-관리)

---

## 1. Planning Agent 개요

### 1.1 역할

**Planning Agent**는 사용자 쿼리를 분석하여 실행 가능한 TODO 리스트를 생성하고, 사용자 승인을 받는 노드입니다.

```
Intent Analysis (new_task or modify_task)
    ↓
Planning Agent
    ├─ TODO 생성 (LLM)
    ├─ interrupt() 📍 (사용자 승인)
    └─ 승인 시 → Supervisor Agent
```

### 1.2 입력/출력

| 항목 | 설명 |
|------|------|
| **입력** | `current_intent`, `messages` |
| **처리** | LLM으로 TODO 생성 또는 수정 |
| **interrupt** | 사용자 승인 요청 (필수) |
| **출력** | `todos` (승인된 TODO 리스트) |
| **라우팅** | `supervisor_agent` 또는 자기 자신 (재생성) |

### 1.3 모드

| 모드 | 트리거 | 동작 |
|------|--------|------|
| **새 TODO 생성** | `current_intent == "new_task"` | 빈 상태에서 TODO 생성 |
| **TODO 수정** | `current_intent == "modify_task"` | 기존 TODO 참조하여 수정 |

---

## 2. TODO 생성 전략

### 2.1 TODO 생성 원칙

| 원칙 | 설명 | 예시 |
|------|------|------|
| **분해성** | 큰 작업을 3-7개의 하위 작업으로 분해 | "보고서 작성" → 데이터 수집, 분석, 작성 |
| **독립성** | 각 TODO는 독립적으로 실행 가능 | 병렬 처리 가능하도록 |
| **명확성** | 제목과 설명이 명확 | "데이터 수집" (❌) → "웹 검색으로 AI 트렌드 데이터 수집" (✅) |
| **의존성** | 순서가 있는 TODO는 dependencies 설정 | TODO 2는 TODO 1 완료 후 |

### 2.2 TODO 개수 기준

```python
COMPLEXITY_RULES = {
    "simple": 1-2,      # 단순 작업 (사실 simple은 simple_qa로 가야 함)
    "moderate": 3-5,    # 일반적인 작업
    "complex": 5-7,     # 복잡한 작업
    "very_complex": 7+  # 매우 복잡 (사용자에게 범위 축소 권장)
}
```

### 2.3 Worker 자동 할당

| Worker | 작업 유형 | 키워드 |
|--------|----------|--------|
| **research** | 정보 수집, 웹 검색, 문서 검색 | "조사", "찾기", "검색", "수집" |
| **analysis** | 데이터 분석, 인사이트 도출 | "분석", "비교", "평가" |
| **coding** | 코드 작성, 알고리즘 구현 | "코드", "구현", "개발" |
| **writing** | 문서 작성, 보고서 생성 | "작성", "문서", "보고서" |

---

## 3. interrupt() 구현

### 3.1 기본 구조

```python
from langgraph.types import interrupt, Command

def planning_agent(state: MainState) -> Command:
    """
    Planning Agent
    TODO 생성 및 사용자 승인
    """
    
    # 1. 모드 확인
    if state["current_intent"] == "new_task":
        # 새 TODO 생성
        proposed_todos = generate_new_todos(state)
    else:  # modify_task
        # 기존 TODO 수정
        proposed_todos = modify_existing_todos(state)
    
    # 2. interrupt() 발생 - 사용자 승인 요청
    user_response = interrupt({
        "type": "plan_approval",
        "message": "다음 계획으로 진행할까요?",
        "data": {
            "proposed_todos": proposed_todos,
            "mode": state["current_intent"]
        }
    })
    
    # 3. 사용자 응답 처리
    if user_response["action"] == "approve":
        # 승인 - Supervisor로 이동
        return Command(
            update={
                "todos": proposed_todos,
                "conversation_mode": "executing"
            },
            goto="supervisor_agent"
        )
    
    elif user_response["action"] == "modify":
        # 수정 요청 - TODO 재생성
        modifications = user_response.get("changes", [])
        modified_todos = apply_user_modifications(proposed_todos, modifications)
        
        # 재귀적으로 다시 승인 요청
        return Command(
            update={"todos": modified_todos},
            goto="planning_agent"
        )
    
    else:  # cancel
        # 취소 - 종료
        return Command(
            update={
                "conversation_mode": "completed",
                "todos": []
            },
            goto=END
        )
```

### 3.2 interrupt() 함수 상세

**interrupt()의 동작**:
1. 그래프 실행을 즉시 중단
2. 중단 지점을 Checkpointer에 저장
3. Frontend에 `__interrupt__` 이벤트 전송
4. 사용자 입력 대기
5. 재개 시 `Command(resume=value)` 받아서 계속

**interrupt() 반환값**:
```python
# Frontend에서 /api/resume 호출 시 전달되는 값
user_response = interrupt(...)

# user_response 예시
{
    "action": "approve",  # or "modify", "cancel"
    "changes": [...]  # modify인 경우
}
```

---

## 4. TODO 수정 모드

### 4.1 수정 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| **추가** | 새 TODO 추가 | "한국 시장 분석도 추가해줘" |
| **수정** | 기존 TODO 변경 | "데이터 수집 범위를 2025년으로 제한해줘" |
| **삭제** | TODO 제거 | "보고서 작성은 빼줘" |
| **순서 변경** | 의존성 재조정 | "분석을 먼저 하고 데이터 수집해줘" |

### 4.2 수정 로직

```python
def modify_existing_todos(state: MainState) -> List[TodoItem]:
    """
    기존 TODO를 참조하여 수정
    """
    existing_todos = state["todos"]
    modification_request = state["messages"][-1].content
    
    # LLM으로 수정 계획 생성
    prompt = f"""
    기존 TODO:
    {format_todos_for_prompt(existing_todos)}
    
    수정 요청:
    {modification_request}
    
    다음 작업을 수행하세요:
    1. 어떤 TODO를 추가/수정/삭제할지 결정
    2. 의존성 재조정 (순서 변경 시)
    3. 새로운 TODO 리스트 생성
    
    JSON 형식으로 응답하세요:
    {{
        "action": "add" | "modify" | "delete" | "reorder",
        "affected_todos": [...],
        "new_todos": [...],
        "summary": "변경 사항 요약"
    }}
    """
    
    modification_plan = llm.invoke(prompt)
    
    # 수정 적용
    new_todos = apply_modifications(existing_todos, modification_plan)
    
    return new_todos

def apply_modifications(
    existing: List[TodoItem],
    plan: dict
) -> List[TodoItem]:
    """수정 계획을 실제 TODO 리스트에 적용"""
    
    if plan["action"] == "add":
        # 새 TODO 추가
        return existing + plan["new_todos"]
    
    elif plan["action"] == "modify":
        # 기존 TODO 수정
        todo_dict = {t["id"]: t for t in existing}
        for update in plan["affected_todos"]:
            todo_dict[update["id"]].update(update)
        return list(todo_dict.values())
    
    elif plan["action"] == "delete":
        # TODO 삭제
        delete_ids = {t["id"] for t in plan["affected_todos"]}
        return [t for t in existing if t["id"] not in delete_ids]
    
    elif plan["action"] == "reorder":
        # 의존성 재조정
        return plan["new_todos"]
```

---

## 5. LLM 프롬프트 설계

### 5.1 새 TODO 생성 프롬프트

```python
NEW_TODO_GENERATION_PROMPT = """
당신은 작업 계획 전문가입니다.

사용자 요청을 분석하여 실행 가능한 TODO 리스트를 생성하세요.

**사용자 요청**:
{query}

**대화 히스토리**:
{history}

**TODO 생성 원칙**:
1. 큰 작업을 3-7개의 하위 작업으로 분해
2. 각 TODO는 독립적으로 실행 가능하게
3. 제목과 설명을 명확하게 작성
4. 순서가 있는 경우 dependencies 설정
5. 적절한 Worker 할당 (research, analysis, coding, writing)

**Worker 선택 가이드**:
- research: 정보 수집, 웹 검색, 문서 검색
- analysis: 데이터 분석, 비교, 평가
- coding: 코드 작성, 알고리즘 구현
- writing: 문서 작성, 보고서 생성

**출력 형식** (JSON):
{{
    "todos": [
        {{
            "id": "todo_1",
            "title": "명확한 제목 (20자 이내)",
            "description": "구체적인 설명 (100자 이내)",
            "assigned_worker": "research" | "analysis" | "coding" | "writing",
            "dependencies": [],
            "estimated_duration": "5분" | "10분" | "30분" 등
        }},
        ...
    ],
    "complexity": "moderate",
    "total_estimated_time": "약 1시간"
}}

JSON으로 응답하세요.
"""
```

### 5.2 TODO 수정 프롬프트

```python
TODO_MODIFICATION_PROMPT = """
당신은 작업 계획 수정 전문가입니다.

기존 TODO 리스트를 사용자 요청에 따라 수정하세요.

**기존 TODO 리스트**:
{existing_todos}

**수정 요청**:
{modification_request}

**수정 유형 결정**:
1. **추가**: 새로운 TODO 추가
2. **수정**: 기존 TODO의 내용 변경
3. **삭제**: TODO 제거
4. **순서 변경**: 의존성 재조정

**주의사항**:
- 의존성 체크: 삭제 시 다른 TODO에 영향 없는지 확인
- ID 유지: 수정 시 기존 TODO의 id는 유지
- 순서 재조정 시 dependencies 업데이트

**출력 형식** (JSON):
{{
    "action": "add" | "modify" | "delete" | "reorder",
    "affected_todos": [
        // 영향받는 TODO 리스트
    ],
    "new_todos": [
        // 전체 TODO 리스트 (수정 후)
    ],
    "summary": "변경 사항을 한 문장으로 요약"
}}

JSON으로 응답하세요.
"""
```

---

## 6. 사용자 응답 처리

### 6.1 승인 (approve)

```python
if user_response["action"] == "approve":
    # UUID 생성 및 메타데이터 추가
    final_todos = []
    for todo in proposed_todos:
        final_todos.append({
            **todo,
            "id": str(uuid.uuid4()),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        })
    
    return Command(
        update={
            "todos": final_todos,
            "conversation_mode": "executing"
        },
        goto="supervisor_agent"
    )
```

### 6.2 수정 (modify)

**Frontend에서 전달되는 수정 데이터**:
```python
user_response = {
    "action": "modify",
    "changes": [
        {
            "type": "add",
            "data": {
                "title": "한국 시장 분석",
                "description": "...",
                "assigned_worker": "analysis"
            }
        },
        {
            "type": "modify",
            "todo_id": "todo_2",
            "field": "description",
            "value": "새로운 설명"
        },
        {
            "type": "delete",
            "todo_id": "todo_3"
        }
    ]
}
```

**수정 적용**:
```python
def apply_user_modifications(
    todos: List[TodoItem],
    changes: List[dict]
) -> List[TodoItem]:
    """사용자 수정 사항 적용"""
    
    result = todos.copy()
    
    for change in changes:
        if change["type"] == "add":
            # 새 TODO 추가
            new_todo = {
                "id": f"todo_{len(result) + 1}",
                **change["data"],
                "status": "pending",
                "dependencies": [],
                "created_at": datetime.now().isoformat()
            }
            result.append(new_todo)
        
        elif change["type"] == "modify":
            # 기존 TODO 수정
            for todo in result:
                if todo["id"] == change["todo_id"]:
                    todo[change["field"]] = change["value"]
                    break
        
        elif change["type"] == "delete":
            # TODO 삭제
            result = [t for t in result if t["id"] != change["todo_id"]]
    
    return result
```

### 6.3 취소 (cancel)

```python
if user_response["action"] == "cancel":
    return Command(
        update={
            "conversation_mode": "completed",
            "todos": [],
            "messages": [AIMessage(content="작업이 취소되었습니다.")]
        },
        goto=END
    )
```

---

## 7. 의존성 관리

### 7.1 의존성 자동 탐지

```python
def detect_dependencies(todos: List[TodoItem]) -> List[TodoItem]:
    """
    TODO 간 의존성을 자동으로 탐지
    """
    for i, todo in enumerate(todos):
        # 이전 TODO들이 필요한 경우
        if requires_previous_results(todo, todos[:i]):
            todo["dependencies"] = [t["id"] for t in todos[:i]]
        else:
            todo["dependencies"] = []
    
    return todos

def requires_previous_results(
    current_todo: TodoItem,
    previous_todos: List[TodoItem]
) -> bool:
    """
    현재 TODO가 이전 TODO의 결과를 필요로 하는지 판단
    """
    # 휴리스틱 기반 판단
    keywords = ["분석", "종합", "정리", "보고서"]
    
    if any(kw in current_todo["title"] for kw in keywords):
        # 데이터 수집 TODO가 있으면 의존
        if any("수집" in t["title"] or "검색" in t["title"] for t in previous_todos):
            return True
    
    return False
```

### 7.2 순환 의존성 체크

```python
def check_circular_dependencies(todos: List[TodoItem]) -> bool:
    """
    순환 의존성 체크 (DFS)
    """
    def has_cycle(node: str, visited: set, rec_stack: set) -> bool:
        visited.add(node)
        rec_stack.add(node)
        
        # 의존하는 TODO들 확인
        todo = next(t for t in todos if t["id"] == node)
        for dep in todo.get("dependencies", []):
            if dep not in visited:
                if has_cycle(dep, visited, rec_stack):
                    return True
            elif dep in rec_stack:
                return True
        
        rec_stack.remove(node)
        return False
    
    visited = set()
    for todo in todos:
        if todo["id"] not in visited:
            if has_cycle(todo["id"], visited, set()):
                return True
    
    return False
```

### 7.3 의존성 시각화 (Frontend용)

```python
def generate_dependency_graph(todos: List[TodoItem]) -> dict:
    """
    Frontend에서 표시할 의존성 그래프 생성
    """
    nodes = []
    edges = []
    
    for todo in todos:
        nodes.append({
            "id": todo["id"],
            "label": todo["title"],
            "status": todo["status"]
        })
        
        for dep in todo.get("dependencies", []):
            edges.append({
                "from": dep,
                "to": todo["id"]
            })
    
    return {"nodes": nodes, "edges": edges}
```

---

## 8. 예외 처리

### 8.1 TODO 생성 실패

```python
def generate_new_todos(state: MainState) -> List[TodoItem]:
    try:
        response = llm.invoke(NEW_TODO_GENERATION_PROMPT.format(...))
        todos = json.loads(response.content)["todos"]
        
        # 검증
        assert len(todos) >= 1
        assert all("title" in t and "assigned_worker" in t for t in todos)
        
        return todos
        
    except Exception as e:
        logger.error(f"TODO generation failed: {e}")
        
        # 폴백: 단순 TODO 1개 생성
        return [{
            "id": "fallback_todo",
            "title": "작업 수행",
            "description": state["messages"][-1].content,
            "assigned_worker": "research",
            "dependencies": []
        }]
```

### 8.2 interrupt() 타임아웃

```python
# Checkpointer에 저장되므로 타임아웃 걱정 없음
# 사용자가 1시간 후에 응답해도 OK

# 단, 세션 만료 정책은 별도 구현
def check_session_expiry(state: MainState) -> bool:
    """세션 만료 체크 (예: 24시간)"""
    created_at = datetime.fromisoformat(state["created_at"])
    now = datetime.now()
    
    if (now - created_at).total_seconds() > 86400:  # 24시간
        return True
    
    return False
```

---

## 9. 테스트 케이스

### 9.1 새 TODO 생성 테스트

```python
def test_planning_agent_new_task():
    state = {
        "current_intent": "new_task",
        "messages": [HumanMessage(content="AI 트렌드 보고서 만들어줘")],
        "todos": [],
        "conversation_mode": "planning"
    }
    
    # Mock interrupt() 응답
    with mock_interrupt({"action": "approve"}):
        result = planning_agent(state)
    
    # 검증
    assert len(result.update["todos"]) >= 3
    assert result.update["conversation_mode"] == "executing"
    assert result.goto == "supervisor_agent"
```

### 9.2 TODO 수정 테스트

```python
def test_planning_agent_modify_task():
    state = {
        "current_intent": "modify_task",
        "messages": [
            HumanMessage(content="AI 보고서 만들어줘"),
            AIMessage(content="TODO 3개 생성됨"),
            HumanMessage(content="한국 시장 분석도 추가해줘")
        ],
        "todos": [
            {"id": "todo_1", "title": "데이터 수집"},
            {"id": "todo_2", "title": "데이터 분석"},
            {"id": "todo_3", "title": "보고서 작성"}
        ]
    }
    
    with mock_interrupt({"action": "approve"}):
        result = planning_agent(state)
    
    # 새 TODO가 추가되었는지 확인
    assert len(result.update["todos"]) == 4
    assert any("한국" in t["title"] for t in result.update["todos"])
```

### 9.3 사용자 수정 응답 테스트

```python
def test_planning_agent_user_modification():
    state = {
        "current_intent": "new_task",
        "messages": [HumanMessage(content="보고서 만들어줘")],
        "todos": []
    }
    
    # 사용자가 "수정" 선택
    with mock_interrupt({
        "action": "modify",
        "changes": [
            {"type": "delete", "todo_id": "todo_3"}
        ]
    }):
        result = planning_agent(state)
    
    # 재귀적으로 다시 planning_agent 호출
    assert result.goto == "planning_agent"
```

---

## 10. 다음 단계

Planning Agent 이후 실행 단계는 다음 문서를 참고하세요:

1. **[05_PHASE3_SUPERVISOR.md](./05_PHASE3_SUPERVISOR.md)**: TODO 실행 관리
2. **[07_INTERRUPT_SCENARIOS.md](./07_INTERRUPT_SCENARIOS.md)**: 전체 Interrupt 시나리오

---

**이전 문서**: [03_PHASE1_INTENT_ANALYSIS.md](./03_PHASE1_INTENT_ANALYSIS.md)  
**다음 문서**: [05_PHASE3_SUPERVISOR.md](./05_PHASE3_SUPERVISOR.md)
