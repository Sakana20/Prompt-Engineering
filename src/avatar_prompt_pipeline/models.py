from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class BriefValidationError(ValueError):
    """Raised when a product brief cannot safely drive prompt generation."""


class IssueCode(StrEnum):
    TOO_SHORT = "TOO_SHORT"
    TOO_LONG = "TOO_LONG"
    MISSING_PLATFORM = "MISSING_PLATFORM"
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
    no_split_phrases: tuple[str, ...] = ()
    forbidden_expressions: tuple[str, ...] = ()
    required_disclosures: tuple[str, ...] = ()
    confirmed_claims: tuple[str, ...] = ()

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
            "no_split_phrases",
            tuple(value for item in self.no_split_phrases if (value := _clean(item))),
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
        object.__setattr__(
            self,
            "confirmed_claims",
            tuple(value for item in self.confirmed_claims if (value := _clean(item))),
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
        if self.no_split_phrases:
            rendered_phrases = [
                f"[[NO_SPLIT]]{phrase}[[/NO_SPLIT]]" for phrase in self.no_split_phrases
            ]
            lines.append("组合保护片段：" + "；".join(rendered_phrases))
        if self.forbidden_expressions:
            lines.append("活动禁用表达：" + "；".join(self.forbidden_expressions))
        if self.required_disclosures:
            lines.append("必须披露：" + "；".join(self.required_disclosures))
        if self.confirmed_claims:
            lines.append("已确认可用信息：" + "；".join(self.confirmed_claims))
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    min_characters: int = 80
    max_characters: int = 100
    banned_expressions: tuple[str, ...] = (
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
    call_to_actions: tuple[str, ...] = (
        "点击视频下方链接",
        "点击左下角链接",
        "点链接",
        "立即购买",
        "赶紧下单",
        "链接就在下方",
        "官方链接就在左下角",
        "下单",
        "点击购买",
        "赶紧冲",
        "快叫上",
        "直播间",
    )
    format_prefixes: tuple[str, ...] = ("#", "-", "*", "1.", "1、", "①")

    def __post_init__(self) -> None:
        if self.min_characters < 1:
            raise BriefValidationError("min_characters 必须大于等于 1")
        if self.max_characters < self.min_characters:
            raise BriefValidationError("max_characters 必须大于等于 min_characters")
        object.__setattr__(
            self,
            "banned_expressions",
            tuple(value for item in self.banned_expressions if (value := _clean(item))),
        )
        object.__setattr__(
            self,
            "call_to_actions",
            tuple(value for item in self.call_to_actions if (value := _clean(item))),
        )
        object.__setattr__(
            self,
            "format_prefixes",
            tuple(value for item in self.format_prefixes if (value := _clean(item))),
        )


@dataclass(frozen=True, slots=True)
class LanguageStyle:
    name: str = "product-led-conversational"
    tone: str = "普通人分享购买理由和使用体验，保留生活感，但商品必须是表达重点"
    point_of_view: str = "像同事或朋友随口分享"
    sentence_style: str = "句子短一些、信息清楚、自然停顿，不使用商品详情页语气"
    emphasis: tuple[str, ...] = (
        "商品名称、购买理由和使用方式应清楚可听，不能被生活细节淹没",
        "抽象评价后面要有具体依据",
        "每句话承担不同信息，不解释显而易见的功能，不为凑字数重复表达",
    )
    avoid_phrases: tuple[str, ...] = (
        "临时想买又怕麻烦",
        "不知道怎么选",
        "拿起来就能用",
        "放着也方便",
        "红包直接抵扣",
        "补一个挺省心",
        "日常使用很合适",
        "以前……后来……",
        "之前……直到……",
        "自从用了……",
        "真后悔没早点……",
    )
    extra_rules: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean(self.name) or "product-led-conversational")
        object.__setattr__(self, "tone", _clean(self.tone))
        object.__setattr__(self, "point_of_view", _clean(self.point_of_view))
        object.__setattr__(self, "sentence_style", _clean(self.sentence_style))
        object.__setattr__(
            self,
            "emphasis",
            tuple(value for item in self.emphasis if (value := _clean(item))),
        )
        object.__setattr__(
            self,
            "avoid_phrases",
            tuple(value for item in self.avoid_phrases if (value := _clean(item))),
        )
        object.__setattr__(
            self,
            "extra_rules",
            tuple(value for item in self.extra_rules if (value := _clean(item))),
        )

    def style_context(self) -> str:
        lines = [f"风格名称：{self.name}"]
        if self.tone:
            lines.append(f"整体语气：{self.tone}")
        if self.point_of_view:
            lines.append(f"叙述视角：{self.point_of_view}")
        if self.sentence_style:
            lines.append(f"句式节奏：{self.sentence_style}")
        if self.emphasis:
            lines.append("表达重点：" + "；".join(self.emphasis))
        if self.avoid_phrases:
            lines.append("避免套话：" + "；".join(self.avoid_phrases))
        if self.extra_rules:
            lines.append("额外规则：" + "；".join(self.extra_rules))
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class PromptPackage:
    schema_version: str
    template_version: str
    brief: ProductBrief
    campaign: CampaignSpec
    validation_config: ValidationConfig
    language_style: LanguageStyle
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
class LibtvOmniHumanTask:
    task_id: str
    image_prompt: str
    marked_script: str
    title: str
    notes: str
    voice_label: str = "温暖闺蜜"
    voice_id: str = "Chinese (Mandarin)_Warm_Bestie"
    aspect_ratio: str = "9:16"


@dataclass(frozen=True, slots=True)
class VisualProfile:
    identity_key: str
    outfit_key: str
