# HolmesNyangz System Enhancement Roadmap

**Date:** 2025-10-21
**Version:** 1.0.0
**Status:** 📋 Planning

---

## 🎯 Executive Summary

홈즈냥즈 시스템의 **핵심 기능은 대부분 구현 완료**되었습니다. 이 문서는 남은 구현 과제와 시스템 고도화 방향을 제시합니다.

**현재 상태:**
- ✅ Multi-Agent System (5 agents)
- ✅ TeamSupervisor Orchestration
- ✅ 3-Tier Hybrid Memory (93% token savings)
- ✅ LangGraph Checkpointing
- ✅ PostgreSQL + MongoDB Dual DB
- ✅ Real-time WebSocket Chat
- ✅ Session Management
- ❌ **Human-in-the-Loop (미구현)**

---

## 📋 목차

1. [미구현 기능](#미구현-기능)
2. [고도화 계획 (우선순위별)](#고도화-계획-우선순위별)
3. [Phase 1: Critical Features](#phase-1-critical-features-human-in-the-loop)
4. [Phase 2: Performance & Reliability](#phase-2-performance--reliability)
5. [Phase 3: User Experience](#phase-3-user-experience)
6. [Phase 4: Advanced Features](#phase-4-advanced-features)
7. [Timeline & Resources](#timeline--resources)

---

## ❌ 미구현 기능

### 1. Human-in-the-Loop (HITL)

**현재 상태:** 계획만 존재, 구현 안 됨

**필요성:** 🔴 Critical
- 중요 계약 결정 시 사용자 승인 필요
- 법률 리스크 최소화
- 사용자 신뢰도 향상

**구현 범위:**
```
1. 사용자 승인이 필요한 액션 정의
   - 계약서 작성/수정
   - 법률 검토 결과
   - 고액 매물 추천 (10억 이상)
   - 투자 의사결정 조언

2. Interrupt 메커니즘 (LangGraph)
   - State 중단점 설정
   - 사용자 입력 대기
   - 타임아웃 처리

3. Frontend UI
   - 승인 대기 모달
   - 승인/거부 버튼
   - 승인 이력 표시

4. Backend API
   - POST /api/v1/chat/approve
   - POST /api/v1/chat/reject
   - GET /api/v1/chat/pending-approvals
```

**예상 구현 시간:** 2-3일

---

## 🚀 고도화 계획 (우선순위별)

### Priority Matrix

| Feature | Impact | Effort | Priority | Status |
|---------|--------|--------|----------|--------|
| **Human-in-the-Loop** | 🔴 High | Medium | **P0** | ❌ Not Started |
| Error Handling & Retry | 🔴 High | Low | **P0** | ⚠️ Partial |
| Monitoring & Logging | 🟡 Medium | Low | **P1** | ⚠️ Partial |
| Rate Limiting | 🟡 Medium | Low | **P1** | ❌ Not Started |
| Caching Layer | 🟢 Low | Medium | **P2** | ❌ Not Started |
| Multi-User Support | 🟡 Medium | High | **P2** | ⚠️ Basic |
| Voice Input/Output | 🟢 Low | High | **P3** | ❌ Not Started |
| Mobile App | 🟢 Low | Very High | **P3** | ❌ Not Started |

---

## 🔴 Phase 1: Critical Features (Human-in-the-Loop)

**목표:** 사용자 안전성 및 신뢰도 확보

**기간:** 1주 (5 working days)

### Task 1.1: LangGraph Interrupt Implementation

**파일:**
- `backend/app/service_agent/supervisor/team_supervisor.py`
- `backend/app/service_agent/foundation/separated_states.py`

**구현:**
```python
# separated_states.py
class MainSupervisorState(TypedDict):
    # ... existing fields ...
    pending_approval: Optional[Dict[str, Any]]  # 승인 대기 중인 액션
    approval_timeout: Optional[datetime]        # 타임아웃 시간
    approval_status: Optional[str]              # "pending" | "approved" | "rejected"

# team_supervisor.py
def require_approval_node(state: MainSupervisorState) -> MainSupervisorState:
    """
    사용자 승인이 필요한 액션 처리

    LangGraph interrupt()를 사용하여 워크플로우 중단
    """
    action = state["next_action"]

    # 승인 필요 여부 판단
    if requires_user_approval(action):
        state["pending_approval"] = {
            "action": action,
            "reason": get_approval_reason(action),
            "timestamp": datetime.now().isoformat()
        }
        state["approval_status"] = "pending"

        # LangGraph interrupt - 사용자 입력 대기
        raise NodeInterrupt(f"Waiting for user approval: {action['type']}")

    return state
```

**Timeline:**
- Day 1: LangGraph interrupt 구현 및 테스트
- Day 2: Backend API 구현

---

### Task 1.2: Frontend Approval UI

**파일:**
- `frontend/src/components/chat/ApprovalModal.tsx` (신규)
- `frontend/src/components/chat/ChatInterface.tsx` (수정)
- `frontend/src/hooks/use-approval.ts` (신규)

**구현:**
```typescript
// ApprovalModal.tsx
interface ApprovalModalProps {
  action: {
    type: string;
    description: string;
    details: any;
  };
  onApprove: () => void;
  onReject: () => void;
}

const ApprovalModal: React.FC<ApprovalModalProps> = ({
  action,
  onApprove,
  onReject
}) => {
  return (
    <Modal>
      <ModalHeader>승인 요청</ModalHeader>
      <ModalBody>
        <Alert variant="warning">
          다음 작업을 실행하려면 승인이 필요합니다:
        </Alert>

        <ActionDetails action={action} />

        <ApprovalButtons>
          <Button onClick={onApprove} variant="primary">
            승인하기
          </Button>
          <Button onClick={onReject} variant="secondary">
            거부하기
          </Button>
        </ApprovalButtons>
      </ModalBody>
    </Modal>
  );
};
```

**Timeline:**
- Day 3: UI 컴포넌트 구현
- Day 4: WebSocket integration
- Day 5: E2E 테스트

---

### Task 1.3: Approval Types Configuration

**파일:**
- `backend/app/core/approval_config.py` (신규)

**구현:**
```python
from enum import Enum
from typing import Callable, Dict

class ApprovalType(Enum):
    CONTRACT_CREATION = "contract_creation"
    CONTRACT_MODIFICATION = "contract_modification"
    LEGAL_REVIEW = "legal_review"
    HIGH_VALUE_RECOMMENDATION = "high_value_recommendation"  # 10억 이상
    INVESTMENT_ADVICE = "investment_advice"

# 승인 필요 여부 판단 규칙
APPROVAL_RULES: Dict[str, Callable] = {
    "contract": lambda action: True,  # 계약 관련은 항상 승인
    "legal": lambda action: True,     # 법률 관련은 항상 승인
    "recommendation": lambda action: (
        action.get("price", 0) >= 1_000_000_000  # 10억 이상
    ),
    "investment": lambda action: (
        action.get("amount", 0) >= 500_000_000   # 5억 이상
    ),
}

def requires_user_approval(action: Dict) -> bool:
    """액션이 사용자 승인을 필요로 하는지 판단"""
    action_type = action.get("type", "")

    for key, rule_func in APPROVAL_RULES.items():
        if key in action_type.lower():
            return rule_func(action)

    return False
```

**Timeline:**
- Day 1: 설정 파일 작성 및 테스트

---

## 🟡 Phase 2: Performance & Reliability

**목표:** 시스템 안정성 및 성능 개선

**기간:** 2주 (10 working days)

### 2.1 Error Handling & Retry Logic

**현재 문제:**
- LLM API 실패 시 전체 워크플로우 중단
- 네트워크 일시 오류에 취약
- 에러 로깅 불충분

**개선 사항:**
```python
# backend/app/service_agent/llm_manager/llm_service.py
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate_response(self, prompt: str) -> str:
        """
        Retry logic:
        - Attempt 1: immediate
        - Attempt 2: wait 2s
        - Attempt 3: wait 4s
        - Failure: raise exception
        """
        try:
            response = await self.client.chat.completions.create(...)
            return response.choices[0].message.content
        except RateLimitError as e:
            logger.warning(f"Rate limit hit, retrying... {e}")
            raise  # Trigger retry
        except APIError as e:
            logger.error(f"API error: {e}")
            raise
```

**Benefits:**
- 99.9% uptime (vs 95% 현재)
- 사용자 경험 개선
- 비용 절감 (불필요한 재시작 방지)

**Timeline:** 3 days

---

### 2.2 Monitoring & Observability

**구현:**

1. **Prometheus Metrics**
```python
# backend/app/core/metrics.py
from prometheus_client import Counter, Histogram

# Metrics
llm_requests = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['model', 'agent', 'status']
)

llm_latency = Histogram(
    'llm_latency_seconds',
    'LLM API latency',
    ['model', 'agent']
)

memory_tokens = Histogram(
    'memory_tokens_used',
    'Tokens used for memory loading',
    ['tier']  # shortterm, midterm, longterm
)
```

2. **Grafana Dashboard**
- LLM API 호출 통계
- 응답 시간 추이
- 메모리 사용량
- 에러율

3. **Alerting**
- 에러율 > 5%: Slack 알림
- 응답 시간 > 30s: Email 알림
- 토큰 사용량 급증: PagerDuty

**Timeline:** 5 days

---

### 2.3 Rate Limiting

**현재 문제:**
- 무제한 요청 가능
- DDoS 공격에 취약
- API 비용 폭증 위험

**구현:**
```python
# backend/app/middleware/rate_limiter.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# API routes
@router.post("/chat/query")
@limiter.limit("10/minute")  # 분당 10 요청
async def process_query(...):
    ...

@router.post("/chat/start")
@limiter.limit("5/minute")   # 분당 5 세션 생성
async def start_session(...):
    ...
```

**Rate Limits:**
- 일반 사용자: 10 req/min
- 프리미엄 사용자: 30 req/min
- Enterprise: 100 req/min

**Timeline:** 2 days

---

## 🟢 Phase 3: User Experience

**목표:** 사용자 편의성 향상

**기간:** 2주 (10 working days)

### 3.1 Caching Layer (Redis)

**현재 문제:**
- 동일한 질문에 매번 LLM 호출
- 부동산 시세 데이터 매번 DB 조회
- 응답 시간 느림

**구현:**
```python
# backend/app/cache/redis_cache.py
import redis.asyncio as redis
from functools import wraps

class CacheService:
    def __init__(self):
        self.redis = redis.from_url("redis://localhost:6379")

    async def cache_response(
        self,
        key: str,
        value: str,
        ttl: int = 3600  # 1 hour
    ):
        await self.redis.setex(key, ttl, value)

    async def get_cached(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

# Usage
@cache_llm_response(ttl=3600)
async def generate_response(prompt: str) -> str:
    # Cache key: hash(prompt + model + temperature)
    ...
```

**Cache Strategy:**
- LLM responses: 1 hour TTL
- 부동산 시세: 1 day TTL
- 메모리 요약: 7 days TTL

**Benefits:**
- 응답 시간 50% 단축
- LLM 비용 30% 절감
- DB 부하 감소

**Timeline:** 4 days

---

### 3.2 Multi-User Support Enhancement

**현재 상태:**
- user_id=1 하드코딩
- 인증/인가 없음
- 세션 충돌 가능

**개선:**
```python
# backend/app/auth/jwt_handler.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> User:
    """JWT 토큰에서 사용자 정보 추출"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
        return await get_user(user_id)
    except JWTError:
        raise HTTPException(status_code=401)

# API routes
@router.post("/chat/start")
async def start_session(
    current_user: User = Depends(get_current_user)
):
    session_id = await create_session(user_id=current_user.id)
    ...
```

**Features:**
- JWT 기반 인증
- 사용자별 세션 격리
- 권한 기반 접근 제어

**Timeline:** 3 days

---

### 3.3 Conversation History Export

**구현:**
```python
@router.get("/chat/{session_id}/export")
async def export_conversation(
    session_id: str,
    format: str = "pdf"  # pdf, txt, json
):
    """대화 내용 내보내기"""
    messages = await get_messages(session_id)

    if format == "pdf":
        return generate_pdf(messages)
    elif format == "txt":
        return generate_txt(messages)
    else:  # json
        return JSONResponse(messages)
```

**Formats:**
- PDF: 보고서 형태
- TXT: Plain text
- JSON: 개발자용

**Timeline:** 2 days

---

### 3.4 Voice Input/Output (Optional)

**구현:**
```typescript
// frontend/src/hooks/use-voice-input.ts
const useVoiceInput = () => {
  const recognition = new webkitSpeechRecognition();

  const startListening = () => {
    recognition.start();
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      sendMessage(transcript);
    };
  };

  return { startListening };
};

// Text-to-Speech
const useTTS = () => {
  const speak = (text: string) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ko-KR';
    speechSynthesis.speak(utterance);
  };

  return { speak };
};
```

**Timeline:** 1 day (using browser APIs)

---

## 🔵 Phase 4: Advanced Features

**목표:** 차별화된 기능 추가

**기간:** 4주 (20 working days)

### 4.1 Proactive Recommendations

**현재:** 사용자 질문에만 반응

**개선:** 능동적 추천
```python
# backend/app/service_agent/proactive/recommendation_engine.py
class ProactiveRecommendationEngine:
    async def analyze_user_preferences(self, user_id: int):
        """
        사용자 대화 기록 분석
        - 선호 지역
        - 가격대
        - 매물 유형 (전세/월세/매매)
        - 필수 조건 (학군, 교통, 편의시설)
        """
        ...

    async def find_matching_properties(self, preferences: Dict):
        """매칭되는 신규 매물 발견"""
        ...

    async def send_push_notification(self, user_id: int, property: Dict):
        """푸시 알림 발송"""
        ...
```

**Features:**
- 일일 매물 추천
- 가격 변동 알림
- 유사 매물 발견 시 알림

**Timeline:** 10 days

---

### 4.2 Market Trend Analysis

**구현:**
```python
# backend/app/analytics/market_analyzer.py
class MarketTrendAnalyzer:
    async def analyze_price_trends(
        self,
        region: str,
        period: int = 90  # days
    ) -> Dict:
        """
        지역별 시세 추이 분석
        - 평균 가격 변화율
        - 거래량 변화
        - HOT/COLD 지역 분류
        """
        ...

    async def predict_future_prices(self, region: str) -> Dict:
        """
        ML 기반 가격 예측 (선택사항)
        - Linear Regression
        - Prophet (Facebook)
        """
        ...
```

**Output:**
- 시각화 차트 (Chart.js)
- 트렌드 리포트
- 투자 추천 지역

**Timeline:** 10 days

---

### 4.3 Mobile App (Optional)

**Technology Stack:**
- React Native
- Expo
- Shared API with web

**Timeline:** 4 weeks (별도 프로젝트)

---

## 📅 Timeline & Resources

### Overall Timeline

```
Week 1-2:   Phase 1 (HITL)                    [P0 - Critical]
Week 3-4:   Phase 2 (Performance)             [P0-P1 - High]
Week 5-6:   Phase 3 (UX)                      [P1-P2 - Medium]
Week 7-10:  Phase 4 (Advanced)                [P2-P3 - Low]
```

### Gantt Chart

```
Phase 1: HITL
├─ Week 1: Backend (LangGraph interrupt, API)
└─ Week 2: Frontend (UI, WebSocket)

Phase 2: Performance
├─ Week 3: Error handling, Retry, Rate limiting
└─ Week 4: Monitoring, Metrics, Alerting

Phase 3: UX
├─ Week 5: Caching, Auth enhancement
└─ Week 6: Export, Voice (optional)

Phase 4: Advanced
├─ Week 7-8: Proactive recommendations
└─ Week 9-10: Market analysis
```

### Resource Requirements

| Phase | Developer | Days | Cost (만원) |
|-------|-----------|------|-------------|
| Phase 1 | 1 FE + 1 BE | 10 | 200 |
| Phase 2 | 1 BE + 1 DevOps | 10 | 200 |
| Phase 3 | 1 FE + 1 BE | 10 | 200 |
| Phase 4 | 1 BE + 1 DA | 20 | 400 |
| **Total** | **2-3 people** | **50** | **1,000** |

---

## 🎯 Success Metrics

### Phase 1 (HITL)
- ✅ 승인 요청 정확도 > 95%
- ✅ 승인 UI 응답 시간 < 1s
- ✅ 타임아웃 처리 정상 작동

### Phase 2 (Performance)
- ✅ Uptime > 99.9%
- ✅ P95 응답 시간 < 5s
- ✅ 에러율 < 1%

### Phase 3 (UX)
- ✅ Cache hit rate > 40%
- ✅ 응답 시간 50% 단축
- ✅ 다중 사용자 동시 접속 지원

### Phase 4 (Advanced)
- ✅ 일일 활성 사용자 > 100명
- ✅ 추천 정확도 > 80%
- ✅ 사용자 만족도 > 4.5/5.0

---

## 🚨 Risk Assessment

### High Risk

1. **LangGraph Interrupt 미지원**
   - Risk: LangGraph가 interrupt를 예상대로 지원하지 않을 수 있음
   - Mitigation: 초기 PoC 테스트 (1 day)

2. **복잡한 Approval Logic**
   - Risk: 승인 규칙이 복잡해져 유지보수 어려움
   - Mitigation: Rule engine 사용 (Drools, Easy Rules)

### Medium Risk

3. **성능 저하**
   - Risk: 추가 기능으로 인한 응답 시간 증가
   - Mitigation: 벤치마크 테스트, 캐싱

4. **비용 증가**
   - Risk: Redis, Monitoring 추가 비용
   - Mitigation: Cloud free tier 활용 (Redis Labs, DataDog)

---

## 📝 Next Steps

### Immediate Actions (This Week)

1. **HITL PoC 테스트**
   ```bash
   # LangGraph interrupt 테스트
   cd backend
   python scripts/test_interrupt.py
   ```

2. **기술 스택 검증**
   - LangGraph 0.2.x interrupt 기능 확인
   - Redis AsyncIO 호환성 테스트

3. **리소스 할당**
   - Frontend developer: 1명
   - Backend developer: 1명
   - DevOps (Part-time): 0.5명

### Decision Points

**Go/No-Go Criteria:**
- [ ] LangGraph interrupt 기술 검증 완료
- [ ] 예산 승인 (1,000만원)
- [ ] 개발 리소스 확보

---

## 📚 References

### Documentation
- [LangGraph Interrupt Documentation](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [HITL Design Pattern](https://www.patterns.dev/posts/human-in-the-loop)

### Related Reports
- `reports/execute_node_implemention/ADVANCED_EXECUTE_ANALYSIS_251020.md`: Execute node 분석
- `reports/long_term_memory/IMPLEMENTATION_COMPLETE_251021.md`: 3-Tier Memory 완료
- `reports/Manual/ARCHITECTURE_OVERVIEW.md`: 시스템 아키텍처

### External Resources
- [LangChain HITL Examples](https://python.langchain.com/docs/langgraph/how-tos/human_in_the_loop)
- [FastAPI Rate Limiting](https://github.com/laurentS/slowapi)

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-21 | Initial roadmap |

---

**Last Updated:** 2025-10-21
**Author:** HolmesNyangz Team
**Status:** 📋 Planning Phase
**Next Review:** 2025-10-28

---

## Appendix A: Current System Status

### ✅ Implemented Features

1. **Multi-Agent System**
   - TeamSupervisor
   - PlanningAgent
   - RealEstateSearchAgent
   - LegalAgent
   - TransactionAgent
   - AnalysisAgent

2. **3-Tier Hybrid Memory**
   - Short-term: Full messages
   - Mid-term: LLM summaries
   - Long-term: LLM summaries
   - 93% token savings

3. **Database**
   - PostgreSQL: Sessions, Messages, Users
   - MongoDB: Real estate data
   - LangGraph Checkpoints

4. **Frontend**
   - React + TypeScript
   - Real-time WebSocket
   - Session management
   - Message history

### ❌ Missing Features

1. **Human-in-the-Loop** (P0)
2. **Error Handling** (Partial)
3. **Monitoring** (Partial)
4. **Rate Limiting** (None)
5. **Caching** (None)
6. **Multi-User Auth** (Basic only)

---

**End of Document**
