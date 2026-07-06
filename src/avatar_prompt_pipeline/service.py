from __future__ import annotations

from .models import CampaignSpec, LanguageStyle, ProductBrief, PromptPackage, ValidationConfig
from .presets import TAOBAO_DEFAULT_CAMPAIGN
from .template_loader import TEMPLATE_VERSION, load_template
from .validation import DEFAULT_VALIDATION_CONFIG, strip_no_split_markers


def _call_to_action_rules(validation_config: ValidationConfig) -> str:
    if validation_config.call_to_actions:
        return "禁止出现以下行动引导：" + "、".join(validation_config.call_to_actions) + "。"
    return "当前校验配置未设置行动引导禁用词；仍不得虚构未确认事实或触发未授权付费流程。"


def compose_prompt_package(
    brief: ProductBrief,
    campaign: CampaignSpec = TAOBAO_DEFAULT_CAMPAIGN,
    validation_config: ValidationConfig = DEFAULT_VALIDATION_CONFIG,
    language_style: LanguageStyle | None = None,
) -> PromptPackage:
    resolved_language_style = language_style or LanguageStyle()
    copywriting_template = load_template("copywriting_prompt.txt")
    avatar_template = load_template("avatar_prompt.txt")
    copywriting_prompt = copywriting_template.replace(
        "{{PRODUCT_CONTEXT}}", brief.product_context()
    ).replace("{{CAMPAIGN_CONTEXT}}", campaign.campaign_context())
    copywriting_prompt = copywriting_prompt.replace(
        "{{LANGUAGE_STYLE_CONTEXT}}", resolved_language_style.style_context()
    )
    copywriting_prompt = copywriting_prompt.replace(
        "{{CALL_TO_ACTION_RULES}}", _call_to_action_rules(validation_config)
    )
    return PromptPackage(
        schema_version="1.0",
        template_version=TEMPLATE_VERSION,
        brief=brief,
        campaign=campaign,
        validation_config=validation_config,
        language_style=resolved_language_style,
        copywriting_prompt=copywriting_prompt,
        avatar_prompt_template=avatar_template,
        review_required=True,
    )


def render_avatar_prompt(script: str) -> str:
    cleaned_script = strip_no_split_markers(script.replace("\x00", "")).strip()
    if not cleaned_script:
        raise ValueError("口播文案不能为空")
    return load_template("avatar_prompt.txt").replace("{{SCRIPT}}", cleaned_script)
