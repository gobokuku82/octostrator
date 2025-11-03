# 🤖 AI 에이전트 통합 가이드

> **목적**: Claude AI가 이 문서를 읽고 부동산 데이터베이스와 AI 에이전트를 즉시 연결할 수 있도록 모든 필요한 정보를 제공합니다.

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [현재 상태](#현재-상태)
3. [데이터베이스 정보](#데이터베이스-정보)
4. [시스템 아키텍처](#시스템-아키텍처)
5. [AI 에이전트 통합 로드맵](#ai-에이전트-통합-로드맵)
6. [구체적인 구현 단계](#구체적인-구현-단계)
7. [참고 문서](#참고-문서)

---

## 프로젝트 개요

### 프로젝트명
**도와줘 홈즈냥즈 (HolmesNyangz)** - 부동산 AI 챗봇

### 목표
사용자가 자연어로 부동산 관련 질문을 하면, AI 에이전트가 PostgreSQL 데이터베이스를 조회하여 정확한 답변을 제공하는 시스템

### 기술 스택
- **Backend**: FastAPI + Python 3.10+
- **Database**: PostgreSQL (부동산 데이터) + MongoDB (은행 데이터)
- **ORM**: SQLAlchemy 2.0+
- **AI Framework**: 미구현 (구현 필요)

### 프로젝트 위치
```
c:\kdy\Projects\holmesnyangz\hny-side-project\hny-side-project\backend
```

---

## 현재 상태

### ✅ 완료된 작업

1. **데이터베이스 스키마 설계 완료**
   - 9개 핵심 테이블 정의
   - 관계(Relationships) 설정
   - 인덱스 및 제약조건 설정

2. **데이터 Import 완료**
   - 부동산 매물: **9,738개**
   - 거래 내역: **10,772개**
   - 지역 정보: **46개**
   - 데이터 타입: 아파트, 오피스텔, 빌라, 원룸

3. **모델 및 스키마 정의**
   - SQLAlchemy 모델: `app/models/`
   - Pydantic 스키마: `app/schemas/`
   - 완전한 타입 힌팅

4. **데이터베이스 연결 설정**
   - PostgreSQL: ✅ 작동 중
   - MongoDB: ✅ 설정 완료

### ⏳ 미완료 작업 (AI 에이전트 구현 필요)

1. **FastAPI 라우터 (API 엔드포인트)**
   - `/api/real-estates/search` - 매물 검색
   - `/api/real-estates/{id}` - 상세 정보
   - `/api/chat/` - 채팅 API
   - 현재 상태: `app/main.py`에 기본 FastAPI 앱만 존재

2. **CRUD 로직**
   - `app/crud/` 폴더가 비어있음
   - 데이터베이스 쿼리 로직 구현 필요

3. **AI 에이전트 통합**
   - LLM 연결 (OpenAI, Anthropic 등)
   - RAG (Retrieval-Augmented Generation) 설정
   - 데이터베이스 쿼리 체인 구성
   - 자연어 → SQL 변환 로직

4. **채팅 시스템**
   - 세션 관리
   - 메시지 히스토리
   - 스트리밍 응답

---

## 데이터베이스 정보

### 연결 정보

**PostgreSQL**
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=real_estate
DB_USER=postgres
DB_PASSWORD=root1234
DATABASE_URL=postgresql+pg8000://postgres:root1234@localhost:5432/real_estate
```

**MongoDB**
```bash
MONGO_DB_HOST=localhost
MONGO_DB_PORT=27017
MONGO_DB_URL=mongodb://localhost:27017/
```

### 환경 변수 파일
- 위치: `backend/.env`
- 예시: `backend/.env.example`

### 데이터베이스 연결 코드
```python
from app.db.postgre_db import SessionLocal, engine
from app.models.real_estate import RealEstate, Transaction, Region

# 세션 생성
db = SessionLocal()

# 쿼리 예시
apartments = db.query(RealEstate).filter(
    RealEstate.property_type == PropertyType.APARTMENT
).limit(10).all()

# 종료
db.close()
```

### 핵심 테이블 구조

상세한 스키마는 [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md)를 참조하세요.

**핵심 9개 테이블:**
1. `regions` - 지역 정보 (구, 동)
2. `real_estates` - 부동산 매물 정보
3. `transactions` - 거래/가격 정보
4. `nearby_facilities` - 주변 편의시설
5. `real_estate_agents` - 중개사 정보
6. `users` - 사용자 정보
7. `chat_sessions` - 채팅 세션
8. `chat_messages` - 채팅 메시지
9. `trust_scores` - 신뢰도 점수

---

## 시스템 아키텍처

### 현재 아키텍처 (데이터 계층만 완성)

```
┌─────────────────────────────────────────┐
│         Frontend (미구현)                │
│         React/Next.js                    │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      FastAPI Backend (기본만 존재)       │
│      - app/main.py (라우터 없음)         │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      SQLAlchemy ORM (✅ 완성)            │
│      - Models: app/models/              │
│      - Schemas: app/schemas/            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      PostgreSQL Database (✅ 완성)       │
│      - 9,738개 매물                      │
│      - 10,772개 거래 내역                │
└─────────────────────────────────────────┘
```

### 목표 아키텍처 (AI 에이전트 추가)

```
┌─────────────────────────────────────────┐
│            Frontend                      │
│         사용자 인터페이스                 │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         FastAPI REST API                 │
│  ┌───────────────────────────────────┐  │
│  │  Chat Endpoint                    │  │
│  │  /api/chat/message                │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         AI Agent Layer                   │
│  ┌───────────────────────────────────┐  │
│  │  LangChain / LlamaIndex           │  │
│  │  - Intent Detection               │  │
│  │  - Query Generation               │  │
│  │  - Response Synthesis             │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  RAG System                       │  │
│  │  - Vector Store (선택)            │  │
│  │  - Database Query Tool            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      Database Access Layer               │
│      - CRUD Operations                   │
│      - Query Builders                    │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         PostgreSQL Database              │
└─────────────────────────────────────────┘
```

---

## AI 에이전트 통합 로드맵

### Phase 1: 기본 인프라 구축 (1-2일)

1. **CRUD 로직 구현**
   - `app/crud/real_estate.py` - 부동산 쿼리
   - `app/crud/chat.py` - 채팅 관리
   - `app/crud/user.py` - 사용자 관리

2. **FastAPI 라우터 생성**
   - `app/api/v1/real_estates.py`
   - `app/api/v1/chat.py`
   - `app/main.py`에 라우터 등록

3. **기본 API 테스트**
   - 매물 조회 엔드포인트
   - 검색 기능
   - CRUD 동작 확인

### Phase 2: AI 에이전트 기본 구현 (2-3일)

1. **AI Framework 선택 및 설치**
   ```bash
   # 옵션 1: LangChain
   uv add langchain langchain-openai langchain-community

   # 옵션 2: LlamaIndex
   uv add llama-index llama-index-llms-openai
   ```

2. **Database Query Tool 구현**
   - 자연어를 SQL로 변환
   - 쿼리 실행 및 결과 반환
   - 에러 핸들링

3. **기본 대화 체인 구성**
   - 사용자 질문 이해
   - 데이터베이스 조회
   - 자연어 응답 생성

### Phase 3: 고급 기능 (3-5일)

1. **컨텍스트 관리**
   - 대화 히스토리
   - 세션 관리
   - 멀티턴 대화

2. **복잡한 쿼리 지원**
   - 다중 조건 필터링
   - 지역 기반 검색
   - 가격 범위 검색

3. **RAG 시스템 (선택사항)**
   - 벡터 데이터베이스
   - 시맨틱 검색

### Phase 4: 최적화 및 프로덕션 준비 (2-3일)

1. **성능 최적화**
   - 쿼리 최적화
   - 캐싱
   - 연결 풀링

2. **에러 핸들링**
   - 예외 처리
   - 재시도 로직
   - 폴백 응답

3. **모니터링**
   - 로깅
   - 메트릭

---

## 구체적인 구현 단계

### Step 1: CRUD 구현

**파일 생성**: `app/crud/real_estate.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.real_estate import RealEstate, Transaction, Region, PropertyType
from typing import Optional, List

def get_real_estate_by_id(db: Session, real_estate_id: int) -> Optional[RealEstate]:
    """ID로 부동산 조회"""
    return db.query(RealEstate).filter(RealEstate.id == real_estate_id).first()

def search_real_estates(
    db: Session,
    region_name: Optional[str] = None,
    property_type: Optional[PropertyType] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    skip: int = 0,
    limit: int = 10
) -> List[RealEstate]:
    """부동산 검색"""
    query = db.query(RealEstate)

    # 지역 필터
    if region_name:
        query = query.join(Region).filter(Region.name.contains(region_name))

    # 타입 필터
    if property_type:
        query = query.filter(RealEstate.property_type == property_type)

    # 가격 필터 (transactions 조인 필요)
    if min_price or max_price:
        query = query.join(Transaction)
        if min_price:
            query = query.filter(Transaction.sale_price >= min_price)
        if max_price:
            query = query.filter(Transaction.sale_price <= max_price)

    return query.offset(skip).limit(limit).all()

def get_real_estates_by_region(
    db: Session,
    region_name: str,
    limit: int = 10
) -> List[RealEstate]:
    """특정 지역의 부동산 조회"""
    return db.query(RealEstate).join(Region).filter(
        Region.name.contains(region_name)
    ).limit(limit).all()
```

### Step 2: FastAPI 라우터 생성

**파일 생성**: `app/api/v1/real_estates.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.postgre_db import get_db
from app.crud import real_estate as crud
from app.schemas.real_estate import RealEstateResponse, RealEstateWithRegion
from app.models.real_estate import PropertyType

router = APIRouter(prefix="/real-estates", tags=["real-estates"])

@router.get("/{real_estate_id}", response_model=RealEstateWithRegion)
def get_real_estate(real_estate_id: int, db: Session = Depends(get_db)):
    """부동산 상세 정보 조회"""
    real_estate = crud.get_real_estate_by_id(db, real_estate_id)
    if not real_estate:
        raise HTTPException(status_code=404, detail="Real estate not found")
    return real_estate

@router.get("/", response_model=List[RealEstateResponse])
def search_real_estates(
    region: Optional[str] = None,
    property_type: Optional[PropertyType] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """부동산 검색"""
    return crud.search_real_estates(
        db,
        region_name=region,
        property_type=property_type,
        min_price=min_price,
        max_price=max_price,
        skip=skip,
        limit=limit
    )
```

**파일 수정**: `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import real_estates

app = FastAPI(
    title="HolmesNyangz API",
    description="부동산 AI 챗봇 API",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(real_estates.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "HolmesNyangz API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

### Step 3: AI 에이전트 기본 구현 (LangChain 예시)

**파일 생성**: `app/ai/database_tool.py`

```python
from langchain.tools import BaseTool
from sqlalchemy.orm import Session
from app.db.postgre_db import SessionLocal
from app.crud import real_estate as crud
from typing import Optional
import json

class RealEstateSearchTool(BaseTool):
    name = "real_estate_search"
    description = """
    부동산을 검색합니다.
    입력은 JSON 형식이어야 합니다:
    {
        "region": "강남구" (선택),
        "property_type": "apartment|officetel|villa|oneroom" (선택),
        "min_price": 10000 (만원 단위, 선택),
        "max_price": 50000 (만원 단위, 선택)
    }
    """

    def _run(self, query: str) -> str:
        """쿼리 실행"""
        db = SessionLocal()
        try:
            # JSON 파싱
            params = json.loads(query)

            # 검색 실행
            results = crud.search_real_estates(
                db,
                region_name=params.get("region"),
                property_type=params.get("property_type"),
                min_price=params.get("min_price"),
                max_price=params.get("max_price"),
                limit=5
            )

            # 결과 포맷팅
            if not results:
                return "검색 결과가 없습니다."

            output = []
            for re in results:
                output.append({
                    "name": re.name,
                    "address": re.address,
                    "property_type": re.property_type.value,
                    "region": re.region.name if re.region else None
                })

            return json.dumps(output, ensure_ascii=False)
        except Exception as e:
            return f"에러 발생: {str(e)}"
        finally:
            db.close()

    async def _arun(self, query: str) -> str:
        """비동기 실행"""
        return self._run(query)
```

**파일 생성**: `app/ai/agent.py`

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.ai.database_tool import RealEstateSearchTool
import os

# LLM 초기화
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# 도구 설정
tools = [RealEstateSearchTool()]

# 프롬프트 설정
prompt = ChatPromptTemplate.from_messages([
    ("system", """당신은 부동산 전문 AI 어시스턴트입니다.
사용자의 질문을 이해하고, 적절한 도구를 사용하여 부동산 정보를 검색합니다.
검색 결과를 바탕으로 친절하고 정확한 답변을 제공하세요.

답변 시 주의사항:
1. 검색 결과가 없으면 정중하게 알려주세요
2. 가격은 만원 단위로 표시합니다
3. 지역명은 정확하게 표시합니다
4. 매물 정보는 간결하게 요약합니다
"""),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 에이전트 생성
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

def chat(message: str) -> str:
    """사용자 메시지 처리"""
    result = agent_executor.invoke({"input": message})
    return result["output"]
```

**파일 생성**: `app/api/v1/chat.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.postgre_db import get_db
from app.ai.agent import chat as ai_chat

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@router.post("/message", response_model=ChatResponse)
def send_message(request: ChatRequest):
    """AI 챗봇에 메시지 전송"""
    try:
        response = ai_chat(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 4: 환경 변수 추가

**파일 수정**: `.env`

```bash
# 기존 설정...

# OpenAI API (또는 다른 LLM)
OPENAI_API_KEY=your_api_key_here

# 또는 Anthropic Claude
ANTHROPIC_API_KEY=your_api_key_here
```

### Step 5: 의존성 추가

**파일 수정**: `pyproject.toml`

```toml
dependencies = [
    # ... 기존 의존성 ...
    "langchain>=0.1.0",
    "langchain-openai>=0.0.5",
    "langchain-community>=0.0.20",
    "openai>=1.10.0",
]
```

설치:
```bash
cd backend
uv sync
```

### Step 6: 서버 실행 및 테스트

```bash
# 서버 실행
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 테스트 (다른 터미널에서)
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "강남구에 있는 아파트 알려줘"}'
```

---

## 참고 문서

### 프로젝트 내부 문서
- [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md) - 데이터베이스 상세 스키마
- [`API_EXAMPLES.md`](./API_EXAMPLES.md) - API 사용 예시
- [`CURRENT_STATUS.md`](./CURRENT_STATUS.md) - 현재 상태 스냅샷

### 코드 위치
- **모델**: `app/models/`
- **스키마**: `app/schemas/`
- **데이터베이스**: `app/db/`
- **설정**: `app/core/config.py`
- **환경변수**: `.env`

### 외부 참고자료
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 문서](https://docs.sqlalchemy.org/en/20/)
- [LangChain 문서](https://python.langchain.com/docs/get_started/introduction)
- [LlamaIndex 문서](https://docs.llamaindex.ai/en/stable/)

---

## 빠른 시작 체크리스트

AI 에이전트 구현을 시작하기 전 확인사항:

- [ ] PostgreSQL 연결 확인
  ```bash
  uv run python -c "from app.db.postgre_db import SessionLocal; db = SessionLocal(); print('✅ 연결 성공'); db.close()"
  ```

- [ ] 데이터 존재 확인
  ```bash
  uv run python -c "from app.db.postgre_db import SessionLocal; from app.models.real_estate import RealEstate; db = SessionLocal(); print(f'매물 수: {db.query(RealEstate).count()}'); db.close()"
  ```

- [ ] 환경 변수 설정
  - `.env` 파일 존재
  - `DATABASE_URL` 설정됨
  - LLM API 키 설정 (OpenAI, Anthropic 등)

- [ ] 의존성 설치
  ```bash
  cd backend
  uv sync
  ```

- [ ] 모델 관계 버그 수정 (RealEstate.favorites)
  - [`app/models/real_estate.py`](../app/models/real_estate.py) 참조

---

## 문의 및 지원

이 문서에 대한 질문이나 추가 정보가 필요한 경우:
1. [`CURRENT_STATUS.md`](./CURRENT_STATUS.md)에서 현재 상태 확인
2. [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md)에서 스키마 세부사항 확인
3. 코드 주석 및 Docstring 참조

---

**마지막 업데이트**: 2025-10-13
**작성자**: AI Assistant
**버전**: 1.0.0
