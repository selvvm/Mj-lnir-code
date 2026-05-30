from __future__ import annotations

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class EditFileTool(Tool):
      name = "edit_file"
      description = (
            "Replace an exact string in a file with new text. The old string must "
            "appear exactly once unless replace_all is true."
      )
      kind = ToolKind.WRITE
      parameters = {
            "type": "object",
            "properties": {
                  "path": {
                        "type": "string",
                        "description": "Path to the file, relative to the working directory or absolute.",
                  },
                  "old_string": {
                        "type": "string",
                        "description": "The exact text to replace, including whitespace.",
                  },
                  "new_string": {
                        "type": "string",
                        "description": "The text to replace it with.",
                  },
                  "replace_all": {
                        "type": "boolean",
                        "description": "Replace every occurrence instead of requiring a single match. Defaults to false.",
                  },
            },
            "required": ["path", "old_string", "new_string"],
      }

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            path = invocation.cwd / invocation.params["path"]
            old_string = invocation.params["old_string"]
            new_string = invocation.params["new_string"]
            replace_all = invocation.params.get("replace_all", False)

            try:
                  content = path.read_text(encoding="utf-8")
            except FileNotFoundError:
                  return ToolResult(success=False, output="", error=f"File not found: {path}")
            except (OSError, UnicodeDecodeError) as exc:
                  return ToolResult(success=False, output="", error=str(exc))

            count = content.count(old_string)
            if count == 0:
                  return ToolResult(success=False, output="", error="old_string not found in file.")
            if count > 1 and not replace_all:
                  return ToolResult(
                        success=False,
                        output="",
                        error=f"old_string is not unique ({count} matches); add context or set replace_all.",
                  )

            try:
                  path.write_text(content.replace(old_string, new_string), encoding="utf-8")
            except OSError as exc:
                  return ToolResult(success=False, output="", error=str(exc))

            replaced = count if replace_all else 1
            return ToolResult(
                  success=True,
                  output=f"Replaced {replaced} occurrence(s) in {path}",
                  metadata={"path": str(path), "replacements": replaced},
            )
