"""Phase 3.6 테스트

Graph Generator + Report Generator 동작 검증
"""
import asyncio
import json
from langchain_core.messages import HumanMessage
from backend.app.octostrator.supervisor.graph import build_supervisor_graph


async def test_graph_generator():
    """Graph Generator 테스트"""
    print("\n" + "=" * 80)
    print("TEST 1: GRAPH GENERATOR")
    print("=" * 80)

    graph = build_supervisor_graph()

    result = await graph.ainvoke({
        "messages": [HumanMessage(
            content="데이터를 검색하고 분석해줘."
        )],
        "output_format": "graph"  # Graph 형식
    })

    print("\n[Graph Generator 결과]")
    graph_data = result.get("final_result")

    if isinstance(graph_data, dict):
        print(f"✓ Graph Data Type: dict")
        print(f"✓ Nodes Count: {len(graph_data.get('nodes', []))}")
        print(f"✓ Edges Count: {len(graph_data.get('edges', []))}")
        print(f"✓ Metadata: {graph_data.get('metadata', {})}")

        # 일부 노드 출력
        print("\n[샘플 Nodes (처음 3개)]:")
        for node in graph_data.get('nodes', [])[:3]:
            print(f"  - {node['id']}: {node['label'][:50]}... (type: {node['type']}, color: {node['color']})")

        # 일부 엣지 출력
        print("\n[샘플 Edges (처음 3개)]:")
        for edge in graph_data.get('edges', [])[:3]:
            print(f"  - {edge['source']} → {edge['target']}")

        # JSON 직렬화 가능 확인
        try:
            json_str = json.dumps(graph_data, ensure_ascii=False, indent=2)
            print(f"\n✓ JSON 직렬화 가능: {len(json_str)} characters")
        except Exception as e:
            print(f"\n❌ JSON 직렬화 실패: {e}")

        return True
    else:
        print(f"❌ Graph Data Type: {type(graph_data)} (expected dict)")
        return False


async def test_report_generator():
    """Report Generator 테스트"""
    print("\n" + "=" * 80)
    print("TEST 2: REPORT GENERATOR")
    print("=" * 80)

    graph = build_supervisor_graph()

    result = await graph.ainvoke({
        "messages": [HumanMessage(
            content="매출 데이터를 검색하고 분석해줘."
        )],
        "output_format": "report"  # Report 형식
    })

    print("\n[Report Generator 결과]")
    report = result.get("final_result")

    if isinstance(report, str):
        print(f"✓ Report Type: str")
        print(f"✓ Report Length: {len(report)} characters")

        # Markdown 구조 확인
        markdown_headers = ["# 분석 보고서", "## 📋 요약", "## 📊 실행 통계", "## 🔍 상세 실행 내역", "## 💡 주요 인사이트"]
        found_headers = [header for header in markdown_headers if header in report]
        print(f"✓ Markdown Headers Found: {len(found_headers)}/{len(markdown_headers)}")

        for header in found_headers:
            print(f"  - {header}")

        # 일부 내용 출력
        print("\n[Report Preview (처음 500자)]:")
        print(report[:500] + "...")

        return True
    else:
        print(f"❌ Report Type: {type(report)} (expected str)")
        return False


async def test_all_formats():
    """모든 형식 테스트"""
    print("\n" + "=" * 80)
    print("TEST 3: ALL FORMATS COMPARISON")
    print("=" * 80)

    graph = build_supervisor_graph()

    formats = ["chat", "graph", "report"]
    results = {}

    for fmt in formats:
        print(f"\n테스트 형식: {fmt}")
        result = await graph.ainvoke({
            "messages": [HumanMessage(
                content="간단한 검색 작업"
            )],
            "output_format": fmt
        })

        final_result = result.get("final_result")
        results[fmt] = {
            "type": type(final_result).__name__,
            "length": len(str(final_result)),
            "success": final_result is not None
        }

        print(f"  - Type: {results[fmt]['type']}")
        print(f"  - Length: {results[fmt]['length']}")
        print(f"  - Success: {results[fmt]['success']}")

    print("\n[형식별 결과 비교]")
    print(f"Chat:   {results['chat']['type']:10} | {results['chat']['length']:6} chars")
    print(f"Graph:  {results['graph']['type']:10} | {results['graph']['length']:6} chars")
    print(f"Report: {results['report']['type']:10} | {results['report']['length']:6} chars")

    all_success = all(r['success'] for r in results.values())
    return all_success


async def main():
    """Phase 3.6 전체 테스트"""
    print("=" * 80)
    print("PHASE 3.6 TEST: GRAPH & REPORT GENERATOR")
    print("=" * 80)

    # 테스트 실행
    test1_pass = await test_graph_generator()
    test2_pass = await test_report_generator()
    test3_pass = await test_all_formats()

    # 최종 결과
    print("\n" + "=" * 80)
    print("검증 결과:")
    print("=" * 80)
    print(f"✓ Graph Generator 테스트: {'통과' if test1_pass else '실패'}")
    print(f"✓ Report Generator 테스트: {'통과' if test2_pass else '실패'}")
    print(f"✓ All Formats 테스트: {'통과' if test3_pass else '실패'}")

    print("\n" + "=" * 80)
    if all([test1_pass, test2_pass, test3_pass]):
        print("🎉 Phase 3.6 테스트 성공!")
    else:
        print("❌ Phase 3.6 테스트 실패 - 일부 검증 실패")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
