# Dynamic Agent Plugin System - 완전한 동적 확장성

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: Agent의 동적 추가/삭제/교체가 가능한 플러그인 시스템 설명

---

## 1. 핵심 답변

### ✅ **YES! 완전히 동적입니다**

```
현재 시스템은:
- ✅ Agent 런타임 추가 가능
- ✅ Agent 런타임 삭제 가능
- ✅ Agent 전체 교체 가능
- ✅ 특정 Agent에 종속되지 않음
- ✅ Zero-downtime 업데이트 가능
```

### 📌 Agent는 "플러그인"입니다
- **필수 Agent**: 0개 (TodoAgent만 권장)
- **선택 Agent**: 무제한
- **의존성**: Agent 이름이 아닌 역할 기반

---

## 2. Agent Plugin Architecture

### 2.1 현재 구조의 확장성

```python
backend/app/octostrator/agents/
├── base/                    # 핵심 시스템 (변경 없음)
│   ├── base_agent.py       # 인터페이스만 정의
│   ├── agent_registry.py   # 동적 관리
│   └── dependency_resolver.py
├── todo/                    # 유일한 시스템 Agent
│   └── todo_agent.py       # TODO 관리 (권장)
└── plugins/                 # 모든 Domain Agent는 플러그인
    ├── diet/               # 삭제 가능
    ├── workout/            # 교체 가능
    ├── schedule/           # 추가 가능
    └── custom/             # 사용자 정의 무제한
```

### 2.2 Agent Discovery System

```python
class AgentRegistry:
    """Agent를 동적으로 발견하고 관리"""

    def discover_agents(self, path: str = "agents/plugins"):
        """지정 경로에서 Agent 자동 발견"""

        discovered_agents = []

        # 디렉토리 스캔
        for module_path in Path(path).rglob("*.py"):
            try:
                # 동적 import
                module = importlib.import_module(module_path)

                # BaseAgent 서브클래스 찾기
                for name, obj in inspect.getmembers(module):
                    if issubclass(obj, BaseAgent) and obj != BaseAgent:
                        # 자동 등록
                        self.register(obj)
                        discovered_agents.append(obj.agent_id)

            except Exception as e:
                logger.warning(f"Agent load failed: {module_path} - {e}")
                # 실패해도 시스템은 계속 동작

        return discovered_agents

    def hot_reload(self):
        """실행 중 Agent 재로드"""

        # 기존 Agent 백업
        backup = self._agents.copy()

        try:
            # 모든 Agent 재발견
            self.clear()
            self.discover_agents()

            logger.info(f"Hot reload complete: {len(self._agents)} agents")

        except Exception as e:
            # 실패 시 롤백
            self._agents = backup
            logger.error(f"Hot reload failed, rolled back: {e}")
```

---

## 3. Agent 추가/삭제 시나리오

### 3.1 새 Agent 추가 (런타임)

```python
# 1. 새 Agent 파일 생성
# agents/plugins/nutrition/nutrition_agent.py

@register_agent("nutrition_agent")
class NutritionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="nutrition_agent",
            agent_name="Nutrition Analysis Agent",
            capabilities=["analyze_food", "calculate_nutrients"]
        )

# 2. 런타임에 추가 (서버 재시작 없음)
async def add_agent_at_runtime():
    # Agent Registry에 추가
    agent_registry.discover_agents("agents/plugins/nutrition")

    # 즉시 사용 가능
    nutrition_agent = agent_registry.get_agent("nutrition_agent")
    result = await nutrition_agent.execute(task)
```

### 3.2 기존 Agent 삭제

```python
async def remove_agent(agent_id: str):
    """Agent를 시스템에서 제거"""

    # 1. 실행 중인 작업 확인
    if agent_registry.is_agent_busy(agent_id):
        # 현재 작업 완료 대기
        await agent_registry.wait_for_completion(agent_id)

    # 2. Registry에서 제거
    agent_registry.unregister(agent_id)

    # 3. 의존성 정리
    dependency_resolver.remove_agent_dependencies(agent_id)

    # 4. 파일 제거 (옵션)
    if delete_files:
        shutil.rmtree(f"agents/plugins/{agent_id}")

    logger.info(f"Agent removed: {agent_id}")
```

### 3.3 Agent 전체 교체

```python
async def replace_all_agents(new_agents_path: str):
    """모든 Agent를 새로운 세트로 교체"""

    # 1. 현재 Agent들 백업
    backup_path = "agents/backup"
    shutil.copytree("agents/plugins", backup_path)

    # 2. 모든 Agent 언등록
    for agent_id in agent_registry.list_agents():
        if agent_id != "todo_agent":  # TodoAgent는 유지
            agent_registry.unregister(agent_id)

    # 3. 새 Agent들 복사
    shutil.copytree(new_agents_path, "agents/plugins")

    # 4. 새 Agent들 발견 및 등록
    agent_registry.discover_agents("agents/plugins")

    # 5. 검증
    if not validate_new_agents():
        # 롤백
        shutil.rmtree("agents/plugins")
        shutil.copytree(backup_path, "agents/plugins")
        agent_registry.discover_agents("agents/plugins")
        raise Exception("Agent replacement failed, rolled back")

    logger.info(f"All agents replaced successfully")
```

---

## 4. Agent 독립성 보장

### 4.1 역할 기반 의존성 (이름 기반 X)

```python
# ❌ BAD: 특정 Agent 이름에 의존
dependencies = ["diet_agent", "workout_agent"]

# ✅ GOOD: 역할/능력에 의존
required_capabilities = ["meal_planning", "exercise_planning"]

# 실행 시 역할에 맞는 Agent 찾기
async def find_agent_by_capability(capability: str):
    """필요한 능력을 가진 Agent 찾기"""

    for agent_id in agent_registry.list_agents():
        agent = agent_registry.get_agent(agent_id)

        if capability in agent.capabilities:
            return agent

    # 없으면 대체 Agent 또는 에러
    return fallback_agent or None
```

### 4.2 Agent Interface Contract

```python
class IAgent(Protocol):
    """모든 Agent가 구현해야 하는 인터페이스"""

    @abstractmethod
    async def execute(self, task: Dict, context: Dict) -> Dict:
        """표준 실행 인터페이스"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """Agent가 제공하는 능력 목록"""
        pass

    @abstractmethod
    def validate_task(self, task: Dict) -> bool:
        """작업 실행 가능 여부 확인"""
        pass

# 모든 Agent는 이 인터페이스만 만족하면 됨
class CustomAgent(BaseAgent):
    def capabilities(self):
        return ["custom_task_1", "custom_task_2"]

    async def execute(self, task, context):
        # 구현은 자유
        return {"result": "success"}
```

---

## 5. TodoAgent의 Agent 무관 처리

### 5.1 능력 기반 TODO 생성

```python
class TodoAgent(BaseAgent):
    """Agent 이름이 아닌 능력 기반으로 TODO 생성"""

    async def generate_todos_from_plan(self, plan: Dict) -> List[TodoItem]:
        todos = []

        for step in plan["steps"]:
            # 필요한 능력 확인
            required_capability = step["capability"]

            # 해당 능력을 가진 Agent 찾기
            capable_agents = self.find_agents_with_capability(required_capability)

            if not capable_agents:
                # 대체 처리
                if self.can_decompose(required_capability):
                    # 작업 분해
                    sub_tasks = self.decompose_task(step)
                    todos.extend(sub_tasks)
                else:
                    # 사용자에게 알림
                    todos.append(self.create_manual_todo(step))
            else:
                # 가장 적합한 Agent 선택
                best_agent = self.select_best_agent(capable_agents, step)

                todos.append(TodoItem(
                    id=generate_id(),
                    agent=best_agent.agent_id,
                    capability=required_capability,
                    task=step["task"],
                    fallback_agents=[a.agent_id for a in capable_agents[1:]]
                ))

        return todos
```

### 5.2 Agent 실패 시 대체

```python
async def execute_todo_with_fallback(todo: TodoItem, context: Dict):
    """Agent 실패 시 대체 Agent로 자동 전환"""

    # Primary Agent 시도
    primary_agent = agent_registry.get_agent(todo["agent"])

    if primary_agent:
        try:
            return await primary_agent.execute(todo["task"], context)
        except Exception as e:
            logger.warning(f"Primary agent failed: {e}")

    # Fallback Agents 시도
    for fallback_id in todo.get("fallback_agents", []):
        fallback_agent = agent_registry.get_agent(fallback_id)

        if fallback_agent:
            try:
                logger.info(f"Trying fallback: {fallback_id}")
                return await fallback_agent.execute(todo["task"], context)
            except:
                continue

    # 모든 Agent 실패 시 수동 처리
    return await request_manual_intervention(todo)
```

---

## 6. 실제 사용 예시

### 6.1 완전히 다른 도메인으로 전환

```python
# 현재: PT Manager (다이어트/운동)
current_agents = ["diet_agent", "workout_agent", "schedule_agent"]

# 전환: 교육 시스템
await replace_all_agents("education_agents/")
new_agents = ["math_agent", "science_agent", "homework_agent"]

# 시스템은 그대로, Agent만 교체됨
# Supervisor, TodoAgent는 변경 없이 동작
```

### 6.2 점진적 마이그레이션

```python
# v1 Agent를 v2로 점진적 교체

# Step 1: v2 Agent 추가 (공존)
agent_registry.register(DietAgentV2, "diet_agent_v2")

# Step 2: 트래픽 점진적 이동
todo_agent.set_routing_rule({
    "diet_tasks": {
        "diet_agent": 0.3,     # 30%
        "diet_agent_v2": 0.7   # 70%
    }
})

# Step 3: 검증 후 완전 전환
agent_registry.unregister("diet_agent")
agent_registry.update_alias("diet_agent_v2", "diet_agent")
```

### 6.3 A/B 테스트

```python
# 두 가지 버전의 Agent 동시 운영

async def ab_test_agents(task: Dict, user_id: str):
    # 사용자별 Agent 선택
    if hash(user_id) % 2 == 0:
        agent = agent_registry.get_agent("workout_agent_a")
    else:
        agent = agent_registry.get_agent("workout_agent_b")

    result = await agent.execute(task)

    # 성능 측정
    metrics.record(agent.agent_id, result)

    return result
```

---

## 7. Agent Marketplace 개념

### 7.1 Agent 배포 패키지

```python
# agent_package.yaml
name: "advanced_nutrition_agent"
version: "2.0.0"
author: "third_party_developer"
capabilities:
  - "nutrition_analysis"
  - "meal_optimization"
  - "allergy_detection"
dependencies:
  - "numpy>=1.20"
  - "pandas>=1.3"
files:
  - "nutrition_agent.py"
  - "models/nutrition_model.pkl"
  - "data/food_database.json"
```

### 7.2 Agent 설치

```bash
# Agent 설치 명령
python manage.py install-agent https://agent-store.com/nutrition_agent

# 자동으로:
# 1. 다운로드
# 2. 의존성 설치
# 3. 검증
# 4. Registry 등록
# 5. 즉시 사용 가능
```

---

## 8. 보안 및 검증

### 8.1 Agent Sandbox

```python
class AgentSandbox:
    """Agent를 격리된 환경에서 실행"""

    async def execute_sandboxed(self, agent: BaseAgent, task: Dict):
        # 리소스 제한
        with ResourceLimit(cpu=1, memory="512MB", timeout=30):
            # 권한 제한
            with PermissionContext(allow=["read"], deny=["write", "network"]):
                result = await agent.execute(task)

        # 결과 검증
        if self.validate_output(result):
            return result
        else:
            raise SecurityException("Invalid agent output")
```

### 8.2 Agent 인증

```python
class AgentCertification:
    """Agent 인증 시스템"""

    def verify_agent(self, agent_path: str) -> bool:
        # 1. 서명 확인
        if not self.verify_signature(agent_path):
            return False

        # 2. 코드 스캔
        if self.detect_malicious_patterns(agent_path):
            return False

        # 3. 테스트 실행
        if not self.run_safety_tests(agent_path):
            return False

        return True
```

---

## 9. 결론

### ✅ 완전한 플러그인 시스템

```
현재 시스템 특징:
- Agent는 언제든 추가/삭제/교체 가능
- 특정 Agent에 종속되지 않음
- 역할 기반 동작 (이름 기반 X)
- Hot reload 지원
- Zero-downtime 업데이트
- Agent Marketplace 가능
- 완전히 다른 도메인으로 전환 가능
```

### 📌 유일한 권장사항

```
TodoAgent만 유지 권장 (필수 아님)
- 이유: TODO 관리와 HITL 처리
- 대체 가능: 다른 TODO 관리 시스템 사용 가능
```

### 🚀 미래 확장성

```
- 100+ Agent 지원
- Multi-domain 지원
- Agent 자동 업데이트
- Community Agent 지원
- Agent as a Service (AaaS)
```

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/DYNAMIC_AGENT_PLUGIN_SYSTEM_251105.md`