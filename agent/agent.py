from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncGenerator

from client.llm_client import LLMClient
from client.response import StreamEventType
from context.manager import ContextManager
from agent.events import AgentEvent
from tools.base import ToolInvocation, ToolResult
from tools.registry import ToolRegistry


class Agent:
      """Orchestration layer between the UI and the LLM transport.

      `main.py` calls `run()`; the Agent owns the LLMClient and delegates
      conversation state to a ContextManager, and never exposes either to the UI.
      """

      def __init__(self, max_iterations: int = 10) -> None:
            self.client = LLMClient()
            self._context = ContextManager()
            self._tools = ToolRegistry()
            self._cwd = Path.cwd()
            self._max_iterations = max_iterations

      async def run(self, message: str) -> AsyncGenerator[AgentEvent, None]:
            """Public entry point: bracket one turn with AGENT_START / AGENT_END."""
            yield AgentEvent.agent_start(message)
            self._context.add_user_message(message)

            async for event in self._agentic_loop():
                  yield event

            yield AgentEvent.agent_end()

      async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
            """Stream the LLM reply, run any tool calls, and loop until it answers."""
            first = True
            for _ in range(self._max_iterations):
                  parts: list[str] = []
                  finish_reason: str | None = None
                  usage: object | None = None
                  tool_calls: list[dict[str, Any]] | None = None
                  error_event: AgentEvent | None = None

                  try:
                        stream = await self.client.chat_completion(
                              self._context.get_messages(),
                              tools=self._tools.get_schemas(),
                              stream=True,
                        )
                        async for event in stream:
                              if event.type is StreamEventType.TEXT_DELTA:
                                    content = event.text_delta or ""
                                    parts.append(content)
                                    yield AgentEvent.text_delta(content)
                              elif event.type is StreamEventType.MESSAGE_COMPLETE:
                                    finish_reason = event.finish_reason
                                    usage = event.usage
                                    tool_calls = event.tool_calls
                              elif event.type is StreamEventType.RATE_LIMIT:
                                    error_event = AgentEvent.agent_error(event.error, event.error_kind or "rate_limit")
                              elif event.type is StreamEventType.ERROR:
                                    error_event = AgentEvent.agent_error(event.error, event.error_kind or "api")
                  except Exception as exc:
                        error_event = AgentEvent.agent_error(str(exc), "unknown")

                  if error_event is not None:
                        # Only the opening user message is safe to drop; once tools
                        # have run the history holds valid call/result pairs.
                        if first:
                              self._context.pop_last()
                        yield error_event
                        return

                  reply = "".join(parts)
                  if tool_calls:
                        first = False
                        self._context.add_assistant_message(reply, tool_calls=tool_calls)
                        for call in tool_calls:
                              yield AgentEvent.tool_start(call["name"], call["arguments"])
                              result = await self._execute_tool(call)
                              self._context.add_tool_result(call["id"], _tool_message(result))
                              yield AgentEvent.tool_result(call["name"], result)
                        continue

                  self._context.add_assistant_message(reply)
                  yield AgentEvent.text_complete(reply, finish_reason, usage)
                  return

            yield AgentEvent.agent_error(
                  f"Stopped after {self._max_iterations} tool iterations.", "max_iterations"
            )

      async def _execute_tool(self, call: dict[str, Any]) -> ToolResult:
            """Look up the called tool, parse its arguments, and run it safely."""
            tool = self._tools.get(call["name"])
            if tool is None:
                  return ToolResult(success=False, output="", error=f"Unknown tool: {call['name']}")
            try:
                  params = json.loads(call["arguments"] or "{}")
            except json.JSONDecodeError as exc:
                  return ToolResult(success=False, output="", error=f"Invalid tool arguments: {exc}")
            try:
                  return await tool.execute(ToolInvocation(params=params, cwd=self._cwd))
            except Exception as exc:
                  return ToolResult(success=False, output="", error=f"Tool raised: {exc}")

      async def close(self) -> None:
            """Release the underlying LLM client."""
            await self.client.close()


def _tool_message(result: ToolResult) -> str:
      """Render a ToolResult into the text fed back to the model."""
      if not result.success:
            return f"Error: {result.error}"
      return result.output if result.output else "(no output)"
