import os
from openai import AsyncOpenAI, RateLimitError, APIConnectionError, OpenAIError
from typing import Any, AsyncGenerator

from client.response import StreamEvent, StreamEventType, TokenUsage


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


def _accumulate_tool_calls(acc: dict[int, dict[str, str]], deltas: Any) -> None:
      """Merge a chunk's streamed tool-call deltas into `acc`, keyed by index.

      The name and id arrive once; the JSON `arguments` stream in piece by piece,
      so they are concatenated until the message completes.
      """
      for delta in deltas:
            entry = acc.setdefault(delta.index, {"id": "", "name": "", "arguments": ""})
            if delta.id:
                  entry["id"] = delta.id
            if delta.function is not None:
                  if delta.function.name:
                        entry["name"] = delta.function.name
                  if delta.function.arguments:
                        entry["arguments"] += delta.function.arguments


def _error_kind(exc: Exception) -> str:
      """Classify an exception into a coarse error category."""
      if isinstance(exc, RateLimitError):
            return "rate_limit"
      if isinstance(exc, APIConnectionError):
            return "network"
      if isinstance(exc, OpenAIError):
            return "api"
      return "unknown"


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

      async def chat_completion(self, messages: list[dict[str,Any]], tools: list[dict[str,Any]] | None = None, stream: bool = True) -> Any:
       #LLM once reached context window tend to stream half response so we need to check wether actual
       #context window is reached or not
            client = self.get_client()
            kwargs: dict[str,Any] = {
                  "model": "deepseek-chat",
                  "messages": messages,
                  "stream": stream
            }
            if tools:
                  kwargs["tools"] = tools

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
                  tool_calls: dict[int, dict[str, str]] = {}
                  async for chunk in response:
                        if chunk.usage is not None:
                              usage = _to_token_usage(chunk.usage)
                        if not chunk.choices:
                              continue
                        choice = chunk.choices[0]
                        if choice.delta.content:
                              yield StreamEvent(type=StreamEventType.TEXT_DELTA, text_delta=choice.delta.content)
                        if choice.delta.tool_calls:
                              _accumulate_tool_calls(tool_calls, choice.delta.tool_calls)
                        if choice.finish_reason is not None:
                              finish_reason = choice.finish_reason
                  yield StreamEvent(
                        type=StreamEventType.MESSAGE_COMPLETE,
                        finish_reason=finish_reason,
                        usage=usage,
                        tool_calls=[tool_calls[i] for i in sorted(tool_calls)] or None,
                  )
            except RateLimitError as exc:
                  yield StreamEvent(type=StreamEventType.RATE_LIMIT, error=str(exc), error_kind="rate_limit")
            except Exception as exc:
                  yield StreamEvent(type=StreamEventType.ERROR, error=str(exc), error_kind=_error_kind(exc))

      async def non_stream_response(self, client: AsyncOpenAI, kwargs: dict[str,Any]) -> StreamEvent:
            try:
                  response = await client.chat.completions.create(**kwargs)
                  choice = response.choices[0]
                  return StreamEvent(
                        type=StreamEventType.MESSAGE_COMPLETE,
                        text_delta=choice.message.content,
                        finish_reason=choice.finish_reason,
                        usage=_to_token_usage(response.usage),
                  )
            except RateLimitError as exc:
                  return StreamEvent(type=StreamEventType.RATE_LIMIT, error=str(exc), error_kind="rate_limit")
            except Exception as exc:
                  return StreamEvent(type=StreamEventType.ERROR, error=str(exc), error_kind=_error_kind(exc))
