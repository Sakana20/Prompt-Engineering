from __future__ import annotations

import re

_REPEATED_PUNCTUATION = re.compile(r"([\uFF0C\u3002\uFF01\uFF1F\uFF1B\uFF1A\u3001,.!?;:])\1+")


def normalize_asr_editable_draft(value: str) -> str:
    """Create a readable draft without changing the immutable ASR transcript."""

    normalized: list[str] = []
    pending_whitespace = False
    for char in value:
        if char.isspace():
            pending_whitespace = bool(normalized)
            continue
        if pending_whitespace and _preserve_ascii_word_boundary(normalized[-1], char):
            normalized.append(" ")
        normalized.append(char)
        pending_whitespace = False
    return _REPEATED_PUNCTUATION.sub(r"\1", "".join(normalized))


def _preserve_ascii_word_boundary(left: str, right: str) -> bool:
    return left.isascii() and left.isalnum() and right.isascii() and right.isalnum()


__all__ = ["normalize_asr_editable_draft"]
