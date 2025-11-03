# LangChain Messages 완전 가이드

## 목차
1. [LangChain Messages란?](#langchain-messages란)
2. [Message 타입들](#message-타입들)
3. [현재 프로젝트 사용 분석](#현재-프로젝트-사용-분석)
4. [사용해야 하는 경우](#사용해야-하는-경우)
5. [State와의 관계](#state와의-관계)
6. [마이그레이션 가이드](#마이그레이션-가이드)

---

## LangChain Messages란?

### 개념

LangChain의 **표준화된 대화 메시지 형식**입니다. LLM과의 대화를 구조화하고 타입 안전하게 만듭니다.

```python
from langchain_core.messages import (
    SystemMessage,     # 시스템 지시사항
    HumanMessage,      # 사용자 메시지
    AIMessage,         # AI 응답
    ToolMessage,       # 도구 실행 결과
    FunctionMessage,   # 함수 호출 결과 (레거시)
    ChatMessage,       # 커스텀 role
)
```

### ❌ 오해: "프리필터나 설정값"
### ✅ 진실: "대화 메시지의 타입 정의"

```python
# Messages는 대화 내용을 담는 데이터 구조입니다

# 잘못된 이해
messages = [...]  # 프리필터? 설정?

# 올바른 이해
messages = [
    SystemMessage(content="당신은 부동산 상담 AI입니다"),  # 시스템 지시
    HumanMessage(content="강남 전세 5억 적정해?"),      # 사용자 질문
    AIMessage(content="네, 적정 가격입니다")           # AI 답변
]
# → 이것이 LLM에 전달되는 대화 이력
```

---

## Message 타입들

### 1. SystemMessage - 시스템 프롬프트

```python
from langchain_core.messages import SystemMessage

# 역할: LLM에게 역할/규칙 부여
system_msg = SystemMessage(
    content="""당신은 부동산 전문 상담 AI입니다.

규칙:
1. 법률 정보는 정확하게
2. 시세 정보는 데이터 기반으로
3. 친절한 말투 사용
"""
)

# OpenAI API 형식으로 변환되면:
# {"role": "system", "content": "당신은 부동산..."}
```

**용도**:
- LLM의 역할 정의 (persona)
- 답변 형식 지정
- 제약사항 설정

### 2. HumanMessage - 사용자 메시지

```python
from langchain_core.messages import HumanMessage

# 역할: 사용자 입력
human_msg = HumanMessage(
    content="강남구 아파트 전세금 5억에서 5.5억으로 올리는게 법적으로 가능해?"
)

# OpenAI API 형식:
# {"role": "user", "content": "강남구 아파트..."}
```

**용도**:
- 사용자 질문
- 사용자 피드백
- 추가 정보 요청

### 3. AIMessage - AI 응답

```python
from langchain_core.messages import AIMessage

# 역할: AI의 답변
ai_msg = AIMessage(
    content="""네, 법적으로 가능합니다.

임대차보호법에 따르면 전세금 인상은 5% 이내로 제한됩니다.
5억 → 5.5억은 10% 인상이므로 법적 한도를 초과합니다.
세입자는 이를 거부할 수 있습니다."""
)

# OpenAI API 형식:
# {"role": "assistant", "content": "네, 법적으로..."}
```

**용도**:
- AI의 답변 저장
- 대화 이력 구축
- 컨텍스트 유지

### 4. ToolMessage - 도구 실행 결과

```python
from langchain_core.messages import ToolMessage, AIMessage

# 시나리오: AI가 도구를 호출하고 결과를 받음

# Step 1: AI가 도구 호출 요청
ai_msg = AIMessage(
    content="",
    tool_calls=[
        {
            "id": "call_123",
            "name": "search_real_estate",
            "args": {"region": "강남구", "type": "apartment"}
        }
    ]
)

# Step 2: 도구 실행 결과
tool_msg = ToolMessage(
    content='{"results": [{"name": "래미안", "price": 500000000}]}',
    tool_call_id="call_123"  # AI 요청과 매칭
)

# Step 3: AI가 도구 결과를 보고 최종 답변
final_msg = AIMessage(
    content="강남구 래미안 아파트의 현재 시세는 5억원입니다."
)
```

**용도**:
- Function Calling 결과 전달
- 도구 실행 추적
- 멀티스텝 추론

### 5. FunctionMessage (레거시)

```python
from langchain_core.messages import FunctionMessage

# OpenAI Function Calling (구 방식)
func_msg = FunctionMessage(
    name="search_real_estate",
    content='{"results": [...]}',
)

# ⚠️ 레거시: 대신 ToolMessage 사용 권장
```

### 6. AnyMessage - 타입 힌트용

```python
from langchain_core.messages import AnyMessage
from typing import List

def process_messages(messages: List[AnyMessage]):
    """모든 Message 타입 허용"""
    for msg in messages:
        if isinstance(msg, SystemMessage):
            print("System:", msg.content)
        elif isinstance(msg, HumanMessage):
            print("User:", msg.content)
        elif isinstance(msg, AIMessage):
            print("AI:", msg.content)
```

**용도**: 타입 힌트에서 "모든 Message 타입" 표현

---

## 현재 프로젝트 사용 분석

### 현재 상태: **Messages 사용 안함** ❌

```python
# 현재 코드 (llm_service.py)

from openai import AsyncOpenAI

class LLMService:
    async def complete_async(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        **kwargs
    ) -> str:
        # 프롬프트를 문자열로 로드
        prompt = self.prompt_manager.get(prompt_name, variables)

        # OpenAI 직접 호출 (문자열 형식)
        response = await self.async_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}  # ← 딕셔너리 형식
            ],
            **params
        )

        return response.choices[0].message.content
```

### 문제점

1. **타입 안전성 없음**
```python
# 현재: 오타 가능
messages = [{"role": "usre", "content": "..."}]  # "usre" 오타!

# Messages 사용 시: 타입 체크
messages = [HumanMessage(content="...")]  # IDE가 검증
```

2. **대화 이력 관리 복잡**
```python
# 현재: 직접 딕셔너리 구성
conversation_history = [
    {"role": "user", "content": "질문1"},
    {"role": "assistant", "content": "답변1"},
    {"role": "user", "content": "질문2"}
]

# Messages 사용 시: 명확한 타입
conversation_history = [
    HumanMessage(content="질문1"),
    AIMessage(content="답변1"),
    HumanMessage(content="질문2")
]
```

3. **도구 호출 처리 어려움**
```python
# 현재: tool_calls를 수동으로 파싱
if response.choices[0].message.tool_calls:
    # 복잡한 수동 처리

# Messages 사용 시: 자동 처리
ai_msg = AIMessage(response.choices[0].message)
if ai_msg.tool_calls:
    # 구조화된 처리
```

---

## 사용해야 하는 경우

### ✅ Messages 사용이 유리한 경우

#### 1. 복잡한 대화 이력 관리

```python
# 현재 State의 conversation_history
class MainSupervisorState(TypedDict):
    conversation_history: List[Dict[str, str]]  # [{"role": "user", "content": "..."}]

# Messages로 개선
from langchain_core.messages import BaseMessage

class MainSupervisorState(TypedDict):
    conversation_history: List[BaseMessage]  # 타입 안전!
```

#### 2. 멀티턴 대화 (Context 유지)

```python
# Messages 사용
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

async def chat_with_context(messages: List[BaseMessage], new_query: str):
    """기존 대화 이력 유지하며 계속 대화"""

    messages.append(HumanMessage(content=new_query))

    response = await llm.ainvoke(messages)

    messages.append(response)  # AIMessage 자동 추가

    return messages
```

#### 3. Function/Tool Calling

```python
# Messages로 도구 호출 추적
from langchain_core.messages import AIMessage, ToolMessage

messages = [
    HumanMessage(content="강남 아파트 시세 알려줘"),
    AIMessage(content="", tool_calls=[...]),  # AI가 도구 호출
    ToolMessage(content="...", tool_call_id="..."),  # 도구 결과
    AIMessage(content="강남 아파트 평균 시세는...")  # 최종 답변
]
```

#### 4. 시스템 프롬프트 관리

```python
# Messages 사용
system_prompt = SystemMessage(
    content="""당신은 부동산 상담 전문가입니다.

역할:
1. 법률 정보 제공
2. 시세 분석
3. 투자 조언

제약:
- 단정적 투자 권유 금지
- 출처 명시
"""
)

# 모든 대화에 자동 포함
messages = [system_prompt] + conversation_history + [new_message]
```

### ❌ Messages 불필요한 경우

#### 1. 단순 프롬프트 실행

```python
# 현재 방식으로 충분
prompt = "다음 텍스트를 요약하세요: {text}"
response = await llm.complete(prompt_name="summarize", variables={"text": text})
```

#### 2. 대화 없는 배치 처리

```python
# 단발성 분석/변환 작업
results = []
for item in items:
    result = await llm.complete(prompt_name="analyze", variables={"item": item})
    results.append(result)
```

---

## State와의 관계

### 현재 State (딕셔너리 형식)

```python
class MainSupervisorState(TypedDict):
    conversation_history: List[Dict[str, str]]  # 현재
    # [
    #   {"role": "user", "content": "질문"},
    #   {"role": "assistant", "content": "답변"}
    # ]
```

### Messages로 개선

```python
from langchain_core.messages import BaseMessage

class MainSupervisorState(TypedDict):
    conversation_history: List[BaseMessage]  # 개선
    # [
    #   HumanMessage(content="질문"),
    #   AIMessage(content="답변")
    # ]
```

### 장점

```python
# 1. 타입 안전
def process_message(msg: BaseMessage):
    if isinstance(msg, HumanMessage):
        print(f"User: {msg.content}")
    elif isinstance(msg, AIMessage):
        print(f"AI: {msg.content}")
        if msg.tool_calls:
            print(f"Tool calls: {msg.tool_calls}")

# 2. 직렬화 자동
messages = [HumanMessage(content="test")]
serialized = [msg.dict() for msg in messages]
# → chat_messages 테이블에 저장 가능

# 3. LangChain 생태계 호환
# - LangSmith 추적
# - LangChain 도구들과 통합
```

---

## 마이그레이션 가이드

### Phase 1: LLMService에 Messages 지원 추가

```python
# backend/app/service_agent/llm_manager/llm_service.py

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    AnyMessage
)
from typing import Union, List

class LLMService:
    """Messages 지원 추가"""

    async def chat(
        self,
        messages: List[BaseMessage],
        model: str = None,
        **kwargs
    ) -> AIMessage:
        """
        Messages 기반 채팅

        Args:
            messages: LangChain Messages 리스트
            model: 모델 이름

        Returns:
            AIMessage (응답)
        """
        # Messages를 OpenAI 형식으로 변환
        openai_messages = [
            {
                "role": self._get_role(msg),
                "content": msg.content
            }
            for msg in messages
        ]

        # OpenAI 호출
        response = await self.async_client.chat.completions.create(
            model=model or self._get_model(),
            messages=openai_messages,
            **kwargs
        )

        # OpenAI 응답을 AIMessage로 변환
        return AIMessage(
            content=response.choices[0].message.content,
            response_metadata={
                "model": response.model,
                "usage": response.usage.dict()
            }
        )

    def _get_role(self, message: BaseMessage) -> str:
        """Message 타입을 OpenAI role로 변환"""
        if isinstance(message, SystemMessage):
            return "system"
        elif isinstance(message, HumanMessage):
            return "user"
        elif isinstance(message, AIMessage):
            return "assistant"
        else:
            return "user"  # 기본값

    # 기존 메서드 유지 (하위 호환성)
    async def complete_async(self, prompt_name: str, **kwargs) -> str:
        """기존 방식 (하위 호환)"""
        # ... 기존 코드 유지
```

### Phase 2: State에 Messages 통합

```python
# backend/app/service_agent/foundation/separated_states.py

from langchain_core.messages import BaseMessage
from typing import List, Union, Dict

class MainSupervisorState(TypedDict):
    """Messages 지원 State"""

    # Option 1: Messages로 완전 전환
    conversation_history: List[BaseMessage]

    # Option 2: 하위 호환 유지 (둘 다 지원)
    # conversation_history: Union[List[BaseMessage], List[Dict[str, str]]]
```

### Phase 3: Service Layer 업데이트

```python
# backend/app/service_agent/services/chat_service.py

from langchain_core.messages import HumanMessage, AIMessage

class ChatService:
    async def send_message(self, session_id: str, user_message: str):
        # DB에서 대화 이력 조회
        db_messages = self.db.query(ChatMessage).filter_by(
            session_id=session_id
        ).all()

        # DB → Messages 변환
        conversation_history = []
        for msg in db_messages:
            if msg.sender_type == "user":
                conversation_history.append(
                    HumanMessage(content=msg.content)
                )
            elif msg.sender_type == "assistant":
                conversation_history.append(
                    AIMessage(content=msg.content)
                )

        # 새 메시지 추가
        conversation_history.append(
            HumanMessage(content=user_message)
        )

        # LLM 호출 (Messages 사용)
        response = await self.llm_service.chat(conversation_history)

        # 응답 저장
        self.db.add(ChatMessage(
            session_id=session_id,
            sender_type="assistant",
            content=response.content
        ))
```

### Phase 4: 시스템 프롬프트 관리

```python
# backend/app/service_agent/llm_manager/system_prompts.py

from langchain_core.messages import SystemMessage

class SystemPrompts:
    """시스템 프롬프트 관리"""

    REAL_ESTATE_CONSULTANT = SystemMessage(
        content="""당신은 부동산 전문 상담 AI입니다.

역할:
1. 법률 정보 제공 (임대차보호법, 주택법 등)
2. 시세 분석 및 평가
3. 투자 조언 (위험도 포함)

제약사항:
- 단정적 투자 권유 금지
- 법률 정보는 출처 명시
- 불확실한 경우 명확히 표현

답변 형식:
- 친절하고 전문적인 말투
- 복잡한 법률 용어는 쉽게 설명
- 구체적인 예시 제공
"""
    )

    @classmethod
    def get_with_context(cls, user_preferences: Dict = None) -> SystemMessage:
        """사용자 맞춤 시스템 프롬프트"""
        base = cls.REAL_ESTATE_CONSULTANT.content

        if user_preferences:
            base += f"\n\n사용자 선호:\n"
            if user_preferences.get("preferred_region"):
                base += f"- 관심 지역: {user_preferences['preferred_region']}\n"
            if user_preferences.get("investment_style"):
                base += f"- 투자 성향: {user_preferences['investment_style']}\n"

        return SystemMessage(content=base)
```

---

## 요약

### LangChain Messages란?

```python
SystemMessage   # 시스템 프롬프트 (역할 정의)
HumanMessage    # 사용자 메시지
AIMessage       # AI 응답
ToolMessage     # 도구 실행 결과
AnyMessage      # 타입 힌트용
```

### 현재 프로젝트

```python
사용 중? ❌ 현재 사용 안함
- OpenAI 직접 호출 (딕셔너리 형식)
- 문자열 기반 프롬프트 관리

필요성? ✅ 다음 경우 유용
- 복잡한 대화 이력 관리
- Function/Tool Calling
- 타입 안전성 필요
```

### 프리필터/설정값?

```python
❌ 아님!
Messages는 대화 메시지의 타입 정의

프리필터 (Prefill): OpenAI의 Assistant 메시지 시작 부분
설정값 (Config): LangGraph의 configurable 옵션
```

### 권장사항

```python
현재 상황: 단순 프롬프트 실행 위주
→ Messages 필수 아님 ✅

향후 계획: Tool Calling, 복잡한 대화
→ Messages 도입 고려 ⚠️

단계적 마이그레이션:
1. LLMService에 chat() 메서드 추가
2. State에 Messages 옵션 추가
3. 기존 방식과 병행 사용
4. 점진적 전환
```

---

*작성일: 2025-10-06*
*버전: 1.0*
