"""
State Management Module - Domain-Agnostic State Layer

⚠️  CURRENT STATE: Generic State Layer (Domain-Independent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Centralized state definitions for the 3-Layer Architecture.
All states are domain-agnostic and work across Fitness, Medical, Legal, Education, etc.

AVAILABLE STATES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Core States:
   - base.py: Base state classes (BaseState, BaseAgentState)
   - octostrator_state.py: Main system state with history tracking

2. Layer States:
   - cognitive_state.py: Cognitive layer (planning, intent understanding)
   - todo_state.py: Todo layer (task management)
   - execute_state.py: Execute layer (agent orchestration)
   - response_state.py: Response layer (output formatting)

3. Supervisor States:
   - supervisors.py: Legacy supervisor states (for backward compatibility)

4. Utilities:
   - reducers.py: State reducers for LangGraph (merge, track, add)
   - state_helpers.py: Helper functions for state management

🔮 HOW TO ADD DOMAIN-SPECIFIC AGENT STATES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Option A: Extend BaseAgentState (Recommended)
────────────────────────────────────────────────────────────────────────
Create domain-specific agent state by extending BaseAgentState:

    # backend/app/octostrator/states/fitness_agent_state.py
    from .base import BaseAgentState
    from typing import Dict, List, Optional

    class FitnessAgentState(BaseAgentState):
        '''
        Fitness domain agent state
        '''
        # Fitness-specific fields
        workout_plan: Optional[Dict]
        nutrition_plan: Optional[Dict]
        member_progress: Optional[Dict]
        inbody_data: Optional[Dict]

Then import in __init__.py:
    from .fitness_agent_state import FitnessAgentState
    __all__ = [..., "FitnessAgentState"]

Option B: Use BaseAgentState Directly (Simple Agents)
────────────────────────────────────────────────────────────────────────
For simple agents, use BaseAgentState without extension:

    # In backend/app/octostrator/agents/medical/medical_nodes.py
    from backend.app.octostrator.states import BaseAgentState

    async def patient_analysis_node(state: BaseAgentState):
        # Access generic fields
        task = state.get("task", {})
        context = state.get("context", {})

        # Use context for domain-specific data
        patient_data = context.get("patient_data", {})

        # Process...
        return {"result": {...}}

Option C: TypedDict for Custom States
────────────────────────────────────────────────────────────────────────
Create custom TypedDict for specific use cases:

    # backend/app/octostrator/states/medical_agent_state.py
    from typing import TypedDict, Optional, Dict, List

    class MedicalAgentState(TypedDict, total=False):
        # From BaseState
        session_id: str
        messages: List[Dict]
        context: Dict

        # Medical-specific
        patient_id: str
        medical_records: List[Dict]
        diagnosis: Optional[str]
        prescriptions: List[Dict]
        vital_signs: Optional[Dict]

DOMAIN EXAMPLES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Fitness Domain States:
   - FitnessAgentState: workout_plan, nutrition_plan, member_progress
   - InBodyState: measurements, body_composition, comparison_data

2. Medical Domain States:
   - MedicalAgentState: patient_id, medical_records, diagnosis, prescriptions
   - PatientState: demographics, medical_history, current_vitals

3. Legal Domain States:
   - LegalAgentState: case_id, documents, legal_research, precedents
   - ContractState: parties, terms, clauses, review_status

4. Education Domain States:
   - EducationAgentState: course_id, assignments, submissions, grades
   - StudentState: enrollment, progress, performance_data

MIGRATION FROM PT-SPECIFIC TO DOMAIN-SPECIFIC:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Previously, this system planned to have PT-specific agent states (diet_agent_state,
workout_agent_state). These were never implemented, and the system already uses
generic states throughout.

Current state structure is already domain-agnostic and works with any domain.

Author: Specialist Agent Development Team
Date: 2025-11-10 (Updated: Domain-Agnostic)
Version: 2.0
"""

# Base imports
from .base import (
    BaseState,
    BaseAgentState,
    BaseModel,
    TaskDict,
    ResultDict,
    ContextDict,
    MessageDict
)

# Layer states
from .cognitive_state import CognitiveState
from .todo_state import (
    TodoAgentState,
    TodoItem,
    TodoBatch,
    TodoFilter
)
from .execute_state import ExecuteState
from .response_state import ResponseState

# Supervisor states (legacy compatibility)
from .supervisors import (
    CognitiveSupervisorState,
    ExecuteSupervisorState,
    MainOrchestratorState,
    HumanInTheLoopState,
    MonitorState
)

# Octostrator State (New - with History Tracking)
from .octostrator_state import OctostratorState

# Reducers
from .reducers import (
    add_with_timestamp_and_step,
    merge_todos_smart,
    track_plan_changes,
    track_user_interactions
)

# State Helpers
from .state_helpers import StateHelpers

# 🔮 Domain-Specific Agent States (Add your domain states here)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Example imports (uncomment and customize for your domain):
#
# from .fitness_agent_state import (
#     FitnessAgentState,
#     WorkoutPlan,
#     NutritionPlan,
#     MemberProgress
# )
#
# from .medical_agent_state import (
#     MedicalAgentState,
#     PatientRecord,
#     Diagnosis,
#     Prescription
# )
#
# from .legal_agent_state import (
#     LegalAgentState,
#     LegalCase,
#     Contract,
#     LegalResearch
# )
#
# from .education_agent_state import (
#     EducationAgentState,
#     Course,
#     Assignment,
#     StudentProgress
# )

__all__ = [
    # Base
    "BaseState",
    "BaseAgentState",
    "BaseModel",
    "TaskDict",
    "ResultDict",
    "ContextDict",
    "MessageDict",

    # Layer states
    "CognitiveState",
    "TodoAgentState",
    "TodoItem",
    "TodoBatch",
    "TodoFilter",
    "ExecuteState",
    "ResponseState",

    # Supervisors (legacy)
    "CognitiveSupervisorState",
    "ExecuteSupervisorState",
    "MainOrchestratorState",
    "HumanInTheLoopState",
    "MonitorState",

    # Octostrator State (New)
    "OctostratorState",

    # Reducers
    "add_with_timestamp_and_step",
    "merge_todos_smart",
    "track_plan_changes",
    "track_user_interactions",

    # State Helpers
    "StateHelpers",

    # 🔮 Domain-Specific Agent States
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Add your domain-specific state exports here:
    #
    # "FitnessAgentState",
    # "WorkoutPlan",
    # "NutritionPlan",
    # "MemberProgress",
    #
    # "MedicalAgentState",
    # "PatientRecord",
    # "Diagnosis",
    # "Prescription",
    #
    # "LegalAgentState",
    # "LegalCase",
    # "Contract",
    # "LegalResearch",
    #
    # "EducationAgentState",
    # "Course",
    # "Assignment",
    # "StudentProgress",
]
