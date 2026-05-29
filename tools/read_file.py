from __future__ import annotations

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class ReadFileTool(Tool):
      name = "read_file"
      description = "Read the contents of a text file at the given path."
      kind = ToolKind.READ
      max_file_size = 256 * 1024  # 256 KB
      parameters = {
            "type": "object",
            "properties": {
                  "path": {
                        "type": "string",
                        "description": "Path to the file, relative to the working directory or absolute.",
                  },
            },
            "required": ["path"],
      }

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            path = invocation.cwd / invocation.params["path"]
            try:
                  size = path.stat().st_size
            except FileNotFoundError:
                  return ToolResult(success=False, output="", error=f"File not found: {path}")
            except OSError as exc:
                  return ToolResult(success=False, output="", error=str(exc))

            if size > self.max_file_size:
                  return ToolResult(
                        success=False,
                        output="",
                        error=f"File too large: {size} bytes (max {self.max_file_size}).",
                  )

            try:
                  data = path.read_bytes()
            except OSError as exc:
                  return ToolResult(success=False, output="", error=str(exc))

            if b"\x00" in data:
                  return ToolResult(success=False, output="", error=f"Cannot read binary file: {path}")
            try:
                  content = data.decode("utf-8")
            except UnicodeDecodeError:
                  return ToolResult(success=False, output="", error=f"Cannot read binary file: {path}")

            return ToolResult(success=True, output=content, metadata={"path": str(path), "size": size})
