# Context API 활용 로드맵

**프로젝트**: AI PT Manager - Context API 확장 계획
**작성일**: 2025-11-06
**버전**: 1.0
**상태**: 📋 PLANNING

---

## 📋 Executive Summary

### 현재 상태 (Phase 2)
- ✅ Context API 인프라 구축 완료
- ✅ 환경별 LLM 설정 자동 전환 (Production/Development/Testing)
- ✅ 45.9% 비용 절감 달성
- ✅ Backward compatibility 유지

### 미활용 잠재력
현재 `AppContext`에 정의되어 있지만 **활용하지 않는** 필드들:
- `user_id`: 사용자 식별자 (정의만 됨)
- `session_id`: 세션 식별자 (정의만 됨)
- `debug`: 디버그 플래그 (정의만 됨)
- `db_conn`: DB 연결 정보 (Phase 5 예정)

### 목표
이 로드맵은 Context API의 추가 활용 방안을 단계적으로 구현하여:
- 📈 개발 생산성 향상
- 🔍 운영 가시성 확보
- 💰 추가 비용 절감
- 🎯 사용자 경험 개선

---

## 🎯 Phase별 목표 및 로드맵

### Phase 2 (완료) ✅
**목표**: 환경별 LLM 설정 자동 전환
**기간**: 완료
**성과**: 45.9% 비용 절감

**주요 기능**:
- ✅ 환경별 preset (Production/Development/Testing)
- ✅ `.env` 파일 1줄로 전환
- ✅ 18개 테스트 100% 통과

---

### Phase 3: 개발 생산성 & 운영 가시성 (권장)
**목표**: 디버그 모드 + 모니터링 + 사용자별 설정
**예상 기간**: 2-3일
**예상 변경량**: ~90 lines
**우선순위**: **P1 (높음)**

#### 3.1 디버그 모드 구현
**문제**: 개발 환경에서 문제 발생 시 진단 어려움
**해결**: Context API를 통한 동적 디버그 모드

**구현 내용**:
```python
@dataclass
class AppContext:
    # ...
    debug: bool = False  # ← 이미 정의됨!
    log_level: str = "INFO"
```

**활용 방법**:
- API 헤더 `X-Debug-Mode: true`로 활성화
- 개발 환경: 상세 로깅
- Production: 최소 로깅

**예상 효과**:
- ✅ 문제 진단 시간 50% 단축
- ✅ Production 로그 노이즈 감소
- ✅ 개발자 생산성 향상

**변경량**: ~20 lines

#### 3.2 모니터링 및 추적 (Observability)
**문제**: 성능 병목 지점 파악 어려움, 비용 추적 불가
**해결**: Context API를 통한 분산 추적 (Distributed Tracing)

**구현 내용**:
```python
@dataclass
class AppContext:
    # ...
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metrics: Dict[str, Any] = field(default_factory=dict)
```

**수집 메트릭**:
- 노드별 실행 시간
- Agent별 실행 시간
- 토큰 사용량
- 예상 비용

**예상 효과**:
- ✅ 병목 지점 파악
- ✅ 사용자별 사용 패턴 분석
- ✅ 비용 추적 및 최적화

**변경량**: ~40 lines

#### 3.3 사용자별 맞춤 설정
**문제**: 모든 사용자가 동일한 서비스 수준
**해결**: `user_id`를 활용한 사용자 등급별 차별화

**구현 내용**:
```python
def _create_llm_for_agents(runtime: Runtime) -> ChatOpenAI:
    context: AppContext = runtime.context

    # 사용자 등급별 설정
    if context.user_id.startswith("premium_"):
        model = "gpt-4o"
        max_tokens = 8000
    elif context.user_id.startswith("trial_"):
        model = "gpt-4o-mini"
        max_tokens = 2000
    else:
        model = context.llm_settings.agent_model
        max_tokens = context.llm_settings.agent_max_tokens

    return ChatOpenAI(model=model, max_tokens=max_tokens)
```

**사용자 등급**:
- **Premium**: GPT-4, 8000 tokens
- **Standard**: gpt-4o-mini, 5000 tokens (기본)
- **Trial**: gpt-4o-mini, 2000 tokens (제한)

**예상 효과**:
- ✅ 수익성 향상 (등급별 차별화)
- ✅ 추가 비용 절감 (체험 사용자 제한)
- ✅ 개인화된 사용자 경험

**변경량**: ~30 lines

**Phase 3 총 변경량**: ~90 lines
**Phase 3 총 소요 기간**: 2-3일

---

### Phase 4: 성능 최적화 (선택)
**목표**: Rate Limiting + 캐싱
**예상 기간**: 3-5일
**예상 변경량**: ~120 lines
**우선순위**: **P2 (중간)**

#### 4.1 Rate Limiting (남용 방지)
**문제**: 무제한 요청으로 비용 폭증 위험
**해결**: `session_id`를 활용한 세션별 Rate Limiting

**구현 내용**:
```python
@dataclass
class AppContext:
    # ...
    session_id: str  # ← 이미 정의됨!
    rate_limit: int = 100  # 세션당 최대 요청 수/시간
```

**Rate Limit 정책**:
- Premium: 1000 req/hour
- Standard: 100 req/hour
- Trial: 20 req/hour

**저장소**: Redis (실시간 카운터)

**예상 효과**:
- ✅ 남용 방지
- ✅ 비용 폭증 방지
- ✅ 공정한 리소스 분배

**변경량**: ~60 lines

#### 4.2 캐싱 전략 (중복 제거)
**문제**: 동일한 요청 반복 → 비용 낭비
**해결**: Context API를 통한 캐싱 제어

**구현 내용**:
```python
@dataclass
class AppContext:
    # ...
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1시간
```

**캐싱 대상**:
- Cognitive 노드 (의도 파악)
- Planning 노드 (계획 수립)

**저장소**: Redis (TTL 기반)

**예상 효과**:
- ✅ 중복 요청 제거 (20-30%)
- ✅ 응답 속도 향상 (90% 감소)
- ✅ 추가 비용 절감 (15-20%)

**변경량**: ~60 lines

**Phase 4 총 변경량**: ~120 lines
**Phase 4 총 소요 기간**: 3-5일

---

### Phase 5: DB 통합 (예정)
**목표**: DB 연결 공유 + 트랜잭션 관리
**예상 기간**: 3-5일
**예상 변경량**: ~100 lines
**우선순위**: **P1 (높음)**

#### 5.1 DB 연결 공유
**문제**: 노드마다 DB 연결 생성 → 연결 고갈
**해결**: `db_conn`을 활용한 연결 재사용

**구현 내용**:
```python
@dataclass
class AppContext:
    # ...
    db_conn: Optional[str] = None  # ← 이미 정의됨!
    db_session: Optional[Any] = None
```

**예상 효과**:
- ✅ DB 연결 재사용 (connection pooling)
- ✅ 트랜잭션 관리 용이
- ✅ 성능 향상

**변경량**: ~50 lines

#### 5.2 트랜잭션 관리
**문제**: 여러 노드의 DB 작업이 원자적이지 않음
**해결**: Graph 단위 트랜잭션

**구현 내용**:
- Graph 시작 시: 트랜잭션 시작
- 모든 노드 성공: 커밋
- 하나라도 실패: 롤백

**예상 효과**:
- ✅ 데이터 일관성 보장
- ✅ 장애 복구 용이

**변경량**: ~50 lines

**Phase 5 총 변경량**: ~100 lines
**Phase 5 총 소요 기간**: 3-5일

---

### Phase 6+: 고급 기능 (선택)
**우선순위**: **P3 (낮음)** - 비즈니스 요구 시 구현

#### 6.1 권한 관리 (Authorization)
**목표**: 역할 기반 Agent 접근 제어
**예상 기간**: 5-7일
**예상 변경량**: ~150 lines

**구현 내용**:
```python
@dataclass
class AppContext:
    user_role: UserRole = UserRole.USER
    permissions: List[str] = None
```

**역할**:
- Admin: 모든 Agent 접근 가능
- User: 대부분 Agent 접근 가능
- Guest: 제한된 Agent만

#### 6.2 A/B 테스트
**목표**: 데이터 기반 최적화
**예상 기간**: 5-7일
**예상 변경량**: ~120 lines

**구현 내용**:
```python
@dataclass
class AppContext:
    experiment_group: ExperimentGroup = ExperimentGroup.CONTROL
    experiment_id: Optional[str] = None
```

**그룹**:
- Control: 기본 설정
- Variant A: 높은 temperature
- Variant B: 낮은 temperature

#### 6.3 Human-in-the-Loop (HITL)
**목표**: 중요 결정에 사람 검토
**예상 기간**: 7-10일
**예상 변경량**: ~180 lines

**구현 내용**:
```python
@dataclass
class AppContext:
    require_approval: bool = False
    approval_webhook: Optional[str] = None
```

#### 6.4 Multi-Tenancy
**목표**: 조직별 격리 (SaaS 비즈니스 모델)
**예상 기간**: 10-14일
**예상 변경량**: ~250 lines

**구현 내용**:
```python
@dataclass
class AppContext:
    organization_id: str
    tenant_settings: Dict[str, Any] = None
```

---

## 📊 Phase별 비교 매트릭스

| Phase | 목표 | 구현 난이도 | 비즈니스 가치 | 변경량 | 소요 기간 | 우선순위 |
|-------|------|-----------|-------------|-------|---------|---------|
| Phase 2 | 환경별 LLM 설정 | 낮음 | 높음 | 27 lines | 완료 | P0 (완료) |
| **Phase 3** | **개발 생산성 + 모니터링** | **낮음** | **높음** | **90 lines** | **2-3일** | **P1 (권장)** |
| Phase 4 | Rate Limiting + 캐싱 | 중간 | 중간 | 120 lines | 3-5일 | P2 (선택) |
| Phase 5 | DB 통합 | 중간 | 높음 | 100 lines | 3-5일 | P1 (예정) |
| Phase 6.1 | 권한 관리 | 높음 | 중간 | 150 lines | 5-7일 | P3 (선택) |
| Phase 6.2 | A/B 테스트 | 높음 | 중간 | 120 lines | 5-7일 | P3 (선택) |
| Phase 6.3 | HITL | 높음 | 낮음 | 180 lines | 7-10일 | P3 (선택) |
| Phase 6.4 | Multi-Tenancy | 높음 | 높음* | 250 lines | 10-14일 | P3 (선택) |

*Multi-Tenancy는 SaaS 비즈니스 모델 시 높은 가치

---

## 📈 예상 효과 분석

### Phase 3 구현 시 (권장)

**개발 생산성**:
- ✅ 디버그 시간 50% 단축
- ✅ 문제 진단 시간 70% 단축
- ✅ 개발자 만족도 향상

**운영 가시성**:
- ✅ 병목 지점 파악 가능
- ✅ 사용자별 사용 패턴 분석
- ✅ 실시간 비용 추적

**비즈니스 가치**:
- ✅ 사용자 등급별 차별화
- ✅ 추가 비용 절감 (10-15%)
- ✅ 수익성 향상

**투자 대비 효과**:
- 투자: 2-3일 개발 시간
- 효과: 지속적인 생산성 향상 + 운영 개선
- ROI: **매우 높음**

### Phase 4 구현 시 (선택)

**비용 절감**:
- ✅ Rate Limiting: 남용 방지
- ✅ 캐싱: 15-20% 추가 절감
- ✅ 총 절감: Phase 2 (45.9%) + Phase 4 (15-20%) = **60% 이상**

**성능 향상**:
- ✅ 응답 속도 90% 감소 (캐싱 히트 시)
- ✅ 중복 요청 제거

**투자 대비 효과**:
- 투자: 3-5일 개발 시간
- 효과: 15-20% 추가 비용 절감
- ROI: **높음**

### Phase 5 구현 시 (예정)

**안정성**:
- ✅ 데이터 일관성 보장
- ✅ 트랜잭션 관리
- ✅ 장애 복구 용이

**성능**:
- ✅ DB 연결 재사용
- ✅ 쿼리 성능 향상

**투자 대비 효과**:
- 투자: 3-5일 개발 시간
- 효과: 시스템 안정성 + 성능 향상
- ROI: **높음**

---

## 🎯 권장 구현 순서

### 우선순위 기반 순서 (권장)

1. **Phase 3** (2-3일) - 개발 생산성 & 운영 가시성
   - 즉각적인 개발 생산성 향상
   - 운영 모니터링 인프라 구축
   - 사용자 등급별 차별화

2. **Phase 5** (3-5일) - DB 통합
   - 시스템 안정성 확보
   - 트랜잭션 관리

3. **Phase 4** (3-5일) - 성능 최적화 (필요 시)
   - 추가 비용 절감 필요 시
   - 사용량 증가 시

4. **Phase 6+** - 고급 기능 (비즈니스 요구 시)
   - 권한 관리: 보안 강화 필요 시
   - A/B 테스트: 최적화 필요 시
   - HITL: 중요 결정 검토 필요 시
   - Multi-Tenancy: SaaS 비즈니스 전환 시

### 비용 대비 가치 기준 순서

| 순위 | Phase | 이유 | ROI |
|-----|-------|------|-----|
| 1 | Phase 3 | 최소 투자, 최대 생산성 향상 | ⭐⭐⭐⭐⭐ |
| 2 | Phase 5 | 시스템 안정성, DB 필수 | ⭐⭐⭐⭐⭐ |
| 3 | Phase 4 | 추가 비용 절감, 성능 향상 | ⭐⭐⭐⭐ |
| 4 | Phase 6.1 | 보안 강화 (필요 시) | ⭐⭐⭐ |
| 5 | Phase 6.2 | 데이터 기반 최적화 (선택) | ⭐⭐⭐ |
| 6 | Phase 6.4 | SaaS 비즈니스 (선택) | ⭐⭐⭐⭐* |
| 7 | Phase 6.3 | HITL (선택) | ⭐⭐ |

*SaaS 비즈니스 모델 시 매우 높음

---

## 🚀 Quick Start: Phase 3 구현

Phase 3는 **최소 투자로 최대 효과**를 얻을 수 있는 단계입니다.

### Phase 3 구현 순서 (2-3일)

#### Day 1: 디버그 모드 + 모니터링 인프라
- ✅ `app_context.py` 확장 (debug, trace_id, metrics 필드 활용)
- ✅ `execute_nodes.py` 수정 (디버그 모드 + 메트릭 수집)
- ✅ API 엔드포인트 수정 (헤더로 디버그 제어)
- ✅ 테스트 작성

#### Day 2: 사용자별 맞춤 설정
- ✅ `_create_llm_for_agents()` 수정 (user_id 기반 분기)
- ✅ 사용자 등급 정의 (Premium/Standard/Trial)
- ✅ 테스트 작성

#### Day 3: 통합 테스트 + 문서화
- ✅ E2E 테스트
- ✅ 성능 벤치마크
- ✅ 문서 업데이트

**예상 변경 파일**:
- `app_context.py` (~10 lines)
- `execute_nodes.py` (~40 lines)
- `octostrator_nodes.py` (~20 lines)
- `api/main.py` (~20 lines)
- `tests/test_phase3.py` (~150 lines, 신규)

**총 변경량**: ~90 lines (테스트 제외)

---

## 📝 성공 기준

### Phase 3 성공 기준

**개발 생산성**:
- [ ] 디버그 모드 API 헤더로 제어 가능
- [ ] 디버그 로그 상세도 확인
- [ ] 문제 진단 시간 50% 단축 (주관적 평가)

**모니터링**:
- [ ] trace_id로 전체 요청 추적 가능
- [ ] 노드별 실행 시간 측정
- [ ] 토큰 사용량 및 비용 추적
- [ ] 메트릭 외부 시스템 전송 (선택)

**사용자별 설정**:
- [ ] Premium 사용자 GPT-4 사용 확인
- [ ] Trial 사용자 토큰 제한 확인
- [ ] 등급별 비용 차이 측정

**테스트**:
- [ ] 10개 이상 테스트 시나리오 작성
- [ ] 100% 테스트 통과
- [ ] Backward compatibility 유지

### Phase 4 성공 기준

**Rate Limiting**:
- [ ] 세션별 요청 제한 동작
- [ ] 제한 초과 시 에러 응답
- [ ] Redis 카운터 정확성

**캐싱**:
- [ ] 동일 요청 캐싱 확인
- [ ] 캐시 히트율 측정 (목표: 20% 이상)
- [ ] 응답 속도 향상 측정

**비용 절감**:
- [ ] Phase 2 (45.9%) + Phase 4 (15-20%) = 60% 이상

### Phase 5 성공 기준

**DB 통합**:
- [ ] 모든 노드에서 동일 DB 세션 사용
- [ ] 트랜잭션 원자성 보장
- [ ] 롤백 동작 확인

---

## 🎉 예상 최종 결과

### 모든 Phase 완료 시

**비용 절감**:
- Phase 2: 45.9%
- Phase 4: 15-20%
- **총 절감: 60% 이상**

**개발 생산성**:
- 디버그 시간 50% 단축
- 문제 진단 70% 단축
- 개발자 만족도 향상

**운영 가시성**:
- 실시간 성능 모니터링
- 병목 지점 파악
- 사용자별 사용 패턴 분석

**시스템 안정성**:
- 데이터 일관성 보장
- 트랜잭션 관리
- 장애 복구 용이

**비즈니스 가치**:
- 사용자 등급별 차별화
- 수익성 향상
- 확장 가능한 아키텍처

---

## 📚 참고 문서

### Context API 관련
- [Phase 2 완료 보고서](../merge/PHASE2_CONTEXT_API_COMPLETION_REPORT_251106.md)
- [Context API 고급 활용 사례](../merge/CONTEXT_API_ADVANCED_USE_CASES.md)
- [Context API 구현 가이드](./CONTEXT_API_IMPLEMENTATION_GUIDE.md)
- [Phase 3 Quick Start](./PHASE3_QUICK_START_GUIDE.md)

### LangGraph 공식 문서
- [LangGraph Context API](https://langchain-ai.github.io/langgraph/)
- [Runtime Context 패턴](https://blog.langchain.com/building-langgraph/)
- [Context Engineering](https://blog.langchain.com/context-engineering-for-agents/)

---

## ✅ Action Items

### Immediate (Phase 3 시작 전)
- [ ] Phase 3 구현 계획서 검토
- [ ] Phase 3 매뉴얼 숙지
- [ ] 개발 환경 준비
- [ ] 팀 리뷰 및 승인

### Phase 3 Implementation
- [ ] Day 1: 디버그 모드 + 모니터링
- [ ] Day 2: 사용자별 맞춤 설정
- [ ] Day 3: 통합 테스트 + 문서화

### Post Phase 3
- [ ] Phase 3 완료 보고서 작성
- [ ] 성능 벤치마크 결과 공유
- [ ] Phase 4 진행 여부 결정

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Status**: 📋 PLANNING
**Author**: AI PT Manager Development Team

**Next Step**: [Context API 구현 가이드](./CONTEXT_API_IMPLEMENTATION_GUIDE.md) 참고하여 Phase 3 구현 시작
