from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
      """Per-session configuration: the model, its API connection, and loop limits.

      `api_key` falls back to the DEEPSEEK_API_KEY environment variable when not
      passed explicitly, so `Config()` works out of the box.
      """

      api_key: str | None = None
      base_url: str = "https://api.deepseek.com"
      model: str = "deepseek-chat"
      max_iterations: int = 10
      cwd: Path = field(default_factory=Path.cwd)
      memory_path: Path = field(default_factory=lambda: Path.home() / ".ai_coding_agent" / "memory.json")

      # USD per 1M tokens. Defaults are DeepSeek deepseek-chat list prices;
      # override them if pricing changes or for a different model.
      price_input_per_1m: float = 0.27
      price_cached_input_per_1m: float = 0.07
      price_output_per_1m: float = 1.10

      def __post_init__(self) -> None:
            if self.api_key is None:
                  self.api_key = os.getenv("DEEPSEEK_API_KEY")
            self.cwd = Path(self.cwd).resolve()
            self.memory_path = Path(self.memory_path)
