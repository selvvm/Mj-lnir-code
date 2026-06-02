from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class MemoryParams(BaseModel):
      action: str = Field(..., description="Action to perform: 'set', 'get', 'delete', 'list', or 'clear'.")
      key: str | None = Field(None, description="Memory key. Required for 'set', 'get', and 'delete'.")
      value: str | None = Field(None, description="Memory value to store. Required for 'set'.")


class MemoryTool(Tool):
      name = "memory"
      description = (
            "Store and retrieve persistent memory that survives across sessions. Call this "
            "whenever you learn something durable worth remembering — user preferences, "
            "project conventions, or important decisions — and to recall it later. "
            "Actions: set (key, value), get (key), delete (key), list, clear."
      )
      kind = ToolKind.MEMORY
      parameters = MemoryParams.model_json_schema()

      def __init__(self, path: Path) -> None:
            self._path = path

      def _load(self) -> dict[str, str]:
            try:
                  return json.loads(self._path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                  return {}

      def _save(self, data: dict[str, str]) -> None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            params = MemoryParams(**invocation.params)
            action = params.action.lower()
            data = self._load()

            if action == "set":
                  if not params.key or params.value is None:
                        return ToolResult.error_result("`key` and `value` required for 'set' action.")
                  data[params.key] = params.value
                  self._save(data)
                  return ToolResult.success_result(f"Stored memory [{params.key}].")

            if action == "get":
                  if not params.key:
                        return ToolResult.error_result("`key` required for 'get' action.")
                  if params.key not in data:
                        return ToolResult.error_result(f"No memory with key [{params.key}].")
                  return ToolResult.success_result(f"{params.key}: {data[params.key]}")

            if action == "delete":
                  if not params.key:
                        return ToolResult.error_result("`key` required for 'delete' action.")
                  if params.key not in data:
                        return ToolResult.error_result(f"No memory with key [{params.key}].")
                  del data[params.key]
                  self._save(data)
                  return ToolResult.success_result(f"Deleted memory [{params.key}].")

            if action == "list":
                  if not data:
                        return ToolResult.success_result("(no memories)")
                  listing = "\n".join(f"{key}: {value}" for key, value in data.items())
                  return ToolResult.success_result(listing)

            if action == "clear":
                  count = len(data)
                  self._save({})
                  return ToolResult.success_result(f"Cleared {count} memory entr{'y' if count == 1 else 'ies'}.")

            return ToolResult.error_result(f"Unknown action: {params.action}")
