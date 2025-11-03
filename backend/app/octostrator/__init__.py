"""Octostrator - Octopus Orchestrator

문어발처럼 여러 에이전트를 자동으로 오케스트레이션하는 시스템

구조:
- contexts/: 런타임 Context 관리 (불변)
- states/: State 관리 (변경 가능)
- supervisor/: Supervisor 에이전트 (메인 오케스트레이터)
- agents/: Worker 에이전트들
- sub_agents/: 공유 하위 에이전트 (모든 에이전트가 사용)
- tools/: 공유 툴 (모든 에이전트가 사용)
"""
