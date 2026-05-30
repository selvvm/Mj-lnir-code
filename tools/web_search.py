from __future__ import annotations

import html
import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult

_DDG_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
_RESULT_RE = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
_SNIPPET_RE = re.compile(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
      return html.unescape(_TAG_RE.sub("", text)).strip()


def _real_url(href: str) -> str:
      """Unwrap DuckDuckGo's //duckduckgo.com/l/?uddg=<encoded> redirect links."""
      if "uddg=" in href:
            params = parse_qs(urlparse(href).query)
            if "uddg" in params:
                  return unquote(params["uddg"][0])
      if href.startswith("//"):
            return "https:" + href
      return href


class WebSearchTool(Tool):
      name = "web_search"
      description = (
            "Search the web and return the top results as title, URL, and snippet. "
            "Backed by DuckDuckGo and needs no API key. Use it to find pages, then "
            "web_fetch to read one."
      )
      kind = ToolKind.NETWORK
      parameters = {
            "type": "object",
            "properties": {
                  "query": {
                        "type": "string",
                        "description": "The search query.",
                  },
                  "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return. Defaults to 5.",
                  },
            },
            "required": ["query"],
      }

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            query = invocation.params["query"]
            max_results = invocation.params.get("max_results", 5)
            try:
                  async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=_HEADERS) as client:
                        response = await client.post(_DDG_URL, data={"q": query})
            except httpx.HTTPError as exc:
                  return ToolResult(success=False, output="", error=str(exc))
            if not response.is_success:
                  return ToolResult(success=False, output="", error=f"HTTP {response.status_code}")

            results = _RESULT_RE.findall(response.text)
            snippets = _SNIPPET_RE.findall(response.text)
            if not results:
                  return ToolResult(success=True, output="No results found.", metadata={"results": 0, "query": query})

            blocks: list[str] = []
            for i, (href, raw_title) in enumerate(results[:max_results]):
                  snippet = _clean(snippets[i]) if i < len(snippets) else ""
                  blocks.append(f"{i + 1}. {_clean(raw_title)}\n   {_real_url(href)}\n   {snippet}")
            return ToolResult(
                  success=True,
                  output="\n\n".join(blocks),
                  metadata={"results": len(blocks), "query": query},
            )
