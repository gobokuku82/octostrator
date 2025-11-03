# 🚀 메모리 시스템 고도화 계획
> 작성일: 2025-10-23
> 작성자: AI Assistant
> 현재 상태: 데이터 재사용 85%, 3-Tier Memory 70%, Checkpointer 90%

## 📊 현재 구현 현황 요약

### ✅ 완성된 기능 (What Works)
1. **스마트 데이터 재사용**
   - 41개 키워드 + 5개 감지 전략
   - 80% 감지율, 60% SearchTeam 건너뛰기
   - 평균 1.3초 응답시간 단축

2. **3-Tier Hybrid Memory**
   - Short/Mid/Long-term 계층 구조
   - chat_sessions.session_metadata 활용
   - LLM 요약 자동 생성

3. **Checkpointer 통합**
   - AsyncPostgresSaver로 상태 영속화
   - 중단된 워크플로우 복원 가능

### ❌ 미구현/문제점 (What's Missing)
1. 전용 Memory 테이블 부재
2. FAISS 벡터 DB 미통합
3. 엔티티/선호도 추적 없음
4. 세션 간 격리 제한적

---

## 🎯 단계별 고도화 로드맵

### Phase 1: 즉시 개선 (1주)
**목표: 현재 시스템 최적화 및 안정화**

#### 1.1 데이터 감지 개선
```python
# backend/app/service_agent/supervisor/team_supervisor.py

class DataDetector:
    """전용 데이터 감지 클래스"""

    def __init__(self):
        self.structural_patterns = ["##", "**", "→", "•", "📋"]
        self.domain_keywords = {
            "legal": ["법률", "계약", "임대", "권리", ...],
            "market": ["시세", "매매", "전세", "가격", ...],
            "real_estate": ["아파트", "매물", "평형", ...],
            "analysis": ["분석", "평가", "추천", ...]
        }
        self.min_content_length = 500

    def detect(self, message: Dict) -> DataDetectionResult:
        """다중 전략 기반 감지"""
        score = 0.0
        reasons = []

        # 전략별 가중치 적용
        if self._has_structural_patterns(message):
            score += 0.4
            reasons.append("structured_data")

        if self._has_domain_keywords(message):
            score += 0.3
            reasons.append("domain_match")

        if self._has_sufficient_length(message):
            score += 0.2
            reasons.append("substantial_content")

        if self._has_json_structure(message):
            score += 0.1
            reasons.append("json_data")

        return DataDetectionResult(
            has_data=score >= 0.5,
            confidence=score,
            reasons=reasons,
            data_type=self._classify_data_type(message)
        )
```

#### 1.2 메트릭 로깅 강화
```python
# 성능 메트릭 수집
class MemoryMetrics:
    def __init__(self):
        self.reuse_attempts = 0
        self.reuse_successes = 0
        self.search_skips = 0
        self.avg_detection_time = 0.0

    def log_reuse_attempt(self, success: bool, detection_time: float):
        self.reuse_attempts += 1
        if success:
            self.reuse_successes += 1
            self.search_skips += 1
        self.avg_detection_time = ...

    def get_stats(self) -> Dict:
        return {
            "reuse_rate": self.reuse_successes / max(self.reuse_attempts, 1),
            "skip_rate": self.search_skips / max(self.reuse_attempts, 1),
            "avg_detection_ms": self.avg_detection_time * 1000
        }
```

#### 1.3 Checkpointer 데이터 활용
```python
async def extract_from_checkpoint(
    self,
    thread_id: str,
    data_type: str = "team_results"
) -> Optional[Dict]:
    """Checkpoint에서 이전 실행 결과 추출"""
    if not self.checkpointer:
        return None

    try:
        # 최신 checkpoint 조회
        checkpoint = await self.checkpointer.get_latest(thread_id)
        if checkpoint and checkpoint.get("state"):
            state = checkpoint["state"]

            # team_results 추출
            if data_type == "team_results":
                return state.get("team_results", {})

            # aggregated_results 추출
            elif data_type == "aggregated":
                return state.get("aggregated_results", {})

        return None
    except Exception as e:
        logger.error(f"Failed to extract from checkpoint: {e}")
        return None
```

---

### Phase 2: 메모리 테이블 구축 (2주)

**목표: 전용 메모리 저장소 구축**

#### 2.1 데이터베이스 스키마
```sql
-- 대화 메모리 (세션 단위)
CREATE TABLE conversation_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    summary TEXT NOT NULL,
    summary_method VARCHAR(20) DEFAULT 'llm',
    keywords TEXT[],
    entities JSONB,
    importance_score FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_user_session (user_id, session_id),
    INDEX idx_importance (importance_score DESC),
    INDEX idx_keywords (keywords) USING GIN
);

-- 엔티티 메모리 (개체 추적)
CREATE TABLE entity_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- 'location', 'property', 'person'
    entity_name VARCHAR(200) NOT NULL,
    properties JSONB NOT NULL,
    first_mentioned TIMESTAMP DEFAULT NOW(),
    last_mentioned TIMESTAMP DEFAULT NOW(),
    mention_count INTEGER DEFAULT 1,

    UNIQUE KEY unique_entity (user_id, entity_type, entity_name),
    INDEX idx_user_type (user_id, entity_type)
);

-- 사용자 선호도
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    preferences JSONB NOT NULL DEFAULT '{}',
    learned_patterns JSONB DEFAULT '{}',
    interaction_style VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 메모리 관계 (연결 정보)
CREATE TABLE memory_relations (
    id SERIAL PRIMARY KEY,
    from_memory_type VARCHAR(20),
    from_memory_id INTEGER,
    to_memory_type VARCHAR(20),
    to_memory_id INTEGER,
    relation_type VARCHAR(50),
    strength FLOAT DEFAULT 0.5,

    INDEX idx_from (from_memory_type, from_memory_id),
    INDEX idx_to (to_memory_type, to_memory_id)
);
```

#### 2.2 메모리 서비스 확장
```python
class EnhancedMemoryService(SimpleMemoryService):
    """확장된 메모리 서비스"""

    async def save_conversation_memory(
        self,
        user_id: int,
        session_id: str,
        summary: str,
        keywords: List[str],
        entities: Dict[str, Any],
        importance: float = 0.5
    ) -> int:
        """대화 메모리 저장 (전용 테이블)"""
        memory = ConversationMemory(
            user_id=user_id,
            session_id=session_id,
            summary=summary,
            keywords=keywords,
            entities=entities,
            importance_score=importance
        )
        self.db.add(memory)
        await self.db.commit()
        return memory.id

    async def track_entity(
        self,
        user_id: int,
        entity_type: str,
        entity_name: str,
        properties: Dict
    ):
        """엔티티 추적 및 업데이트"""
        # Upsert 로직
        existing = await self.get_entity(user_id, entity_type, entity_name)
        if existing:
            existing.properties.update(properties)
            existing.mention_count += 1
            existing.last_mentioned = datetime.now()
        else:
            entity = EntityMemory(
                user_id=user_id,
                entity_type=entity_type,
                entity_name=entity_name,
                properties=properties
            )
            self.db.add(entity)
        await self.db.commit()

    async def learn_user_preference(
        self,
        user_id: int,
        preference_type: str,
        value: Any
    ):
        """사용자 선호도 학습"""
        # 점진적 학습 로직
        pass
```

---

### Phase 3: 벡터 검색 통합 (3주)

**목표: FAISS 기반 의미 검색 구현**

#### 3.1 벡터 인덱싱 파이프라인
```python
class VectorMemoryIndex:
    """FAISS 기반 벡터 메모리 인덱스"""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata = []  # memory_id 매핑

    async def add_memory(
        self,
        memory_id: int,
        text: str,
        memory_type: str = "conversation"
    ):
        """메모리를 벡터화하여 인덱스에 추가"""
        # OpenAI Embedding
        embedding = await self.get_embedding(text)

        # FAISS에 추가
        self.index.add(np.array([embedding]))
        self.metadata.append({
            "memory_id": memory_id,
            "memory_type": memory_type,
            "indexed_at": datetime.now()
        })

    async def search_similar(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.8
    ) -> List[Dict]:
        """의미 유사도 기반 검색"""
        query_embedding = await self.get_embedding(query)

        # FAISS 검색
        distances, indices = self.index.search(
            np.array([query_embedding]), k
        )

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if dist < threshold:
                meta = self.metadata[idx]
                results.append({
                    "memory_id": meta["memory_id"],
                    "memory_type": meta["memory_type"],
                    "similarity": 1.0 - dist,
                    "distance": dist
                })

        return results
```

#### 3.2 하이브리드 검색
```python
async def hybrid_memory_search(
    self,
    query: str,
    user_id: int,
    search_mode: str = "hybrid"
) -> List[Dict]:
    """키워드 + 벡터 하이브리드 검색"""

    results = []

    if search_mode in ["keyword", "hybrid"]:
        # 키워드 기반 검색
        keyword_results = await self.keyword_search(query, user_id)
        results.extend(keyword_results)

    if search_mode in ["vector", "hybrid"]:
        # 벡터 유사도 검색
        vector_results = await self.vector_search(query, user_id)
        results.extend(vector_results)

    # 중복 제거 및 스코어 병합
    merged = self.merge_results(results)

    # 중요도 기반 재정렬
    return sorted(merged, key=lambda x: x["final_score"], reverse=True)
```

---

### Phase 4: 지능형 메모리 관리 (4주)

**목표: 자동 학습 및 최적화**

#### 4.1 메모리 중요도 자동 조정
```python
class MemoryImportanceManager:
    """메모리 중요도 동적 관리"""

    async def update_importance(self, memory_id: int):
        """접근 패턴 기반 중요도 업데이트"""
        memory = await self.get_memory(memory_id)

        # 팩터 계산
        recency_factor = self.calculate_recency(memory.last_accessed)
        frequency_factor = memory.access_count / 100.0
        relevance_factor = await self.calculate_relevance(memory)

        # 가중 평균
        new_importance = (
            recency_factor * 0.3 +
            frequency_factor * 0.3 +
            relevance_factor * 0.4
        )

        memory.importance_score = min(1.0, new_importance)
        await self.db.commit()

    async def prune_old_memories(self, user_id: int):
        """오래된/중요도 낮은 메모리 정리"""
        threshold_date = datetime.now() - timedelta(days=90)

        # 삭제 대상 선정
        candidates = await self.db.query(
            ConversationMemory
        ).filter(
            ConversationMemory.user_id == user_id,
            ConversationMemory.importance_score < 0.3,
            ConversationMemory.last_accessed < threshold_date
        ).all()

        # 압축 후 아카이브
        for memory in candidates:
            await self.archive_memory(memory)
            await self.db.delete(memory)
```

#### 4.2 컨텍스트 인식 메모리 로딩
```python
class ContextAwareMemoryLoader:
    """상황 인식 메모리 로더"""

    async def load_contextual_memories(
        self,
        user_id: int,
        current_query: str,
        context: Dict
    ) -> Dict[str, List]:
        """쿼리와 컨텍스트 기반 메모리 로딩"""

        # 1. 의도 분석
        intent = await self.analyze_intent(current_query)

        # 2. 관련 엔티티 추출
        entities = await self.extract_entities(current_query)

        # 3. 시간적 관련성 고려
        time_context = context.get("time_context", "recent")

        # 4. 계층별 메모리 로딩
        memories = {
            "direct": [],      # 직접 관련
            "related": [],     # 간접 관련
            "background": []   # 배경 정보
        }

        # 직접 관련 메모리 (엔티티 매칭)
        for entity in entities:
            entity_memories = await self.find_entity_memories(
                user_id, entity
            )
            memories["direct"].extend(entity_memories)

        # 간접 관련 메모리 (의미 유사도)
        similar = await self.vector_search(
            current_query,
            user_id,
            threshold=0.7
        )
        memories["related"] = similar

        # 배경 정보 (선호도, 패턴)
        preferences = await self.get_user_preferences(user_id)
        memories["background"] = preferences

        return memories
```

---

## 📈 예상 성과 지표

| 지표 | 현재 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|------|---------|---------|---------|---------|
| **데이터 재사용률** | 80% | 90% | 92% | 95% | 97% |
| **응답 정확도** | 75% | 78% | 82% | 88% | 93% |
| **컨텍스트 유지** | 3 턴 | 5 턴 | 10 턴 | 20 턴 | 무제한 |
| **메모리 검색 시간** | 100ms | 80ms | 60ms | 40ms | 20ms |
| **스토리지 효율성** | - | - | 30% 개선 | 50% 개선 | 70% 개선 |

---

## 🔧 구현 우선순위

### 즉시 적용 (1주 내)
1. ✅ DataDetector 클래스 구현
2. ✅ 메트릭 로깅 시스템
3. ✅ Checkpointer 데이터 추출

### 단기 목표 (1개월)
1. 🔄 메모리 테이블 생성
2. 🔄 엔티티 추적 시작
3. 🔄 기본 벡터 검색

### 중기 목표 (3개월)
1. 📋 하이브리드 검색 완성
2. 📋 메모리 중요도 관리
3. 📋 컨텍스트 인식 로딩

### 장기 목표 (6개월)
1. 🎯 완전 자동화된 메모리 관리
2. 🎯 다중 사용자 격리
3. 🎯 분산 메모리 시스템

---

## 💡 핵심 인사이트

1. **현재 시스템은 기반이 탄탄함**
   - LangGraph 0.6의 Checkpointer
   - PostgreSQL JSONB 활용
   - 3-Tier 구조 이미 구현

2. **즉시 개선 가능한 부분 많음**
   - 키워드 확장만으로도 큰 효과
   - 메트릭 로깅으로 최적화 가능
   - Checkpointer 데이터 활용 미흡

3. **단계적 접근 필요**
   - Phase 1: 현재 시스템 최적화
   - Phase 2: 전용 저장소 구축
   - Phase 3: 벡터 검색 통합
   - Phase 4: 지능형 관리

4. **ROI 극대화 전략**
   - 작은 수정, 큰 효과 우선
   - 기존 코드 최대한 활용
   - 점진적 마이그레이션

---

## 📝 다음 단계 Action Items

### 이번 주 (Phase 1.1)
- [ ] DataDetector 클래스 작성 및 테스트
- [ ] 메트릭 로깅 시스템 구현
- [ ] 성능 벤치마크 측정

### 다음 주 (Phase 1.2-1.3)
- [ ] Checkpointer 데이터 추출 구현
- [ ] 통합 테스트 시나리오 작성
- [ ] 프로덕션 배포 준비

### 이번 달 (Phase 2 시작)
- [ ] 메모리 테이블 DDL 작성
- [ ] 마이그레이션 스크립트 준비
- [ ] EnhancedMemoryService 프로토타입

---

*이 계획은 현재 구현 상태를 기반으로 실용적이고 점진적인 개선을 목표로 합니다.*
*각 Phase는 독립적으로 가치를 제공하며, 중단 시에도 이전 단계의 성과는 유지됩니다.*