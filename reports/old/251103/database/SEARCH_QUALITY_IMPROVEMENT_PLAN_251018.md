# FAISS 검색 품질 개선 종합 계획서

**작성일**: 2025-10-18
**작성자**: Claude (AI Assistant)
**목적**: 법률 검색 정확도 26% → 70~85% 개선

---

## 📊 현재 상황 분석

### 1. 테스트 결과 요약

**Phase 2 테스트 (200개 질문)**:
```
전체 정확도: 25.0% (50/200)
- 카테고리 1 (공통 매매_임대차): 58% (29/50)
- 카테고리 2 (임대차_전세_월세): 38% (19/50)
- 카테고리 3 (공급_및_관리): 2% (1/50)
- 카테고리 4 (기타): 2% (1/50)

법령 검색 편향:
- 공인중개사법 시행규칙: 351회 (58.5%)
- 공인중개사법: 73회
- 주택임대차보호법: 13회만 (매우 낮음)
```

### 2. 재임베딩 시도 (18:20 → 19:12)

**수정 내용**:
- `rebuild_faiss_from_chunks.py` Line 158-198
- 문서 임베딩: `content` → `enhanced_content` (제목+장 포함)
- 예시: `"[제2장 공인중개사] 자격시험\n제4조(자격시험) ①..."`

**결과**:
- ❌ **개선 효과 없음**: 26% → 25% (오히려 1% 하락)
- ❌ 카테고리 3, 4: 4% → 2% (악화)

### 3. 근본 원인 분석

#### **발견 1: 코드가 ChromaDB 사용 중** ⭐⭐⭐ 핵심!

**파일**: `hybrid_legal_search.py`

```python
# Line 28-29: ChromaDB import
import chromadb
from chromadb.config import Settings

# Line 84-95: ChromaDB 초기화
def _init_chromadb(self):
    self.chroma_client = chromadb.PersistentClient(
        path=self.chroma_db_path,
        settings=Settings(anonymized_telemetry=False)
    )
    self.collection = self.chroma_client.get_collection(self.collection_name)

# Line 240: ChromaDB 검색
results = self.collection.query(**search_params)
```

**결론**:
- FAISS DB는 새로 만들었지만 (제목 포함)
- 코드는 아직 **ChromaDB 사용 중** (옛날 데이터)
- → FAISS 재임베딩이 전혀 적용 안 됨!

#### **발견 2: Domain Shift 문제**

**문서 임베딩**:
```
"[제2장 공인중개사] 자격시험
제4조(자격시험) ①공인중개사가 되려는 자는..."
```

**쿼리 임베딩** (`hybrid_legal_search.py` Line 229):
```python
query_embedding = self.embedding_model.encode(query)
# query = "공인중개사 자격시험에 응시할 수 있는 조건은 무엇인가요?"
```

**문제**:
- 문서: `[장] 제목\n본문` 형식
- 쿼리: `질문 그대로`
- → 임베딩 공간에서 형식 불일치 → 벡터 유사도 낮음

#### **발견 3: 실행 흐름**

```
search_executor.py (Line 501)
  ↓ query 전달
hybrid_legal_search.py search() (Line 446)
  ↓ mode='hybrid'
hybrid_legal_search.py hybrid_search() (Line 257)
  ↓
hybrid_legal_search.py vector_search() (Line 210)
  ↓ Line 229: ChromaDB 검색
self.embedding_model.encode(query)  ← 쿼리 그대로
  ↓
self.collection.query(...)  ← ChromaDB (옛날 데이터)
```

---

## 💡 해결 방안

### Phase 1: ChromaDB → FAISS 코드 전환 ⭐⭐⭐⭐⭐ (필수)

**목적**: 새로 만든 FAISS DB (제목 포함 데이터) 사용

**수정 파일**: `hybrid_legal_search.py`

#### **1-1. Import 변경**

**현재** (Line 28-30):
```python
import chromadb
from chromadb.config import Settings
```

**변경 후**:
```python
import faiss
import pickle
import numpy as np
```

#### **1-2. 초기화 메서드 변경**

**현재** (Line 45-65):
```python
def __init__(
    self,
    sqlite_db_path: Optional[str] = None,
    chroma_db_path: Optional[str] = None,
    embedding_model_path: Optional[str] = None,
    collection_name: str = "korean_legal_documents"
):
    self.chroma_db_path = chroma_db_path or str(Config.LEGAL_PATHS["chroma_db"])
    self.collection_name = collection_name

    # 초기화
    self._init_sqlite()
    self._init_chromadb()  # ← 이거
    self._init_embedding_model()
```

**변경 후**:
```python
def __init__(
    self,
    sqlite_db_path: Optional[str] = None,
    faiss_db_path: Optional[str] = None,  # ← 변경
    embedding_model_path: Optional[str] = None
):
    self.faiss_db_path = faiss_db_path or str(Config.LEGAL_PATHS["faiss_db"])

    # 초기화
    self._init_sqlite()
    self._init_faiss()  # ← 변경
    self._init_embedding_model()
```

#### **1-3. FAISS 초기화 메서드 추가**

**삭제**: `_init_chromadb()` (Line 84-95)

**추가**: `_init_faiss()`
```python
def _init_faiss(self):
    """FAISS 초기화"""
    try:
        # FAISS 인덱스 로드
        faiss_index_path = Path(self.faiss_db_path) / "legal_documents.index"
        self.faiss_index = faiss.read_index(str(faiss_index_path))

        # 메타데이터 로드
        metadata_path = Path(self.faiss_db_path) / "legal_metadata.pkl"
        with open(metadata_path, 'rb') as f:
            self.faiss_metadata = pickle.load(f)

        logger.info(f"FAISS loaded: {self.faiss_index.ntotal} vectors")
    except Exception as e:
        logger.error(f"FAISS initialization failed: {e}")
        raise
```

#### **1-4. vector_search() 메서드 변경**

**현재** (Line 210-251):
```python
def vector_search(
    self,
    query: str,
    n_results: int = 10,
    where_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    try:
        # 쿼리 임베딩
        query_embedding = self.embedding_model.encode(query, convert_to_tensor=False).tolist()

        # ChromaDB 검색
        search_params = {
            "query_embeddings": [query_embedding],
            "n_results": n_results
        }

        if where_filters:
            search_params["where"] = where_filters

        results = self.collection.query(**search_params)

        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return {"ids": [], "documents": [], "metadatas": [], "distances": []}
```

**변경 후**:
```python
def vector_search(
    self,
    query: str,
    n_results: int = 10,
    where_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    try:
        # 쿼리 임베딩
        query_embedding = self.embedding_model.encode(query, convert_to_tensor=False)
        query_embedding = query_embedding.astype('float32').reshape(1, -1)

        # FAISS 검색
        distances, indices = self.faiss_index.search(query_embedding, n_results)

        # 결과 구성
        ids = []
        documents = []
        metadatas = []
        result_distances = []

        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.faiss_metadata):
                meta = self.faiss_metadata[idx]

                # where_filters 적용
                if where_filters:
                    skip = False
                    for key, value in where_filters.items():
                        if meta.get(key) != value:
                            skip = True
                            break
                    if skip:
                        continue

                ids.append(meta.get("chunk_id", f"chunk_{idx}"))
                documents.append(meta.get("content", ""))
                metadatas.append(meta)
                result_distances.append(float(distances[0][i]))

        return {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
            "distances": result_distances
        }

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return {"ids": [], "documents": [], "metadatas": [], "distances": []}
```

#### **1-5. search_specific_article() 수정**

**현재** (Line 363-374):
```python
# ChromaDB에서 chunk 내용 조회
chunk_ids = self.get_chunk_ids_for_article(article["article_id"])

chunks = []
if chunk_ids:
    try:
        chroma_results = self.collection.get(ids=chunk_ids)
        if chroma_results and chroma_results["documents"]:
            chunks = chroma_results["documents"]
    except Exception as e:
        logger.error(f"Failed to retrieve chunks from ChromaDB: {e}")
```

**변경 후**:
```python
# FAISS에서 chunk 내용 조회
chunk_ids = self.get_chunk_ids_for_article(article["article_id"])

chunks = []
if chunk_ids:
    try:
        # FAISS 메타데이터에서 chunk_id로 검색
        for chunk_id in chunk_ids:
            for meta in self.faiss_metadata:
                if meta.get("chunk_id") == chunk_id:
                    chunks.append(meta.get("content", ""))
                    break
    except Exception as e:
        logger.error(f"Failed to retrieve chunks from FAISS: {e}")
```

#### **1-6. Config 경로 추가**

**파일**: `app/service_agent/foundation/config.py`

**추가**:
```python
LEGAL_PATHS = {
    "sqlite_db": backend_dir / "data" / "storage" / "legal_info" / "sqlite_db" / "legal_metadata.db",
    "faiss_db": backend_dir / "data" / "storage" / "legal_info" / "faiss_db",  # ← 추가
    "embedding_model": backend_dir / "app" / "ml_models" / "KURE_v1",
    # chroma_db 제거 (더 이상 사용 안 함)
}
```

**예상 효과**: 25% → 30% (FAISS 사용으로 약간 개선)

**예상 시간**: 1시간 (코드 수정 + 테스트)

---

### Phase 2: 쿼리 전처리 추가 ⭐⭐⭐⭐ (강력 권장)

**목적**: 쿼리를 문서 형식과 유사하게 변환하여 벡터 유사도 향상

**수정 파일**: `hybrid_legal_search.py`

#### **2-1. 쿼리 전처리 함수 추가**

**위치**: Line 210 앞에 추가

```python
def _enhance_query_for_search(self, query: str) -> str:
    """
    쿼리를 문서 형식과 유사하게 변환

    목적:
    - 문서 임베딩: "[장] 제목\\n본문" 형식
    - 쿼리도 유사한 형식으로 변환하여 벡터 유사도 향상

    예시:
    입력: "공인중개사 자격시험에 응시할 수 있는 조건은 무엇인가요?"
    출력: "자격시험 응시 조건\\n공인중개사 자격시험에 응시할 수 있는 조건은 무엇인가요?"

    Args:
        query: 원본 사용자 쿼리

    Returns:
        전처리된 쿼리 (제목 형식 키워드 + 원본)
    """
    try:
        # 방법 1: 간단한 키워드 추출 (LLM 없이)
        import re

        # 불필요한 부분 제거
        clean = re.sub(r'[?인가요무엇어떻게왜]', '', query)
        clean = re.sub(r'\\s+', ' ', clean).strip()

        # 명사 추출 (간단한 패턴)
        # 실제로는 KoNLPy 같은 형태소 분석기 사용 권장
        keywords = []

        # 법률 용어 추출
        legal_terms = [
            "자격시험", "응시", "조건", "전세금", "인상률", "임대차", "계약",
            "보증금", "갱신", "임차인", "임대인", "중개사", "등록",
            "금지행위", "손해배상", "계약서", "설명의무"
        ]

        for term in legal_terms:
            if term in query:
                keywords.append(term)

        # 키워드가 있으면 제목 형식으로 변환
        if keywords:
            title = " ".join(keywords[:3])  # 최대 3개
            enhanced = f"{title}\\n{query}"
            return enhanced

        # 키워드 없으면 원본 그대로
        return query

    except Exception as e:
        logger.warning(f"Query enhancement failed: {e}")
        return query
```

**고급 버전 (LLM 사용)**:
```python
def _enhance_query_with_llm(self, query: str) -> str:
    """
    LLM을 사용한 쿼리 전처리 (더 정확)

    Args:
        query: 원본 쿼리

    Returns:
        제목 형식 키워드 + 원본
    """
    try:
        # LLMService를 통한 키워드 추출
        if not hasattr(self, 'llm_service'):
            from app.service_agent.llm_manager import LLMService
            self.llm_service = LLMService()

        result = self.llm_service.complete_json(
            prompt_name="query_to_title",
            variables={"query": query},
            temperature=0.1
        )

        title = result.get("title", "")
        if title:
            return f"{title}\\n{query}"

        return query

    except Exception as e:
        logger.warning(f"LLM query enhancement failed: {e}")
        return query
```

#### **2-2. vector_search() 메서드 수정**

**현재** (Phase 1 변경 후):
```python
def vector_search(self, query: str, n_results: int = 10, ...):
    # 쿼리 임베딩
    query_embedding = self.embedding_model.encode(query, convert_to_tensor=False)
```

**변경 후**:
```python
def vector_search(self, query: str, n_results: int = 10, ...):
    # ⭐ 쿼리 전처리 추가
    enhanced_query = self._enhance_query_for_search(query)

    logger.info(f"Original query: {query}")
    logger.info(f"Enhanced query: {enhanced_query}")

    # 쿼리 임베딩
    query_embedding = self.embedding_model.encode(enhanced_query, convert_to_tensor=False)
```

**예상 효과**: 30% → 70~80% (대폭 개선!)

**예상 시간**: 30분 (함수 추가 + 테스트)

---

### Phase 3: SQLite FTS5 Hybrid 검색 ⭐⭐⭐⭐⭐ (선택)

**목적**: 키워드 검색 + 벡터 검색 결합으로 최고 성능 달성

#### **3-1. SQLite FTS5 테이블 생성**

**파일**: `backend/data/storage/legal_info/sqlite_db/schema.sql`

**추가**:
```sql
-- FTS5 가상 테이블 (전문 검색)
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    article_id UNINDEXED,
    law_title,
    article_number,
    article_title,
    content,
    content='articles',
    content_rowid='article_id'
);

-- 트리거: articles 테이블 변경 시 FTS 자동 업데이트
CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(article_id, law_title, article_number, article_title, content)
    VALUES (new.article_id,
            (SELECT title FROM laws WHERE law_id = new.law_id),
            new.article_number,
            new.article_title,
            new.content);
END;
```

#### **3-2. FTS 데이터 초기 인덱싱**

**파일**: `backend/scripts/rebuild_sqlite_fts.py` (신규 생성)

```python
"""
SQLite FTS5 인덱스 재생성
"""
import sqlite3
from pathlib import Path

backend_dir = Path(__file__).parent.parent
SQLITE_DB_PATH = backend_dir / "data" / "storage" / "legal_info" / "sqlite_db" / "legal_metadata.db"

def rebuild_fts():
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    cursor = conn.cursor()

    # 기존 FTS 테이블 삭제
    cursor.execute("DROP TABLE IF EXISTS articles_fts")

    # FTS 테이블 재생성
    cursor.execute("""
        CREATE VIRTUAL TABLE articles_fts USING fts5(
            article_id UNINDEXED,
            law_title,
            article_number,
            article_title,
            content
        )
    """)

    # 데이터 인덱싱
    cursor.execute("""
        INSERT INTO articles_fts(article_id, law_title, article_number, article_title, content)
        SELECT
            a.article_id,
            l.title,
            a.article_number,
            a.article_title,
            a.content
        FROM articles a
        JOIN laws l ON a.law_id = l.law_id
        WHERE a.is_deleted = 0
    """)

    conn.commit()
    conn.close()

    print(f"✅ FTS5 인덱싱 완료")

if __name__ == "__main__":
    rebuild_fts()
```

#### **3-3. 하이브리드 검색 메서드 추가**

**파일**: `hybrid_legal_search.py`

**추가**:
```python
def keyword_search(self, query: str, n_results: int = 30) -> List[Dict[str, Any]]:
    """
    SQLite FTS5 키워드 검색

    Args:
        query: 검색 쿼리
        n_results: 결과 개수

    Returns:
        검색 결과 리스트
    """
    try:
        cursor = self.sqlite_conn.cursor()

        cursor.execute(
            """
            SELECT
                a.article_id,
                a.law_id,
                a.article_number,
                a.article_title,
                a.content,
                l.title as law_title,
                bm25(articles_fts) as rank_score
            FROM articles_fts
            JOIN articles a ON articles_fts.article_id = a.article_id
            JOIN laws l ON a.law_id = l.law_id
            WHERE articles_fts MATCH ?
            ORDER BY rank_score DESC
            LIMIT ?
            """,
            (query, n_results)
        )

        results = []
        for row in cursor.fetchall():
            results.append({
                "article_id": row[0],
                "law_id": row[1],
                "article_number": row[2],
                "article_title": row[3],
                "content": row[4],
                "law_title": row[5],
                "keyword_score": -row[6]  # BM25 스코어 (음수이므로 반전)
            })

        return results

    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        return []


def hybrid_search_advanced(
    self,
    query: str,
    limit: int = 10,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    고급 하이브리드 검색: 키워드 + 벡터 결합

    전략:
    1. FTS5 키워드 검색 (Top 30) - BM25 스코어
    2. FAISS 벡터 검색 (Top 30) - L2 distance
    3. 두 결과를 Reciprocal Rank Fusion (RRF)으로 병합
    4. 최종 Top N 반환

    Args:
        query: 검색 쿼리
        limit: 최종 결과 개수

    Returns:
        통합 검색 결과
    """
    # 1. 키워드 검색
    keyword_results = self.keyword_search(query, n_results=30)

    # 2. 벡터 검색
    vector_results = self.vector_search(query, n_results=30)

    # 3. RRF 병합
    # RRF 공식: score = Σ 1/(k + rank)
    # k=60 (일반적인 값)
    k = 60
    scores = {}

    # 키워드 검색 스코어
    for rank, result in enumerate(keyword_results, 1):
        chunk_id = result.get("article_id")
        scores[chunk_id] = scores.get(chunk_id, 0) + 1/(k + rank)

    # 벡터 검색 스코어
    for rank, (chunk_id, meta) in enumerate(zip(vector_results["ids"], vector_results["metadatas"]), 1):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1/(k + rank)

    # 4. 스코어 정렬
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    # 5. 결과 구성
    final_results = []
    for chunk_id, score in ranked:
        # 메타데이터 조회 (SQLite)
        # ... (생략)
        final_results.append({
            "chunk_id": chunk_id,
            "rrf_score": score,
            # ... 기타 정보
        })

    return final_results
```

**예상 효과**: 70% → 85~95% (최고 성능!)

**예상 시간**: 3시간 (FTS5 설정 + RRF 구현 + 테스트)

---

## 📊 예상 개선 효과

### Phase별 성능 예측

| Phase | 정확도 | 카테고리 1 | 카테고리 2 | 카테고리 3 | 카테고리 4 | 시간 |
|-------|--------|-----------|-----------|-----------|-----------|------|
| **현재** | 25% | 58% | 38% | 2% | 2% | - |
| **Phase 1** | 30% | 60% | 40% | 5% | 5% | 1시간 |
| **Phase 1+2** | **70~80%** | **85%** | **75%** | **60%** | **55%** | 1.5시간 |
| **Phase 1+2+3** | **85~95%** | **95%** | **90%** | **80%** | **75%** | 4.5시간 |

### 검색 예시 개선 예측

**질문**: "공인중개사 자격시험에 응시할 수 있는 조건은 무엇인가요?"

**현재 (25%)**:
```
1위: 공인중개사법 시행규칙 제7조 "분사무소설치신고서의 서식" ❌
2위: 공인중개사법 시행규칙 제19조 "보증의 변경신고" ❌
3위: 부동산등기규칙 제90조 ❌
```

**Phase 1 후 (30%)**:
```
1위: 공인중개사법 시행규칙 제4조 "중개사무소 개설등록의 신청" ❌
2위: 공인중개사법 제4조 "자격시험" ✅
3위: 공인중개사법 제5조 "결격사유" ✅
```

**Phase 1+2 후 (75%)**:
```
1위: 공인중개사법 제4조 "자격시험" ✅
2위: 공인중개사법 제5조 "결격사유" ✅
3위: 공인중개사법 제6조 "자격증 교부" ✅
```

**Phase 1+2+3 후 (90%)**:
```
1위: 공인중개사법 제4조 "자격시험" ✅ (키워드+벡터 모두 매칭)
2위: 공인중개사법 시행령 제7조 "자격시험 과목" ✅
3위: 공인중개사법 시행규칙 제2조 "시험 방법" ✅
```

---

## 🎯 권장 실행 순서

### **전략 A: 빠른 개선** (권장 ⭐⭐⭐⭐⭐)

**목표**: 1.5시간 내 25% → 75% 개선

1. **Phase 1 실행** (1시간)
   - ChromaDB → FAISS 코드 전환
   - 테스트 실행
   - 결과 확인: 30% 예상

2. **Phase 2 실행** (30분)
   - 쿼리 전처리 추가
   - 테스트 실행
   - 결과 확인: 70~80% 예상

3. **완료!**
   - 카테고리 3, 4 개선 확인
   - 법령 검색 분포 균형 확인

---

### **전략 B: 최고 성능** (선택)

**목표**: 4.5시간 내 25% → 90% 개선

1. **Phase 1 + Phase 2** (1.5시간)
   - 전략 A와 동일

2. **Phase 3 실행** (3시간)
   - SQLite FTS5 설정
   - RRF Hybrid 검색
   - 테스트 실행
   - 결과 확인: 85~95% 예상

3. **완료!**
   - 프로덕션 수준 검색 품질

---

### **전략 C: 단계적 검증** (신중한 접근)

**목표**: 각 단계마다 테스트하여 효과 검증

1. **Phase 1만 먼저** (1시간)
   - ChromaDB → FAISS 전환
   - **테스트 & 분석**
   - 개선 효과 확인 (30% 예상)

2. **Phase 2 추가** (30분)
   - 쿼리 전처리
   - **테스트 & 분석**
   - 추가 개선 확인 (70~80% 예상)

3. **필요 시 Phase 3** (3시간)
   - 80% 미만이면 Phase 3 실행
   - **최종 테스트**

---

## 🚨 리스크 및 대응

### 리스크 1: Phase 1 후에도 개선 미미

**원인**:
- FAISS 데이터가 실제로는 ChromaDB와 동일
- 재임베딩이 제대로 안 됨

**대응**:
```python
# FAISS 메타데이터 확인
with open('legal_metadata.pkl', 'rb') as f:
    meta = pickle.load(f)

# 샘플 content 확인
print(meta[0]['content'][:300])
# "[제2장 공인중개사] 자격시험\\n..." 형식이어야 함
```

**해결책**:
- rebuild_faiss_from_chunks.py 재확인
- 재임베딩 다시 실행

---

### 리스크 2: Phase 2 후에도 50% 미만

**원인**:
- 쿼리 전처리 로직이 부적절
- 키워드 추출 실패

**대응**:
- LLM 기반 키워드 추출 사용
- 로그 확인: enhanced_query 출력

**해결책**:
```python
# LLM 사용 전환
def _enhance_query_for_search(self, query):
    return self._enhance_query_with_llm(query)
```

---

### 리스크 3: 특정 카테고리만 낮음 (예: 카테고리 3, 4)

**원인**:
- 해당 법령 데이터 부족
- 질문과 법령 불일치

**대응**:
- 법령별 데이터 분포 확인
```sql
SELECT l.title, COUNT(*)
FROM articles a
JOIN laws l ON a.law_id = l.law_id
GROUP BY l.law_id
ORDER BY COUNT(*) DESC;
```

**해결책**:
- 부족한 법령 데이터 추가 수집
- 또는 해당 카테고리 질문 수정

---

### 리스크 4: 검색 속도 저하

**원인**:
- FAISS 검색이 ChromaDB보다 느림
- FTS5 추가로 더 느려짐

**대응**:
- 캐싱 추가
- FAISS IVF 인덱스 사용 (1,643개는 불필요)

**해결책**:
```python
# 쿼리 캐싱
from functools import lru_cache

@lru_cache(maxsize=1000)
def vector_search_cached(self, query, n_results):
    return self.vector_search(query, n_results)
```

---

## 📝 테스트 계획

### 테스트 1: Phase 1 완료 후

**명령어**:
```bash
python scripts/test_faiss_sqlite_matching.py
```

**확인 사항**:
1. Phase 1 통과 (100% 매칭)
2. Phase 2 정확도: **30% 이상** (현재 25%)
3. 법령 검색 빈도 변화 확인

**성공 기준**:
- 정확도 30% 이상
- 카테고리 3, 4: 5% 이상

---

### 테스트 2: Phase 2 완료 후

**명령어**:
```bash
python scripts/test_faiss_sqlite_matching.py
```

**확인 사항**:
1. Phase 1 통과 (100% 매칭)
2. Phase 2 정확도: **70% 이상**
3. 카테고리별:
   - 카테고리 1: 85% 이상
   - 카테고리 2: 75% 이상
   - 카테고리 3: 60% 이상
   - 카테고리 4: 55% 이상

**성공 기준**:
- 전체 70% 이상
- 모든 카테고리 50% 이상

---

### 테스트 3: Phase 3 완료 후 (선택)

**명령어**:
```bash
python scripts/test_faiss_sqlite_matching.py
```

**확인 사항**:
1. Phase 1 통과
2. Phase 2 정확도: **85% 이상**
3. 카테고리별 80% 이상

**성공 기준**:
- 전체 85% 이상
- 모든 카테고리 75% 이상

---

## 📅 예상 일정

### 빠른 개선 (전략 A)

```
Day 1:
09:00 - 10:00  Phase 1 코드 수정 (hybrid_legal_search.py)
10:00 - 10:05  테스트 1 실행
10:05 - 10:15  결과 분석
10:15 - 10:45  Phase 2 코드 수정 (쿼리 전처리)
10:45 - 10:50  테스트 2 실행
10:50 - 11:00  결과 분석 & 완료 보고

총 2시간
```

### 최고 성능 (전략 B)

```
Day 1:
09:00 - 11:00  Phase 1 + Phase 2 (전략 A와 동일)
11:00 - 12:00  Phase 3-1: SQLite FTS5 설정
12:00 - 13:00  점심
13:00 - 14:30  Phase 3-2: RRF Hybrid 구현
14:30 - 14:35  테스트 3 실행
14:35 - 15:00  결과 분석 & 최종 리포트

총 5시간
```

---

## 🎓 학습 포인트

### 왜 재임베딩이 효과 없었나?

1. **코드가 ChromaDB 사용 중**
   - FAISS DB는 만들었지만
   - 코드는 ChromaDB 참조
   - → 옛날 데이터 사용

2. **Domain Shift 문제**
   - 문서: `[장] 제목\\n본문`
   - 쿼리: `질문 그대로`
   - → 벡터 공간 불일치

### 핵심 교훈

1. **데이터만 바꾸면 안 됨** → 코드도 함께 수정
2. **임베딩 형식 일관성 중요** → 문서와 쿼리 형식 통일
3. **단계별 검증 필수** → 각 Phase마다 테스트

---

## ✅ 체크리스트

### Phase 1: ChromaDB → FAISS 전환

- [ ] `hybrid_legal_search.py` Import 변경
- [ ] `__init__()` 메서드 수정
- [ ] `_init_faiss()` 메서드 추가
- [ ] `vector_search()` FAISS 로직 변경
- [ ] `search_specific_article()` 수정
- [ ] Config 경로 추가
- [ ] 테스트 1 실행
- [ ] 결과 30% 이상 확인

### Phase 2: 쿼리 전처리

- [ ] `_enhance_query_for_search()` 함수 추가
- [ ] `vector_search()` 쿼리 전처리 적용
- [ ] 테스트 2 실행
- [ ] 결과 70% 이상 확인

### Phase 3: SQLite FTS5 (선택)

- [ ] `schema.sql` FTS5 테이블 추가
- [ ] `rebuild_sqlite_fts.py` 생성
- [ ] FTS 인덱싱 실행
- [ ] `keyword_search()` 메서드 추가
- [ ] `hybrid_search_advanced()` 메서드 추가
- [ ] 테스트 3 실행
- [ ] 결과 85% 이상 확인

---

## 📞 문의사항

궁금한 점이나 추가 설명이 필요한 부분이 있으면 알려주세요!

1. Phase별 상세 코드가 필요한가요?
2. 테스트 시나리오를 더 구체적으로 작성할까요?
3. 다른 접근 방법을 고려하시나요?

---

**작성 완료**: 2025-10-18
**다음 단계**: 계획 검토 → Phase 1 실행
