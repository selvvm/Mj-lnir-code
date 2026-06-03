from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prompts.system import get_system_prompt
from context.text import count_tokens
from config.config import Config
from tools.memory import load_memory


@dataclass
class MessageItems:
      role: str
      content: str
      token_count: int
      tool_calls: list[dict[str, Any]] | None = None
      tool_call_id: str | None = None


class ContextManager:
      """Owns the agent's conversation context — the system prompt and message history."""

      def __init__(self, config: Config | None = None) -> None:
            self._config = config or Config()
            self.system_prompt = self._build_system_prompt()
            self._model_name = self._config.model
            self._messages: list[MessageItems] = []

      def _build_system_prompt(self) -> str:
            """Base prompt with live config, plus the stored memory keys (the index)."""
            keys = list(load_memory(self._config.memory_path).keys())
            user_memory = "\n".join(f"- {key}" for key in keys) if keys else None
            return get_system_prompt(self._config, user_memory=user_memory)

      def add_user_message(self, content: str) -> None:
            item = MessageItems(
                  role="user",
                  content=content,
                  token_count=count_tokens(
                        content,
                        self._model_name,
                  ),
            )
            self._messages.append(item)

      def add_assistant_message(self, content: str, tool_calls: list[dict[str, Any]] | None = None) -> None:
            item = MessageItems(
                  role="assistant",
                  content=content,
                  token_count=count_tokens(
                        content,
                        self._model_name,
                  ),
                  tool_calls=tool_calls,
            )
            self._messages.append(item)

      def add_tool_result(self, tool_call_id: str, content: str) -> None:
            item = MessageItems(
                  role="tool",
                  content=content,
                  token_count=count_tokens(content, self._model_name),
                  tool_call_id=tool_call_id,
            )
            self._messages.append(item)

      def pop_last(self) -> None:
            """Remove the most recent message (used to discard a failed turn)."""
            if self._messages:
                  self._messages.pop()

      def total_tokens(self) -> int:
            """Approximate tokens for the whole context: system prompt + all messages."""
            return count_tokens(self.system_prompt, self._model_name) + sum(
                  m.token_count for m in self._messages
            )

      def prune(self) -> int:
            """Drop oldest messages until under the context budget; return how many.

            Stops dropping once the front is no longer a `tool` message, so a tool
            result is never left without the assistant tool-call that produced it
            (which the API would reject).
            """
            budget = self._config.max_context_tokens
            dropped = 0
            while self.total_tokens() > budget and len(self._messages) > 1:
                  self._messages.pop(0)
                  dropped += 1
            while self._messages and self._messages[0].role == "tool":
                  self._messages.pop(0)
                  dropped += 1
            return dropped

      def get_messages(self) -> list[dict[str, Any]]:
            """Return system prompt + history as role/content dicts for the LLM."""
            messages: list[dict[str, Any]] = [
                  {"role": "system", "content": self.system_prompt}
            ]
            for m in self._messages:
                  if m.role == "tool":
                        messages.append(
                              {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
                        )
                  elif m.tool_calls:
                        messages.append({
                              "role": m.role,
                              "content": m.content,
                              "tool_calls": [
                                    {
                                          "id": tc["id"],
                                          "type": "function",
                                          "function": {"name": tc["name"], "arguments": tc["arguments"]},
                                    }
                                    for tc in m.tool_calls
                              ],
                        })
                  else:
                        messages.append({"role": m.role, "content": m.content})
            return messages
