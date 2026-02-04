# LangChain 1.0 & LangGraph 1.0 컴포넌트 완전 가이드

**작성일**: 2025-11-16
**대상**: Octostrator 프로젝트 개발자
**목적**: LangChain/LangGraph 1.0의 모든 활용 가능한 컴포넌트 정리

---

## 목차

1. [LangChain 1.0 Core Components](#1-langchain-10-core-components)
2. [LangGraph 1.0 Libraries](#2-langgraph-10-libraries)
3. [Middleware 시스템](#3-middleware-시스템)
4. [Checkpointer & Persistence](#4-checkpointer--persistence)
5. [Tools & Toolkits](#5-tools--toolkits)
6. [Memory Systems](#6-memory-systems)
7. [Integrations](#7-integrations)
8. [Monitoring & Debugging](#8-monitoring--debugging)

---

## 1. LangChain 1.0 Core Components

### 1.1 create_agent (핵심 API)

**가장 빠른 에이전트 구축 방법**

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

agent = create_agent(
    model=ChatOpenAI(model="gpt-4o-mini"),
    tools=[tool1, tool2, tool3],
    checkpointer=checkpointer,  # 옵션
    middleware=[...],           # 옵션
    name="MyAgent"
)
```

**주요 특징**:
- LangGraph 런타임 기반
- Middleware 자동 통합
- ReAct 패턴 기본 지원
- 스트리밍 지원

### 1.2 Language Models

#### A. ChatOpenAI (OpenAI)

```python
from langchain_openai import ChatOpenAI

# GPT-4o
gpt4o = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=2000,
    streaming=True
)

# GPT-4o-mini (비용 효율적)
gpt4o_mini = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3
)

# 구조화된 출력
from pydantic import BaseModel

class TodoItem(BaseModel):
    title: str
    priority: str

structured_llm = gpt4o.with_structured_output(TodoItem)
result = structured_llm.invoke("Create a high priority task")
```

#### B. ChatAnthropic (Claude)

```python
from langchain_anthropic import ChatAnthropic

# Claude 3.7 (2025년 3월 출시)
claude = ChatAnthropic(
    model="claude-3-7-sonnet",
    temperature=0,
    max_tokens=4096
)

# 툴 호출 지원
claude_with_tools = ChatAnthropic(
    model="claude-3-7-sonnet"
).bind_tools([tool1, tool2])
```

#### C. 기타 모델

```python
# Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
gemini = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

# Cohere
from langchain_cohere import ChatCohere
cohere = ChatCohere(model="command-r-plus")

# Hugging Face
from langchain_huggingface import ChatHuggingFace
hf = ChatHuggingFace(model="meta-llama/Meta-Llama-3-8B-Instruct")
```

### 1.3 Prompts

#### A. ChatPromptTemplate

```python
from langchain_core.prompts import ChatPromptTemplate

# 기본 사용
prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 {role}입니다."),
    ("human", "{input}"),
])

# Few-shot
few_shot_prompt = ChatPromptTemplate.from_messages([
    ("system", "TODO를 생성하는 전문가입니다."),
    ("human", "프로젝트 시작"),
    ("ai", "1. 팀 구성\n2. 킥오프 미팅"),
    ("human", "{input}")
])

# 사용
messages = prompt.format_messages(role="TODO 관리자", input="신규 프로젝트")
```

#### B. PromptTemplate (Legacy, 간단한 경우)

```python
from langchain_core.prompts import PromptTemplate

template = PromptTemplate.from_template(
    "다음 작업에 대한 TODO를 생성하세요: {task}"
)
```

#### C. PipelinePromptTemplate (복잡한 조합)

```python
from langchain_core.prompts import PipelinePromptTemplate, PromptTemplate

# 부분 템플릿
intro_template = PromptTemplate.from_template("역할: {role}\n")
context_template = PromptTemplate.from_template("컨텍스트: {context}\n")
task_template = PromptTemplate.from_template("작업: {task}")

# 조합
full_prompt = PipelinePromptTemplate(
    final_prompt=PromptTemplate.from_template("{intro}{context}{task}"),
    pipeline_prompts=[
        ("intro", intro_template),
        ("context", context_template),
        ("task", task_template)
    ]
)
```

### 1.4 Output Parsers

#### A. PydanticOutputParser

```python
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class TodoList(BaseModel):
    todos: List[dict] = Field(description="TODO 항목 리스트")
    total_count: int = Field(description="총 개수")

parser = PydanticOutputParser(pydantic_object=TodoList)

# 프롬프트에 포맷 지시 추가
prompt = ChatPromptTemplate.from_template(
    "TODO 생성:\n{format_instructions}\n\n작업: {task}"
).partial(format_instructions=parser.get_format_instructions())

# 파싱
chain = prompt | llm | parser
result = chain.invoke({"task": "프로젝트 준비"})
# result는 TodoList 객체
```

#### B. JsonOutputParser

```python
from langchain_core.output_parsers import JsonOutputParser

json_parser = JsonOutputParser()

chain = prompt | llm | json_parser
result = chain.invoke({...})  # dict 반환
```

#### C. StrOutputParser

```python
from langchain_core.output_parsers import StrOutputParser

str_parser = StrOutputParser()

chain = prompt | llm | str_parser
result = chain.invoke({...})  # str 반환
```

### 1.5 Runnables & LCEL

#### A. 기본 체인

```python
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# LCEL (LangChain Expression Language)
chain = (
    {"input": RunnablePassthrough()}
    | prompt
    | llm
    | parser
)

result = chain.invoke("사용자 입력")
```

#### B. RunnableParallel (병렬 실행)

```python
from langchain_core.runnables import RunnableParallel

parallel_chain = RunnableParallel(
    intent=intent_chain,
    entities=entity_chain,
    sentiment=sentiment_chain
)

result = parallel_chain.invoke({"input": "..."})
# result = {
#   "intent": ...,
#   "entities": ...,
#   "sentiment": ...
# }
```

#### C. RunnableBranch (조건부 라우팅)

```python
from langchain_core.runnables import RunnableBranch

branch = RunnableBranch(
    (lambda x: x["type"] == "todo", todo_chain),
    (lambda x: x["type"] == "question", qa_chain),
    default_chain  # fallback
)

result = branch.invoke({"type": "todo", "input": "..."})
```

#### D. RunnableRetry (재시도)

```python
from langchain_core.runnables import RunnableRetry

retry_chain = RunnableRetry(
    runnable=llm_chain,
    max_attempts=3,
    wait_exponential_jitter=True
)
```

---

## 2. LangGraph 1.0 Libraries

### 2.1 langgraph-supervisor

**계층적 멀티 에이전트 시스템**

```bash
pip install langgraph-supervisor
```

```python
from langgraph_supervisor import create_supervisor

supervisor = create_supervisor(
    agents=[agent1, agent2, agent3],
    model=ChatOpenAI(model="gpt-4o"),
    prompt="Supervisor 지시사항...",
    include_conversation_history=True,  # 전체 히스토리 포함 (기본)
    # 또는
    include_conversation_history="last_message"  # 마지막만
)

graph = supervisor.compile(checkpointer=checkpointer)
```

**고급 옵션**:
```python
from langgraph_supervisor import create_supervisor, SupervisorConfig

config = SupervisorConfig(
    # 핸드오프 도구 커스터마이즈
    handoff_tool_name_template="{agent_name}_tool",
    handoff_tool_description_template="Transfer to {agent_name} for {task}",

    # 추가 인자
    enable_task_description=True,  # 핸드오프 시 task 인자 추가

    # 메시지 필터링
    message_filter=lambda msg: msg.type != "system"
)

supervisor = create_supervisor(
    agents=[agent1, agent2],
    model=llm,
    config=config
)
```

### 2.2 langgraph-swarm

**동적 에이전트 핸드오프 시스템**

```bash
pip install langgraph-swarm
```

```python
from langgraph_swarm import create_swarm, create_handoff_tool

# Handoff 도구 생성
handoff_to_researcher = create_handoff_tool(
    to_agent="researcher",
    name="transfer_to_researcher",
    description="연구 작업이 필요할 때 Researcher에게 전달",
    # LLM이 채울 수 있는 추가 인자
    additional_args={
        "task_description": {
            "type": "string",
            "description": "연구 작업 설명"
        }
    }
)

# 에이전트에 핸드오프 도구 포함
researcher = create_agent(
    model=llm,
    tools=[research_tool, handoff_to_writer],
    name="researcher"
)

writer = create_agent(
    model=llm,
    tools=[write_tool, handoff_to_researcher],
    name="writer"
)

# Swarm 생성
swarm = create_swarm(
    agents=[researcher, writer],
    initial_agent="researcher",
    include_conversation_history=True
)

graph = swarm.compile(checkpointer=checkpointer)
```

**InjectedState 사용** (고급):
```python
from langgraph_swarm import InjectedState, InjectedToolCallId
from langchain_core.tools import tool

@tool
def custom_handoff_tool(
    task: str,
    state: InjectedState,  # 현재 상태 자동 주입
    tool_call_id: InjectedToolCallId  # 도구 호출 ID 자동 주입
):
    """커스텀 핸드오프 도구"""
    # 상태 접근
    current_context = state["context"]

    # 핸드오프 메시지
    return {
        "messages": [{
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": f"Transferring task: {task}"
        }],
        "handoff_to": "target_agent",
        "task_context": task
    }
```

### 2.3 langgraph-checkpoint-postgres

**PostgreSQL 기반 체크포인터**

```bash
pip install langgraph-checkpoint-postgres
```

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 기본 사용
checkpointer = AsyncPostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost:5432/db"
)
await checkpointer.setup()  # 테이블 생성

# 수동 연결 (세밀한 제어)
from psycopg import AsyncConnection
from psycopg.rows import dict_row

conn = await AsyncConnection.connect(
    "postgresql://...",
    autocommit=True,  # 필수!
    row_factory=dict_row  # 필수!
)

checkpointer = AsyncPostgresSaver(conn)
await checkpointer.setup()
```

**체크포인트 관리**:
```python
# 저장
await checkpointer.aput(
    config={"configurable": {"thread_id": "123"}},
    checkpoint=checkpoint_data,
    metadata={"user_id": "user1", "phase": "cognitive"},
    new_versions={}
)

# 로드
checkpoint = await checkpointer.aget(
    config={"configurable": {"thread_id": "123"}}
)

# 히스토리 조회
async for cp in checkpointer.alist(
    config={"configurable": {"thread_id": "123"}},
    limit=10
):
    print(cp.checkpoint_id, cp.metadata)
```

### 2.4 LangGraph Prebuilt Components

#### A. create_react_agent

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

react_agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4o"),
    tools=[tool1, tool2, tool3],
    checkpointer=checkpointer,
    state_modifier="당신은 TODO 관리 전문가입니다."  # System message
)

# 실행
result = await react_agent.ainvoke(
    {"messages": [("human", "TODO 생성해줘")]},
    config={"configurable": {"thread_id": "123"}}
)
```

#### B. ToolNode

```python
from langgraph.prebuilt import ToolNode

# 도구 노드 (도구 실행 전용)
tool_node = ToolNode(tools=[tool1, tool2, tool3])

# 그래프에 추가
builder.add_node("tools", tool_node)
```

#### C. tools_condition

```python
from langgraph.prebuilt import tools_condition

# 조건부 엣지: 도구 호출 여부 판단
builder.add_conditional_edges(
    "agent",
    tools_condition,  # 내장 조건 함수
    {
        "tools": "tools",  # 도구 호출 필요 시
        "__end__": END     # 종료 시
    }
)
```

---

## 3. Middleware 시스템

### 3.1 내장 Middleware

#### A. PIIMiddleware

```python
from langchain.agents.middleware import PIIMiddleware

# Email 삭제
email_pii = PIIMiddleware(
    pii_type="email",
    strategy="redact",
    apply_to_input=True,
    apply_to_output=False
)

# Credit Card 마스킹
card_pii = PIIMiddleware(
    pii_type="credit_card",
    strategy="mask",  # **** **** **** 1234
    apply_to_input=True
)

# IP 주소 해싱
ip_pii = PIIMiddleware(
    pii_type="ip",
    strategy="hash",
    apply_to_input=True
)

# 커스텀 PII (정규식)
api_key_pii = PIIMiddleware(
    pii_type="api_key",
    detector=r"sk-[a-zA-Z0-9]{32}",
    strategy="block",  # 오류 발생
    apply_to_input=True
)

# 지원 타입: email, credit_card, ip, mac_address, url, ssn (US), phone
```

#### B. HumanInTheLoopMiddleware

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

hitl = HumanInTheLoopMiddleware(
    interrupt_on={
        # 도구별 설정
        "dangerous_tool": {
            "allowed_decisions": ["approve", "reject"],  # edit 불가
            "default_decision": "reject",
            "require_reason": True  # 거부 시 이유 필수
        },
        "moderate_tool": {
            "allowed_decisions": ["approve", "edit", "reject"],
            "timeout_seconds": 300  # 5분 타임아웃
        },
        "safe_tool": False  # 자동 승인
    },

    # 글로벌 설정
    approval_required_by_default=False,
    global_timeout=600
)

# 체크포인터 필수!
agent = create_agent(
    model=llm,
    tools=[dangerous_tool, moderate_tool, safe_tool],
    checkpointer=checkpointer,
    middleware=[hitl]
)
```

#### C. SummarizationMiddleware

```python
from langchain.agents.middleware import SummarizationMiddleware

summarization = SummarizationMiddleware(
    max_tokens=4000,
    summarization_model=ChatOpenAI(model="gpt-4o-mini"),

    # 전략
    strategy="rolling",  # 또는 "truncate"

    # 보존 설정
    preserve_system_messages=True,
    preserve_last_n_messages=10,
    preserve_first_n_messages=2,

    # 커스텀 요약 프롬프트
    summarization_prompt="다음 대화를 간결하게 요약: {conversation}"
)
```

### 3.2 커스텀 Middleware

```python
from langchain.agents.middleware import BaseMiddleware
from typing import Any, Dict

class CustomMiddleware(BaseMiddleware):
    """커스텀 미들웨어 템플릿"""

    async def before_agent_step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 단계 실행 전"""
        # 상태 수정, 로깅 등
        print(f"[Before Step] State: {state}")
        return state

    async def after_agent_step(self, state: Dict[str, Any], result: Any) -> Any:
        """에이전트 단계 실행 후"""
        print(f"[After Step] Result: {result}")
        return result

    async def before_tool_call(self, tool_name: str, tool_input: Dict) -> Dict:
        """도구 호출 전"""
        print(f"[Before Tool] {tool_name}: {tool_input}")
        # 입력 검증, 변환 등
        return tool_input

    async def after_tool_call(self, tool_name: str, result: Any) -> Any:
        """도구 호출 후"""
        print(f"[After Tool] {tool_name}: {result}")
        return result

    async def on_error(self, error: Exception) -> None:
        """에러 발생 시"""
        print(f"[Error] {error}")
```

---

## 4. Checkpointer & Persistence

### 4.1 AsyncPostgresSaver (프로덕션)

**이미 설명됨 (2.3 참조)**

### 4.2 MemorySaver (개발/테스트)

```python
from langgraph.checkpoint.memory import MemorySaver

# 인메모리 체크포인터
memory_saver = MemorySaver()

graph = builder.compile(checkpointer=memory_saver)

# 휘발성 - 프로세스 종료 시 소실
```

### 4.3 SqliteSaver (간단한 영속성)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# SQLite 파일 사용
sqlite_saver = SqliteSaver.from_conn_string("checkpoints.db")

# 또는 인메모리 SQLite
sqlite_saver = SqliteSaver.from_conn_string(":memory:")

graph = builder.compile(checkpointer=sqlite_saver)
```

### 4.4 AsyncSqliteSaver (비동기)

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async_sqlite = AsyncSqliteSaver.from_conn_string("checkpoints.db")
await async_sqlite.setup()

graph = builder.compile(checkpointer=async_sqlite)
```

---

## 5. Tools & Toolkits

### 5.1 도구 정의 방법

#### A. @tool 데코레이터 (권장)

```python
from langchain_core.tools import tool
from typing import Annotated

@tool
def search_database(
    query: Annotated[str, "검색 쿼리"],
    limit: Annotated[int, "결과 개수"] = 10
) -> str:
    """데이터베이스에서 정보를 검색합니다."""
    # 구현
    return f"Found {limit} results for {query}"
```

#### B. StructuredTool (동적 생성)

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

class SearchInput(BaseModel):
    query: str
    limit: int = 10

def search_func(query: str, limit: int = 10) -> str:
    return f"Results: {limit}"

search_tool = StructuredTool.from_function(
    func=search_func,
    name="search_database",
    description="데이터베이스 검색",
    args_schema=SearchInput
)
```

#### C. Tool 클래스 (복잡한 경우)

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class CustomSearchInput(BaseModel):
    query: str = Field(description="검색 쿼리")
    filters: dict = Field(default={}, description="필터")

class CustomSearchTool(BaseTool):
    name = "custom_search"
    description = "커스텀 검색 도구"
    args_schema = CustomSearchInput

    def _run(self, query: str, filters: dict = {}) -> str:
        """동기 실행"""
        return f"Search: {query} with {filters}"

    async def _arun(self, query: str, filters: dict = {}) -> str:
        """비동기 실행"""
        # await async_operation()
        return f"Async search: {query}"
```

### 5.2 내장 Toolkits

#### A. Retriever Tools

```python
from langchain.tools.retriever import create_retriever_tool
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Vector Store
vectorstore = FAISS.from_texts(
    ["문서1", "문서2"],
    embedding=OpenAIEmbeddings()
)

# Retriever Tool 생성
retriever_tool = create_retriever_tool(
    retriever=vectorstore.as_retriever(),
    name="knowledge_base",
    description="회사 지식 베이스 검색"
)
```

#### B. SQL Database Tools

```python
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

db = SQLDatabase.from_uri("postgresql://...")

toolkit = SQLDatabaseToolkit(db=db, llm=llm)

tools = toolkit.get_tools()
# - query_sql_db: SQL 쿼리 실행
# - schema_sql_db: 스키마 조회
# - list_tables_sql_db: 테이블 목록
# - query_sql_checker: 쿼리 검증
```

#### C. API Tools

```python
from langchain_community.tools import APIOperation
from langchain_community.utilities import OpenAPISpec

# OpenAPI 스펙에서 도구 생성
spec = OpenAPISpec.from_url("https://api.example.com/openapi.json")

tools = []
for operation_id in spec.get_operation_ids():
    tool = APIOperation.from_openapi_spec(spec, operation_id)
    tools.append(tool)
```

#### D. File System Tools

```python
from langchain_community.tools.file_management import (
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
    CopyFileTool,
    DeleteFileTool,
    MoveFileTool
)

file_tools = [
    ReadFileTool(),
    WriteFileTool(),
    ListDirectoryTool(),
    CopyFileTool(),
    DeleteFileTool(),
    MoveFileTool()
]
```

---

## 6. Memory Systems

### 6.1 LangGraph 내장 메모리 (Checkpointer)

**이미 설명됨 - 체크포인터가 메모리 역할**

### 6.2 LangChain Memory (Legacy, 호환성)

#### A. ConversationBufferMemory

```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# 추가
memory.save_context(
    {"input": "안녕"},
    {"output": "안녕하세요"}
)

# 조회
messages = memory.load_memory_variables({})["chat_history"]
```

#### B. ConversationSummaryMemory

```python
from langchain.memory import ConversationSummaryMemory

summary_memory = ConversationSummaryMemory(
    llm=ChatOpenAI(model="gpt-4o-mini"),
    memory_key="chat_history",
    return_messages=True
)

# 자동으로 요약
```

#### C. VectorStoreMemory (시맨틱 검색)

```python
from langchain.memory import VectorStoreRetrieverMemory
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

vectorstore = FAISS.from_texts([], embedding=OpenAIEmbeddings())

memory = VectorStoreRetrieverMemory(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
)

# 저장
memory.save_context({"input": "..."}, {"output": "..."})

# 관련 기억 검색
relevant = memory.load_memory_variables({"input": "현재 질문"})
```

---

## 7. Integrations

### 7.1 Vector Stores

#### A. FAISS (로컬)

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

vectorstore = FAISS.from_texts(
    texts=["문서1", "문서2"],
    embedding=OpenAIEmbeddings()
)

# 저장
vectorstore.save_local("faiss_index")

# 로드
vectorstore = FAISS.load_local("faiss_index", OpenAIEmbeddings())

# 검색
results = vectorstore.similarity_search("쿼리", k=5)
```

#### B. Chroma (간단한 벡터 DB)

```python
from langchain_community.vectorstores import Chroma

vectorstore = Chroma.from_texts(
    texts=["문서1", "문서2"],
    embedding=OpenAIEmbeddings(),
    persist_directory="./chroma_db"
)
```

#### C. Pinecone (프로덕션)

```python
from langchain_community.vectorstores import Pinecone
import pinecone

pinecone.init(api_key="...", environment="...")

vectorstore = Pinecone.from_texts(
    texts=["문서1", "문서2"],
    embedding=OpenAIEmbeddings(),
    index_name="my-index"
)
```

### 7.2 Document Loaders

```python
# PDF
from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader("document.pdf")
docs = loader.load()

# CSV
from langchain_community.document_loaders import CSVLoader
loader = CSVLoader("data.csv")

# Web
from langchain_community.document_loaders import WebBaseLoader
loader = WebBaseLoader("https://...")

# Notion
from langchain_community.document_loaders import NotionDirectoryLoader
loader = NotionDirectoryLoader("notion_export/")
```

### 7.3 Text Splitters

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

chunks = splitter.split_documents(docs)
```

### 7.4 Retrievers

```python
# Vector Store Retriever
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)

# MMR (Maximum Marginal Relevance)
mmr_retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 20}
)

# Ensemble Retriever (여러 retriever 결합)
from langchain.retrievers import EnsembleRetriever

ensemble = EnsembleRetriever(
    retrievers=[retriever1, retriever2],
    weights=[0.5, 0.5]
)
```

---

## 8. Monitoring & Debugging

### 8.1 LangSmith (공식 모니터링)

```python
import os

# 환경 변수 설정
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"
os.environ["LANGCHAIN_PROJECT"] = "octostrator"

# 자동으로 모든 LLM 호출, 체인 실행 등이 추적됨
```

**기능**:
- 모든 LLM 호출 추적
- 비용 분석
- 성능 메트릭
- 오류 추적
- A/B 테스팅

### 8.2 LangGraph Studio (시각적 디버깅)

**그래프 시각화 및 단계별 디버깅**

```bash
pip install langgraph-studio
langgraph-studio
```

### 8.3 커스텀 로깅

```python
import logging

# LangChain 로깅
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("langchain")

# 또는 콜백
from langchain.callbacks import StdOutCallbackHandler

handler = StdOutCallbackHandler()

llm.invoke("test", config={"callbacks": [handler]})
```

---

## 9. 고급 컴포넌트

### 9.1 LangChain MCP Adapters (2025년 3월 신규)

**Anthropic Model Context Protocol (MCP) 도구 사용**

```python
from langchain_mcp import MCPAdapter

# MCP 도구를 LangChain 도구로 변환
mcp_tools = MCPAdapter.from_mcp_server("mcp://server-url")

agent = create_agent(
    model=llm,
    tools=mcp_tools
)
```

### 9.2 Async/Streaming

```python
# 비동기 실행
result = await chain.ainvoke({"input": "..."})

# 스트리밍
async for chunk in chain.astream({"input": "..."}):
    print(chunk, end="", flush=True)

# 이벤트 스트리밍
async for event in chain.astream_events({"input": "..."}):
    if event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="")
```

### 9.3 Batch Processing

```python
# 배치 실행
results = chain.batch([
    {"input": "질문1"},
    {"input": "질문2"},
    {"input": "질문3"}
])

# 비동기 배치
results = await chain.abatch([...])
```

---

## 10. 프로덕션 체크리스트

### 필수 컴포넌트

- [ ] **LLM**: ChatOpenAI (gpt-4o-mini)
- [ ] **Checkpointer**: AsyncPostgresSaver
- [ ] **Middleware**: PIIMiddleware, HumanInTheLoopMiddleware
- [ ] **Tools**: 최소 3개 이상 커스텀 도구
- [ ] **Error Handling**: try/except, RunnableRetry
- [ ] **Logging**: LangSmith 또는 커스텀
- [ ] **Monitoring**: LangSmith
- [ ] **Testing**: 단위 테스트, 통합 테스트

### 권장 컴포넌트

- [ ] **SummarizationMiddleware**: 긴 대화 관리
- [ ] **Vector Store**: 지식 베이스 (FAISS/Pinecone)
- [ ] **Retriever**: RAG 구현
- [ ] **Output Parsers**: 구조화된 출력
- [ ] **Runnables**: LCEL로 체인 구성

---

## 결론

LangChain 1.0과 LangGraph 1.0은 **프로덕션 준비가 완료된** 풍부한 컴포넌트 생태계를 제공합니다.

**핵심 요약**:
1. **create_agent**: 가장 빠른 에이전트 구축
2. **Middleware**: 프로덕션 필수 (PII, HITL, Summarization)
3. **langgraph-supervisor/swarm**: 멀티 에이전트 패턴
4. **AsyncPostgresSaver**: 영구 상태 저장
5. **LangSmith**: 모니터링 및 디버깅

모든 컴포넌트를 조합하여 **엔터프라이즈급 AI 에이전트 시스템**을 구축할 수 있습니다.
