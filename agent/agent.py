from __future__ import annotations

from typing import AsyncGenerator

from client.llm_client import LLMClient
from client.response import StreamEventType
from agent.events import AgentEvent


class Agent:
      """Orchestration layer between the UI and the LLM transport.

      `main.py` calls `run()`; the Agent owns the LLMClient and the conversation
      history, and never exposes LLMClient to the UI.
      """

      def __init__(self) -> None:
            self.client = LLMClient()
            self._messages: list[dict[str, str]] = []

      async def run(self, message: str) -> AsyncGenerator[AgentEvent, None]:
            """Public entry point: bracket one turn with AGENT_START / AGENT_END."""
            yield AgentEvent.agent_start(message)
            # add user message to context
            self._messages.append({"role": "user", "content": message})

            async for event in self._agentic_loop():
                  yield event

            yield AgentEvent.agent_end()

      async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
            """Internal loop: stream the LLM reply and translate StreamEvents."""
            parts: list[str] = []
            finish_reason: str | None = None
            usage: object | None = None
            error_event: AgentEvent | None = None

            try:
                  stream = await self.client.chat_completion(self._messages, stream=True)
                  async for event in stream:
                        if event.type is StreamEventType.TEXT_DELTA:
                              content = event.text_delta or ""
                              parts.append(content)
                              yield AgentEvent.text_delta(content)
                        elif event.type is StreamEventType.MESSAGE_COMPLETE:
                              finish_reason = event.finish_reason
                              usage = event.usage
                        elif event.type is StreamEventType.RATE_LIMIT:
                              error_event = AgentEvent.agent_error(event.error, event.error_kind or "rate_limit")
                        elif event.type is StreamEventType.ERROR:
                              error_event = AgentEvent.agent_error(event.error, event.error_kind or "api")
            except Exception as exc:
                  error_event = AgentEvent.agent_error(str(exc), "unknown")

            if error_event is not None:
                  # Failed turn: drop the dangling user message so history stays clean.
                  if self._messages and self._messages[-1]["role"] == "user":
                        self._messages.pop()
                  yield error_event
            else:
                  reply = "".join(parts)
                  self._messages.append({"role": "assistant", "content": reply})
                  yield AgentEvent.text_complete(reply, finish_reason, usage)

      async def close(self) -> None:
            """Release the underlying LLM client."""
            await self.client.close()
