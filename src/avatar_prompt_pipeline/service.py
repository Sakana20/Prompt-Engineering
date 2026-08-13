from __future__ import annotations

from datetime import date

from .learning.publication import COPY_RESOURCE_NAME, reference_path
from .models import CampaignSpec, LanguageStyle, ProductBrief, PromptPackage, ValidationConfig
from .presets import TAOBAO_DEFAULT_CAMPAIGN
from .source_blocks import (
    render_copy_block_context,
    render_person_block_context,
    select_copy_blocks,
    select_person_blocks,
)
from .template_loader import TEMPLATE_VERSION, load_template
from .validation import DEFAULT_VALIDATION_CONFIG, strip_no_split_markers, temporal_context


def _call_to_action_rules(validation_config: ValidationConfig) -> str:
    rules: list[str] = []
    if validation_config.call_to_actions:
        rules.append("禁止出现以下行动引导：" + "、".join(validation_config.call_to_actions) + "。")
    else:
        rules.append("当前校验配置未设置行动引导禁用词；仍不得虚构未确认事实或触发未授权付费流程。")
    if validation_config.forbid_numeric_redpacket_amounts:
        rules.append("禁止出现任何阿拉伯数字或中文数字的红包金额；只能使用已确认的模糊福利表达。")
    return "\n".join(rules)


def compose_prompt_package(
    brief: ProductBrief,
    campaign: CampaignSpec = TAOBAO_DEFAULT_CAMPAIGN,
    validation_config: ValidationConfig = DEFAULT_VALIDATION_CONFIG,
    language_style: LanguageStyle | None = None,
    *,
    reference_date: date | None = None,
    batch_size: int = 1,
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
    copywriting_prompt = copywriting_prompt.replace(
        "{{TEMPORAL_CONTEXT}}", temporal_context(reference_date)
    )
    current_temporal_context = temporal_context(reference_date)
    copy_blocks = select_copy_blocks(
        brief.category,
        "|".join(
            (
                brief.category,
                brief.product_name,
                "；".join(brief.selling_points),
                resolved_language_style.style_context(),
                current_temporal_context,
            )
        ),
        reference_path(COPY_RESOURCE_NAME),
        batch_size=batch_size,
    )
    copy_context = render_copy_block_context(copy_blocks)
    copywriting_prompt += copy_context
    person_blocks = select_person_blocks(
        "|".join((brief.category, brief.product_name, current_temporal_context)),
        reference_path("person-prompt-source-blocks.md"),
    )
    person_context = render_person_block_context(person_blocks)
    avatar_template += person_context
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
        selected_copy_block_ids=tuple(block.block_id for block in copy_blocks),
        copy_learning_context_character_count=len(copy_context),
        selected_person_block_ids=tuple(block.block_id for block in person_blocks),
        person_learning_context_character_count=len(person_context),
    )


def render_avatar_prompt(script: str) -> str:
    cleaned_script = strip_no_split_markers(script.replace("\x00", "")).strip()
    if not cleaned_script:
        raise ValueError("口播文案不能为空")
    template = load_template("avatar_prompt.txt")
    person_blocks = select_person_blocks(
        cleaned_script + "|" + temporal_context(),
        reference_path("person-prompt-source-blocks.md"),
    )
    template += render_person_block_context(person_blocks)
    return template.replace("{{SCRIPT}}", cleaned_script)
