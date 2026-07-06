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
    MISSING_NO_SPLIT_MARKER = "MISSING_NO_SPLIT_MARKER"
    MALFORMED_NO_SPLIT_MARKER = "MALFORMED_NO_SPLIT_MARKER"
    BANNED_EXPRESSION = "BANNED_EXPRESSION"
    CALL_TO_ACTION = "CALL_TO_ACTION"
    FORMAT_VIOLATION = "FORMAT_VIOLATION"
    DUPLICATE_COPY = "DUPLICATE_COPY"
    HIGH_SIMILARITY = "HIGH_SIMILARITY"
    DUPLICATE_PERSON = "DUPLICATE_PERSON"
    DUPLICATE_OUTFIT = "DUPLICATE_OUTFIT"


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
class BenefitPoint:
    id: str
    text: str
    required: bool = True
    exact_match: bool = True
    no_split: bool = True
    priority: int = 1

    def __post_init__(self) -> None:
        benefit_id = _clean(self.id)
        text = _clean(self.text)
        if not benefit_id or not text:
            raise BriefValidationError("利益点 id 和 text 不能为空")
        if self.priority < 1:
            raise BriefValidationError("利益点 priority 必须大于等于 1")
        object.__setattr__(self, "id", benefit_id)
        object.__setattr__(self, "text", text)


@dataclass(frozen=True, slots=True)
class CampaignSpec:
    platform: str = ""
    campaign_name: str = ""
    benefit_points: tuple[BenefitPoint, ...] = ()
    forbidden_expressions: tuple[str, ...] = ()
    required_disclosures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.benefit_points) > 3:
            raise BriefValidationError("单个任务最多支持 3 条利益点")
        benefit_ids = [benefit.id for benefit in self.benefit_points]
        if len(benefit_ids) != len(set(benefit_ids)):
            raise BriefValidationError("利益点 id 必须唯一")
        object.__setattr__(self, "platform", _clean(self.platform))
        object.__setattr__(self, "campaign_name", _clean(self.campaign_name))
        object.__setattr__(
            self,
            "benefit_points",
            tuple(sorted(self.benefit_points, key=lambda benefit: benefit.priority)),
        )
        object.__setattr__(
            self,
            "forbidden_expressions",
            tuple(value for item in self.forbidden_expressions if (value := _clean(item))),
        )
        object.__setattr__(
            self,
            "required_disclosures",
            tuple(value for item in self.required_disclosures if (value := _clean(item))),
        )

    def campaign_context(self) -> str:
        lines = [f"平台：{self.platform or '未指定'}"]
        if self.campaign_name:
            lines.append(f"活动：{self.campaign_name}")
        if not self.benefit_points:
            lines.append("利益点：无；不得自行创造促销、金额、门槛或优惠")
        for benefit in self.benefit_points:
            rendered = (
                f"[[NO_SPLIT]]{benefit.text}[[/NO_SPLIT]]" if benefit.no_split else benefit.text
            )
            requirements = [
                "必须出现" if benefit.required else "可选",
                "逐字保留" if benefit.exact_match else "允许自然转述",
            ]
            lines.append(f"利益点[{benefit.id}]：{rendered}，要求：{'、'.join(requirements)}")
        if self.forbidden_expressions:
            lines.append("活动禁用表达：" + "；".join(self.forbidden_expressions))
        if self.required_disclosures:
            lines.append("必须披露：" + "；".join(self.required_disclosures))
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class PromptPackage:
    schema_version: str
    template_version: str
    brief: ProductBrief
    campaign: CampaignSpec
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


@dataclass(frozen=True, slots=True)
class OceanengineTask:
    task_id: str
    person_prompt: str
    marked_script: str
    aspect_ratio: str
    voice: str
    title: str
    notes: str


@dataclass(frozen=True, slots=True)
class VisualProfile:
    identity_key: str
    outfit_key: str
