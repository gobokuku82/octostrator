# Agent Plugin System - 실제 구현 예시

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: Agent 플러그인 시스템의 구체적인 구현 예시

---

## 1. Agent 자동 발견 구현

### 1.1 디렉토리 구조

```
backend/app/octostrator/agents/
├── __init__.py
├── base/                       # 핵심 시스템 (수정 금지)
│   └── base_agent.py
├── system/                     # 시스템 Agent
│   └── todo_agent.py          # 유일한 시스템 Agent
└── plugins/                    # 사용자 Agent (자유롭게 추가/삭제)
    ├── __init__.py
    ├── health/                 # 건강 관련 Agent들
    │   ├── diet_agent.py
    │   └── workout_agent.py
    ├── productivity/           # 생산성 Agent들
    │   ├── schedule_agent.py
    │   └── task_agent.py
    └── custom/                 # 사용자 정의
        └── {any_agent}.py
```

### 1.2 Agent 자동 로더

```python
# backend/app/octostrator/agents/loader.py

class AgentLoader:
    """Agent 동적 로딩 시스템"""

    def __init__(self):
        self.plugin_paths = [
            "app/octostrator/agents/plugins",
            "app/custom_agents",  # 사용자 정의 경로
            "/opt/agents"  # 외부 Agent 경로
        ]

    def load_all_agents(self) -> Dict[str, Type[BaseAgent]]:
        """모든 Agent 로드"""
        agents = {}

        for path in self.plugin_paths:
            if not os.path.exists(path):
                continue

            agents.update(self._load_from_directory(path))

        logger.info(f"Loaded {len(agents)} agents")
        return agents

    def _load_from_directory(self, directory: str) -> Dict[str, Type[BaseAgent]]:
        """특정 디렉토리에서 Agent 로드"""
        agents = {}

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py') and not file.startswith('_'):
                    module_path = os.path.join(root, file)

                    try:
                        # 동적 모듈 로드
                        spec = importlib.util.spec_from_file_location(
                            f"agent_{uuid.uuid4().hex[:8]}",
                            module_path
                        )
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # BaseAgent 서브클래스 찾기
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if issubclass(obj, BaseAgent) and obj != BaseAgent:
                                agent_id = getattr(obj, 'agent_id', name.lower())
                                agents[agent_id] = obj
                                logger.info(f"Discovered agent: {agent_id} from {module_path}")

                    except Exception as e:
                        logger.error(f"Failed to load {module_path}: {e}")
                        # 하나 실패해도 계속 진행

        return agents
```

---

## 2. 역할 기반 Agent 시스템

### 2.1 Capability 정의

```python
# backend/app/octostrator/agents/capabilities.py

class Capability(Enum):
    """시스템에서 사용하는 표준 능력"""

    # 건강 관련
    MEAL_PLANNING = "meal_planning"
    NUTRITION_ANALYSIS = "nutrition_analysis"
    EXERCISE_PLANNING = "exercise_planning"
    HEALTH_TRACKING = "health_tracking"

    # 생산성
    SCHEDULING = "scheduling"
    TASK_MANAGEMENT = "task_management"
    REMINDER = "reminder"

    # 분석
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation"

    # 커뮤니케이션
    NOTIFICATION = "notification"
    EMAIL = "email"

    # 사용자 정의
    CUSTOM = "custom_{name}"
```

### 2.2 능력 기반 Agent 선택

```python
class CapabilityBasedRouter:
    """능력 기반으로 Agent 선택"""

    def __init__(self, agent_registry):
        self.registry = agent_registry

    def find_agent_for_task(self, required_capability: str) -> Optional[BaseAgent]:
        """특정 능력을 가진 Agent 찾기"""

        # 1. 정확히 일치하는 Agent 찾기
        candidates = []

        for agent_id in self.registry.list_agents():
            agent = self.registry.get_agent(agent_id)

            if required_capability in agent.capabilities:
                candidates.append({
                    'agent': agent,
                    'score': self._calculate_fitness_score(agent, required_capability)
                })

        if not candidates:
            # 2. 유사한 능력을 가진 Agent 찾기
            candidates = self._find_similar_capability_agents(required_capability)

        if not candidates:
            # 3. 범용 Agent 사용
            return self._get_fallback_agent()

        # 가장 적합한 Agent 선택
        best = max(candidates, key=lambda x: x['score'])
        return best['agent']

    def _calculate_fitness_score(self, agent: BaseAgent, capability: str) -> float:
        """Agent 적합도 점수 계산"""
        score = 0.0

        # 주 능력인지 확인
        if capability in agent.primary_capabilities:
            score += 1.0
        else:
            score += 0.5

        # 성능 이력
        success_rate = self._get_agent_success_rate(agent.agent_id, capability)
        score += success_rate

        # 현재 부하
        load = self._get_agent_load(agent.agent_id)
        score -= load * 0.2

        return score
```

---

## 3. Agent 추가 실제 예시

### 3.1 새로운 Agent 생성

```python
# backend/app/octostrator/agents/plugins/custom/meditation_agent.py

from app.octostrator.agents.base import BaseAgent, register_agent

@register_agent("meditation_agent")
class MeditationAgent(BaseAgent):
    """명상 가이드 Agent (새로 추가)"""

    def __init__(self):
        super().__init__(
            agent_id="meditation_agent",
            agent_name="Meditation Guide Agent",
            capabilities=[
                "meditation_guidance",
                "stress_management",
                "breathing_exercise"
            ],
            primary_capabilities=["meditation_guidance"],
            enable_checkpoint=False  # Stateless
        )

    def build_graph(self, llm=None):
        workflow = StateGraph(MeditationState)

        workflow.add_node("assess_mood", self._assess_mood)
        workflow.add_node("select_meditation", self._select_meditation)
        workflow.add_node("guide_session", self._guide_session)

        workflow.add_edge(START, "assess_mood")
        workflow.add_edge("assess_mood", "select_meditation")
        workflow.add_edge("select_meditation", "guide_session")
        workflow.add_edge("guide_session", END)

        return workflow.compile()

    async def execute(self, task, context):
        if task["type"] == "meditation_session":
            return await self._run_meditation_session(task["params"])
        elif task["type"] == "breathing_exercise":
            return await self._run_breathing_exercise(task["params"])
        else:
            return {"error": "Unknown task type"}
```

### 3.2 런타임 Agent 추가

```python
# API Endpoint로 Agent 추가

@router.post("/agents/add")
async def add_new_agent(agent_file: UploadFile):
    """새 Agent를 런타임에 추가"""

    # 1. 파일 저장
    agent_path = f"agents/plugins/uploaded/{agent_file.filename}"
    with open(agent_path, "wb") as f:
        f.write(await agent_file.read())

    # 2. 검증
    validator = AgentValidator()
    if not validator.validate(agent_path):
        os.remove(agent_path)
        raise HTTPException(400, "Invalid agent file")

    # 3. 로드
    loader = AgentLoader()
    new_agents = loader._load_from_directory("agents/plugins/uploaded")

    # 4. Registry 등록
    for agent_id, agent_class in new_agents.items():
        agent_registry.register(agent_class, agent_id)

    # 5. 즉시 사용 가능
    return {
        "status": "success",
        "agents_added": list(new_agents.keys()),
        "message": "Agents are now available"
    }
```

---

## 4. Agent 교체 시나리오

### 4.1 DietAgent v1 → v2 교체

```python
# 현재 DietAgent v1
class DietAgentV1(BaseAgent):
    capabilities = ["meal_planning", "calorie_counting"]

# 새로운 DietAgent v2
class DietAgentV2(BaseAgent):
    capabilities = ["meal_planning", "calorie_counting", "macro_tracking", "ai_coaching"]

# 점진적 교체 프로세스
async def upgrade_diet_agent():
    """DietAgent를 v2로 안전하게 업그레이드"""

    # 1. V2 등록 (V1과 공존)
    agent_registry.register(DietAgentV2, "diet_agent_v2")

    # 2. 카나리 배포 (10% 트래픽)
    router_config = {
        "meal_planning": {
            "diet_agent": 0.9,     # 90%는 v1
            "diet_agent_v2": 0.1   # 10%는 v2
        }
    }

    # 3. 모니터링 (1시간)
    await monitor_performance(duration_hours=1)

    # 4. 점진적 증가
    for percentage in [25, 50, 75, 100]:
        router_config["meal_planning"]["diet_agent_v2"] = percentage / 100
        router_config["meal_planning"]["diet_agent"] = (100 - percentage) / 100

        await monitor_performance(duration_hours=0.5)

        if detect_issues():
            # 롤백
            router_config["meal_planning"]["diet_agent"] = 1.0
            router_config["meal_planning"]["diet_agent_v2"] = 0.0
            break

    # 5. 완전 전환
    if router_config["meal_planning"]["diet_agent_v2"] == 1.0:
        agent_registry.unregister("diet_agent")
        agent_registry.rename("diet_agent_v2", "diet_agent")
```

---

## 5. 도메인 완전 전환 예시

### 5.1 PT Manager → 교육 시스템 전환

```python
async def transform_to_education_system():
    """PT Manager를 교육 시스템으로 완전 전환"""

    # 1. 현재 Agent 백업
    backup_agents = {
        "diet_agent": agent_registry.get_agent("diet_agent"),
        "workout_agent": agent_registry.get_agent("workout_agent"),
        "schedule_agent": agent_registry.get_agent("schedule_agent")
    }

    # 2. 모든 건강 관련 Agent 제거
    for agent_id in ["diet_agent", "workout_agent", "nutrition_agent"]:
        if agent_registry.has_agent(agent_id):
            agent_registry.unregister(agent_id)

    # 3. 교육 Agent 추가
    education_agents = [
        MathTutorAgent(),
        ScienceTeacherAgent(),
        HomeworkManagerAgent(),
        QuizGeneratorAgent(),
        ProgressTrackerAgent()
    ]

    for agent in education_agents:
        agent_registry.register(agent.__class__, agent.agent_id)

    # 4. TodoAgent는 그대로 (TODO 관리 역할은 동일)
    # 5. Supervisor도 그대로 (조율 역할은 동일)

    # 6. 능력 매핑 업데이트
    capability_mapping.update({
        "meal_planning": "lesson_planning",
        "exercise_planning": "homework_planning",
        "health_tracking": "grade_tracking"
    })

    logger.info("System transformed from PT Manager to Education System")

    return {
        "previous_domain": "health_fitness",
        "new_domain": "education",
        "agents_replaced": len(backup_agents),
        "new_agents": len(education_agents)
    }
```

---

## 6. Agent 관리 CLI

### 6.1 Agent 관리 명령어

```bash
# Agent 목록 보기
python manage.py agents list

# 출력:
# System Agents (1):
#   - todo_agent (TODO Management)
#
# Plugin Agents (5):
#   - diet_agent (meal_planning, nutrition_analysis)
#   - workout_agent (exercise_planning)
#   - schedule_agent (scheduling, calendar_sync)
#   - meditation_agent (meditation_guidance) [NEW]
#   - sleep_agent (sleep_tracking) [NEW]

# Agent 추가
python manage.py agents add meditation_agent.py

# Agent 제거
python manage.py agents remove workout_agent

# Agent 업데이트
python manage.py agents update diet_agent diet_agent_v2.py

# Agent 검색 (능력 기반)
python manage.py agents find --capability "meal_planning"

# 출력:
# Agents with 'meal_planning' capability:
#   - diet_agent (primary)
#   - nutrition_agent (secondary)
```

### 6.2 Agent 상태 모니터링

```python
# backend/app/octostrator/agents/monitor.py

class AgentMonitor:
    """Agent 실시간 모니터링"""

    def get_agent_status(self):
        """모든 Agent 상태 조회"""

        status = {
            "total_agents": agent_registry.count(),
            "active_agents": [],
            "idle_agents": [],
            "failed_agents": [],
            "statistics": {}
        }

        for agent_id in agent_registry.list_agents():
            agent = agent_registry.get_agent(agent_id)

            agent_info = {
                "id": agent_id,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "tasks_completed": agent.metrics.tasks_completed,
                "success_rate": agent.metrics.success_rate,
                "avg_execution_time": agent.metrics.avg_time
            }

            if agent.status == "active":
                status["active_agents"].append(agent_info)
            elif agent.status == "idle":
                status["idle_agents"].append(agent_info)
            else:
                status["failed_agents"].append(agent_info)

        return status
```

---

## 7. Agent 보안 및 격리

### 7.1 Agent Sandbox 실행

```python
class SecureAgentExecutor:
    """Agent를 격리된 환경에서 안전하게 실행"""

    async def execute_untrusted_agent(self, agent: BaseAgent, task: Dict):
        """신뢰할 수 없는 Agent 실행"""

        # Docker 컨테이너에서 실행
        container = docker.create_container(
            image="agent-sandbox:latest",
            command=f"python run_agent.py {agent.agent_id}",
            mem_limit="512m",
            cpu_shares=512,
            network_disabled=False,  # 네트워크 제한
            read_only=True,  # 읽기 전용
            timeout=30  # 30초 제한
        )

        try:
            # Agent 코드 주입
            docker.put_archive(container, "/app", agent_code)

            # 실행
            docker.start(container)
            result = docker.wait(container, timeout=30)

            # 결과 추출
            output = docker.logs(container)

            # 검증
            if self.validate_output(output):
                return json.loads(output)
            else:
                raise SecurityError("Invalid agent output")

        finally:
            # 정리
            docker.remove_container(container)
```

---

## 8. 결론

### 시스템의 유연성

```
✅ Agent는 완전한 플러그인
✅ 런타임 추가/삭제 가능
✅ 도메인 전환 가능
✅ 능력 기반 동작
✅ 특정 Agent 종속성 없음
```

### 실제 활용 예시

```
1. PT Manager → 교육 시스템
2. 교육 시스템 → 비즈니스 자동화
3. 비즈니스 → 게임 봇
4. 어떤 도메인이든 가능
```

### 핵심 원칙

```python
# Agent는 교체 가능한 부품
if not agent_available("diet_agent"):
    use_alternative("nutrition_agent")
    or use_fallback("general_agent")
    or request_manual_intervention()
```

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/AGENT_PLUGIN_EXAMPLES_251105.md`