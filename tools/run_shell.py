from __future__ import annotations

import asyncio

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class RunShellTool(Tool):
      name = "run_shell"
      description = "Run a shell command in the working directory and capture its output."
      kind = ToolKind.SHELL
      parameters = {
            "type": "object",
            "properties": {
                  "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                  },
            },
            "required": ["command"],
      }

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            command = invocation.params["command"]
            try:
                  proc = await asyncio.create_subprocess_shell(
                        command,
                        cwd=str(invocation.cwd),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                  )
                  stdout, stderr = await proc.communicate()
            except OSError as exc:
                  return ToolResult(success=False, output="", error=str(exc))

            output = stdout.decode(errors="replace")
            error = stderr.decode(errors="replace")
            success = proc.returncode == 0
            return ToolResult(
                  success=success,
                  output=output,
                  error=error or None if not success else None,
                  metadata={"returncode": proc.returncode},
            )
