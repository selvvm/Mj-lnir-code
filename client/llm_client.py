import os
from openai import AsyncOpenAI, RateLimitError
from typing import Any, AsyncGenerator

from client.response import StreamEvent, EventType, TokenUsage


def _to_token_usage(usage: Any) -> TokenUsage:
      if usage is None:
            return TokenUsage()
      details = getattr(usage, "prompt_tokens_details", None)
      cached_tokens = getattr(details, "cached_tokens", None) if details is not None else None
      if cached_tokens is None:
            cached_tokens = getattr(usage, "prompt_cache_hit_tokens", 0)
      return TokenUsage(
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
            total_tokens=usage.total_tokens or 0,
            cached_tokens=cached_tokens or 0,
      )


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
            kwargs: dict[str,Any] = {
                  "model": "deepseek-chat",
                  "messages": messages,
                  "stream": stream
            }

            if stream:
                  kwargs["stream_options"] = {"include_usage": True}
                  return self.stream_response(client, kwargs)
            else:
                  return await self.non_stream_response(client, kwargs)


      async def stream_response(self, client: AsyncOpenAI, kwargs: dict[str,Any]) -> AsyncGenerator[StreamEvent,None]:
            try:
                  response = await client.chat.completions.create(**kwargs)
                  finish_reason: str | None = None
                  usage: TokenUsage | None = None
                  async for chunk in response:
                        if chunk.usage is not None:
                              usage = _to_token_usage(chunk.usage)
                        if not chunk.choices:
                              continue
                        choice = chunk.choices[0]
                        if choice.delta.content:
                              yield StreamEvent(type=EventType.TEXT_DELTA, text_delta=choice.delta.content)
                        if choice.finish_reason is not None:
                              finish_reason = choice.finish_reason
                  yield StreamEvent(
                        type=EventType.MESSAGE_COMPLETE,
                        finish_reason=finish_reason,
                        usage=usage,
                  )
            except RateLimitError as exc:
                  yield StreamEvent(type=EventType.RATE_LIMIT, error=str(exc))
            except Exception as exc:
                  yield StreamEvent(type=EventType.ERROR, error=str(exc))

      async def non_stream_response(self, client: AsyncOpenAI, kwargs: dict[str,Any]) -> StreamEvent:
            try:
                  response = await client.chat.completions.create(**kwargs)
                  choice = response.choices[0]
                  return StreamEvent(
                        type=EventType.MESSAGE_COMPLETE,
                        text_delta=choice.message.content,
                        finish_reason=choice.finish_reason,
                        usage=_to_token_usage(response.usage),
                  )
            except RateLimitError as exc:
                  return StreamEvent(type=EventType.RATE_LIMIT, error=str(exc))
            except Exception as exc:
                  return StreamEvent(type=EventType.ERROR, error=str(exc))
