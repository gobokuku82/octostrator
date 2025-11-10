"""Tools Registry - Domain-Agnostic Tools Layer

⚠️  CURRENT STATE: Generic Tools Layer (Domain-Independent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This module provides a generic tools registry system that works across all domains
(Fitness, Medical, Legal, Education, etc.).

🔮 HOW TO ADD DOMAIN-SPECIFIC TOOLS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For comprehensive examples and patterns, see TOOLS_GUIDE.md

Option A: Separate Tool Modules (Recommended for Complex Domains)
────────────────────────────────────────────────────────────────────────
Create domain-specific tool modules:

    backend/app/octostrator/tools/
    ├── __init__.py              (this file - registry)
    ├── TOOLS_GUIDE.md           (comprehensive guide)
    ├── fitness_tools.py         (Fitness domain tools)
    ├── medical_tools.py         (Medical domain tools)
    ├── legal_tools.py           (Legal domain tools)
    └── education_tools.py       (Education domain tools)

Example fitness_tools.py - See TOOLS_GUIDE.md for full examples.

    Key pattern:
    - Use async def for all tool functions
    - Use get_db_session() context manager for database access
    - Return Dict with results or errors
    - Include proper type hints

Then import in __init__.py:
    from .fitness_tools import (
        create_workout_program,
        get_member_progress,
        analyze_body_composition,
        # ... more tools
    )

    TOOLS = {
        "create_workout_program": create_workout_program,
        "get_member_progress": get_member_progress,
        "analyze_body_composition": analyze_body_composition,
        # ... more tools
    }

Option B: Inline Tools in Agent Nodes (Recommended for Simple Domains)
────────────────────────────────────────────────────────────────────────
Write tool logic directly in agent nodes using @tool decorator.
See TOOLS_GUIDE.md for complete examples.

    Key pattern:
    - Use @tool decorator from langchain.tools
    - Define async functions with proper docstrings
    - Pass tools list to agent constructor

Option C: LangChain Tool Decorators (Advanced)
────────────────────────────────────────────────────────────────────────
Use LangChain's @tool decorator with Annotated type hints for better
LLM integration. See TOOLS_GUIDE.md for complete examples.

    Key pattern:
    - Use Annotated[type, "description"] for parameters
    - Raise ToolException for errors
    - Full docstrings for LLM understanding

DOMAIN EXAMPLES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Fitness Domain Tools:
   - create_workout_program()
   - get_member_progress()
   - analyze_body_composition()
   - schedule_training_session()
   - track_nutrition_intake()

2. Medical Domain Tools:
   - get_patient_records()
   - create_prescription()
   - schedule_appointment()
   - analyze_vital_signs()
   - search_medical_history()

3. Legal Domain Tools:
   - search_legal_cases()
   - create_contract()
   - analyze_legal_document()
   - search_precedents()
   - generate_legal_brief()

4. Education Domain Tools:
   - create_assignment()
   - grade_submission()
   - get_student_progress()
   - schedule_class()
   - analyze_performance()

TOOL REGISTRY PATTERN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Simple Dict-based registry (LangGraph philosophy - stateless, simple):

    TOOLS: Dict[str, Callable] = {
        "tool_name_1": tool_function_1,
        "tool_name_2": tool_function_2,
        # ... more tools
    }

    def get_tool(name: str) -> Callable:
        if name not in TOOLS:
            available = ", ".join(sorted(TOOLS.keys()))
            raise ValueError(f"Tool '{name}' not found. Available: {available}")
        return TOOLS[name]

    def list_tools() -> List[str]:
        return sorted(TOOLS.keys())

    def list_tools_by_domain(domain: str) -> List[str]:
        # Group tools by domain prefix or metadata
        pass

TESTING TOOLS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# backend/test_your_domain_tools.py
import asyncio
from backend.app.octostrator.tools.your_domain_tools import your_tool_function

async def test_tool():
    result = await your_tool_function(param1="value1", param2="value2")
    print(f"Result: {result}")
    assert result["status"] == "success"

if __name__ == "__main__":
    asyncio.run(test_tool())

MIGRATION FROM PT-SPECIFIC TO DOMAIN-SPECIFIC:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Previously, this system had 62 PT-specific tools across 7 modules:
- frontdesk_tools.py (12 tools)
- assessor_tools.py (7 tools)
- program_designer_tools.py (10 tools)
- manager_tools.py (8 tools)
- marketing_tools.py (9 tools)
- owner_assistant_tools.py (8 tools)
- trainer_education_tools.py (8 tools)

These have been archived to:
    backend/app/octostrator/tools/archive_fitness/

You can reference these archived files when implementing your domain-specific tools,
but note that the models they reference have also been archived/generalized.

For detailed patterns and examples, see:
    backend/app/octostrator/tools/TOOLS_GUIDE.md

Author: Specialist Agent Development Team
Date: 2025-11-10 (Updated: Domain-Agnostic)
Version: 2.0
"""

from typing import Callable, Dict, List

# ==================== Tools Registry ====================

TOOLS: Dict[str, Callable] = {
    # 🔮 Add your domain-specific tools here:
    # Example:
    # "create_workout_program": create_workout_program,
    # "get_patient_records": get_patient_records,
    # "search_legal_cases": search_legal_cases,
    # "create_assignment": create_assignment,
}


# ==================== Helper Functions ====================

def get_tool(name: str) -> Callable:
    """Get a tool function by name

    Args:
        name: Tool name

    Returns:
        Callable: Tool function

    Raises:
        ValueError: If tool not found

    Example:
        >>> tool_func = get_tool("create_workout_program")
        >>> result = await tool_func(user_id=1, program_name="Beginner")
    """
    if name not in TOOLS:
        available = ", ".join(sorted(TOOLS.keys()))
        raise ValueError(
            f"Tool '{name}' not found.\n"
            f"Available tools: {available}"
        )
    return TOOLS[name]


def list_tools() -> List[str]:
    """List all available tools

    Returns:
        List[str]: Sorted list of tool names

    Example:
        >>> tools = list_tools()
        >>> print(tools)
        ['create_assignment', 'create_workout_program', ...]
    """
    return sorted(TOOLS.keys())


def list_tools_by_domain(domain: str) -> List[str]:
    """List tools for a specific domain

    Args:
        domain: Domain name (e.g., 'fitness', 'medical', 'legal', 'education')

    Returns:
        List[str]: Sorted list of tool names for the domain

    Raises:
        ValueError: If domain not found

    Example:
        >>> fitness_tools = list_tools_by_domain("fitness")
        >>> print(fitness_tools)
        ['create_workout_program', 'get_member_progress', ...]

    Note:
        This is a placeholder. Implement domain grouping logic based on your needs:
        - Option 1: Use tool name prefixes (e.g., "fitness_create_program")
        - Option 2: Add domain metadata to tool functions
        - Option 3: Maintain separate domain_tools dictionaries
    """
    # Placeholder implementation - customize based on your domain organization
    domain_tools: Dict[str, List[str]] = {
        # Example structure:
        # "fitness": ["create_workout_program", "get_member_progress", ...],
        # "medical": ["get_patient_records", "create_prescription", ...],
        # "legal": ["search_legal_cases", "create_contract", ...],
        # "education": ["create_assignment", "grade_submission", ...],
    }

    if domain not in domain_tools:
        available = ", ".join(sorted(domain_tools.keys()))
        raise ValueError(
            f"Domain '{domain}' not found.\n"
            f"Available domains: {available}"
        )

    return sorted(domain_tools[domain])


def print_tools_summary() -> None:
    """Print summary of all registered tools (for debugging)

    Example:
        >>> print_tools_summary()
        [Tools Registry] 15 tools registered

        Fitness Tools (5):
          - create_workout_program
          - get_member_progress
          ...
    """
    print(f"[Tools Registry] {len(TOOLS)} tools registered\n")

    # Group by domain if needed
    if TOOLS:
        print("Registered Tools:")
        for tool_name in sorted(TOOLS.keys()):
            print(f"  - {tool_name}")
    else:
        print("No tools registered yet.")
        print("\nTo add tools, see TOOLS_GUIDE.md")


# ==================== Exports ====================

__all__ = [
    # Registry
    "TOOLS",

    # Helper Functions
    "get_tool",
    "list_tools",
    "list_tools_by_domain",
    "print_tools_summary",

    # 🔮 Domain-Specific Tools
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Add your domain-specific tool exports here:
    #
    # Fitness domain:
    # "create_workout_program",
    # "get_member_progress",
    # "analyze_body_composition",
    #
    # Medical domain:
    # "get_patient_records",
    # "create_prescription",
    # "schedule_appointment",
    #
    # Legal domain:
    # "search_legal_cases",
    # "create_contract",
    # "analyze_legal_document",
    #
    # Education domain:
    # "create_assignment",
    # "grade_submission",
    # "get_student_progress",
]
