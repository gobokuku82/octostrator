"""
Test comprehensive intent with analysis team execution
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.foundation.context import create_default_llm_context
from app.service_agent.foundation.separated_states import StateManager
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_comprehensive_query():
    """Test comprehensive query that should trigger both search and analysis teams"""

    # Create supervisor
    llm_context = create_default_llm_context()
    supervisor = TeamBasedSupervisor(llm_context=llm_context)

    # Test queries - both should be COMPREHENSIVE and use search + analysis teams
    test_queries = [
        "집주인이 짜증나, 지금 10년살고 있었는데 전세금 3억이었는데, 갑자기 10억으로 올려달래. 법적으로 해결방법 알려줘",
        "전세금 3억을 10억으로 올려달래. 이거 법적으로 가능한거야? 어떻게 대응해야 해?"
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Testing query: {query}")
        print('='*80)

        # Create initial state
        initial_state = {
            "query": query,
            "session_id": f"test_comprehensive_{query[:20]}",
            "user_info": {"user_id": "test_user"},
            "conversation_history": [],
            "execution_state": "pending",
            "status": "pending",
            "error": None
        }

        try:
            # Execute the workflow
            result = await supervisor.app.ainvoke(initial_state)

            # Check results
            print(f"\nExecution Summary:")
            print(f"- Status: {result.get('status')}")
            print(f"- Intent: {result.get('planning_state', {}).get('analyzed_intent', {}).get('intent_type')}")
            print(f"- Active Teams: {result.get('active_teams')}")
            print(f"- Completed Teams: {result.get('completed_teams')}")

            # Check if analysis team was executed
            if 'analysis' in result.get('active_teams', []):
                print("✅ Analysis team was included in active teams")
            else:
                print("❌ Analysis team was NOT included in active teams")

            if 'analysis' in result.get('completed_teams', []):
                print("✅ Analysis team was executed")
            else:
                print("⚠️ Analysis team was NOT executed")

            # Show team results
            team_results = result.get('team_results', {})
            print(f"\nTeam Results:")
            for team, data in team_results.items():
                print(f"  - {team}: {type(data).__name__} with {len(str(data))} chars")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_comprehensive_query())