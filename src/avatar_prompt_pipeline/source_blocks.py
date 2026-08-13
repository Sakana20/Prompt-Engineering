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


PERSON_BLOCK_LIMITS = {
    "identity": 2,
    "hair": 2,
    "outfit": 4,
    "scene": 2,
}
PERSON_CONTEXT_CHARACTER_LIMIT = 4500
PERSON_CONTEXT_HEADING = "\n\n【本次筛选的人物学习块】\n"


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
    contracts: dict[str, SourceBlockContract] = {}
    pattern = re.compile(
        r"^### `(?P<block_id>[a-z0-9][a-z0-9-]{2,95})`[ \t]*\n+"
        r"[ \t]*```text[ \t]*\n(?P<template>.*?)\n```(?=\n|$)",
        flags=re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(published):
        block_id = match.group("block_id")
        template = match.group("template")
        slot_names = set(re.findall(r"\[([^\[\]\n]+)\]", template))
        contracts[block_id] = SourceBlockContract(
            block_id=block_id,
            solid_food_only=category_family(template) is not CategoryFamily.BEVERAGE,
            minimum_source_slot_values=max(1, len(slot_names)),
        )
    return contracts


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
