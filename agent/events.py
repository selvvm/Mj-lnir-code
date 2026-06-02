from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentEventType(str, Enum):
      # Agent lifecycle
      AGENT_START = "agent_start"
      AGENT_END = "agent_end"
      AGENT_ERROR = "agent_error"

      # Text streaming
      TEXT_DELTA = "text_delta"
      TEXT_COMPLETE = "text_complete"

      # Tool calls
      TOOL_START = "tool_start"
      TOOL_RESULT = "tool_result"

      # Context management
      CONTEXT_PRUNED = "context_pruned"


@dataclass
class AgentEvent:
      type: AgentEventType
      data: dict[str, Any] = field(default_factory=dict)

      @classmethod
      def agent_start(cls, message: str) -> AgentEvent:
            return cls(type=AgentEventType.AGENT_START, data={"message": message})

      @classmethod
      def agent_end(cls) -> AgentEvent:
            return cls(type=AgentEventType.AGENT_END)

      @classmethod
      def agent_error(cls, error: str, kind: str = "unknown") -> AgentEvent:
            return cls(type=AgentEventType.AGENT_ERROR, data={"error": error, "kind": kind})

      @classmethod
      def text_delta(cls, text: str) -> AgentEvent:
            return cls(type=AgentEventType.TEXT_DELTA, data={"text": text})

      @classmethod
      def text_complete(cls, text: str, finish_reason: str | None = None, usage: Any = None) -> AgentEvent:
            return cls(
                  type=AgentEventType.TEXT_COMPLETE,
                  data={"text": text, "finish_reason": finish_reason, "usage": usage},
            )

      @classmethod
      def tool_start(cls, name: str, arguments: str) -> AgentEvent:
            return cls(type=AgentEventType.TOOL_START, data={"name": name, "arguments": arguments})

      @classmethod
      def context_pruned(cls, dropped: int, total_tokens: int) -> AgentEvent:
            return cls(
                  type=AgentEventType.CONTEXT_PRUNED,
                  data={"dropped": dropped, "total_tokens": total_tokens},
            )

      @classmethod
      def tool_result(cls, name: str, result: Any) -> AgentEvent:
            return cls(
                  type=AgentEventType.TOOL_RESULT,
                  data={
                        "name": name,
                        "success": result.success,
                        "output": result.output,
                        "error": result.error,
                  },
            )
