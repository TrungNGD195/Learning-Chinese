from typing import Protocol
from pathlib import Path

import tiktoken
from tiktoken.load import load_tiktoken_bpe


class TokenCounter(Protocol):
    """Provider-independent model-token counting boundary."""

    def count(self, text: str) -> int:
        """Return the exact model token count for text."""
        ...


class TiktokenTokenCounter:
    """Synchronous local token counter for the selected GPT model family."""

    def __init__(self) -> None:
        vocab_path = Path(__file__).with_name("assets") / "o200k_base.tiktoken"
        ranks = load_tiktoken_bpe(
            str(vocab_path),
            expected_hash="446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d",
        )
        pattern = "|".join(
            (
                r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
                r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
                r"\p{N}{1,3}",
                r" ?[^\s\p{L}\p{N}]+[\r\n/]*",
                r"\s*[\r\n]+",
                r"\s+(?!\S)",
                r"\s+",
            )
        )
        self._encoding = tiktoken.Encoding(
            name="o200k_base",
            pat_str=pattern,
            mergeable_ranks=ranks,
            special_tokens={"<|endoftext|>": 199_999, "<|endofprompt|>": 200_018},
        )

    def count(self, text: str) -> int:
        if not isinstance(text, str):
            raise TypeError("Token input must be text")
        return len(self._encoding.encode(text))
