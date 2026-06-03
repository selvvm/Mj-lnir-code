from __future__ import annotations

import uuid
from datetime import datetime

from client.llm_client import LLMClient
from client.response import TokenUsage
from config.config import Config
from context.manager import ContextManager
from tools.memory import MemoryTool
from tools.registry import create_default_registry
from tools.subagent import CodeExplorerTool, CodeReviewerTool
from tools.todo import TodosTool


class Session:
      """A single chat session: its own config, client, context, and tools.

      Holding this state per Session means independent conversations don't share
      history, token accounting, or transport — each owns its own. A Session also
      carries identity (`session_id`) and lifecycle metadata (`created_at`,
      `updated_at`, turn count) so sessions can be tracked and persisted.
      """

      def __init__(self, config: Config) -> None:
            self.config = config
            self.client = LLMClient(config=config)
            self.context_manager = ContextManager(config=config)
            self.cwd = config.cwd

            # The todos tool owns its task list; the per-session registry keeps it
            # scoped to this session. Memory persists to disk across sessions.
            self.tool_registry = create_default_registry()
            self.tool_registry.register(TodosTool())
            self.tool_registry.register(MemoryTool(config.memory_path))
            self.tool_registry.register(CodeExplorerTool(config))
            self.tool_registry.register(CodeReviewerTool(config))

            self.session_id = str(uuid.uuid4())
            self.created_at = datetime.now()
            self.updated_at = datetime.now()

            self._turn_count = 0
            self.token_usage = TokenUsage()

      def increment_turn(self) -> int:
            """Record that a turn completed; bump the count and `updated_at`."""
            self._turn_count += 1
            self.updated_at = datetime.now()
            return self._turn_count

      def add_usage(self, usage: TokenUsage | None) -> None:
            """Accumulate one LLM call's token usage into the session total."""
            if usage is not None:
                  self.token_usage = self.token_usage + usage

      @property
      def estimated_cost(self) -> float:
            """Rough USD cost of the session from its accumulated token usage."""
            usage = self.token_usage
            uncached_input = max(usage.prompt_tokens - usage.cached_tokens, 0)
            return (
                  uncached_input * self.config.price_input_per_1m
                  + usage.cached_tokens * self.config.price_cached_input_per_1m
                  + usage.completion_tokens * self.config.price_output_per_1m
            ) / 1_000_000
