from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

from .learning.publication import reference_path


class CategoryFamily(StrEnum):
    BEVERAGE = "beverage"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class SourceBlockContract:
    block_id: str
    solid_food_only: bool
    minimum_source_slot_values: int = 1


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
    return SOURCE_BLOCK_CONTRACTS.get(source_block_id) or learned_source_block_contracts().get(
        source_block_id
    )


def source_fill_is_compatible(category: str, contract: SourceBlockContract) -> bool:
    return not (contract.solid_food_only and category_family(category) is CategoryFamily.BEVERAGE)


def _json_fences(path: Path) -> tuple[dict[str, object], ...]:
    if not path.is_file():
        return ()
    text = path.read_text(encoding="utf-8")
    records: list[dict[str, object]] = []
    for match in re.finditer(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(cast(dict[str, object], value))
    return tuple(records)


def learned_source_block_contracts(path: Path | None = None) -> dict[str, SourceBlockContract]:
    resource = path or reference_path("learned-copy-source-blocks.md")
    contracts: dict[str, SourceBlockContract] = {}
    for record in _json_fences(resource):
        block_id = record.get("block_id")
        minimum = record.get("minimum_source_slot_values", 1)
        solid_food_only = record.get("solid_food_only", False)
        if (
            isinstance(block_id, str)
            and isinstance(minimum, int)
            and not isinstance(minimum, bool)
            and minimum >= 1
            and isinstance(solid_food_only, bool)
        ):
            contracts[block_id] = SourceBlockContract(
                block_id=block_id,
                solid_food_only=solid_food_only,
                minimum_source_slot_values=minimum,
            )
    return contracts


def learned_person_blocks(path: Path | None = None) -> tuple[dict[str, object], ...]:
    resource = path or reference_path("person-prompt-source-blocks.md")
    return _json_fences(resource)
