from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .learning.publication import (
    COPY_RESOURCE_NAME,
    PUBLISHED_COPY_SECTION_HEADING,
    reference_path,
)


class CategoryFamily(StrEnum):
    BEVERAGE = "beverage"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class SourceBlockContract:
    block_id: str
    solid_food_only: bool
    minimum_source_slot_values: int = 1


@dataclass(frozen=True, slots=True)
class PersonSourceBlock:
    block_id: str
    block_type: str
    description: str


@dataclass(frozen=True, slots=True)
class CopySourceBlock:
    block_id: str
    template: str
    contract: SourceBlockContract
    source_fill_restriction: str = ""


PERSON_BLOCK_LIMITS = {
    "identity": 2,
    "hair": 2,
    "outfit": 4,
    "scene": 2,
}
PERSON_CONTEXT_CHARACTER_LIMIT = 4500
PERSON_CONTEXT_HEADING = "\n\n【本次筛选的人物学习块】\n"
COPY_BLOCK_MINIMUM_LIMIT = 4
COPY_CONTEXT_CHARACTER_LIMIT = 7000
COPY_CONTEXT_HEADING = "\n\n【本次筛选的真人原文块】\n"


_BEVERAGE_CATEGORY_TERMS = (
    "咖啡",
    "奶茶",
    "果茶",
    "茶饮",
    "饮品",
    "饮料",
    "果汁",
    "豆浆",
    "酸奶",
    "可乐",
    "瑞幸",
    "蜜雪冰城",
)


def _contract(
    block_id: str,
    *,
    solid_food_only: bool = True,
    minimum_source_slot_values: int = 1,
) -> SourceBlockContract:
    return SourceBlockContract(
        block_id=block_id,
        solid_food_only=solid_food_only,
        minimum_source_slot_values=minimum_source_slot_values,
    )


SOURCE_BLOCK_CONTRACTS = {
    contract.block_id: contract
    for contract in (
        _contract(
            "learn-001-combination",
            solid_food_only=False,
            minimum_source_slot_values=4,
        ),
        _contract("learn-002-eating-order"),
        _contract("learn-003-watch-snack"),
        _contract("learn-004-afternoon"),
        _contract("learn-005-not-hungry"),
        _contract("learn-006-winter"),
        _contract("learn-007-no-trouble"),
        _contract("learn-008-evening"),
        _contract("learn-012-squid-rhythm"),
        _contract("learn-013-friends-at-home"),
        _contract("learn-014-wrapped"),
        _contract("learn-015-finally"),
        _contract("learn-016-smell-texture"),
    )
}


def category_family(category: str) -> CategoryFamily:
    normalized = category.replace(" ", "")
    if any(term in normalized for term in _BEVERAGE_CATEGORY_TERMS):
        return CategoryFamily.BEVERAGE
    return CategoryFamily.OTHER


def source_block_contract(source_block_id: str) -> SourceBlockContract | None:
    return SOURCE_BLOCK_CONTRACTS.get(source_block_id) or published_copy_block_contracts().get(
        source_block_id
    )


def source_fill_is_compatible(category: str, contract: SourceBlockContract) -> bool:
    return not (contract.solid_food_only and category_family(category) is CategoryFamily.BEVERAGE)


def published_copy_block_contracts(path: Path | None = None) -> dict[str, SourceBlockContract]:
    resource = path or reference_path(COPY_RESOURCE_NAME)
    if not resource.is_file():
        return {}
    _, marker, published = resource.read_text(encoding="utf-8").partition(
        PUBLISHED_COPY_SECTION_HEADING
    )
    if not marker:
        return {}
    return {block.block_id: block.contract for block in _parse_copy_blocks(published)}


def learned_copy_blocks(path: Path | None = None) -> tuple[CopySourceBlock, ...]:
    resource = path or reference_path(COPY_RESOURCE_NAME)
    if not resource.is_file():
        return ()
    return _parse_copy_blocks(resource.read_text(encoding="utf-8"))


def _parse_copy_blocks(text: str) -> tuple[CopySourceBlock, ...]:
    pattern = re.compile(
        r"^### `(?P<block_id>[a-z0-9][a-z0-9-]{2,95})`[ \t]*\n+"
        r"[ \t]*```text[ \t]*\n(?P<template>.*?)\n```(?=\n|$)",
        flags=re.MULTILINE | re.DOTALL,
    )
    blocks: list[CopySourceBlock] = []
    for match in pattern.finditer(text):
        block_id = match.group("block_id")
        template = match.group("template").strip()
        configured = SOURCE_BLOCK_CONTRACTS.get(block_id)
        slot_names = set(re.findall(r"\[([^\[\]\n]+)\]", template))
        contract = configured or SourceBlockContract(
            block_id=block_id,
            solid_food_only=category_family(template) is not CategoryFamily.BEVERAGE,
            minimum_source_slot_values=max(1, len(slot_names)),
        )
        blocks.append(CopySourceBlock(block_id, template, contract))
    if len({block.block_id for block in blocks}) != len(blocks):
        raise ValueError("文案正式资源包含重复 block ID")
    return tuple(blocks)


def select_copy_blocks(
    category: str,
    context: str,
    path: Path | None = None,
    *,
    batch_size: int = 1,
) -> tuple[CopySourceBlock, ...]:
    if batch_size < 1:
        raise ValueError("文案学习筛选的 batch_size 必须大于等于 1")
    block_limit = max(COPY_BLOCK_MINIMUM_LIMIT, batch_size // 2 + 2)
    candidates = []
    for block in learned_copy_blocks(path):
        restrictions: list[str] = []
        if not source_fill_is_compatible(category, block.contract):
            restrictions.append("品类不兼容")
        if not _copy_season_is_compatible(block.template, context):
            restrictions.append("需重建季节")
        candidates.append(
            CopySourceBlock(
                block.block_id,
                block.template,
                block.contract,
                "、".join(restrictions),
            )
        )
    ranked = sorted(
        candidates,
        key=lambda block: (
            bool(block.source_fill_restriction),
            hashlib.sha256(f"{context}|{block.block_id}".encode()).hexdigest(),
            block.block_id,
        ),
    )
    selected: list[CopySourceBlock] = []
    character_count = len(COPY_CONTEXT_HEADING)
    for block in ranked:
        separator_size = 2 if selected else 0
        projected = character_count + separator_size + len(_render_copy_block(block))
        if projected > COPY_CONTEXT_CHARACTER_LIMIT:
            continue
        selected.append(block)
        character_count = projected
        if len(selected) == block_limit:
            break
    return tuple(selected)


def select_copy_block(
    category: str,
    context: str,
    path: Path | None = None,
    *,
    block_id: str = "",
    require_source_fill_compatible: bool = False,
) -> CopySourceBlock:
    candidates = select_copy_blocks(category, context, path, batch_size=1)
    if block_id:
        candidates = tuple(
            block
            for block in (
                CopySourceBlock(
                    item.block_id,
                    item.template,
                    item.contract,
                    "、".join(
                        reason
                        for reason in (
                            "品类不兼容"
                            if not source_fill_is_compatible(category, item.contract)
                            else "",
                            "需重建季节"
                            if not _copy_season_is_compatible(item.template, context)
                            else "",
                        )
                        if reason
                    ),
                )
                for item in learned_copy_blocks(path)
                if item.block_id == block_id
            )
        )
        if not candidates:
            raise ValueError(f"未找到真人原文块：{block_id}")
    if require_source_fill_compatible:
        incompatible = tuple(block for block in candidates if block.source_fill_restriction)
        candidates = tuple(block for block in candidates if not block.source_fill_restriction)
        if not candidates and incompatible and block_id:
            raise ValueError(
                f"真人原文块 {block_id} 不适用于 source_fill："
                f"{incompatible[0].source_fill_restriction}"
            )
    if not candidates:
        raise ValueError("没有符合当前品类与季节的真人原文块")
    return candidates[0]


def _copy_season_is_compatible(template: str, context: str) -> bool:
    return _person_season_is_compatible(template, context)


def render_copy_block_context(blocks: tuple[CopySourceBlock, ...]) -> str:
    if not blocks:
        return ""
    return COPY_CONTEXT_HEADING + "\n\n".join(_render_copy_block(block) for block in blocks)


def _render_copy_block(block: CopySourceBlock) -> str:
    source_fill = (
        "是"
        if not block.source_fill_restriction
        else f"否，仅 human_rewrite：{block.source_fill_restriction}"
    )
    return (
        f"### `{block.block_id}` · source_fill 兼容：{source_fill}\n\n"
        f"```text\n{block.template}\n```"
    )


def learned_person_blocks(path: Path | None = None) -> tuple[PersonSourceBlock, ...]:
    resource = path or reference_path("person-prompt-source-blocks.md")
    if not resource.is_file():
        return ()
    pattern = re.compile(
        r"^### `(?P<block_id>[a-z0-9][a-z0-9-]{2,95})` · "
        r"`(?P<block_type>identity|hair|outfit|scene)`[ \t]*\n+"
        r"[ \t]*```text[ \t]*\n(?P<description>.*?)\n```(?=\n|$)",
        flags=re.MULTILINE | re.DOTALL,
    )
    blocks = tuple(
        PersonSourceBlock(
            block_id=match.group("block_id"),
            block_type=match.group("block_type"),
            description=match.group("description").strip(),
        )
        for match in pattern.finditer(resource.read_text(encoding="utf-8"))
    )
    if len({block.block_id for block in blocks}) != len(blocks):
        raise ValueError("人物正式资源包含重复 block ID")
    return blocks


def select_person_blocks(
    context: str,
    path: Path | None = None,
) -> tuple[PersonSourceBlock, ...]:
    grouped: dict[str, list[PersonSourceBlock]] = {
        block_type: [] for block_type in PERSON_BLOCK_LIMITS
    }
    for block in learned_person_blocks(path):
        grouped[block.block_type].append(block)

    selected: list[PersonSourceBlock] = []
    character_count = len(PERSON_CONTEXT_HEADING)
    for block_type, limit in PERSON_BLOCK_LIMITS.items():
        compatible = [
            block
            for block in grouped[block_type]
            if _person_season_is_compatible(block.description, context)
        ]
        ranked = sorted(
            compatible,
            key=lambda block: (
                hashlib.sha256(f"{context}|{block.block_id}".encode()).hexdigest(),
                block.block_id,
            ),
        )
        selected_in_type = 0
        for block in ranked:
            separator_size = 2 if selected else 0
            projected = character_count + separator_size + len(_render_person_block(block))
            if projected > PERSON_CONTEXT_CHARACTER_LIMIT:
                continue
            selected.append(block)
            character_count = projected
            selected_in_type += 1
            if selected_in_type == limit:
                break
    return tuple(selected)


def _person_season_is_compatible(description: str, context: str) -> bool:
    seasons = {
        "春季": (
            "冬季",
            "冬天",
            "冬日",
            "寒冬",
            "夏季",
            "夏天",
            "夏日",
            "盛夏",
            "秋季",
            "秋天",
            "秋日",
        ),
        "夏季": ("冬季", "冬天", "冬日", "寒冬", "春季", "春天", "春日", "秋季", "秋天", "秋日"),
        "秋季": (
            "冬季",
            "冬天",
            "冬日",
            "寒冬",
            "春季",
            "春天",
            "春日",
            "夏季",
            "夏天",
            "夏日",
            "盛夏",
        ),
        "冬季": ("春季", "春天", "春日", "夏季", "夏天", "夏日", "盛夏", "秋季", "秋天", "秋日"),
    }
    for current, incompatible in seasons.items():
        if current in context:
            return not any(term in description for term in incompatible)
    return True


def render_person_block_context(blocks: tuple[PersonSourceBlock, ...]) -> str:
    if not blocks:
        return ""
    rendered = "\n\n".join(_render_person_block(block) for block in blocks)
    return PERSON_CONTEXT_HEADING + rendered


def _render_person_block(block: PersonSourceBlock) -> str:
    return f"### `{block.block_id}` · `{block.block_type}`\n\n```text\n{block.description}\n```"


def person_block_context(context: str, path: Path | None = None) -> str:
    return render_person_block_context(select_person_blocks(context, path))
