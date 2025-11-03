import sys
from pathlib import Path
backend_dir = Path.cwd() / "backend"
sys.path.insert(0, str(backend_dir))

from app.service_agent.cognitive_agents.planning_agent import PlanningAgent
from app.service_agent.cognitive_agents.query_decomposer import QueryDecomposer

async def test_query():
    # 사용자의 질문들
    queries = [
        "10년 살아서 전세금을 10억에서 20억으로 올릴려고해. 세입자에게 법적인 근거로 설명할 수 있도록",
        "집주인이 전세금을 10억에서 20억으로 올릴려고해. 10년살긴했지만, 5%이내로만 인상가능한거 아닌가?"
    ]
    
    planner = PlanningAgent()
    decomposer = QueryDecomposer()
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*70}")
        print(f"질문 {i}: {query}")
        print('='*70)
        
        # Intent 분석
        intent_result = await planner.analyze_intent(query)
        print(f"\n[1] 의도 분석")
        print(f"  의도: {intent_result.intent_type.value}")
        print(f"  신뢰도: {intent_result.confidence}")
        print(f"  추천 에이전트: {intent_result.suggested_agents}")
        
        # Query 분해
        decomp_result = await decomposer.decompose(query, intent_result)
        print(f"\n[2] 질문 분해")
        print(f"  복합 질문: {decomp_result.is_compound}")
        print(f"  작업 수: {len(decomp_result.sub_tasks)}")
        print(f"  실행 모드: {decomp_result.execution_mode}")
        for task in decomp_result.sub_tasks:
            print(f"  작업: {task.description}")
            print(f"    팀: {task.agent}, 유형: {task.type}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_query())
