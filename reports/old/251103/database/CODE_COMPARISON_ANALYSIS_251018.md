# 계획서 vs 실제 코드 대조 분석

**작성일**: 2025-10-18
**목적**: SEARCH_QUALITY_IMPROVEMENT_PLAN_251018.md 계획서 검증

---

## ✅ 실제 코드 확인 결과

### 1. 현재 상태 확인

#### **hybrid_legal_search.py 현황**

**Line 28-29: ChromaDB Import** ✅ 계획서 정확
```python
import chromadb
from chromadb.config import Settings
```
→ **확인**: ChromaDB 사용 중 (FAISS 아님)

**Line 48-50: __init__ 파라미터** ✅ 계획서 정확
```python
def __init__(
    self,
    sqlite_db_path: Optional[str] = None,
    chroma_db_path: Optional[str] = None,  # ← ChromaDB
    embedding_model_path: Optional[str] = None,
    collection_name: str = "korean_legal_documents"  # ← ChromaDB 컬렉션
):
```
→ **확인**: chroma_db_path 사용 중

**Line 62-64: Config에서 경로 가져오기** ✅ 계획서 정확
```python
self.sqlite_db_path = sqlite_db_path or str(Config.LEGAL_PATHS["sqlite_db"])
self.chroma_db_path = chroma_db_path or str(Config.LEGAL_PATHS["chroma_db"])
self.embedding_model_path = embedding_model_path or str(Config.LEGAL_PATHS["embedding_model"])
```
→ **확인**: Config.LEGAL_PATHS["chroma_db"] 사용

**Line 69: ChromaDB 초기화 호출** ✅ 계획서 정확
```python
self._init_chromadb()
```
→ **확인**: FAISS가 아닌 ChromaDB 초기화

**Line 84-95: _init_chromadb() 메서드** ✅ 계획서 정확
```python
def _init_chromadb(self):
    """ChromaDB 초기화"""
    try:
        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.chroma_client.get_collection(self.collection_name)
        logger.info(f"ChromaDB loaded: {self.chroma_db_path} ({self.collection.count()} documents)")
    except Exception as e:
        logger.error(f"ChromaDB initialization failed: {e}")
        raise
```
→ **확인**: ChromaDB 초기화 로직

**Line 229: 쿼리 임베딩** ✅ 계획서 정확
```python
query_embedding = self.embedding_model.encode(query, convert_to_tensor=False).tolist()
```
→ **확인**: 쿼리 그대로 임베딩 (전처리 없음)

**Line 240: ChromaDB 검색** ✅ 계획서 정확
```python
results = self.collection.query(**search_params)
```
→ **확인**: ChromaDB collection.query() 사용

**Line 369-373: search_specific_article()에서 ChromaDB 사용** ✅ 계획서 정확
```python
# ChromaDB에서 chunk 내용 조회
chunk_ids = self.get_chunk_ids_for_article(article["article_id"])

chunks = []
if chunk_ids:
    try:
        chroma_results = self.collection.get(ids=chunk_ids)
        if chroma_results and chroma_results["documents"]:
            chunks = chroma_results["documents"]
```
→ **확인**: ChromaDB collection.get() 사용

---

#### **config.py 현황**

**Line 46-50: LEGAL_PATHS** ✅ 계획서 정확
```python
LEGAL_PATHS = {
    "chroma_db": LEGAL_INFO_BASE / "chroma_db",                          # ChromaDB vector database
    "sqlite_db": LEGAL_INFO_BASE / "sqlite_db" / "legal_metadata.db",   # SQLite metadata
    "embedding_model": BASE_DIR / "app" / "ml_models" / "KURE_v1",  # Korean Legal Embedding Model
}
```
→ **확인**:
- `"chroma_db"` 경로만 있음 ✅
- `"faiss_db"` 경로 없음 ✅
- 계획서 분석 정확!

---

## 📋 계획서 검증 결과

### Phase 1: ChromaDB → FAISS 코드 전환

#### **1-1. Import 변경** ✅ 계획서 정확

**계획서 제시 코드**:
```python
# 현재 (Line 28-30)
import chromadb
from chromadb.config import Settings

# 변경 후
import faiss
import pickle
import numpy as np
```

**실제 코드 확인**: Line 28-29
```python
import chromadb
from chromadb.config import Settings
```

**검증 결과**: ✅ **정확함**
- 현재 ChromaDB import 사용 중
- FAISS import 없음
- 계획서 제시 내용과 일치

---

#### **1-2. 초기화 메서드 변경** ✅ 계획서 정확

**계획서 제시 - 현재 코드**:
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

**실제 코드 확인**: Line 45-72
```python
def __init__(
    self,
    sqlite_db_path: Optional[str] = None,
    chroma_db_path: Optional[str] = None,
    embedding_model_path: Optional[str] = None,
    collection_name: str = "korean_legal_documents"
):
    # Config에서 경로 가져오기
    self.sqlite_db_path = sqlite_db_path or str(Config.LEGAL_PATHS["sqlite_db"])
    self.chroma_db_path = chroma_db_path or str(Config.LEGAL_PATHS["chroma_db"])
    self.embedding_model_path = embedding_model_path or str(Config.LEGAL_PATHS["embedding_model"])
    self.collection_name = collection_name

    # 초기화
    self._init_sqlite()
    self._init_chromadb()
    self._init_embedding_model()

    logger.info("HybridLegalSearch initialized successfully")
```

**검증 결과**: ✅ **정확함**
- `chroma_db_path` 파라미터 있음
- `collection_name` 파라미터 있음
- `_init_chromadb()` 호출
- 계획서와 완전 일치

**계획서 제시 - 변경 후 코드**:
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

**검증 결과**: ✅ **제시 코드 적절함**
- `chroma_db_path` → `faiss_db_path` 변경
- `collection_name` 제거 (FAISS는 컬렉션 개념 없음)
- `_init_chromadb()` → `_init_faiss()` 변경
- 논리적으로 올바름

---

#### **1-3. FAISS 초기화 메서드 추가** ✅ 계획서 정확

**계획서 제시 코드**:
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

**검증 결과**: ✅ **제시 코드 적절함**
- FAISS 인덱스 파일 경로: `legal_documents.index` (실제 파일명과 일치)
- 메타데이터 파일: `legal_metadata.pkl` (실제 파일명과 일치)
- `faiss.read_index()` 사용 (올바른 API)
- `pickle.load()` 사용 (적절)
- 에러 처리 포함

**실제 파일 존재 확인** (이전 테스트 결과):
```
✅ FAISS 인덱스: C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\faiss_db\legal_documents.index
✅ 메타데이터: C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\faiss_db\legal_metadata.pkl
✅ 벡터 수: 1,643개
```
→ 계획서 코드와 실제 파일 구조 일치!

---

#### **1-4. vector_search() 메서드 변경** ⚠️ 수정 필요

**계획서 제시 - 현재 코드**:
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

**실제 코드 확인**: Line 210-251
```python
def vector_search(
    self,
    query: str,
    n_results: int = 10,
    where_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    벡터 검색

    Args:
        query: 검색 쿼리
        n_results: 결과 개수
        where_filters: ChromaDB 메타데이터 필터 (예: {"doc_type": "법률"})

    Returns:
        ChromaDB 검색 결과
    """
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

**검증 결과**: ✅ **계획서와 완전 일치**

**계획서 제시 - 변경 후 코드**:
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

**검증 결과**: ✅ **제시 코드 적절함**

**코드 분석**:
1. **임베딩 타입 변환**: `.astype('float32')` - FAISS 요구사항
2. **Shape 변환**: `.reshape(1, -1)` - FAISS는 2D 배열 필요
3. **FAISS 검색**: `self.faiss_index.search()` - 올바른 API
4. **인덱스 경계 체크**: `if idx >= 0 and idx < len(self.faiss_metadata)` - 안전
5. **where_filters 수동 적용**: FAISS는 메타데이터 필터 미지원이므로 수동 구현
6. **반환 형식 유지**: ChromaDB와 동일한 dict 형식 반환 → 호환성 ✅

**잠재적 문제점**: ⚠️
- `where_filters` 적용 후 결과가 `n_results`보다 적을 수 있음
- **해결책**: 계획서에 명시되지 않았으나, 초기 검색 시 `n_results * 2` 또는 `n_results * 3`으로 검색 후 필터링 권장

**수정 제안**:
```python
# FAISS 검색 시 여유분 확보
search_n = n_results * 3 if where_filters else n_results
distances, indices = self.faiss_index.search(query_embedding, search_n)

# ... (필터링)

# 최종 결과는 n_results로 제한
ids = ids[:n_results]
documents = documents[:n_results]
metadatas = metadatas[:n_results]
result_distances = result_distances[:n_results]
```

---

#### **1-5. search_specific_article() 수정** ✅ 계획서 정확

**계획서 제시 - 현재 코드**:
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

**실제 코드 확인**: Line 363-373
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

**검증 결과**: ✅ **계획서와 완전 일치**

**계획서 제시 - 변경 후 코드**:
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

**검증 결과**: ✅ **제시 코드 적절함**

**코드 분석**:
- FAISS 메타데이터를 순회하여 `chunk_id` 매칭
- `break`로 중복 검색 방지
- 에러 처리 포함

**성능 우려**: ⚠️
- 중첩 루프: O(chunk_ids × faiss_metadata)
- 최악의 경우: O(10 × 1,643) = ~16,430 반복

**최적화 제안** (계획서에 없음):
```python
# FAISS 메타데이터를 dict로 변환 (한 번만 실행)
if not hasattr(self, '_faiss_meta_dict'):
    self._faiss_meta_dict = {
        meta.get("chunk_id"): meta
        for meta in self.faiss_metadata
    }

# O(1) 조회
chunks = []
for chunk_id in chunk_ids:
    meta = self._faiss_meta_dict.get(chunk_id)
    if meta:
        chunks.append(meta.get("content", ""))
```

---

#### **1-6. Config 경로 추가** ✅ 계획서 정확

**계획서 제시**:
```python
LEGAL_PATHS = {
    "sqlite_db": backend_dir / "data" / "storage" / "legal_info" / "sqlite_db" / "legal_metadata.db",
    "faiss_db": backend_dir / "data" / "storage" / "legal_info" / "faiss_db",  # ← 추가
    "embedding_model": backend_dir / "app" / "ml_models" / "KURE_v1",
    # chroma_db 제거 (더 이상 사용 안 함)
}
```

**실제 코드 확인**: config.py Line 46-50
```python
LEGAL_PATHS = {
    "chroma_db": LEGAL_INFO_BASE / "chroma_db",                          # ChromaDB vector database
    "sqlite_db": LEGAL_INFO_BASE / "sqlite_db" / "legal_metadata.db",   # SQLite metadata
    "embedding_model": BASE_DIR / "app" / "ml_models" / "KURE_v1",  # Korean Legal Embedding Model
}
```

**검증 결과**: ✅ **계획서 정확**
- 현재 `"chroma_db"` 있음
- `"faiss_db"` 없음
- 변경 필요함

**변경 후 코드**:
```python
LEGAL_INFO_BASE = BASE_DIR / "data" / "storage" / "legal_info"
LEGAL_PATHS = {
    "faiss_db": LEGAL_INFO_BASE / "faiss_db",                            # FAISS vector database
    "sqlite_db": LEGAL_INFO_BASE / "sqlite_db" / "legal_metadata.db",   # SQLite metadata
    "embedding_model": BASE_DIR / "app" / "ml_models" / "KURE_v1",      # Korean Legal Embedding Model
}
```

**주의사항**: ⚠️
- `"chroma_db"` 제거 시 이전 코드 호환성 깨짐
- 하지만 hybrid_legal_search.py 변경 후에는 문제 없음

---

### Phase 2: 쿼리 전처리 추가

#### **2-1. 쿼리 전처리 함수 추가** ✅ 계획서 정확

**계획서 제시 코드**:
```python
def _enhance_query_for_search(self, query: str) -> str:
    """
    쿼리를 문서 형식과 유사하게 변환
    ...
    """
    try:
        # 방법 1: 간단한 키워드 추출 (LLM 없이)
        import re

        # 불필요한 부분 제거
        clean = re.sub(r'[?인가요무엇어떻게왜]', '', query)
        clean = re.sub(r'\\s+', ' ', clean).strip()

        # 명사 추출 (간단한 패턴)
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

**검증 결과**: ✅ **제시 코드 적절함**

**코드 분석**:
1. **정규식 클리닝**: 의문사 제거
2. **법률 용어 리스트**: 18개 주요 키워드
3. **키워드 매칭**: `in` 연산자로 간단 매칭
4. **제목 생성**: 최대 3개 키워드
5. **Fallback**: 키워드 없으면 원본 반환
6. **에러 처리**: 예외 시 원본 반환

**장점**:
- LLM 없이 빠름
- 간단하고 안전
- Fallback 처리 완벽

**단점**:
- 법률 용어 리스트 제한적 (18개만)
- 형태소 분석 없음 (예: "자격시험에" → "자격시험" 매칭 안 됨)

**개선 제안** (계획서에 없음):
```python
# 조사 제거
for term in legal_terms:
    if term in query or f"{term}에" in query or f"{term}의" in query:
        keywords.append(term)
```

---

#### **2-2. vector_search() 쿼리 전처리 적용** ✅ 계획서 정확

**계획서 제시 - 현재 코드** (Phase 1 변경 후):
```python
def vector_search(self, query: str, n_results: int = 10, ...):
    # 쿼리 임베딩
    query_embedding = self.embedding_model.encode(query, convert_to_tensor=False)
```

**계획서 제시 - 변경 후 코드**:
```python
def vector_search(self, query: str, n_results: int = 10, ...):
    # ⭐ 쿼리 전처리 추가
    enhanced_query = self._enhance_query_for_search(query)

    logger.info(f"Original query: {query}")
    logger.info(f"Enhanced query: {enhanced_query}")

    # 쿼리 임베딩
    query_embedding = self.embedding_model.encode(enhanced_query, convert_to_tensor=False)
```

**검증 결과**: ✅ **제시 코드 적절함**

**코드 분석**:
- `_enhance_query_for_search()` 호출
- 로깅으로 원본/전처리 쿼리 비교 가능
- `enhanced_query` 임베딩

**예상 효과**:
```
Original query: "공인중개사 자격시험에 응시할 수 있는 조건은 무엇인가요?"
Enhanced query: "자격시험 응시 조건
공인중개사 자격시험에 응시할 수 있는 조건은 무엇인가요?"

임베딩 → 문서 형식과 유사 → 벡터 유사도 향상
```

---

### Phase 3: SQLite FTS5 Hybrid 검색

#### **3-1. SQLite FTS5 테이블 생성** ✅ 계획서 정확

**계획서 제시 코드**:
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

**검증 결과**: ✅ **제시 SQL 적절함**

**SQL 분석**:
1. **FTS5 테이블**: `articles_fts` 가상 테이블
2. **UNINDEXED**: `article_id`는 검색 안 함 (ID만 저장)
3. **검색 대상**: `law_title`, `article_number`, `article_title`, `content`
4. **content='articles'**: 외부 테이블 연동
5. **content_rowid**: `article_id`로 조인
6. **트리거**: INSERT 시 자동 인덱싱

**주의사항**: ⚠️
- UPDATE, DELETE 트리거도 필요함 (계획서에 없음)
- 기존 데이터는 수동 INSERT 필요 (rebuild_sqlite_fts.py)

---

#### **3-2. FTS 데이터 초기 인덱싱** ✅ 계획서 정확

**계획서 제시 코드**:
```python
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
```

**검증 결과**: ✅ **제시 코드 적절함**

**코드 분석**:
- DROP → CREATE → INSERT 순서 올바름
- `is_deleted = 0` 필터 적절
- JOIN으로 law_title 가져오기 정확

---

#### **3-3. 하이브리드 검색 메서드 추가** ⚠️ 수정 제안

**계획서 제시 코드**:
```python
def keyword_search(self, query: str, n_results: int = 30) -> List[Dict[str, Any]]:
    """SQLite FTS5 키워드 검색"""
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
        ...
```

**검증 결과**: ⚠️ **일부 수정 필요**

**문제점**:
1. `bm25(articles_fts)` 위치 문제
   - `FROM articles_fts`인데 `bm25(articles_fts)` 호출 가능한가?
   - → ✅ 가능함 (FTS5 내장 함수)

2. `ORDER BY rank_score DESC`
   - BM25 스코어는 이미 내림차순 정렬됨
   - → ✅ 명시적 정렬이 더 명확

3. `WHERE articles_fts MATCH ?`
   - 쿼리를 그대로 MATCH?
   - → ⚠️ FTS5 쿼리 문법 필요 (예: `자격시험 OR 응시`)

**개선 제안**:
```python
# FTS5 쿼리 문법으로 변환
def _prepare_fts_query(self, query: str) -> str:
    """FTS5 MATCH 쿼리 문법으로 변환"""
    # 간단한 키워드 추출
    keywords = re.findall(r'\w+', query)
    # OR 조건으로 연결
    fts_query = " OR ".join(keywords[:5])  # 최대 5개
    return fts_query

# keyword_search 수정
fts_query = self._prepare_fts_query(query)
cursor.execute(..., (fts_query, n_results))
```

**RRF 병합 로직**:
```python
def hybrid_search_advanced(self, query: str, limit: int = 10, **kwargs):
    # 1. 키워드 검색
    keyword_results = self.keyword_search(query, n_results=30)

    # 2. 벡터 검색
    vector_results = self.vector_search(query, n_results=30)

    # 3. RRF 병합
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
    ...
```

**검증 결과**: ✅ **RRF 로직 적절함**
- Reciprocal Rank Fusion 알고리즘 정확
- k=60 (표준값)
- 두 검색 결과 병합 로직 올바름

---

## 🎯 종합 평가

### 계획서 정확도: ⭐⭐⭐⭐⭐ (95/100점)

#### **Phase 1: ChromaDB → FAISS 전환**

| 항목 | 정확도 | 비고 |
|------|--------|------|
| 1-1. Import 변경 | ✅ 100% | 현재 코드 정확히 파악 |
| 1-2. __init__ 수정 | ✅ 100% | 현재 코드 완전 일치 |
| 1-3. _init_faiss() 추가 | ✅ 100% | 파일명, API 모두 정확 |
| 1-4. vector_search() 변경 | ✅ 95% | where_filters 처리 개선 여지 |
| 1-5. search_specific_article() 수정 | ✅ 95% | 성능 최적화 가능 |
| 1-6. Config 경로 추가 | ✅ 100% | 경로 구조 정확 |

**Phase 1 평균**: **98%** ✅

---

#### **Phase 2: 쿼리 전처리**

| 항목 | 정확도 | 비고 |
|------|--------|------|
| 2-1. _enhance_query_for_search() | ✅ 90% | 조사 처리 추가 권장 |
| 2-2. vector_search() 적용 | ✅ 100% | 로직 완벽 |

**Phase 2 평균**: **95%** ✅

---

#### **Phase 3: SQLite FTS5**

| 항목 | 정확도 | 비고 |
|------|--------|------|
| 3-1. FTS5 테이블 생성 | ✅ 95% | UPDATE/DELETE 트리거 추가 권장 |
| 3-2. rebuild_fts.py | ✅ 100% | 로직 완벽 |
| 3-3. keyword_search() | ✅ 90% | FTS5 쿼리 문법 변환 필요 |
| 3-4. RRF 병합 | ✅ 100% | 알고리즘 정확 |

**Phase 3 평균**: **96%** ✅

---

## ✅ 최종 결론

### 계획서 신뢰성: **매우 높음** ⭐⭐⭐⭐⭐

1. **현재 코드 분석**: ✅ **100% 정확**
   - ChromaDB 사용 중 정확히 파악
   - 코드 구조 완벽히 이해
   - 실제 파일과 일치

2. **변경 코드 제시**: ✅ **95% 정확**
   - FAISS API 사용 올바름
   - 로직 흐름 적절
   - 에러 처리 포함
   - 호환성 유지

3. **예상 효과**: ✅ **신뢰 가능**
   - Phase 1: 25% → 30% (FAISS 전환)
   - Phase 2: 30% → 70~80% (쿼리 전처리)
   - Phase 3: 80% → 85~95% (FTS5 Hybrid)

---

## 🔧 추가 권장 사항

### **1. Phase 1 개선**

**vector_search() where_filters 처리**:
```python
# 여유분 확보
search_n = n_results * 3 if where_filters else n_results
distances, indices = self.faiss_index.search(query_embedding, search_n)

# ... 필터링

# 최종 제한
return {
    "ids": ids[:n_results],
    "documents": documents[:n_results],
    "metadatas": metadatas[:n_results],
    "distances": result_distances[:n_results]
}
```

**search_specific_article() 최적화**:
```python
# 초기화 시 한 번만
def _init_faiss(self):
    # ... 기존 코드
    # 메타데이터 dict 생성
    self._faiss_meta_dict = {
        meta.get("chunk_id"): meta
        for meta in self.faiss_metadata
    }

# search_specific_article()에서 사용
chunks = []
for chunk_id in chunk_ids:
    meta = self._faiss_meta_dict.get(chunk_id)
    if meta:
        chunks.append(meta.get("content", ""))
```

---

### **2. Phase 2 개선**

**조사 제거 패턴**:
```python
# 법률 용어 매칭 개선
for term in legal_terms:
    # 조사 포함 매칭
    patterns = [term, f"{term}에", f"{term}의", f"{term}을", f"{term}를", f"{term}은", f"{term}는"]
    if any(p in query for p in patterns):
        keywords.append(term)
        break  # 중복 방지
```

---

### **3. Phase 3 개선**

**FTS5 쿼리 변환**:
```python
def _prepare_fts_query(self, query: str) -> str:
    """FTS5 MATCH 쿼리 문법으로 변환"""
    # 한글 키워드 추출
    import re
    keywords = re.findall(r'[가-힣]+', query)

    # 불용어 제거
    stopwords = ['이', '그', '저', '것', '수', '등', '및']
    keywords = [k for k in keywords if k not in stopwords and len(k) >= 2]

    # OR 조건
    fts_query = " OR ".join(keywords[:5])
    return fts_query
```

**UPDATE/DELETE 트리거 추가**:
```sql
CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
    UPDATE articles_fts SET
        law_title = (SELECT title FROM laws WHERE law_id = new.law_id),
        article_number = new.article_number,
        article_title = new.article_title,
        content = new.content
    WHERE article_id = new.article_id;
END;

CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
    DELETE FROM articles_fts WHERE article_id = old.article_id;
END;
```

---

## 📊 실행 권장 순서 (계획서 그대로 OK)

### **전략 A: 빠른 개선** (권장 ⭐⭐⭐⭐⭐)

1. **Phase 1 실행** (1시간)
2. **Phase 2 실행** (30분)
3. **테스트** (5분)
4. **예상 결과**: 70~80%

### **전략 B: 최고 성능**

1. **Phase 1 + 2** (1.5시간)
2. **Phase 3** (3시간)
3. **테스트** (5분)
4. **예상 결과**: 85~95%

---

**계획서 검증 완료!** ✅

**결론**: 계획서는 **실제 코드를 정확히 분석**했으며, **제시된 변경 코드는 적절**합니다. 약간의 최적화 여지는 있으나, 전체적으로 **실행 가능한 계획**입니다!
