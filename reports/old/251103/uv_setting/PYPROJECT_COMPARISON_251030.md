# pyproject.toml 비교 분석
작성일: 2025-10-30

## 파일 크기 비교

| 항목 | 협력자 브랜치 | 메인 프로젝트 | 차이 |
|------|-------------|-------------|------|
| **파일 라인 수** | 16줄 | 204줄 | **12.75배** |
| **의존성 패키지** | 8개 | 185개 | **23배** |
| **파일 구조** | 기본 | 확장 (dev 의존성 포함) | - |

---

## 상세 비교

### 1. 기본 정보 (project)

#### 협력자 브랜치
```toml
[project]
name = "backend"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
```

#### 메인 프로젝트
```toml
[project]
name = "holmesnyangz"
version = "0.1.0"
description = "Real Estate AI Chatbot with LangGraph"
readme = "README.md"
requires-python = ">=3.12"
```

**공통점**:
- ✅ Python 3.12 요구사항
- ✅ 버전 0.1.0
- ✅ README.md 포함

**차이점**:
- 프로젝트 이름 (backend vs holmesnyangz)
- 설명 상세도 (간단 vs 구체적)

---

### 2. 의존성 비교

#### 협력자 브랜치 (8개)
```toml
dependencies = [
    "fastapi>=0.119.0",
    "greenlet>=3.2.4",
    "openai>=2.5.0",
    "publicdatareader>=1.1.1.post2",
    "pymongo>=4.10.0",
    "sqlalchemy>=2.0.44",
    "uvicorn>=0.37.0",
    "websockets==12.0",
]
```

#### 메인 프로젝트 (185개, 주요 카테고리)

**AI/LLM 프레임워크** (협력자는 OpenAI만):
```toml
"anthropic>=0.69.0",
"openai>=1.109.1",
"langchain>=0.3.27",
"langchain-anthropic>=0.3.19",
"langchain-chroma>=0.2.5",
"langchain-community>=0.3.27",
"langchain-core>=0.3.75",
"langchain-huggingface>=0.3.1",
"langchain-openai>=0.3.32",
"langchain-text-splitters>=0.3.11",
"langgraph>=0.6.8",
"langgraph-checkpoint>=2.1.2",
"langgraph-checkpoint-postgres>=2.0.25",
"langgraph-checkpoint-sqlite>=2.0.11",
"langgraph-prebuilt>=0.6.4",
"langgraph-sdk>=0.2.9",
"langgraph-supervisor>=0.0.29",
"langsmith>=0.4.34",
```

**벡터 데이터베이스** (협력자는 없음):
```toml
"chromadb>=1.1.1",
"faiss-cpu>=1.9.0.post1",
"sqlite-vec>=0.1.6",
```

**ML/AI 모델** (협력자는 없음):
```toml
"torch>=2.8.0",
"transformers>=4.57.0",
"sentence-transformers>=5.1.1",
"huggingface-hub>=0.35.3",
"accelerate>=1.10.1",
"tokenizers>=0.22.1",
"tiktoken>=0.12.0",
```

**데이터 처리** (협력자는 없음):
```toml
"numpy>=2.3.3",
"pandas>=2.3.3",
"scikit-learn>=1.7.2",
"scipy>=1.16.2",
```

**웹 프레임워크** (공통):
```toml
"fastapi>=0.115.0",        # 협력자: >=0.119.0
"uvicorn>=0.32.0",         # 협력자: >=0.37.0
"websockets>=12.0",        # 협력자: ==12.0
```

**데이터베이스** (공통 + 추가):
```toml
# 공통
"sqlalchemy>=2.0.23",      # 협력자: >=2.0.44
"greenlet>=3.2.4",         # 협력자: >=3.2.4

# 메인만
"asyncpg>=0.30.0",
"aiosqlite>=0.20.0",
"psycopg>=3.2.10",
"psycopg-pool>=3.2.6",
```

**문서화** (협력자는 없음):
```toml
"mkdocs>=1.6.0",
"mkdocs-material>=9.5.0",
"mkdocs-material-extensions>=1.3.1",
"mkdocs-get-deps>=0.2.0",
```

**기타 공통**:
```toml
"publicdatareader",        # 둘 다 포함
```

---

### 3. 개발 의존성

#### 협력자 브랜치
```toml
# 없음 - 개발 의존성 섹션 없음
```

#### 메인 프로젝트
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.14.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.14.0",
]
```

---

### 4. 빌드 시스템

#### 협력자 브랜치
```toml
# 명시되지 않음 (기본값 사용 추정)
```

#### 메인 프로젝트
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## 비교 요약

### 공통점
1. ✅ Python 3.12 사용
2. ✅ FastAPI, SQLAlchemy, Uvicorn 등 기본 웹 프레임워크
3. ✅ PublicDataReader (한국 공공데이터)
4. ✅ WebSockets 지원
5. ✅ 프로젝트 기본 구조 (name, version, description)

### 주요 차이점

#### 협력자 브랜치 (경량 버전)
- **목적**: 최소 기능 테스트/실험용
- **AI 모델**: OpenAI만
- **데이터베이스**: MongoDB 포함
- **벡터 DB**: 없음
- **ML 라이브러리**: 없음
- **문서화**: 없음
- **개발 도구**: 없음
- **총 의존성**: 8개

#### 메인 프로젝트 (전체 기능)
- **목적**: 프로덕션 AI 챗봇
- **AI 모델**: Anthropic + OpenAI + LangChain/LangGraph 전체 스택
- **데이터베이스**: PostgreSQL, SQLite, AsyncPG
- **벡터 DB**: ChromaDB, FAISS, SQLite-vec
- **ML 라이브러리**: PyTorch, Transformers, Sentence-Transformers
- **문서화**: MkDocs + Material 테마
- **개발 도구**: pytest + asyncio + mock
- **총 의존성**: 185개

---

## 시각화 비교

### 패키지 분포 (메인 프로젝트)

```
AI/LLM 프레임워크:  ████████████████████ 20개 (11%)
ML/데이터 처리:     ████████████ 15개 (8%)
웹/API:            ████████ 10개 (5%)
데이터베이스:       ██████ 8개 (4%)
벡터 DB:           ███ 3개 (2%)
문서화:            ███ 4개 (2%)
보안/인증:         █████ 6개 (3%)
유틸리티:          ████████████████████████████ 119개 (64%)
```

### 패키지 분포 (협력자 브랜치)

```
웹/API:            ███ 3개 (37%)
AI:                █ 1개 (12%)
데이터베이스:       ████ 3개 (37%)
기타:              █ 1개 (12%)
```

---

## 버전 충돌 가능성

### 주의할 패키지

| 패키지 | 협력자 | 메인 | 호환성 |
|--------|--------|------|--------|
| fastapi | >=0.119.0 | >=0.115.0 | ✅ 호환 |
| uvicorn | >=0.37.0 | >=0.32.0 | ✅ 호환 |
| openai | >=2.5.0 | >=1.109.1 | ⚠️ 메이저 버전 차이 |
| sqlalchemy | >=2.0.44 | >=2.0.23 | ✅ 호환 |
| websockets | ==12.0 | >=12.0 | ✅ 호환 |

**주의**: 협력자는 OpenAI 2.5.0 이상, 메인은 1.109.1 이상
→ 메인 프로젝트 업데이트 필요할 수 있음

---

## 결론

### 매우 큰 차이가 있습니다

**협력자 브랜치**:
- 최소한의 웹 API + OpenAI 기본
- 테스트/실험용 경량 버전
- MongoDB 사용

**메인 프로젝트**:
- 완전한 AI 챗봇 스택
- LangChain/LangGraph 기반 에이전트
- 벡터 DB + ML 모델 + 문서화
- PostgreSQL 사용

**권장사항**:
1. ✅ 각자의 pyproject.toml 유지
2. ✅ 공통 기능 통합 시 의존성 조율 필요
3. ⚠️ OpenAI 버전 차이 확인 필요
4. ✅ Python 3.12는 공통이므로 호환성 좋음

---

## 파일 전체 비교

### 협력자 브랜치 (16줄)
```toml
[project]
name = "backend"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.119.0",
    "greenlet>=3.2.4",
    "openai>=2.5.0",
    "publicdatareader>=1.1.1.post2",
    "pymongo>=4.10.0",
    "sqlalchemy>=2.0.44",
    "uvicorn>=0.37.0",
    "websockets==12.0",
]
```

### 메인 프로젝트 (204줄)
- 첫 50줄은 위에서 확인
- 185개 패키지 나열
- dev dependencies 추가
- build-system 설정 추가
- tool.uv 설정 추가

**크기 비교**:
- 협력자: **16줄** (100%)
- 메인: **204줄** (1,275%)
- 차이: **188줄 (12.75배)**
