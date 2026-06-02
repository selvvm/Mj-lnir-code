from __future__ import annotations

import dataclasses

from pydantic import BaseModel, Field

from config.config import Config
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class SubagentParams(BaseModel):
      task: str = Field(..., description="A clear, self-contained task for the subagent to complete.")


class _Subagent(Tool):
      """Base for specialized subagents that delegate to a fresh, isolated Agent.

      A concrete subagent sets its `name`, `description`, `role` (its system-prompt
      persona), and `allowed_tools` (the read-only toolset it may use). Each call
      spins up a new Session + Agent, runs it to completion silently, and returns
      only the final text. The child cannot spawn further subagents, so depth is 1.
      """

      kind = ToolKind.AGENT
      parameters = SubagentParams.model_json_schema()
      role: str = ""
      allowed_tools: set[str] = set()

      def __init__(self, config: Config) -> None:
            self._config = config

      async def execute(self, invocation: ToolInvocation) -> ToolResult:
            # Imported lazily to avoid a circular import (agent -> session -> tools).
            from agent.agent import Agent
            from agent.events import AgentEventType
            from agent.session import Session

            params = SubagentParams(**invocation.params)

            child_config = dataclasses.replace(self._config, developer_instructions=self.role)
            child = Session(child_config)
            for name in [tool.name for tool in child.tool_registry.get_tools()]:
                  if name not in self.allowed_tools:
                        child.tool_registry.unregister(name)

            agent = Agent(child)
            final = ""
            try:
                  async for event in agent.run(params.task):
                        if event.type is AgentEventType.TEXT_COMPLETE:
                              final = event.data["text"]
                        elif event.type is AgentEventType.AGENT_ERROR:
                              return ToolResult.error_result(f"Subagent failed: {event.data.get('error')}")
            finally:
                  await agent.close()

            return ToolResult.success_result(final or "(subagent returned no output)")


_EXPLORER_ROLE = """You are a code exploration subagent. Investigate the codebase to \
answer the question or complete the exploration task you are given.

- Use grep and read_file to locate relevant code and trace how things connect.
- Read enough to be accurate; do not guess.
- You are read-only: never modify anything.
- Return a clear, concise summary citing file paths and line numbers (path:line) so \
the caller can navigate directly. If you cannot find something, say so plainly."""


_REVIEWER_ROLE = """You are a code review subagent. Examine the code or diff relevant \
to the task and report problems.

- Use run_shell (e.g. `git diff`, `git status`) and read_file/grep to gather context.
- Focus on real issues: bugs, edge cases, security problems, and clear simplifications \
— not style nitpicks.
- Be specific: cite file paths and line numbers (path:line) and explain why each finding \
matters.
- You are read-only: never modify any files.
- Return a concise, prioritized review. If you find nothing significant, say so."""


class CodeExplorerTool(_Subagent):
      name = "code_explorer"
      description = (
            "Delegate codebase exploration to a read-only subagent: locate code, trace "
            "usages, and summarize how things work. Returns the subagent's findings."
      )
      role = _EXPLORER_ROLE
      allowed_tools = {"read_file", "grep", "web_search", "web_fetch"}


class CodeReviewerTool(_Subagent):
      name = "code_reviewer"
      description = (
            "Delegate a code review to a subagent: examine code or the current diff for "
            "bugs, risks, and improvements. Returns a concise, prioritized review."
      )
      role = _REVIEWER_ROLE
      allowed_tools = {"read_file", "grep", "run_shell"}
