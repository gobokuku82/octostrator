"""LLM Client - OpenAI API 클라이언트"""

import os
from typing import Optional, Any
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.app.core.config import settings

class LLMConfig(BaseModel):
    """LLM 설정"""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 60

class LLMClient:
    """
    LLM 클라이언트

    OpenAI API를 사용한 LLM 호출 관리.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Args:
            config: LLM 설정 (기본값: LLMConfig())
        """
        self.config = config or LLMConfig()
        
        # Try loading from settings first (reliable), then fallback to os.getenv
        # Explicitly load from backend/.env for safety
        env_path = os.path.join(os.getcwd(), 'backend', '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
        else:
            load_dotenv() # Fallback to default .env

        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")

        if not api_key:
            print(f"DEBUG: Current Env Vars: {list(os.environ.keys())}")
            print(f"DEBUG: Checked path: {env_path}")
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please set it in your .env file."
            )

        self.client = AsyncOpenAI(api_key=api_key, timeout=self.config.timeout)

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """
        채팅 완성 API 호출

        Args:
            messages: 메시지 리스트 [{"role": "user", "content": "..."}]
            temperature: 온도 (None이면 config 값 사용)
            max_tokens: 최대 토큰 (None이면 config 값 사용)
            response_format: 응답 형식 (예: {"type": "json_object"})

        Returns:
            응답 텍스트
        """
        try:
            params = {
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.config.temperature,
            }

            if max_tokens or self.config.max_tokens:
                params["max_tokens"] = max_tokens or self.config.max_tokens

            if response_format:
                params["response_format"] = response_format

            # DEBUG: Print prompt to stdout to trace "completion" issues
            # print(f"--- LLM REQUEST ---\nMessages: {messages}\n-------------------")

            response = await self.client.chat.completions.create(**params)
            content = response.choices[0].message.content or ""
            
            # DEBUG: Print response
            # print(f"--- LLM RESPONSE ---\n{content}\n--------------------")
            
            return content

        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {str(e)}") from e

    async def chat_with_system(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """
        시스템 프롬프트와 함께 채팅 API 호출

        Args:
            system_prompt: 시스템 프롬프트
            user_message: 사용자 메시지
            temperature: 온도
            max_tokens: 최대 토큰
            response_format: 응답 형식

        Returns:
            응답 텍스트
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        JSON 형식으로 응답 받기

        Args:
            messages: 메시지 리스트
            temperature: 온도
            max_tokens: 최대 토큰

        Returns:
            JSON 형식의 응답 텍스트
        """
        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

    async def test_connection(self) -> bool:
        """
        OpenAI API 연결 테스트

        Returns:
            연결 성공 여부
        """
        try:
            response = await self.chat(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
            )
            return bool(response)
        except Exception:
            return False


# 전역 클라이언트 인스턴스 (싱글톤 패턴)
_client_instance: Optional[LLMClient] = None


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """
    LLM 클라이언트 인스턴스 가져오기 (싱글톤)

    Args:
        config: LLM 설정 (처음 호출 시에만 사용됨)

    Returns:
        LLMClient 인스턴스
    """
    global _client_instance

    if _client_instance is None:
        _client_instance = LLMClient(config)

    return _client_instance
