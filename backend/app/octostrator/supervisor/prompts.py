"""Supervisor 프롬프트 템플릿

현재 시스템에서 사용되는 프롬프트들은 각 노드 파일 내에 정의되어 있습니다.
- intent_understanding.py: 의도 파악
- planning.py: 계획 수립
- aggregator.py: 결과 취합
- generators/: 답변 생성

이 파일은 향후 공통 프롬프트가 필요할 때 사용할 수 있습니다.
"""

# 현재 시스템의 에이전트 목록 (참고용)
AVAILABLE_AGENTS = {
    "search": "데이터 검색 에이전트 (벡터DB, 웹 검색 등)",
    "validation": "데이터 검증 에이전트 (완전성, 스키마 검증 등)",
    "analysis": "데이터 분석 에이전트 (트렌드, 패턴 분석 등)",
    "comparison": "비교 분석 에이전트 (전년 대비, A/B 테스트 등)",
    "document": "문서 생성 에이전트 (보고서, 요약문 등)",
}

# TODO: 향후 공통 시스템 프롬프트가 필요하면 여기에 추가
