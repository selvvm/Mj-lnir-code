from __future__ import annotations

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class WriteFileTool(Tool):
      name = "write_file"
      description = "Write text content to a file, creating or overwriting it."
      kind = ToolKind.WRITE
      parameters = {
            "type": "object",
            "properties": {
                  "path": {
                        "type": "string",
                        "description": "Path to the file, relative to the working directory or absolute.",
                  },
                  "content": {
                        "type": "string",
                        "description": "The full text content to write to the file.",
                  },
            },
            "required": ["path", "content"],
      }

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            path = invocation.cwd / invocation.params["path"]
            content = invocation.params["content"]
            try:
                  path.parent.mkdir(parents=True, exist_ok=True)
                  path.write_text(content, encoding="utf-8")
            except OSError as exc:
                  return ToolResult(success=False, output="", error=str(exc))
            return ToolResult(
                  success=True,
                  output=f"Wrote {len(content)} characters to {path}",
                  metadata={"path": str(path)},
            )
