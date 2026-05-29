from __future__ import annotations


def count_tokens(content: str, model_name: str) -> int:
      """Approximate the number of tokens in `content`.

      Uses a simple ~4-chars-per-token heuristic so no tokenizer dependency is
      needed. `model_name` is accepted for future per-model tokenizers (e.g.
      tiktoken) but is unused by the heuristic.
      """
      return len(content) // 4
