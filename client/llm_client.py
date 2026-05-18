import os
from openai import AsyncOpenAI
from typing import Any, AsyncGenerator

class LLMClient:
      def __init__(self) -> None:
            self._client: AsyncOpenAI | None = None

      def get_client(self) -> AsyncOpenAI:
            if self._client is None:
                  self._client = AsyncOpenAI(
                        api_key=os.getenv("DEEPSEEK_API_KEY"),
                        base_url="https://api.deepseek.com"
                        )
            return self._client

      async def close(self) -> None:
            if self._client is not None:
                  await self._client.close()
                  self._client = None

      async def chat_completion(self, messages: list[dict[str,Any]], stream: bool = True) -> Any:
       #LLM once reached context window tend to stream half response so we need to check wether actual
       #context window is reached or not
            client = self.get_client()
            kwargs={
                  "model": "deepseek-chat",
                  "messages": messages,
                  "stream": stream
            }

            if stream:
                  return self.stream_response(client, kwargs)
            else:
                  return await self.non_stream_response(client, kwargs)


      async def stream_response(self, client: AsyncOpenAI, kwargs: dict[str,Any]) -> AsyncGenerator[str,None]:
            response = await client.chat.completions.create(**kwargs)
            async for chunk in response:
                  content = chunk.choices[0].delta.content
                  if content is not None:
                        yield content

      async def non_stream_response(self, client: AsyncOpenAI, kwargs: dict[str,Any]) -> str:
            response = await client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
