from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ToolKind(str, Enum):
      READ = "read"
      WRITE = "write"
      SHELL = "shell"
      NETWORK = "network"
      TASK = "task"
      MEMORY = "memory"


@dataclass
class ToolResult:
      success: bool
      output: str
      error: str | None = None
      metadata: dict[str, Any] = field(default_factory=dict)

      @classmethod
      def success_result(cls, output: str, metadata: dict[str, Any] | None = None) -> ToolResult:
            return cls(success=True, output=output, metadata=metadata or {})

      @classmethod
      def error_result(cls, error: str, metadata: dict[str, Any] | None = None) -> ToolResult:
            return cls(success=False, output="", error=error, metadata=metadata or {})


@dataclass
class ToolInvocation:
      params: dict[str, Any]
      cwd: Path


@dataclass
class ToolConfirmation:
      tool_name: str
      params: dict[str, Any]
      description: str


class Tool(abc.ABC):
      """Base class for every tool the agent can call.

      A concrete tool defines its `name`, `description`, JSON-schema
      `parameters`, and `kind` (the category used for permission/safety
      gating), and implements `execute` to run it. `schema()` renders the tool
      into the OpenAI/DeepSeek function-tool format expected by the API.
      """

      name: str = "base_tool"
      description: str = "Base tool"
      kind: ToolKind
      parameters: dict[str, Any] = {"type": "object", "properties": {}}

      def schema(self) -> dict[str, Any]:
            """Render this tool as an OpenAI/DeepSeek function-tool schema."""
            return {
                  "type": "function",
                  "function": {
                        "name": self.name,
                        "description": self.description,
                        "parameters": self.parameters,
                  },
            }

      @abc.abstractmethod
      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            """Run the tool with the model-supplied `invocation` and return a result.

            `invocation.params` holds the JSON arguments the model produced and
            `invocation.cwd` the directory to resolve relative paths against. The
            `ToolResult.output` is fed back into the conversation as the tool's
            output, so it should be a self-contained, readable result.
            """
            ...
