# 🧹 Octostrator Cleanup Plan

**작성일**: 2025-11-05
**작성자**: AI PT Manager Development Team
**목적**: 불필요한 파일 제거 및 코드베이스 정리

---

## 📊 현재 상태 요약

- **전체 코드**: 9,460 lines
- **정상 코드**: 7,200 lines (76%)
- **중복/오래된 코드**: 1,000 lines (11%)
- **깨진 코드**: 517 lines (5%)

---

## 🚨 중요 문제

### 문제 1: supervisor_state.py 파일 누락 (심각도: CRITICAL)
- **상황**: 6개 파일이 존재하지 않는 `supervisor_state.py`를 import
- **영향**: Runtime에서 ModuleNotFoundError 발생
- **해결**: 이미 `supervisors.py`로 대체됨, import만 수정 필요

### 문제 2: Diet Agent 3개 버전 중복 (심각도: HIGH)
- `agent.py` (86줄) - 구버전, 깨짐
- `diet_agent.py` (397줄) - 중간 버전
- `diet_agent_v2.py` (414줄) - **최신 버전, 유지**

---

## 📝 삭제 계획 (단계별)

### Phase 1: 즉시 삭제 가능 (위험도: ZERO) ⚡

#### 삭제할 파일들:
```bash
# 1. 빈 파일
rm backend/app/octostrator/supervisor/response_prompts.py  # 0 lines

# 2. Placeholder 코드
rm backend/app/octostrator/agents/placeholder_agents.py  # 178 lines, TODO 스텁만 있음

# 3. 사용하지 않는 디렉토리
rm -rf backend/app/octostrator/sub_agents/  # 10 lines, 빈 디렉토리
```

**영향**: 없음 (아무도 사용하지 않음)
**예상 시간**: 15분
**총 라인 수**: 188 lines 제거

---

### Phase 2: Diet Agent 정리 (위험도: LOW) 🥗

#### 전제조건:
- [ ] `diet_agent_v2.py` 작동 확인
- [ ] 모든 import가 v2를 가리키는지 확인

#### 삭제할 파일들:
```bash
# 구버전 Diet Agent들
rm backend/app/octostrator/agents/diet/agent.py  # 86 lines
rm backend/app/octostrator/agents/diet/diet_agent.py  # 397 lines
```

#### 수정할 파일:
```python
# agents/diet/__init__.py 수정
# 기존: from .agent import diet_agent_node
# 변경: from .diet_agent_v2 import DietAgentV2

# supervisor/main_graph.py 수정
# diet_agent_node 참조 제거 또는 DietAgentV2로 변경
```

**영향**: Diet 기능 정상 작동 확인 필요
**예상 시간**: 1주일 (테스트 포함)
**총 라인 수**: 483 lines 제거

---

### Phase 3: Legacy Agent 교체 (위험도: MEDIUM) 🔄

#### 전제조건:
- [ ] 각 Agent의 BaseAgent 버전 구현 완료

#### 구현 후 삭제할 파일들:
```bash
# Legacy agents (supervisor_state.py 의존)
rm backend/app/octostrator/agents/workout/agent.py  # 80 lines
rm backend/app/octostrator/agents/schedule/agent.py  # 77 lines
rm backend/app/octostrator/agents/member_care/agent.py  # 98 lines
rm backend/app/octostrator/agents/coaching/agent.py  # 82 lines
```

**영향**: 새 Agent 구현 필요
**예상 시간**: 3-4주 (구현 + 테스트)
**총 라인 수**: 337 lines 제거

---

### Phase 4: 최종 정리 (위험도: LOW) ✨

#### 리팩토링:
- `supervisor/main_graph.py`에서 legacy 코드 제거
- 중복 import 정리
- 사용하지 않는 함수 제거

---

## 📋 체크리스트

### 오늘 (Phase 1)
- [ ] `supervisor/response_prompts.py` 삭제
- [ ] `agents/placeholder_agents.py` 삭제
- [ ] `sub_agents/` 디렉토리 삭제
- [ ] git commit: "chore: Remove unused and empty files"

### 이번 주 (Phase 2)
- [ ] `diet_agent_v2.py` 테스트 작성
- [ ] `diet_agent_v2.py` 작동 확인
- [ ] `agents/diet/__init__.py` import 수정
- [ ] 구버전 diet agent 파일 삭제
- [ ] 통합 테스트 실행
- [ ] git commit: "refactor: Consolidate diet agent to v2 only"

### 이번 달 (Phase 3)
- [ ] WorkoutAgentV2 구현
- [ ] ScheduleAgentV2 구현
- [ ] MemberCareAgentV2 구현
- [ ] CoachingAgentV2 구현
- [ ] 각 Agent 테스트
- [ ] Legacy agent 파일들 삭제
- [ ] git commit: "feat: Complete agent migration to BaseAgent"

---

## 🎯 최종 목표

### Before Cleanup:
```
- 총 코드: 9,460 lines
- 중복/불필요: ~1,000 lines
- 파일 수: 45+ files
```

### After Cleanup:
```
- 총 코드: ~8,460 lines (11% 감소)
- 모든 코드 활성화
- 명확한 구조
- BaseAgent 기반 통일된 아키텍처
```

---

## ⚠️ 주의사항

1. **백업 필수**: 삭제 전 반드시 백업
   ```bash
   cp -r backend/app/octostrator backend/app/octostrator_backup_$(date +%Y%m%d)
   ```

2. **테스트 우선**: 각 Phase 후 반드시 테스트
   ```bash
   pytest backend/tests/test_octostrator.py
   ```

3. **단계별 진행**: Phase를 건너뛰지 말 것

4. **Import 확인**: 삭제 전 해당 파일을 import하는 곳 확인
   ```bash
   grep -r "from .agent import" backend/
   ```

---

## 📈 진행 상황 추적

| Phase | 상태 | 시작일 | 완료일 | 삭제된 라인 |
|-------|------|--------|--------|------------|
| Phase 1 | 대기 | - | - | 188 |
| Phase 2 | 대기 | - | - | 483 |
| Phase 3 | 대기 | - | - | 337 |
| Phase 4 | 대기 | - | - | ~100 |
| **Total** | - | - | - | **~1,108** |

---

## 💡 추가 권장사항

1. **문서화**: 각 변경사항 문서화
2. **CI/CD**: 자동 테스트 파이프라인 설정
3. **코드 리뷰**: 각 Phase 완료 후 팀 리뷰
4. **성능 측정**: Cleanup 전후 성능 비교

---

**마지막 업데이트**: 2025-11-05