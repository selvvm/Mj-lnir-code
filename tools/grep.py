from __future__ import annotations

import asyncio
import fnmatch
import re
import shutil
from pathlib import Path

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult

_DEFAULT_HEAD_LIMIT = 200
_SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


class GrepTool(Tool):
      name = "grep"
      description = (
            "Search file contents with a regular expression. Uses ripgrep when "
            "available and otherwise a built-in scanner that skips binary files and "
            "common vendor directories. Returns matching file paths, matching lines, "
            "or per-file match counts."
      )
      kind = ToolKind.READ
      parameters = {
            "type": "object",
            "properties": {
                  "pattern": {
                        "type": "string",
                        "description": "Regular expression to search for.",
                  },
                  "path": {
                        "type": "string",
                        "description": "File or directory to search, relative to the working directory. Defaults to the whole working directory.",
                  },
                  "glob": {
                        "type": "string",
                        "description": "Only search files whose name matches this glob, e.g. '*.py'.",
                  },
                  "case_insensitive": {
                        "type": "boolean",
                        "description": "Case-insensitive match. Defaults to false.",
                  },
                  "output_mode": {
                        "type": "string",
                        "enum": ["files_with_matches", "content", "count"],
                        "description": "files_with_matches (paths), content (matching lines with line numbers), or count (matches per file). Defaults to files_with_matches.",
                  },
                  "context_lines": {
                        "type": "integer",
                        "description": "Lines of context to show around each match in content mode. Defaults to 0.",
                  },
                  "head_limit": {
                        "type": "integer",
                        "description": "Maximum number of output lines. Defaults to 200.",
                  },
            },
            "required": ["pattern"],
      }

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            params = invocation.params
            pattern = params["pattern"]
            rel_path = params.get("path", ".")
            output_mode = params.get("output_mode", "files_with_matches")
            case_insensitive = params.get("case_insensitive", False)
            glob = params.get("glob")
            context_lines = params.get("context_lines", 0)
            head_limit = params.get("head_limit", _DEFAULT_HEAD_LIMIT)

            try:
                  re.compile(pattern, re.IGNORECASE if case_insensitive else 0)
            except re.error as exc:
                  return ToolResult(success=False, output="", error=f"Invalid regex: {exc}")

            base = invocation.cwd / rel_path
            if not base.exists():
                  return ToolResult(success=False, output="", error=f"Path not found: {base}")

            if shutil.which("rg"):
                  lines = await self._ripgrep(
                        invocation.cwd, pattern, rel_path, output_mode, case_insensitive, glob, context_lines
                  )
            else:
                  lines = self._fallback(
                        invocation.cwd, base, pattern, output_mode, case_insensitive, glob, context_lines
                  )

            total = len(lines)
            shown = lines[:head_limit]
            if not shown:
                  return ToolResult(success=True, output="No matches found.", metadata={"matches": 0})
            output = "\n".join(shown)
            truncated = total > head_limit
            if truncated:
                  output += f"\n… ({total - head_limit} more lines truncated)"
            return ToolResult(success=True, output=output, metadata={"matches": total, "truncated": truncated})

      async def _ripgrep(
            self,
            cwd: Path,
            pattern: str,
            rel_path: str,
            output_mode: str,
            case_insensitive: bool,
            glob: str | None,
            context_lines: int,
      ) -> list[str]:
            args = ["rg", "--no-messages", "--color", "never"]
            if case_insensitive:
                  args.append("-i")
            if glob:
                  args += ["-g", glob]
            if output_mode == "files_with_matches":
                  args.append("-l")
            elif output_mode == "count":
                  args.append("-c")
            else:
                  args += ["-n", "--no-heading", "--with-filename"]
                  if context_lines:
                        args += ["-C", str(context_lines)]
            args += ["--", pattern, rel_path]
            proc = await asyncio.create_subprocess_exec(
                  *args,
                  cwd=str(cwd),
                  stdout=asyncio.subprocess.PIPE,
                  stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return [line for line in stdout.decode(errors="replace").splitlines() if line]

      def _fallback(
            self,
            cwd: Path,
            base: Path,
            pattern: str,
            output_mode: str,
            case_insensitive: bool,
            glob: str | None,
            context_lines: int,
      ) -> list[str]:
            regex = re.compile(pattern, re.IGNORECASE if case_insensitive else 0)
            files = [base] if base.is_file() else [
                  p for p in sorted(base.rglob("*"))
                  if p.is_file()
                  and not _SKIP_DIRS.intersection(p.parts)
                  and (not glob or fnmatch.fnmatch(p.name, glob))
            ]

            results: list[str] = []
            for path in files:
                  try:
                        data = path.read_bytes()
                  except OSError:
                        continue
                  if b"\x00" in data:
                        continue
                  try:
                        file_lines = data.decode("utf-8").splitlines()
                  except UnicodeDecodeError:
                        continue

                  matched = [i for i, line in enumerate(file_lines) if regex.search(line)]
                  if not matched:
                        continue
                  rel = self._display_path(path, cwd)
                  if output_mode == "files_with_matches":
                        results.append(rel)
                  elif output_mode == "count":
                        results.append(f"{rel}:{len(matched)}")
                  else:
                        emitted: set[int] = set()
                        for i in matched:
                              lo = max(0, i - context_lines)
                              hi = min(len(file_lines), i + context_lines + 1)
                              for j in range(lo, hi):
                                    if j not in emitted:
                                          emitted.add(j)
                                          results.append(f"{rel}:{j + 1}:{file_lines[j]}")
            return results

      @staticmethod
      def _display_path(path: Path, cwd: Path) -> str:
            try:
                  return str(path.relative_to(cwd))
            except ValueError:
                  return str(path)
