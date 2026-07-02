from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class BriefValidationError(ValueError):
    """Raised when a product brief cannot safely drive prompt generation."""


class IssueCode(StrEnum):
    TOO_SHORT = "TOO_SHORT"
    TOO_LONG = "TOO_LONG"
    MISSING_BENEFIT = "MISSING_BENEFIT"
    BANNED_EXPRESSION = "BANNED_EXPRESSION"
    CALL_TO_ACTION = "CALL_TO_ACTION"
    FORMAT_VIOLATION = "FORMAT_VIOLATION"
    DUPLICATE_COPY = "DUPLICATE_COPY"
    HIGH_SIMILARITY = "HIGH_SIMILARITY"


def _clean(value: str) -> str:
    return " ".join(value.replace("\x00", "").split())


@dataclass(frozen=True, slots=True)
class ProductBrief:
    category: str
    product_name: str = ""
    selling_points: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        category = _clean(self.category)
        if not category:
            raise BriefValidationError("商品品类不能为空")
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "product_name", _clean(self.product_name))
        object.__setattr__(
            self,
            "selling_points",
            tuple(point for item in self.selling_points if (point := _clean(item))),
        )
        object.__setattr__(
            self,
            "forbidden_claims",
            tuple(claim for item in self.forbidden_claims if (claim := _clean(item))),
        )

    @property
    def is_draft_only(self) -> bool:
        return not self.selling_points

    def product_context(self) -> str:
        lines = [f"商品品类：{self.category}"]
        if self.product_name:
            lines.append(f"商品名称：{self.product_name}")
        if self.selling_points:
            lines.append("已确认卖点：" + "；".join(self.selling_points))
        else:
            lines.append("未提供已确认卖点：仅生成品类创意草案，不得补充具体商品事实")
        if self.forbidden_claims:
            lines.append("禁止使用：" + "；".join(self.forbidden_claims))
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class PromptPackage:
    schema_version: str
    template_version: str
    brief: ProductBrief
    copywriting_prompt: str
    avatar_prompt_template: str
    review_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: IssueCode
    message: str
    value: str = ""


@dataclass(frozen=True, slots=True)
class CopyValidationReport:
    character_count: int
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "is_valid": self.is_valid}


@dataclass(frozen=True, slots=True)
class GeneratedScript:
    text: str
    report: CopyValidationReport


@dataclass(frozen=True, slots=True)
class AvatarVideoPrompt:
    text: str
    source_script: str
