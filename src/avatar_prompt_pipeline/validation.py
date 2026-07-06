from __future__ import annotations

import re
from collections.abc import Sequence

from .models import (
    CampaignSpec,
    CopyValidationReport,
    IssueCode,
    ValidationConfig,
    ValidationIssue,
    VisualProfile,
)
from .presets import TAOBAO_DEFAULT_BENEFIT, TAOBAO_DEFAULT_CAMPAIGN

DEFAULT_VALIDATION_CONFIG = ValidationConfig()
REQUIRED_BENEFIT = TAOBAO_DEFAULT_BENEFIT
NO_SPLIT_OPEN = "[[NO_SPLIT]]"
NO_SPLIT_CLOSE = "[[/NO_SPLIT]]"
MARKED_REQUIRED_BENEFIT = f"{NO_SPLIT_OPEN}{REQUIRED_BENEFIT}{NO_SPLIT_CLOSE}"
MIN_COPY_CHARACTERS = DEFAULT_VALIDATION_CONFIG.min_characters
MAX_COPY_CHARACTERS = DEFAULT_VALIDATION_CONFIG.max_characters
BANNED_EXPRESSIONS = DEFAULT_VALIDATION_CONFIG.banned_expressions
CALLS_TO_ACTION = DEFAULT_VALIDATION_CONFIG.call_to_actions
FORMAT_PREFIXES = DEFAULT_VALIDATION_CONFIG.format_prefixes


def strip_no_split_markers(text: str) -> str:
    return text.replace(NO_SPLIT_OPEN, "").replace(NO_SPLIT_CLOSE, "")


def wrap_required_benefit(text: str) -> str:
    if MARKED_REQUIRED_BENEFIT in text:
        return text
    return text.replace(REQUIRED_BENEFIT, MARKED_REQUIRED_BENEFIT)


def wrap_campaign_benefits(text: str, campaign: CampaignSpec) -> str:
    wrapped = text
    for phrase in campaign.no_split_phrases:
        marked = f"{NO_SPLIT_OPEN}{phrase}{NO_SPLIT_CLOSE}"
        if marked not in wrapped:
            wrapped = wrapped.replace(phrase, marked)
    for benefit in campaign.benefit_points:
        marked = f"{NO_SPLIT_OPEN}{benefit.text}{NO_SPLIT_CLOSE}"
        if benefit.no_split and marked not in wrapped:
            wrapped = wrapped.replace(benefit.text, marked)
    return wrapped


def count_spoken_characters(text: str) -> int:
    return len(re.sub(r"\s+", "", strip_no_split_markers(text)))


def validate_copy(
    text: str,
    campaign: CampaignSpec = TAOBAO_DEFAULT_CAMPAIGN,
    validation_config: ValidationConfig = DEFAULT_VALIDATION_CONFIG,
) -> CopyValidationReport:
    cleaned = text.replace("\x00", "").strip()
    count = count_spoken_characters(cleaned)
    issues: list[ValidationIssue] = []
    if count < validation_config.min_characters:
        issues.append(
            ValidationIssue(
                IssueCode.TOO_SHORT,
                f"口播少于 {validation_config.min_characters} 字",
                str(count),
            )
        )
    if count > validation_config.max_characters:
        issues.append(
            ValidationIssue(
                IssueCode.TOO_LONG,
                f"口播超过 {validation_config.max_characters} 字",
                str(count),
            )
        )
    if cleaned.count(NO_SPLIT_OPEN) != cleaned.count(NO_SPLIT_CLOSE):
        issues.append(
            ValidationIssue(
                IssueCode.MALFORMED_NO_SPLIT_MARKER,
                "NO_SPLIT 标签必须成对出现",
            )
        )
    expression_scope = strip_no_split_markers(cleaned)
    for phrase in campaign.no_split_phrases:
        marked = f"{NO_SPLIT_OPEN}{phrase}{NO_SPLIT_CLOSE}"
        if marked not in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.MISSING_NO_SPLIT_MARKER,
                    "组合保护片段必须使用 NO_SPLIT 标签完整包裹",
                    marked,
                )
            )
    for benefit in campaign.benefit_points:
        if benefit.required and benefit.exact_match and benefit.text not in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.MISSING_BENEFIT,
                    f"缺少必填利益点：{benefit.id}",
                    benefit.text,
                )
            )
            continue
        marked = f"{NO_SPLIT_OPEN}{benefit.text}{NO_SPLIT_CLOSE}"
        if benefit.required and benefit.no_split and marked not in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.MISSING_NO_SPLIT_MARKER,
                    f"利益点 {benefit.id} 必须使用 NO_SPLIT 标签完整包裹",
                    marked,
                )
            )
        if benefit.text in expression_scope:
            expression_scope = expression_scope.replace(benefit.text, "")

    banned_expressions = (*validation_config.banned_expressions, *campaign.forbidden_expressions)
    for expression in banned_expressions:
        if expression in expression_scope:
            issues.append(ValidationIssue(IssueCode.BANNED_EXPRESSION, "出现禁止表达", expression))
    for expression in validation_config.call_to_actions:
        if expression in cleaned:
            issues.append(ValidationIssue(IssueCode.CALL_TO_ACTION, "出现行动引导", expression))
    if "\n" in cleaned or cleaned.startswith(validation_config.format_prefixes):
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


def validate_visual_diversity(
    profiles: Sequence[VisualProfile],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    seen_identities: dict[str, int] = {}
    seen_outfits: dict[str, int] = {}
    for index, profile in enumerate(profiles, start=1):
        identity = profile.identity_key.strip()
        outfit = profile.outfit_key.strip()
        if not identity or not outfit:
            raise ValueError("人物身份键和服装键不能为空")
        if identity in seen_identities:
            issues.append(
                ValidationIssue(
                    IssueCode.DUPLICATE_PERSON,
                    "批次存在重复人物",
                    f"{seen_identities[identity]},{index}",
                )
            )
        else:
            seen_identities[identity] = index
        if outfit in seen_outfits:
            issues.append(
                ValidationIssue(
                    IssueCode.DUPLICATE_OUTFIT,
                    "批次存在重复服装",
                    f"{seen_outfits[outfit]},{index}",
                )
            )
        else:
            seen_outfits[outfit] = index
    return tuple(issues)
