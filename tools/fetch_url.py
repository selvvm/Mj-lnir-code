from __future__ import annotations

import httpx

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class FetchUrlTool(Tool):
      name = "fetch_url"
      description = "Fetch the contents of an HTTP(S) URL and return the response body."
      kind = ToolKind.NETWORK
      parameters = {
            "type": "object",
            "properties": {
                  "url": {
                        "type": "string",
                        "description": "The HTTP(S) URL to fetch.",
                  },
            },
            "required": ["url"],
      }

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            url = invocation.params["url"]
            try:
                  async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                        response = await client.get(url)
            except httpx.HTTPError as exc:
                  return ToolResult(success=False, output="", error=str(exc))

            return ToolResult(
                  success=response.is_success,
                  output=response.text,
                  error=None if response.is_success else f"HTTP {response.status_code}",
                  metadata={"status_code": response.status_code, "url": str(response.url)},
            )
