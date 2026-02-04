"""Resource Models - 자원 관리 및 할당 모델

이 파일은 states/resource.py에서 models/로 이동됨.
Pydantic 모델만 포함.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ============================================================
# Agent Resource Models
# ============================================================

class AgentResource(BaseModel):
    """
    에이전트 자원 정보

    에이전트의 현재 상태, 가용성, 비용 정보 등을 관리
    """

    # 기본 정보
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str  # "collector", "analyzer", "report_agent" 등
    agent_type: Literal["ml", "biz", "utility"]

    # 계층 정보 (Phase 2 확장용)
    hierarchy_level: Literal["worker", "supervisor", "orchestrator"] = "worker"
    parent_supervisor: Optional[str] = None  # supervisor agent_id

    # 가용성
    status: Literal["idle", "busy", "error", "maintenance"] = "idle"
    max_concurrent_tasks: int = 1  # 동시 처리 가능한 task 수
    current_tasks: List[str] = Field(default_factory=list)  # 현재 처리 중인 todo IDs

    # 성능 정보
    average_execution_time_sec: float = 60.0  # 평균 실행 시간
    success_rate: float = 1.0  # 성공률 (0.0 ~ 1.0)

    # 비용 정보
    has_cost: bool = False
    cost_per_execution: float = 0.0  # 실행당 비용 (USD)
    cost_per_second: float = 0.0  # 초당 비용 (스트리밍 API 등)

    # 의존성 및 제약
    dependencies: List[str] = Field(default_factory=list)  # 의존하는 다른 agent IDs
    required_resources: Dict[str, Any] = Field(default_factory=dict)  # GPU, memory 등

    # 통계
    total_executions: int = 0
    total_failures: int = 0
    last_execution_at: Optional[datetime] = None
    last_error: Optional[str] = None

    # 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def is_available(self) -> bool:
        """에이전트가 사용 가능한지 확인"""
        return (
            self.status == "idle" and
            len(self.current_tasks) < self.max_concurrent_tasks
        )

    def can_accept_task(self) -> bool:
        """추가 task를 받을 수 있는지 확인"""
        return len(self.current_tasks) < self.max_concurrent_tasks

    def assign_task(self, todo_id: str):
        """Task 할당"""
        if self.can_accept_task():
            self.current_tasks.append(todo_id)
            if len(self.current_tasks) >= self.max_concurrent_tasks:
                self.status = "busy"
            self.updated_at = datetime.now()

    def release_task(self, todo_id: str, success: bool = True):
        """Task 해제"""
        if todo_id in self.current_tasks:
            self.current_tasks.remove(todo_id)

        if len(self.current_tasks) == 0:
            self.status = "idle"

        self.total_executions += 1
        if not success:
            self.total_failures += 1

        self.success_rate = 1.0 - (self.total_failures / self.total_executions)
        self.last_execution_at = datetime.now()
        self.updated_at = datetime.now()


# ============================================================
# Resource Allocation Models
# ============================================================

class ResourceAllocation(BaseModel):
    """
    자원 할당 정보

    특정 todo에 대한 agent 할당 정보
    """

    allocation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    todo_id: str
    agent_id: str
    agent_name: str

    # 할당 정보
    allocated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 예상 정보
    estimated_duration_sec: float = 60.0
    estimated_cost: float = 0.0

    # 실제 정보
    actual_duration_sec: Optional[float] = None
    actual_cost: Optional[float] = None

    # 상태
    status: Literal["allocated", "running", "completed", "failed", "cancelled"] = "allocated"

    # 결과
    success: bool = False
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================
# Resource Constraints Models
# ============================================================

class ResourceConstraints(BaseModel):
    """
    자원 제약 조건

    계획 실행 시 자원 사용 제약
    """

    # 병렬 실행 제약
    max_parallel_ml_agents: int = 3  # 동시 실행 가능한 ML agent 수
    max_parallel_biz_agents: int = 2  # 동시 실행 가능한 Biz agent 수
    max_total_parallel: int = 5  # 전체 동시 실행 수

    # 비용 제약
    max_total_cost: Optional[float] = None  # 최대 총 비용 (USD)
    max_cost_per_agent: Optional[float] = None  # agent당 최대 비용

    # 시간 제약
    max_total_duration_sec: Optional[int] = None  # 최대 총 실행 시간
    timeout_per_agent_sec: int = 300  # agent당 타임아웃

    # 자원 제약
    required_gpu: bool = False
    min_memory_gb: Optional[float] = None

    # 우선순위
    optimize_for: Literal["speed", "cost", "balanced"] = "balanced"


# ============================================================
# Resource Plan Models
# ============================================================

class ResourcePlan(BaseModel):
    """
    자원 할당 계획

    전체 계획에 대한 자원 할당 결과
    """

    resource_plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str  # 연결된 Plan ID

    # 할당 정보
    allocations: List[ResourceAllocation] = Field(default_factory=list)

    # 제약 조건
    constraints: ResourceConstraints = Field(default_factory=ResourceConstraints)

    # 예상 정보
    estimated_total_duration_sec: float = 0.0
    estimated_total_cost: float = 0.0
    estimated_parallel_groups: int = 0

    # 실제 정보
    actual_total_duration_sec: Optional[float] = None
    actual_total_cost: Optional[float] = None

    # 상태
    status: Literal["draft", "approved", "executing", "completed", "failed"] = "draft"

    # 최적화 정보
    optimization_score: float = 0.0  # 0.0 ~ 1.0
    optimization_notes: List[str] = Field(default_factory=list)

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================
# Helper Functions
# ============================================================

def create_agent_resource(
    agent_name: str,
    agent_type: Literal["ml", "biz", "utility"],
    max_concurrent_tasks: int = 1,
    has_cost: bool = False,
    cost_per_execution: float = 0.0,
    average_execution_time_sec: float = 60.0
) -> AgentResource:
    """
    AgentResource 생성 헬퍼

    Args:
        agent_name: 에이전트 이름
        agent_type: 에이전트 타입
        max_concurrent_tasks: 최대 동시 처리 수
        has_cost: 비용 여부
        cost_per_execution: 실행당 비용
        average_execution_time_sec: 평균 실행 시간

    Returns:
        AgentResource 인스턴스
    """
    return AgentResource(
        agent_name=agent_name,
        agent_type=agent_type,
        max_concurrent_tasks=max_concurrent_tasks,
        has_cost=has_cost,
        cost_per_execution=cost_per_execution,
        average_execution_time_sec=average_execution_time_sec
    )


def create_resource_allocation(
    todo_id: str,
    agent: AgentResource,
    estimated_duration_sec: Optional[float] = None
) -> ResourceAllocation:
    """
    ResourceAllocation 생성 헬퍼

    Args:
        todo_id: Todo ID
        agent: 할당할 AgentResource
        estimated_duration_sec: 예상 실행 시간 (None이면 agent 평균 사용)

    Returns:
        ResourceAllocation 인스턴스
    """
    duration = estimated_duration_sec or agent.average_execution_time_sec

    # 비용 계산
    cost = 0.0
    if agent.has_cost:
        if agent.cost_per_execution > 0:
            cost = agent.cost_per_execution
        elif agent.cost_per_second > 0:
            cost = agent.cost_per_second * duration

    return ResourceAllocation(
        todo_id=todo_id,
        agent_id=agent.agent_id,
        agent_name=agent.agent_name,
        estimated_duration_sec=duration,
        estimated_cost=cost
    )


def create_resource_constraints(
    max_parallel_ml_agents: int = 3,
    max_parallel_biz_agents: int = 2,
    max_total_cost: Optional[float] = None,
    optimize_for: Literal["speed", "cost", "balanced"] = "balanced"
) -> ResourceConstraints:
    """
    ResourceConstraints 생성 헬퍼

    Args:
        max_parallel_ml_agents: 최대 병렬 ML agent 수
        max_parallel_biz_agents: 최대 병렬 Biz agent 수
        max_total_cost: 최대 총 비용
        optimize_for: 최적화 목표

    Returns:
        ResourceConstraints 인스턴스
    """
    return ResourceConstraints(
        max_parallel_ml_agents=max_parallel_ml_agents,
        max_parallel_biz_agents=max_parallel_biz_agents,
        max_total_parallel=max_parallel_ml_agents + max_parallel_biz_agents,
        max_total_cost=max_total_cost,
        optimize_for=optimize_for
    )
