# Quick Start Guide

**작성일**: 2025-11-05
**버전**: 2.0
**목적**: 3-Layer 아키텍처 빠른 시작 가이드

---

## 🚀 5분 안에 시작하기

### 1. 기본 사용법

```python
# main.py
import asyncio
from backend.app.octostrator.main_orchestrator import create_orchestrator

async def main():
    # Orchestrator 생성
    orchestrator = await create_orchestrator()

    # 요청 처리
    result = await orchestrator.process_request(
        user_message="다이어트 계획 만들어줘",
        session_id="session_123"
    )

    print(result)

asyncio.run(main())
```

### 2. 새로운 Agent 만들기 (10분)

```python
# my_agent.py
from backend.app.octostrator.agents.base.base_agent import BaseAgent
from backend.app.octostrator.agents.base.agent_registry import register_agent
from langgraph.graph import StateGraph, START, END

@register_agent("my_agent")
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="my_agent",
            agent_name="My Custom Agent"
        )

    def build_graph(self, llm=None):
        workflow = StateGraph(BaseAgentState)
        workflow.add_node("process", self.process_node)
        workflow.add_edge(START, "process")
        workflow.add_edge("process", END)
        return workflow

    async def process_node(self, state):
        return {"result": {"message": "Hello from MyAgent!"}}

    async def process_task(self, task, context):
        pass
```

---

## 📊 시스템 아키텍처 한눈에 보기

```
User Request
     ↓
[Main Orchestrator] ← 전체 조율
     ↓
[Layer 1: Cognitive Supervisor] ← 계획 수립
     ↓
[Layer 2: TodoAgent] ← TODO 관리 + HITL
     ↓
[Layer 3: Execute Supervisor] ← 실행 관리
     ↓
[Domain Agents] ← 실제 작업
     ↓
Final Response
```

---

## 🔧 핵심 컴포넌트

### Main Orchestrator
- **역할**: 전체 시스템 조율
- **파일**: `main_orchestrator.py`
- **사용법**: `await orchestrator.process_request(message, session_id)`

### Cognitive Supervisor
- **역할**: 사용자 의도 분석 및 계획 수립
- **파일**: `supervisor/cognitive_supervisor.py`
- **출력**: 실행 계획 (Plan)

### TodoAgent
- **역할**: Plan → TODO 변환, HITL 처리
- **파일**: `agents/todo/todo_agent.py`
- **특징**: Human-in-the-Loop 지원

### Execute Supervisor
- **역할**: Agent 실행 관리, 병렬 처리
- **파일**: `supervisor/execute_supervisor.py`
- **특징**: 의존성 기반 자동 병렬화

### Domain Agents
- **역할**: 실제 도메인 작업 수행
- **예시**: DietAgent, WorkoutAgent, ScheduleAgent
- **패턴**: BaseAgent 상속

---

## 💻 주요 API

### 요청 처리

```python
result = await orchestrator.process_request(
    user_message="요청 내용",
    session_id="session_123",
    user_id="user_456",
    context={"key": "value"}
)
```

### Human Feedback 처리

```python
feedback_result = await orchestrator.handle_human_feedback(
    session_id="session_123",
    feedback={
        "action": "modified",
        "modifications": [...]
    }
)
```

### Agent 등록

```python
# 자동 등록 (데코레이터)
@register_agent("my_agent")
class MyAgent(BaseAgent):
    pass

# 수동 등록
agent_registry.register(MyAgent, "my_agent")

# 자동 발견
agent_registry.discover_agents("path/to/agents")
```

---

## 🛠️ 환경 설정

### 1. 필수 패키지

```bash
pip install langgraph==1.0.0
pip install langchain-openai
pip install asyncpg  # PostgreSQL checkpoint
pip install pydantic
```

### 2. 환경 변수

```bash
# .env
OPENAI_API_KEY=sk-...
POSTGRES_URL=postgresql://user:pass@localhost/db
AUTO_APPROVE_TODOS=false
LLM_MODEL=gpt-4o-mini
```

### 3. 디렉토리 구조

```
backend/app/octostrator/
├── main_orchestrator.py      # 메인
├── supervisor/
│   ├── cognitive_supervisor.py
│   └── execute_supervisor.py
├── agents/
│   ├── base/                 # 기본 클래스
│   │   ├── base_agent.py
│   │   └── agent_registry.py
│   ├── todo/                 # TodoAgent
│   └── {domain}/              # 도메인 Agent
└── manual/                    # 문서
```

---

## 📝 Agent 개발 체크리스트

- [ ] BaseAgent 상속
- [ ] `build_graph()` 구현
- [ ] `process_task()` 구현
- [ ] State 정의
- [ ] Capabilities 설정
- [ ] 노드 구현
- [ ] 테스트 작성
- [ ] `@register_agent()` 데코레이터 추가

---

## 🔍 디버깅 팁

### 로깅 활성화

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### State 추적

```python
logger.debug(f"State: {state.dict()}")
```

### Graph 시각화

```python
from langgraph.graph import visualize
image = visualize(workflow)
```

---

## 🐛 일반적인 문제 해결

### Import 에러
```python
# 해결: 절대 경로 사용
from backend.app.octostrator.agents.base import BaseAgent
```

### Agent를 찾을 수 없음
```python
# 해결: Registry 확인
agent_registry.discover_agents()
print(agent_registry.list_agents())
```

### Checkpoint 에러
```python
# 해결: DB 연결 확인
checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
await checkpointer.setup()
```

---

## 📚 추가 문서

1. **[시스템 아키텍처 메뉴얼](./SYSTEM_ARCHITECTURE_MANUAL_251105.md)**
   - 전체 시스템 상세 설명

2. **[Agent 개발 가이드](./AGENT_DEVELOPMENT_GUIDE_251105.md)**
   - Agent 개발 상세 가이드

3. **[API Reference](./API_REFERENCE_251105.md)**
   - 전체 API 문서

4. **[Migration Guide](./MIGRATION_GUIDE_251105.md)**
   - 기존 시스템 마이그레이션

---

## 💡 Best Practices

### 1. Agent는 단일 책임
```python
# Good: 하나의 도메인
class DietAgent(BaseAgent):  # 식단만

# Bad: 여러 도메인
class AllInOneAgent(BaseAgent):  # 식단+운동+일정
```

### 2. Stateless 우선
```python
# Good: Stateless
enable_checkpoint=False  # 빠르고 단순

# Stateful은 필요할 때만
enable_checkpoint=True  # 복잡한 워크플로우
```

### 3. 에러 처리
```python
async def node(self, state):
    try:
        # 로직
        return {"result": data}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}
```

### 4. 명확한 Capability
```python
self.capabilities = [
    Capability.MEAL_PLANNING.value,  # 명확
    # "do_everything"  # 모호함 X
]
```

---

## 🎯 다음 단계

1. **간단한 Agent 만들기**
   - MyAgent 예제로 시작
   - 점진적으로 복잡도 증가

2. **기존 Agent 분석**
   - DietAgentV2 코드 리뷰
   - 패턴 이해

3. **테스트 작성**
   - 단위 테스트
   - 통합 테스트

4. **프로덕션 준비**
   - 성능 최적화
   - 모니터링 설정
   - 에러 처리 강화

---

## 🆘 도움말

### 질문이 있으신가요?

1. **문서 확인**: `/manual/` 디렉토리의 상세 문서
2. **코드 예제**: `/agents/diet/diet_agent_v2.py` 참고
3. **테스트 코드**: 각 컴포넌트의 테스트 파일

### 버그 발견?

1. 로그 확인
2. State 추적
3. 재현 가능한 최소 코드 작성

---

**Happy Coding! 🚀**

**작성일**: 2025-11-05
**버전**: 2.0