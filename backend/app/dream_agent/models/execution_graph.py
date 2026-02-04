"""Execution Graph Models - 실행 그래프 및 DAG 구조 모델

이 파일은 states/execution_graph.py에서 models/로 이동됨.
Pydantic 모델만 포함.
"""

from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ============================================================
# Execution Node Models
# ============================================================

class ExecutionNode(BaseModel):
    """
    실행 노드

    DAG의 단일 노드 (Todo에 해당)
    """

    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    todo_id: str
    task: str

    # 의존성
    dependencies: List[str] = Field(default_factory=list)  # 이 노드가 의존하는 node IDs
    dependents: List[str] = Field(default_factory=list)  # 이 노드에 의존하는 node IDs

    # 실행 정보
    layer: str  # cognitive, planning, ml_execution, biz_execution, response
    agent_name: Optional[str] = None
    estimated_duration_sec: float = 60.0

    # 그룹 정보
    parallel_group: int = 0  # 병렬 실행 그룹 번호 (0부터 시작)
    depth: int = 0  # DAG에서의 깊이

    # 상태
    status: str = "pending"  # pending, ready, running, completed, failed

    # Critical Path
    is_critical: bool = False  # Critical Path에 포함되는지 여부

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================
# Execution Group Models
# ============================================================

class ExecutionGroup(BaseModel):
    """
    실행 그룹

    병렬로 실행 가능한 노드들의 그룹
    """

    group_id: int  # 그룹 번호 (실행 순서)
    nodes: List[ExecutionNode] = Field(default_factory=list)

    # 그룹 통계
    total_nodes: int = 0
    ml_nodes: int = 0
    biz_nodes: int = 0

    # 예상 정보
    estimated_duration_sec: float = 0.0  # 그룹 내 최대 실행 시간
    estimated_cost: float = 0.0

    # LangGraph Command 정보
    command_type: str = "parallel"  # parallel, sequential
    goto_targets: List[str] = Field(default_factory=list)  # LangGraph goto targets

    def add_node(self, node: ExecutionNode):
        """노드 추가"""
        self.nodes.append(node)
        self.total_nodes = len(self.nodes)

        if node.layer == "ml_execution":
            self.ml_nodes += 1
        elif node.layer == "biz_execution":
            self.biz_nodes += 1

        # 최대 실행 시간 업데이트
        if node.estimated_duration_sec > self.estimated_duration_sec:
            self.estimated_duration_sec = node.estimated_duration_sec


# ============================================================
# Execution Graph Models
# ============================================================

class ExecutionGraph(BaseModel):
    """
    실행 그래프 (DAG)

    전체 실행 계획의 DAG 표현
    """

    graph_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str

    # 노드 및 그룹
    nodes: List[ExecutionNode] = Field(default_factory=list)
    groups: List[ExecutionGroup] = Field(default_factory=list)

    # DAG 정보
    total_nodes: int = 0
    total_groups: int = 0
    max_depth: int = 0

    # Critical Path
    critical_path: List[str] = Field(default_factory=list)  # node IDs
    critical_path_duration: float = 0.0

    # 예상 정보
    estimated_sequential_duration: float = 0.0  # 순차 실행 시간
    estimated_parallel_duration: float = 0.0  # 병렬 실행 시간
    parallelization_factor: float = 1.0  # 병렬화 효율 (sequential / parallel)

    # LangGraph 정보
    supports_parallel_execution: bool = False
    langgraph_commands: List[Dict[str, Any]] = Field(default_factory=list)

    # Mermaid 다이어그램
    mermaid_diagram: str = ""

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def get_node(self, node_id: str) -> Optional[ExecutionNode]:
        """노드 조회"""
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def get_group(self, group_id: int) -> Optional[ExecutionGroup]:
        """그룹 조회"""
        return next((g for g in self.groups if g.group_id == group_id), None)

    def get_root_nodes(self) -> List[ExecutionNode]:
        """루트 노드 조회 (의존성 없는 노드)"""
        return [n for n in self.nodes if not n.dependencies]

    def get_leaf_nodes(self) -> List[ExecutionNode]:
        """리프 노드 조회 (의존하는 노드가 없는 노드)"""
        return [n for n in self.nodes if not n.dependents]


# ============================================================
# Helper Functions
# ============================================================

def create_execution_node(
    todo_id: str,
    task: str,
    layer: str,
    dependencies: Optional[List[str]] = None,
    agent_name: Optional[str] = None,
    estimated_duration_sec: float = 60.0
) -> ExecutionNode:
    """
    ExecutionNode 생성 헬퍼

    Args:
        todo_id: Todo ID
        task: 작업 설명
        layer: 실행 레이어
        dependencies: 의존하는 todo IDs
        agent_name: 에이전트 이름
        estimated_duration_sec: 예상 실행 시간

    Returns:
        ExecutionNode 인스턴스
    """
    return ExecutionNode(
        todo_id=todo_id,
        task=task,
        layer=layer,
        dependencies=dependencies or [],
        agent_name=agent_name,
        estimated_duration_sec=estimated_duration_sec
    )


def create_execution_group(group_id: int) -> ExecutionGroup:
    """
    ExecutionGroup 생성 헬퍼

    Args:
        group_id: 그룹 번호

    Returns:
        ExecutionGroup 인스턴스
    """
    return ExecutionGroup(group_id=group_id)


def create_execution_graph(plan_id: str) -> ExecutionGraph:
    """
    ExecutionGraph 생성 헬퍼

    Args:
        plan_id: Plan ID

    Returns:
        ExecutionGraph 인스턴스
    """
    return ExecutionGraph(plan_id=plan_id)
