# LangSmith 도입 가이드 (LangGraph 0.6)

## 문서 정보
- **작성일**: 2025-10-30
- **대상 시스템**: `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\service_agent`
- **LangGraph 버전**: 0.6.x
- **참조**: 공식 LangSmith 문서 (2025년 10월 기준)

---

## 목차
1. [LangSmith란?](#1-langsmith란)
2. [주요 기능 및 장점](#2-주요-기능-및-장점)
3. [설치 및 환경 설정](#3-설치-및-환경-설정)
4. [기본 통합 방법](#4-기본-통합-방법)
5. [고급 통합 (Custom Functions)](#5-고급-통합-custom-functions)
6. [실전 적용 가이드](#6-실전-적용-가이드)
7. [대시보드 활용](#7-대시보드-활용)
8. [문제 해결](#8-문제-해결)

---

## 1. LangSmith란?

**LangSmith**는 LangChain에서 제공하는 LLM 애플리케이션의 **관찰성(Observability)**, **디버깅(Debugging)**, **평가(Evaluation)** 플랫폼입니다.

### 핵심 역할
- **트레이싱(Tracing)**: 모든 LLM 호출, 도구 실행, 에이전트 단계를 시각화
- **디버깅**: 성능 문제, 오류, 예상치 못한 동작 분석
- **평가**: 에이전트 성능 측정 및 개선
- **모니터링**: 프로덕션 환경에서 실시간 추적

---

## 2. 주요 기능 및 장점

### 2.1 자동 트레이싱
- LangChain/LangGraph 사용 시 **자동으로** 모든 실행 추적
- 별도 코드 수정 없이 환경 변수만 설정하면 동작

### 2.2 시각적 디버깅
- 에이전트 실행 과정을 **트리 구조**로 시각화
- 각 단계의 입력/출력, 실행 시간, 오류 메시지 확인
- LangGraph의 노드 실행 순서와 상태 변화 추적

### 2.3 성능 분석
- LLM 응답 시간, 토큰 사용량 측정
- 병목 구간 식별 및 최적화
- 비용 추적 (API 호출 비용)

### 2.4 에이전트 평가
- 테스트 데이터셋으로 에이전트 성능 평가
- A/B 테스트 및 프롬프트 개선 실험
- 시간에 따른 성능 변화 추적

---

## 3. 설치 및 환경 설정

### 3.1 패키지 설치

```bash
# LangSmith SDK 설치 (최신 버전: 2025년 10월 23일)
pip install langsmith

# LangGraph 0.6 설치 (이미 설치되어 있음)
pip install langgraph>=0.6.0

# LangChain 관련 패키지 (이미 설치되어 있으면 생략)
pip install langchain langchain-openai
```

### 3.2 LangSmith API 키 발급

1. **LangSmith 대시보드 접속**
   - https://smith.langchain.com 에 가입 및 로그인

2. **API 키 생성**
   - 대시보드에서 `Settings` → `API Keys` 클릭
   - `Create API Key` 버튼 클릭
   - 생성된 키를 안전하게 복사 (한 번만 표시됨)

3. **프로젝트 생성**
   - 대시보드에서 `Projects` → `New Project` 클릭
   - 프로젝트 이름 설정 (예: `holmesnyangz-service-agent`)

### 3.3 환경 변수 설정

#### Option A: `.env` 파일 설정 (권장)

`backend/.env` 파일에 다음 변수 추가:

```bash
# LangSmith Configuration
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_api_key_here
LANGSMITH_PROJECT=holmesnyangz-service-agent
LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# Alternative naming (LangChain v2 compatibility)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_api_key_here
LANGCHAIN_PROJECT=holmesnyangz-service-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

#### Option B: Python 코드에서 설정

```python
import os

# LangSmith 활성화
os.environ['LANGSMITH_TRACING'] = 'true'
os.environ['LANGSMITH_API_KEY'] = 'your_api_key_here'
os.environ['LANGSMITH_PROJECT'] = 'holmesnyangz-service-agent'

# 또는 LangChain v2 naming
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_API_KEY'] = 'your_api_key_here'
os.environ['LANGCHAIN_PROJECT'] = 'holmesnyangz-service-agent'
```

### 3.4 환경 변수 설명

| 변수명 | 필수 | 설명 | 기본값 |
|--------|------|------|--------|
| `LANGSMITH_TRACING` | ✅ | 트레이싱 활성화 여부 | `false` |
| `LANGSMITH_API_KEY` | ✅ | LangSmith API 키 | - |
| `LANGSMITH_PROJECT` | ⚠️ | 프로젝트 이름 | `default` |
| `LANGSMITH_ENDPOINT` | ❌ | API 엔드포인트 | `https://api.smith.langchain.com` |

> **참고**: `LANGCHAIN_*` 변수는 `LANGSMITH_*`의 별칭입니다. 둘 다 동작합니다.

---

## 4. 기본 통합 방법

### 4.1 LangChain 모듈 사용 시 (자동 추적)

**현재 시스템에 해당**: `team_supervisor.py`, `planning_agent.py` 등에서 LangChain 모듈 사용 중

**장점**: 코드 수정 없이 자동으로 추적됨

**동작 원리**:
- LangChain의 `ChatOpenAI`, `LLMChain` 등이 자동으로 트레이싱 컨텍스트 인식
- LangGraph의 모든 노드 실행이 자동으로 기록됨
- 환경 변수만 설정하면 즉시 사용 가능

**적용 코드 예시** (수정 불필요):

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

# 기존 코드 그대로 사용 - 자동으로 추적됨
llm = ChatOpenAI(
    model="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY")
)

# LangGraph 워크플로우도 자동 추적
workflow = StateGraph(MainSupervisorState)
workflow.add_node("planning", self.planning_node)
workflow.add_node("execute_teams", self.execute_teams_node)
# ... 나머지 노드들

app = workflow.compile()
result = await app.ainvoke(initial_state)  # ← 자동으로 LangSmith에 기록됨
```

### 4.2 자동 추적 확인

1. 애플리케이션 실행 후 LangSmith 대시보드 접속
2. `Projects` → 설정한 프로젝트 선택
3. `Traces` 탭에서 실행 기록 확인

---

## 5. 고급 통합 (Custom Functions)

### 5.1 `@traceable` 데코레이터 사용

**언제 필요한가?**
- LangChain 외부의 커스텀 함수 추적 시
- 외부 API 호출 추적 시
- 데이터베이스 쿼리 추적 시

**적용 방법**:

```python
from langsmith import traceable

# 기본 사용
@traceable(run_type="tool", name="PostgreSQL Query")
async def query_real_estate_data(query: str):
    """부동산 데이터베이스 쿼리"""
    # DB 쿼리 실행
    results = await db.execute(query)
    return results

# Metadata 추가
@traceable(
    run_type="tool",
    name="Market Analysis",
    metadata={"version": "2.0", "team": "analysis"}
)
async def analyze_market_data(region: str):
    """시장 데이터 분석"""
    # 분석 로직
    return analysis_result

# Tags 추가 (필터링용)
@traceable(
    run_type="chain",
    name="Document Generation Pipeline",
    tags=["document", "contract", "production"]
)
async def generate_contract(data: dict):
    """계약서 생성 파이프라인"""
    # 생성 로직
    return contract
```

### 5.2 `run_type` 옵션

| run_type | 용도 | 예시 |
|----------|------|------|
| `"llm"` | LLM 호출 | GPT-4 API 호출 |
| `"chain"` | 전체 파이프라인 | 멀티스텝 워크플로우 |
| `"tool"` | 도구/유틸리티 함수 | DB 쿼리, API 호출 |
| `"retriever"` | 검색/조회 | RAG 검색, 벡터 검색 |

### 5.3 외부 SDK 래핑

#### OpenAI SDK 래핑

```python
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

# OpenAI 클라이언트 래핑
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
wrapped_client = wrap_openai(client)

# 이제 모든 호출이 자동으로 추적됨
response = await wrapped_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### 5.4 중첩 트레이싱

함수 호출이 계층적으로 추적됨:

```python
@traceable(run_type="chain", name="Full Pipeline")
async def process_query(query: str):
    # Step 1: 의도 분석
    intent = await analyze_intent(query)  # ← 자동으로 자식 트레이스

    # Step 2: 검색
    results = await search_data(intent)  # ← 자동으로 자식 트레이스

    # Step 3: 응답 생성
    response = await generate_response(results)  # ← 자동으로 자식 트레이스

    return response

@traceable(run_type="tool", name="Intent Analysis")
async def analyze_intent(query: str):
    # ...

@traceable(run_type="tool", name="Data Search")
async def search_data(intent):
    # ...

@traceable(run_type="llm", name="Response Generation")
async def generate_response(results):
    # ...
```

**대시보드에서 보이는 구조**:
```
Full Pipeline
├── Intent Analysis
├── Data Search
└── Response Generation
```

---

## 6. 실전 적용 가이드

### 6.1 현재 시스템에 적용하기

#### Step 1: 환경 변수 설정 (필수)

`backend/.env` 파일에 추가:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here
LANGSMITH_PROJECT=holmesnyangz-production
```

#### Step 2: 기존 LangChain 코드는 그대로 사용 (자동 추적)

`team_supervisor.py`, `planning_agent.py` 등의 기존 코드는 **수정 불필요**:
- `ChatOpenAI` 호출 → 자동 추적
- `StateGraph.compile()` → 모든 노드 자동 추적
- `app.ainvoke()` → 전체 워크플로우 자동 추적

#### Step 3: 커스텀 함수에만 선택적으로 `@traceable` 추가

**추천 적용 대상**:

1. **데이터베이스 쿼리** (`backend/app/db/`)
```python
@traceable(run_type="tool", name="Load Chat History")
async def get_chat_history(session_id: str):
    # ...
```

2. **외부 도구** (`backend/app/service_agent/tools/`)
```python
@traceable(run_type="tool", name="Real Estate Search")
async def search_real_estate(query: dict):
    # ...
```

3. **커스텀 분석 로직**
```python
@traceable(run_type="chain", name="ROI Calculator")
async def calculate_roi(property_data: dict):
    # ...
```

### 6.2 프로젝트별 환경 분리

#### 개발/테스트/프로덕션 분리:

```bash
# .env.development
LANGSMITH_PROJECT=holmesnyangz-dev

# .env.test
LANGSMITH_PROJECT=holmesnyangz-test

# .env.production
LANGSMITH_PROJECT=holmesnyangz-production
```

#### 팀별 프로젝트 분리 (선택):

```python
# team_supervisor.py
import os

def get_project_name(team_name: str) -> str:
    base_project = os.getenv("LANGSMITH_PROJECT", "holmesnyangz")
    return f"{base_project}-{team_name}"

# 팀별로 다른 프로젝트에 기록
os.environ["LANGSMITH_PROJECT"] = get_project_name("search")
# search_executor 실행...

os.environ["LANGSMITH_PROJECT"] = get_project_name("analysis")
# analysis_executor 실행...
```

### 6.3 성능 최적화 (선택)

#### 샘플링 설정:

```python
import os

# 프로덕션에서는 10%만 추적 (성능 최적화)
os.environ["LANGSMITH_SAMPLING_RATE"] = "0.1"  # 10%

# 개발 환경에서는 100% 추적
# os.environ["LANGSMITH_SAMPLING_RATE"] = "1.0"  # 100%
```

#### 비동기 전송:

LangSmith는 기본적으로 비동기로 데이터를 전송하므로 **성능 영향 최소화**.

---

## 7. 대시보드 활용

### 7.1 트레이스 보기

1. **LangSmith 대시보드** → `Projects` → 프로젝트 선택
2. **Traces** 탭에서 최근 실행 목록 확인
3. 특정 트레이스 클릭 → 상세 내역 확인

**확인 가능한 정보**:
- 전체 실행 시간
- 각 노드별 실행 시간
- LLM 입력/출력 (프롬프트, 응답)
- 에러 메시지 및 스택 트레이스
- 중간 상태값 (State)

### 7.2 필터링 및 검색

**필터 옵션**:
- **Status**: Success, Error
- **Duration**: 실행 시간 범위
- **Tags**: 커스텀 태그
- **Date**: 날짜 범위

**검색**:
- 쿼리 텍스트로 검색
- 에러 메시지로 검색
- 메타데이터로 검색

### 7.3 성능 분석

#### 토큰 사용량 추적:
- 대시보드에서 `Usage` 탭 확인
- 일별/주별 토큰 사용량 그래프
- 비용 추정 (모델별 요금표 기준)

#### 지연 시간 분석:
- `Latency` 탭에서 병목 구간 식별
- 평균/최대/최소 실행 시간
- 시간에 따른 성능 변화 추적

### 7.4 에러 디버깅

1. **에러 발생 트레이스** 필터링
2. 에러 발생 노드 확인
3. 입력값 검토
4. 스택 트레이스 분석
5. 재현 테스트

---

## 8. 문제 해결

### 8.1 트레이스가 보이지 않을 때

**체크리스트**:

1. ✅ 환경 변수 설정 확인
```python
import os
print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
print(f"LANGSMITH_API_KEY: {os.getenv('LANGSMITH_API_KEY')[:10]}...")
print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
```

2. ✅ API 키 유효성 확인
   - 대시보드에서 API 키 재생성 시도

3. ✅ 네트워크 연결 확인
   - https://api.smith.langchain.com 접속 가능 여부

4. ✅ 프로젝트 이름 확인
   - 대시보드에 프로젝트가 존재하는지 확인

5. ✅ Python 패키지 버전 확인
```bash
pip show langsmith
pip show langgraph
```

### 8.2 성능 저하 시

**원인**:
- 동기 전송 설정 (기본값: 비동기)
- 과도한 데이터 로깅

**해결책**:

1. **샘플링 활성화**
```python
os.environ["LANGSMITH_SAMPLING_RATE"] = "0.1"  # 10%만 추적
```

2. **대용량 데이터 제외**
```python
@traceable(run_type="tool", name="Large Data Processing")
async def process_large_data(data: list):
    # 큰 데이터는 요약만 로깅
    return {"count": len(data), "sample": data[:5]}
```

3. **개발 환경에서만 활성화**
```python
if os.getenv("ENVIRONMENT") == "development":
    os.environ["LANGSMITH_TRACING"] = "true"
else:
    os.environ["LANGSMITH_TRACING"] = "false"
```

### 8.3 API 키 노출 방지

**권장 사항**:

1. ✅ `.env` 파일 사용
2. ✅ `.gitignore`에 `.env` 추가
3. ✅ CI/CD에서 환경 변수로 주입
4. ❌ 코드에 직접 하드코딩 금지

```python
# ❌ 절대 하지 말 것
os.environ["LANGSMITH_API_KEY"] = "lsv2_pt_abcdef123456"

# ✅ 올바른 방법
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("LANGSMITH_API_KEY")
```

### 8.4 자주 묻는 질문 (FAQ)

**Q1: LangGraph 0.6과 호환되나요?**
- A: 네, 완벽히 호환됩니다. LangSmith SDK는 LangGraph 0.6과 1.0 모두 지원합니다.

**Q2: 비용이 얼마나 드나요?**
- A: LangSmith는 무료 티어 제공 (월 5,000 트레이스). 자세한 요금은 https://smith.langchain.com/pricing 참조

**Q3: 프로덕션 환경에서 사용해도 안전한가요?**
- A: 네, 비동기 전송으로 성능 영향 최소화. 샘플링으로 부하 조절 가능.

**Q4: 민감한 데이터가 로깅되나요?**
- A: 기본적으로 모든 입력/출력이 로깅됩니다. 민감 데이터는 `@traceable` 데코레이터에서 제외하거나 마스킹 처리 필요.

**Q5: LangGraph Studio와 차이점은?**
- A: LangGraph Studio는 로컬 개발 도구. LangSmith는 클라우드 기반 프로덕션 모니터링 플랫폼.

---

## 9. 추가 리소스

### 공식 문서
- **LangSmith 공식 문서**: https://docs.langchain.com/langsmith
- **LangGraph 트레이싱 가이드**: https://docs.langchain.com/langsmith/trace-with-langgraph
- **@traceable 데코레이터**: https://docs.langchain.com/langsmith/annotate-code

### 튜토리얼
- **Getting Started**: https://docs.langchain.com/langsmith/walkthrough
- **Evaluation Guide**: https://docs.langchain.com/langsmith/evaluation
- **Production Best Practices**: https://docs.langchain.com/langsmith/production

### 커뮤니티
- **Discord**: https://discord.gg/langchain
- **GitHub Issues**: https://github.com/langchain-ai/langsmith-sdk/issues
- **Community Forum**: https://community.langchain.com

---

## 10. 요약 체크리스트

### 최소 설정 (5분 내 완료)

- [ ] LangSmith 계정 생성
- [ ] API 키 발급
- [ ] `.env` 파일에 환경 변수 추가
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=your_project
```
- [ ] 애플리케이션 실행 후 대시보드 확인

### 고급 설정 (선택)

- [ ] 커스텀 함수에 `@traceable` 데코레이터 추가
- [ ] 프로젝트별 환경 분리
- [ ] 성능 최적화 (샘플링)
- [ ] 에러 알림 설정
- [ ] 평가 데이터셋 구축

---

**문서 작성자**: Claude (Anthropic)
**최종 수정**: 2025-10-30
**버전**: 1.0
**시스템**: holmesnyangz/beta_v001/backend/app/service_agent
