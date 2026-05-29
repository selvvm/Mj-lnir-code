from __future__ import annotations

import logging
from typing import Any

from tools.base import Tool
from tools.fetch_url import FetchUrlTool
from tools.read_file import ReadFileTool
from tools.run_shell import RunShellTool
from tools.write_file import WriteFileTool


logger = logging.getLogger(__name__)


def _default_tools() -> list[Tool]:
      return [ReadFileTool(), WriteFileTool(), RunShellTool(), FetchUrlTool()]


class ToolRegistry:
      """Holds the agent's available tools and exposes them to the LLM and dispatch.

      `schemas()` produces the list sent to the API's `tools` parameter; `get()`
      looks a tool up by the name the model called so the agent can `execute` it.
      """

      def __init__(self, tools: list[Tool] | None = None) -> None:
            self._tools: dict[str, Tool] = {}
            for tool in _default_tools() if tools is None else tools:
                  self.register(tool)

      def register(self, tool: Tool) -> None:
            if tool.name in self._tools:
                  logger.warning(f"Overwriting existing tool: {tool.name}")
            self._tools[tool.name] = tool
            logger.debug(f"Registered tool: {tool.name}")

      def unregister(self, name: str) -> bool:
            if name in self._tools:
                  del self._tools[name]
                  return True
            return False

      def get(self, name: str) -> Tool | None:
            return self._tools.get(name)

      def get_tools(self) -> list[Tool]:
            """Return every registered tool instance."""
            return list(self._tools.values())

      def get_schemas(self) -> list[dict[str, Any]]:
            """Return every tool's function-tool schema for the API `tools` param."""
            return [tool.schema() for tool in self.get_tools()]

      def __contains__(self, name: str) -> bool:
            return name in self._tools

      def __len__(self) -> int:
            return len(self._tools)
