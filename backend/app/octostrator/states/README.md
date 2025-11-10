# State Management Structure

**Date**: 2025-11-05
**Version**: 1.0
**Purpose**: Centralized state management for the 3-Layer Architecture

## Overview

This directory contains all state definitions for the Specialist Agent system. States are separated by their purpose and role to enable independent development and clear role division among team members.

## Directory Structure

```
states/
├── __init__.py          # Module exports and imports
├── base.py              # Base state classes
├── supervisors.py       # All supervisor states (single file)
├── todo_agent_state.py  # TodoAgent specific state
├── diet_agent_state.py  # DietAgent specific state
├── workout_agent_state.py # WorkoutAgent specific state
└── README.md            # This file
```

## Design Philosophy

### 1. Simple Structure for Supervisors
- All supervisor states are in a single file (`supervisors.py`)
- Easier to maintain consistency across supervisors
- Supervisors are core infrastructure, managed by core team

### 2. Individual Files for Agent States
- Each agent has its own `*_agent_state.py` file
- Enables independent development by different team members
- Clear ownership and responsibility
- Easier to add new agents without conflicts

### 3. Inheritance Hierarchy
```
BaseState (TypedDict)
    ├── BaseAgentState
    │   ├── TodoAgentState
    │   ├── DietAgentState
    │   └── WorkoutAgentState
    └── Supervisor States
        ├── CognitiveSupervisorState
        ├── ExecuteSupervisorState
        └── MainOrchestratorState
```

## Usage Examples

### Using Supervisor States
```python
from backend.app.octostrator.states.supervisors import CognitiveSupervisorState

# In your supervisor code
class CognitiveSupervisor:
    def __init__(self):
        # Use CognitiveSupervisorState
        pass
```

### Using Agent States
```python
from backend.app.octostrator.states.diet_agent_state import DietAgentState

# In your agent code
class DietAgent(BaseAgent):
    def build_graph(self):
        workflow = StateGraph(DietAgentState)
        # ...
```

### Creating a New Agent State
1. Create a new file: `{agent_name}_agent_state.py`
2. Import BaseAgentState: `from .base import BaseAgentState`
3. Define your state class inheriting from BaseAgentState
4. Add specific fields for your agent
5. Update `__init__.py` to export your new state

Example:
```python
# schedule_agent_state.py
from typing import Dict, List, Optional, Any, TypedDict
from datetime import datetime
from .base import BaseAgentState

class ScheduleAgentState(BaseAgentState):
    """State for ScheduleAgent"""
    schedule: Optional[Dict[str, Any]] = None
    appointments: List[Dict[str, Any]]
    conflicts: List[str]
    # ... agent-specific fields
```

## Key State Classes

### Base States
- **BaseState**: Root state with common fields (session_id, messages, context, etc.)
- **BaseAgentState**: Extended state for all agents (task, capabilities, results, etc.)

### Supervisor States
- **CognitiveSupervisorState**: Planning and intent understanding
- **ExecuteSupervisorState**: Agent execution management
- **MainOrchestratorState**: Overall workflow coordination
- **HumanInTheLoopState**: User interaction management
- **MonitorState**: System monitoring and health

### Agent States
- **TodoAgentState**: TODO list management and HITL
- **DietAgentState**: Diet planning and nutrition tracking
- **WorkoutAgentState**: Exercise planning and fitness tracking

## Benefits of This Structure

1. **Role Division**: Each developer can work on their agent independently
2. **Clear Ownership**: Easy to identify who owns which state
3. **Reduced Conflicts**: Separate files minimize merge conflicts
4. **Scalability**: Easy to add new agents without affecting existing ones
5. **Type Safety**: TypedDict provides type hints for better IDE support
6. **Modularity**: States can be imported individually as needed

## Team Collaboration Guide

### For Core Team Members
- Maintain `base.py` and `supervisors.py`
- Review changes to base structures
- Ensure consistency across supervisor states

### For Agent Developers
1. Work only on your assigned `*_agent_state.py` file
2. Inherit from BaseAgentState
3. Document your state fields clearly
4. Update `__init__.py` when adding new exports
5. Test your state with your agent before committing

### Adding a New Agent
1. Create `{name}_agent_state.py` in this directory
2. Define your state class inheriting from BaseAgentState
3. Add necessary imports to `__init__.py`
4. Document the state in this README
5. Create your agent using the new state

## Migration Notes

If you're migrating from the old structure where states were defined inside agent files:

1. Move your state class to `states/{agent_name}_agent_state.py`
2. Update imports in your agent file
3. Remove the old state definition
4. Test thoroughly

## Best Practices

1. **Keep States Focused**: Only include fields that need to be shared between nodes
2. **Use Optional Types**: Make fields Optional when they might not always be set
3. **Document Fields**: Add comments explaining complex fields
4. **Type Everything**: Use proper type hints for all fields
5. **Default Values**: Use Field(default_factory=...) for mutable defaults

## Support

For questions about state management:
1. Check existing state files for examples
2. Consult the team lead for architectural decisions
3. Create an issue for state-related bugs or improvements

---

**Remember**: States are the backbone of our LangGraph workflows. Well-designed states make the entire system more maintainable and scalable.