from __future__ import annotations

from dataclasses import asdict, dataclass

from .validation import LearningValidationError


@dataclass(frozen=True, slots=True)
class LearningFieldOption:
    value: str
    label: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


CATEGORY_FAMILY_OPTIONS = (
    LearningFieldOption("", "请选择品类族", "提交审核前必须选择"),
    LearningFieldOption("beverage", "饮品", "咖啡、奶茶、果汁等以饮用为主要动作的商品"),
    LearningFieldOption("other", "非饮品", "食品、正餐及其他不以饮用为主要动作的商品"),
)
CONSUMPTION_NEED_OPTIONS = (
    LearningFieldOption("", "请选择消费需求", "选择文案主要服务的消费场景"),
    LearningFieldOption("meal", "正餐", "饱腹或一餐需求"),
    LearningFieldOption("craving", "解馋", "嘴馋、想吃或想喝"),
    LearningFieldOption("afternoon_tea", "下午茶", "午后饮食场景"),
    LearningFieldOption("commute", "通勤", "上下班或路途中使用"),
    LearningFieldOption("sharing", "分享", "与家人朋友共同使用"),
    LearningFieldOption("binge_watching", "追剧", "观影或追剧陪伴"),
    LearningFieldOption("daily_use", "日常使用", "非食品类日常需求"),
    LearningFieldOption("urgent_need", "临时急需", "即时补货或应急需求"),
    LearningFieldOption("gifting", "送礼", "赠送他人的需求"),
    LearningFieldOption("other", "其他", "以上场景均不适用"),
)
SEASON_OPTIONS = (
    LearningFieldOption("all", "全季通用", "没有明确季节限制"),
    LearningFieldOption("spring", "春季", "只适合春季语境"),
    LearningFieldOption("summer", "夏季", "只适合夏季语境"),
    LearningFieldOption("autumn", "秋季", "只适合秋季语境"),
    LearningFieldOption("winter", "冬季", "只适合冬季语境"),
)
SOURCE_USAGE_OPTIONS = (
    LearningFieldOption("source_fill", "直接填槽", "原句结构可保留，只替换强类型商品插槽"),
    LearningFieldOption("human_rewrite", "AI 改写参考", "只学习语言节奏和表达逻辑"),
)

_SINGLE_VALUE_OPTIONS = {
    "category_family": CATEGORY_FAMILY_OPTIONS,
    "consumption_need": CONSUMPTION_NEED_OPTIONS,
    "season": SEASON_OPTIONS,
}
_SOURCE_USAGE_VALUES = frozenset(option.value for option in SOURCE_USAGE_OPTIONS)


def copy_learning_field_options() -> dict[str, list[dict[str, str]]]:
    return {
        **{
            field: [option.to_dict() for option in options]
            for field, options in _SINGLE_VALUE_OPTIONS.items()
        },
        "source_usage": [option.to_dict() for option in SOURCE_USAGE_OPTIONS],
    }


def validate_copy_learning_fields(
    *,
    category_family: str,
    consumption_need: str,
    season: str,
    source_usage: tuple[str, ...],
) -> None:
    values = {
        "category_family": category_family,
        "consumption_need": consumption_need,
        "season": season,
    }
    labels = {
        "category_family": "品类族",
        "consumption_need": "消费需求",
        "season": "季节限制",
    }
    for field, value in values.items():
        allowed = {option.value for option in _SINGLE_VALUE_OPTIONS[field]}
        if value not in allowed:
            raise LearningValidationError(f"{labels[field]}必须从审核台选项中选择")
    if not set(source_usage) <= _SOURCE_USAGE_VALUES:
        raise LearningValidationError("来源块用途只能选择直接填槽或 AI 改写参考")


__all__ = [
    "CATEGORY_FAMILY_OPTIONS",
    "CONSUMPTION_NEED_OPTIONS",
    "SEASON_OPTIONS",
    "SOURCE_USAGE_OPTIONS",
    "LearningFieldOption",
    "copy_learning_field_options",
    "validate_copy_learning_fields",
]
