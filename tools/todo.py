from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class TodoStatus(str, Enum):
      PENDING = "pending"
      IN_PROGRESS = "in_progress"
      COMPLETED = "completed"


@dataclass
class TodoItem:
      id: int
      content: str
      status: TodoStatus = TodoStatus.PENDING


class TodoStore:
      """The session's task list. Owned by the Session, mutated by the TodosTool.

      Keeping the list here (rather than inside the tool) means it is session
      state the UI and persistence can reach, while the tool stays a thin
      behavior layer over it.
      """

      def __init__(self) -> None:
            self._items: list[TodoItem] = []
            self._next_id = 1

      def add(self, content: str) -> TodoItem:
            item = TodoItem(id=self._next_id, content=content)
            self._next_id += 1
            self._items.append(item)
            return item

      def set_status(self, task_id: int, status: TodoStatus) -> TodoItem | None:
            for item in self._items:
                  if item.id == task_id:
                        item.status = status
                        return item
            return None

      def clear(self) -> int:
            count = len(self._items)
            self._items.clear()
            return count

      def items(self) -> list[TodoItem]:
            return list(self._items)


_MARKERS = {
      TodoStatus.PENDING: "[ ]",
      TodoStatus.IN_PROGRESS: "[~]",
      TodoStatus.COMPLETED: "[x]",
}


def _render(store: TodoStore) -> str:
      items = store.items()
      if not items:
            return "(no tasks)"
      return "\n".join(f"{_MARKERS[item.status]} #{item.id} {item.content}" for item in items)


class TodosParams(BaseModel):
      action: Literal["add", "complete", "list", "clear"] = Field(
            ..., description="add a task, complete a task, list all tasks, or clear the list."
      )
      content: str | None = Field(
            None, description="Task description. Required when action is 'add'."
      )
      task_id: int | None = Field(
            None, description="Task id to mark complete. Required when action is 'complete'."
      )


class TodosTool(Tool):
      name = "todos"
      description = (
            "Manage a task list for the current session: add tasks, mark them complete, "
            "list them, or clear them. Use it to plan and track progress on multi-step work."
      )
      kind = ToolKind.TASK
      parameters = TodosParams.model_json_schema()

      def __init__(self, store: TodoStore) -> None:
            self._store = store

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            try:
                  params = TodosParams.model_validate(invocation.params)
            except ValidationError as exc:
                  return ToolResult(success=False, output="", error=f"Invalid arguments: {exc}")

            if params.action == "add":
                  if not params.content:
                        return ToolResult(success=False, output="", error="'content' is required to add a task.")
                  item = self._store.add(params.content)
                  return ToolResult(
                        success=True,
                        output=f"Added task #{item.id}.\n{_render(self._store)}",
                        metadata={"id": item.id, "count": len(self._store.items())},
                  )

            if params.action == "complete":
                  if params.task_id is None:
                        return ToolResult(success=False, output="", error="'task_id' is required to complete a task.")
                  item = self._store.set_status(params.task_id, TodoStatus.COMPLETED)
                  if item is None:
                        return ToolResult(success=False, output="", error=f"No task with id {params.task_id}.")
                  return ToolResult(
                        success=True,
                        output=f"Completed task #{item.id}.\n{_render(self._store)}",
                        metadata={"id": item.id},
                  )

            if params.action == "clear":
                  cleared = self._store.clear()
                  return ToolResult(success=True, output=f"Cleared {cleared} task(s).", metadata={"cleared": cleared})

            return ToolResult(
                  success=True,
                  output=_render(self._store),
                  metadata={"count": len(self._store.items())},
            )
