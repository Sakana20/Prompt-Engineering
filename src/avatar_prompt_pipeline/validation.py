from __future__ import annotations

import re
from collections.abc import Sequence

from .models import CopyValidationReport, IssueCode, ValidationIssue

REQUIRED_BENEFIT = "淘宝闪购，最高12元无门槛红包天天享。"
MIN_COPY_CHARACTERS = 80
MAX_COPY_CHARACTERS = 120

BANNED_EXPRESSIONS = (
    "最",
    "绝对",
    "全网最低",
    "补贴",
    "0元购",
    "免单",
    "秒杀",
    "限时疯抢",
    "比超市便宜",
    "闭眼入",
    "快冲",
    "姐妹们",
    "家人们",
    "冲就完了",
)
CALLS_TO_ACTION = (
    "点击视频下方链接",
    "点链接",
    "立即购买",
    "赶紧下单",
    "点击购买",
    "直播间",
)
FORMAT_PREFIXES = ("#", "-", "*", "1.", "1、", "①")


def count_spoken_characters(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def validate_copy(text: str) -> CopyValidationReport:
    cleaned = text.replace("\x00", "").strip()
    count = count_spoken_characters(cleaned)
    issues: list[ValidationIssue] = []
    if count < MIN_COPY_CHARACTERS:
        issues.append(
            ValidationIssue(IssueCode.TOO_SHORT, f"口播少于 {MIN_COPY_CHARACTERS} 字", str(count))
        )
    if count > MAX_COPY_CHARACTERS:
        issues.append(
            ValidationIssue(IssueCode.TOO_LONG, f"口播超过 {MAX_COPY_CHARACTERS} 字", str(count))
        )
    if REQUIRED_BENEFIT not in cleaned:
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_BENEFIT,
                "缺少固定淘宝闪购利益点，或利益点未按已验证口径输出",
                REQUIRED_BENEFIT,
            )
        )

    # “最高”是固定利益点的一部分；先移除固定口径，再检查禁用的单字“最”。
    expression_scope = cleaned.replace(REQUIRED_BENEFIT, "")
    for expression in BANNED_EXPRESSIONS:
        if expression in expression_scope:
            issues.append(ValidationIssue(IssueCode.BANNED_EXPRESSION, "出现禁止表达", expression))
    for expression in CALLS_TO_ACTION:
        if expression in cleaned:
            issues.append(ValidationIssue(IssueCode.CALL_TO_ACTION, "出现行动引导", expression))
    if "\n" in cleaned or cleaned.startswith(FORMAT_PREFIXES):
        issues.append(
            ValidationIssue(
                IssueCode.FORMAT_VIOLATION,
                "最终口播必须是单段正文，不能包含标题、列表或换行",
            )
        )
    return CopyValidationReport(character_count=count, issues=tuple(issues))


def _bigrams(text: str) -> set[str]:
    normalized = re.sub(r"[\W_]+", "", text)
    return {normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))}


def copy_similarity(left: str, right: str) -> float:
    left_bigrams = _bigrams(left)
    right_bigrams = _bigrams(right)
    union = left_bigrams | right_bigrams
    if not union:
        return 1.0 if left.strip() == right.strip() else 0.0
    return len(left_bigrams & right_bigrams) / len(union)


def validate_batch_diversity(
    copies: Sequence[str], *, similarity_threshold: float = 0.72
) -> tuple[ValidationIssue, ...]:
    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("相似度阈值必须在 0 到 1 之间")
    issues: list[ValidationIssue] = []
    for left_index, left in enumerate(copies):
        for right_index in range(left_index + 1, len(copies)):
            right = copies[right_index]
            pair = f"{left_index + 1},{right_index + 1}"
            if left.strip() == right.strip():
                issues.append(ValidationIssue(IssueCode.DUPLICATE_COPY, "批次存在重复文案", pair))
                continue
            similarity = copy_similarity(left, right)
            if similarity >= similarity_threshold:
                issues.append(
                    ValidationIssue(
                        IssueCode.HIGH_SIMILARITY,
                        f"批次文案相似度过高：{similarity:.2f}",
                        pair,
                    )
                )
    return tuple(issues)
