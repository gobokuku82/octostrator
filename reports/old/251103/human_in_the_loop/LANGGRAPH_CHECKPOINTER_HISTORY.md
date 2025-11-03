# LangGraph Checkpointer 역사 및 버전 정보

**작성일:** 2025-10-21
**목적:** Checkpointer의 등장 배경과 버전별 발전 과정 이해

---

## 🎯 핵심 요약

### Checkpointer가 최상위 개념인 이유

```
┌─────────────────────────────────────────┐
│  LangGraph Framework (최상위)          │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Checkpointer (기반 인프라) ← 필수!    │
│  - 없으면 HITL 불가능                   │
│  - 없으면 State 유지 불가능             │
│  - 없으면 Time Travel 불가능            │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Human-in-the-Loop (Feature)            │
│  - interrupt()                          │
│  - Command                              │
└─────────────────────────────────────────┘
```

**비유:**
- Checkpointer = 건물의 기초 공사
- HITL = 건물의 특정 기능 (엘리베이터)
- interrupt/Command = 엘리베이터 버튼

**기초 공사 없이는 엘리베이터를 설치할 수 없듯이,**
**Checkpointer 없이는 HITL을 구현할 수 없습니다.**

---

## 📅 LangGraph 버전 히스토리

### Timeline

```
2023-??-??  LangGraph v0.1.x
            ├─ Checkpointer 개념 최초 도입
            ├─ InMemorySaver (실험용)
            └─ Database-agnostic 설계

2024-08-12  LangGraph v0.2.0 (중요!)
            ├─ Checkpointer 라이브러리 생태계 구축
            ├─ langgraph-checkpoint (base interface)
            ├─ langgraph-checkpoint-sqlite
            ├─ langgraph-checkpoint-postgres
            └─ Breaking Changes:
                - thread_ts → checkpoint_id
                - parent_ts → parent_checkpoint_id

2024-10-??  LangGraph v0.6.x
            ├─ Command primitive 도입
            ├─ interrupt() 개선
            └─ HITL 기능 강화

2024-10-17  LangGraph v1.0.0 (최신)
            ├─ Python 3.14 지원
            ├─ Production-ready
            └─ Documentation 개선

2024-10-20  checkpoint==3.0.0
            ├─ JSON 타입 역직렬화 제한
            ├─ Python 3.9 지원 종료
            └─ 0.6.x 브랜치와 호환
```

---

## 🔍 버전별 상세 분석

### v0.1.x (2023년 중반, 추정)

**Checkpointer 최초 등장**

```python
# v0.1.x 시절 - 기본 개념만 존재
from langgraph.checkpoint import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

**특징:**
- ✅ 기본 Checkpointer 인터페이스 정의
- ✅ InMemorySaver 제공 (실험용)
- ❌ 프로덕션용 구현 없음 (Postgres 등)
- ❌ 별도 라이브러리 분리 안 됨

**제한사항:**
- 메모리에만 저장 (서버 재시작 시 소실)
- 멀티 인스턴스 지원 안 됨
- 프로덕션 부적합

---

### v0.2.0 (2024년 8월 12일) - 🎉 Major Update

**"Checkpointer Ecosystem 구축"**

**공식 발표:**
> "LangGraph v0.2: Increased customization with new checkpointer libraries"
> - LangChain Blog, August 12, 2024

**새로운 기능:**

1. **Checkpointer 라이브러리 분리**
   ```bash
   # v0.2.0부터 별도 패키지로 분리
   pip install langgraph-checkpoint              # Base interface
   pip install langgraph-checkpoint-sqlite       # SQLite (local)
   pip install langgraph-checkpoint-postgres     # Postgres (production)
   ```

2. **BaseCheckpointSaver Interface**
   ```python
   from langgraph.checkpoint import BaseCheckpointSaver

   class CustomCheckpointer(BaseCheckpointSaver):
       """Custom checkpointer 구현 가능"""
       async def aget(self, config):
           ...
       async def aput(self, config, checkpoint, metadata):
           ...
   ```

3. **AsyncPostgresSaver (프로덕션용)**
   ```python
   # v0.2.0부터 공식 지원
   from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

   checkpointer = await AsyncPostgresSaver.from_conn_string(
       "postgresql://user:pass@localhost/db"
   )
   ```

**Breaking Changes:**
```python
# v0.1.x
state.values["thread_ts"]
state.values["parent_ts"]

# v0.2.0+ (변경됨!)
state.values["checkpoint_id"]
state.values["parent_checkpoint_id"]
```

**영향:**
- 기존 코드 수정 필요
- 데이터베이스 스키마 변경
- Migration 스크립트 필요

---

### v0.6.x (2024년 10월) - HITL 강화

**Command Primitive 도입**

```python
# v0.6.0부터 가능
from langgraph.types import Command, interrupt

# interrupt() 사용
def approval_node(state):
    user_input = interrupt({"action": "approve"})
    return {"result": user_input}

# Command로 재개
result = graph.invoke(
    Command(resume="approved"),
    config=config
)
```

**주요 개선사항:**
1. **Command 객체**
   - `Command(resume=...)`: 재개
   - `Command(update=...)`: State 업데이트
   - `Command(goto=...)`: 특정 노드로 이동

2. **interrupt() 개선**
   - 더 안정적인 중단/재개
   - 여러 interrupt 동시 처리 가능
   - 타임아웃 지원

3. **Checkpointer 호환성**
   - checkpoint==3.0 호환 (v0.6.11)
   - 성능 최적화

---

### v1.0.0 (2024년 10월 17일) - Production Ready

**안정화 버전**

**주요 특징:**
- ✅ Production-ready
- ✅ Python 3.14 지원
- ✅ Breaking changes 최소화
- ✅ 문서 개선

**Checkpointer 상태:**
- AsyncPostgresSaver 안정화
- SQLite Checkpointer 개선
- Redis Checkpointer (커뮤니티)

---

## 🤔 왜 교재에 Checkpointer가 없을까?

### 가능한 이유들

#### 1. **교재 출판 시기**

```
2023년 초반 교재 (v0.1.x 이전)
  ↓
Checkpointer 개념 없음 또는 미성숙

2023년 중반 교재 (v0.1.x)
  ↓
Checkpointer 있지만 InMemorySaver만
프로덕션 사용 불가능

2024년 초반 교재 (v0.2.x 이전)
  ↓
Checkpointer 있지만 생태계 미비

2024년 중반 이후 교재 (v0.2.0+)
  ↓
✅ Checkpointer 완전 지원
```

#### 2. **교재 범위**

**초급 교재:**
- 기본 Graph 구성에 집중
- State management만 다룸
- Checkpointer는 고급 주제로 분류

**중급 교재:**
- Multi-agent 시스템
- Tool calling
- Checkpointer는 Optional로 다룸

**고급 교재:**
- ✅ Checkpointer 필수
- ✅ HITL 구현
- ✅ Production deployment

#### 3. **기술 변화 속도**

```
교재 집필 (6개월)
  ↓
편집 및 검토 (3개월)
  ↓
출판 (2개월)
  ↓
총 11개월 소요

그 사이 LangGraph는:
- v0.1 → v0.2 → v0.6 → v1.0 (4번 메이저 업데이트!)
```

---

## 📚 Checkpointer 학습 자료

### 공식 문서 (최신)

1. **LangGraph Persistence**
   - https://langchain-ai.github.io/langgraph/concepts/persistence/
   - Checkpointer 개념 설명

2. **Checkpointer Reference**
   - https://langchain-ai.github.io/langgraph/reference/checkpoints/
   - API 레퍼런스

3. **Add Memory Tutorial**
   - https://langchain-ai.github.io/langgraph/tutorials/get-started/3-add-memory/
   - 실습 예제

4. **HITL How-to**
   - https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/
   - Checkpointer 필수 사용

### 블로그 포스트

1. **LangGraph v0.2 Release**
   - https://blog.langchain.com/langgraph-v0-2/
   - Checkpointer 생태계 소개

2. **Human-in-the-Loop with LangGraph**
   - https://medium.com/the-advanced-school-of-ai/human-in-the-loop-with-langgraph-mastering-interrupts-and-commands-9e1cf2183ae3
   - interrupt & Command 상세 설명

---

## 🔧 홈즈냥즈의 Checkpointer 사용

### 현재 구현

**파일:** `backend/app/service_agent/foundation/checkpointer.py`

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def create_checkpointer() -> AsyncPostgresSaver:
    """
    AsyncPostgresSaver 생성

    v0.2.0+ 기능 사용
    """
    checkpointer = await AsyncPostgresSaver.from_conn_string(
        settings.DATABASE_URL
    )

    # Setup (테이블 생성 및 마이그레이션)
    await checkpointer.setup()

    return checkpointer
```

**사용된 버전:**
- LangGraph >= 0.6.0
- langgraph-checkpoint-postgres >= 1.0.0

**장점:**
- ✅ Production-ready (PostgreSQL)
- ✅ 서버 재시작 후에도 State 유지
- ✅ Multi-instance 지원
- ✅ HITL 구현 가능

**데이터베이스 테이블:**
```sql
-- AsyncPostgresSaver가 자동 생성
checkpoints
checkpoint_writes
checkpoint_blobs
checkpoint_migrations  -- 10개 마이그레이션 완료
```

---

## 💡 핵심 이해

### Checkpointer가 "최상위"인 이유

```python
# Checkpointer 없으면?

# ❌ HITL 불가능
def approval_node(state):
    user_input = interrupt(...)  # Error! Checkpointer 필요
    return state

# ❌ Memory 불가능
graph.invoke({"query": "..."}, config={"thread_id": "123"})
# 이전 대화 기억 못함 (State 저장 안 됨)

# ❌ Time Travel 불가능
state = graph.get_state(config)  # Error!
```

```python
# Checkpointer 있으면?

checkpointer = await create_checkpointer()
graph = builder.compile(checkpointer=checkpointer)

# ✅ HITL 가능
interrupt(...)  # OK!

# ✅ Memory 가능
# 같은 thread_id로 재호출 시 이전 대화 기억

# ✅ Time Travel 가능
state = graph.get_state(config)  # OK!
state_history = graph.get_state_history(config)  # OK!
```

### 설정을 처음에 정해야 하는 이유

```python
# Graph 컴파일 시 Checkpointer 고정
graph = builder.compile(checkpointer=checkpointer)

# 이후 변경 불가!
# graph.checkpointer = new_checkpointer  # Error!

# 이유:
# 1. Graph는 immutable (변경 불가)
# 2. Checkpointer는 Graph의 핵심 인프라
# 3. 런타임 중 변경 시 State 불일치 발생 위험
```

**Best Practice:**
```python
# 1. Checkpointer 먼저 생성
checkpointer = await AsyncPostgresSaver.from_conn_string(...)

# 2. Graph 빌드
builder = StateGraph(State)
builder.add_node(...)
builder.add_edge(...)

# 3. Checkpointer와 함께 컴파일 (단 1회)
graph = builder.compile(checkpointer=checkpointer)

# 4. 평생 사용
# graph는 재사용, checkpointer는 변경 불가
```

---

## 📊 버전 비교표

| Feature | v0.1.x | v0.2.0 | v0.6.x | v1.0.0 |
|---------|--------|--------|--------|--------|
| **Checkpointer** | Basic | ✅ Full | ✅ Full | ✅ Full |
| **InMemorySaver** | ✅ | ✅ | ✅ | ✅ |
| **AsyncPostgresSaver** | ❌ | ✅ | ✅ | ✅ |
| **SQLiteSaver** | ❌ | ✅ | ✅ | ✅ |
| **interrupt()** | ❌ | Basic | ✅ Full | ✅ Full |
| **Command** | ❌ | ❌ | ✅ | ✅ |
| **HITL** | ❌ | Partial | ✅ | ✅ |
| **Time Travel** | ❌ | ✅ | ✅ | ✅ |
| **Production Ready** | ❌ | ⚠️ | ⚠️ | ✅ |

---

## 🎓 학습 순서 추천

### 1단계: Checkpointer 기초 (필수)
- Persistence 개념 이해
- InMemorySaver 실습
- thread_id와 checkpoint_id 이해

### 2단계: 프로덕션 Checkpointer
- AsyncPostgresSaver 설정
- Database 스키마 이해
- Migration 관리

### 3단계: HITL 구현
- interrupt() 사용법
- Command primitive
- Approval workflow 구현

### 4단계: 고급 기능
- Time Travel
- State 조작
- Custom Checkpointer 구현

---

## 🔗 참고 자료

### 공식 문서
- [LangGraph v0.2 Release](https://blog.langchain.com/langgraph-v0-2/)
- [Persistence Concepts](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [Checkpointer Reference](https://langchain-ai.github.io/langgraph/reference/checkpoints/)

### GitHub
- [LangGraph Releases](https://github.com/langchain-ai/langgraph/releases)
- [langgraph-checkpoint PyPI](https://pypi.org/project/langgraph-checkpoint/)

### 커뮤니티
- [LangChain Discord](https://discord.gg/langchain)
- [GitHub Discussions](https://github.com/langchain-ai/langgraph/discussions)

---

## ✅ 결론

### 질문 1: Checkpointer는 언제 나왔는가?

**답변:**
- **v0.1.x (2023년 중반)**: 최초 도입, 기본 개념만
- **v0.2.0 (2024년 8월 12일)**: 완전한 생태계 구축 🎉
- **v0.6.x (2024년 10월)**: HITL과 통합
- **v1.0.0 (2024년 10월 17일)**: Production-ready

### 질문 2: 왜 교재에 없는가?

**답변:**
1. 교재 출판 시기가 v0.2.0 이전일 가능성 높음
2. 초급 교재는 고급 주제로 분류하여 제외
3. 기술 변화 속도가 매우 빠름 (6개월마다 메이저 업데이트)

### 질문 3: 왜 최상위 개념인가?

**답변:**
- HITL, Memory, Time Travel 모두 **Checkpointer에 의존**
- 없으면 어떤 고급 기능도 사용 불가
- Graph 컴파일 시 반드시 설정해야 함
- 런타임 중 변경 불가 (인프라이기 때문)

**비유:** Checkpointer = 건물의 기초 공사

---

**Last Updated:** 2025-10-21
**LangGraph Version:** v1.0.0
**Checkpoint Version:** v3.0.0
**Status:** ✅ 완료
