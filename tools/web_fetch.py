from __future__ import annotations

import html
import re

import httpx

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult

_HEADERS = {
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
_DEFAULT_MAX_LENGTH = 20000

_DROP_RE = re.compile(r"<(script|style|head|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_BLOCK_RE = re.compile(r"</(p|div|li|h[1-6]|tr|article|section)\s*>", re.IGNORECASE)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)


def _html_to_text(raw: str) -> tuple[str, str]:
      title_match = _TITLE_RE.search(raw)
      title = html.unescape(_TAG_RE.sub("", title_match.group(1))).strip() if title_match else ""

      body = _DROP_RE.sub(" ", raw)
      body = _BLOCK_RE.sub("\n", body)
      body = _BR_RE.sub("\n", body)
      text = html.unescape(_TAG_RE.sub("", body))
      text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
      return title, text


class WebFetchTool(Tool):
      name = "web_fetch"
      description = (
            "Fetch a URL and return its content. HTML pages are converted to readable "
            "text (with the page title); JSON and plain text are returned as-is. Output "
            "is truncated to max_length characters."
      )
      kind = ToolKind.NETWORK
      parameters = {
            "type": "object",
            "properties": {
                  "url": {
                        "type": "string",
                        "description": "The HTTP(S) URL to fetch.",
                  },
                  "max_length": {
                        "type": "integer",
                        "description": "Maximum characters to return. Defaults to 20000.",
                  },
            },
            "required": ["url"],
      }

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            url = invocation.params["url"]
            max_length = invocation.params.get("max_length", _DEFAULT_MAX_LENGTH)
            try:
                  async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=_HEADERS) as client:
                        response = await client.get(url)
            except httpx.HTTPError as exc:
                  return ToolResult(success=False, output="", error=str(exc))
            if not response.is_success:
                  return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP {response.status_code}",
                        metadata={"status_code": response.status_code},
                  )

            content_type = response.headers.get("content-type", "")
            title = ""
            if "html" in content_type or response.text.lstrip()[:1] == "<":
                  title, body = _html_to_text(response.text)
            else:
                  body = response.text

            truncated = len(body) > max_length
            output = body[:max_length]
            if truncated:
                  output += f"\n… (truncated at {max_length} chars)"
            if title:
                  output = f"# {title}\n\n{output}"

            return ToolResult(
                  success=True,
                  output=output,
                  metadata={
                        "status_code": response.status_code,
                        "url": str(response.url),
                        "content_type": content_type,
                        "truncated": truncated,
                        **({"title": title} if title else {}),
                  },
            )
