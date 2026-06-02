from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class TodosParams(BaseModel):
      action: str = Field(..., description="Action to perform: 'add', 'complete', 'list', or 'clear'.")
      content: str | None = Field(None, description="Todo text. Required for the 'add' action.")
      id: str | None = Field(None, description="Todo id. Required for the 'complete' action.")


class TodosTool(Tool):
      name = "todos"
      description = (
            "Manage a task list for the current session: add tasks, mark them complete, "
            "list them, or clear them. Use it to plan and track progress on multi-step work."
      )
      kind = ToolKind.TASK
      parameters = TodosParams.model_json_schema()

      def __init__(self) -> None:
            self._todos: dict[str, str] = {}

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            params = TodosParams(**invocation.params)
            action = params.action.lower()

            if action == "add":
                  if not params.content:
                        return ToolResult.error_result("`content` required for 'add' action.")
                  todo_id = str(uuid.uuid4())[:8]
                  self._todos[todo_id] = params.content
                  return ToolResult.success_result(f"Added todo [{todo_id}]: {params.content}")

            if action == "complete":
                  if not params.id:
                        return ToolResult.error_result("`id` required for 'complete' action.")
                  if params.id not in self._todos:
                        return ToolResult.error_result(f"No todo with id [{params.id}].")
                  content = self._todos.pop(params.id)
                  return ToolResult.success_result(f"Completed todo [{params.id}]: {content}")

            if action == "clear":
                  count = len(self._todos)
                  self._todos.clear()
                  return ToolResult.success_result(f"Cleared {count} todo(s).")

            if action == "list":
                  if not self._todos:
                        return ToolResult.success_result("(no todos)")
                  listing = "\n".join(f"[{todo_id}] {text}" for todo_id, text in self._todos.items())
                  return ToolResult.success_result(listing)

            return ToolResult.error_result(f"Unknown action: {params.action}")
