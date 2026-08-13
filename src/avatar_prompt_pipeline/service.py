from __future__ import annotations

from datetime import date

from .learning.publication import COPY_RESOURCE_NAME, reference_path
from .models import (
    CampaignSpec,
    CreativeBrief,
    LanguageStyle,
    ProductBrief,
    PromptPackage,
    ValidationConfig,
)
from .presets import TAOBAO_DEFAULT_CAMPAIGN
from .source_blocks import (
    CopySourceBlock,
    render_person_block_context,
    select_copy_block,
    select_person_blocks,
)
from .template_loader import TEMPLATE_VERSION, load_template
from .validation import DEFAULT_VALIDATION_CONFIG, strip_no_split_markers, temporal_context


def _call_to_action_rules(validation_config: ValidationConfig) -> str:
    rules: list[str] = []
    if validation_config.call_to_actions:
        rules.append("禁止出现以下行动引导：" + "、".join(validation_config.call_to_actions) + "。")
    else:
        rules.append("当前校验配置没有额外行动引导禁词。")
    if validation_config.forbid_numeric_redpacket_amounts:
        rules.append("禁止出现任何阿拉伯数字或中文数字的红包金额；只能使用已确认的模糊福利表达。")
    return "\n".join(rules)


def _source_mode_context(copy_mode: str, source_context: str) -> str:
    if copy_mode == "natural_generate":
        return (
            "本条模式：natural_generate。\n"
            "不使用真人学习块，自行选择最贴合商品的生活切口；不要填写或推断来源字段。"
        )
    if copy_mode == "source_fill":
        return (
            "本条模式：source_fill。\n"
            "只替换下方原文块的方括号，保留其余原词、顺序、重复与口语停顿，不润色、不扩句。"
            "插槽只能使用已确认商品事实；活动信息在完整商品段之后另行自然衔接。\n" + source_context
        )
    if copy_mode == "human_rewrite":
        return (
            "本条模式：human_rewrite。\n"
            "以下原文块只提供口语节奏和自然字眼。至少保留两个非季节性原字眼或短语，"
            "把商品、需求和场景重写为当前任务；不得恢复样本中的活动、价格、配送或品牌事实。\n"
            + source_context
        )
    raise ValueError("copy_mode 只能是 source_fill、human_rewrite 或 natural_generate")


def compose_prompt_package(
    brief: ProductBrief,
    campaign: CampaignSpec = TAOBAO_DEFAULT_CAMPAIGN,
    validation_config: ValidationConfig = DEFAULT_VALIDATION_CONFIG,
    language_style: LanguageStyle | None = None,
    creative_brief: CreativeBrief | None = None,
    *,
    reference_date: date | None = None,
    batch_size: int = 1,
    copy_mode: str = "natural_generate",
    source_block_id: str = "",
) -> PromptPackage:
    resolved_language_style = language_style or LanguageStyle()
    resolved_creative_brief = creative_brief or (
        resolved_language_style.to_creative_brief()
        if language_style is not None
        else CreativeBrief()
    )
    copywriting_template = load_template("copywriting_prompt.txt")
    avatar_template = load_template("avatar_prompt.txt")
    copywriting_prompt = copywriting_template.replace(
        "{{PRODUCT_CONTEXT}}", brief.product_context()
    ).replace("{{CAMPAIGN_CONTEXT}}", campaign.campaign_context())
    copywriting_prompt = copywriting_prompt.replace(
        "{{CREATIVE_BRIEF_CONTEXT}}", resolved_creative_brief.context()
    )
    copywriting_prompt = copywriting_prompt.replace(
        "{{CALL_TO_ACTION_RULES}}", _call_to_action_rules(validation_config)
    )
    copywriting_prompt = copywriting_prompt.replace(
        "{{TEMPORAL_CONTEXT}}", temporal_context(reference_date)
    )
    copywriting_prompt = copywriting_prompt.replace(
        "{{LENGTH_RULE}}",
        (
            f"正文长度为 {validation_config.min_characters}-"
            f"{validation_config.max_characters} 个中文字符。"
        ),
    )
    batch_diversity_rule = (
        "- 同批内容在人设、切口、节奏或情绪上有实际差异。" if batch_size > 1 else ""
    )
    copywriting_prompt = copywriting_prompt.replace(
        "{{BATCH_DIVERSITY_RULE}}", batch_diversity_rule
    )
    banned_rule = (
        "除活动资料要求逐字保留的片段外，不得使用："
        + "、".join(validation_config.banned_expressions)
        + "。"
        if validation_config.banned_expressions
        else "当前校验配置没有额外禁词。"
    )
    copywriting_prompt = copywriting_prompt.replace("{{BANNED_EXPRESSION_RULE}}", banned_rule)
    current_temporal_context = temporal_context(reference_date)
    selection_context = "|".join(
        (
            brief.category,
            brief.product_name,
            "；".join(brief.selling_points),
            resolved_creative_brief.context(),
            current_temporal_context,
        )
    )
    selected_copy_blocks: tuple[CopySourceBlock, ...] = ()
    source_context = ""
    if copy_mode != "natural_generate":
        selected_block = select_copy_block(
            brief.category,
            selection_context,
            reference_path(COPY_RESOURCE_NAME),
            block_id=source_block_id,
            require_source_fill_compatible=copy_mode == "source_fill",
        )
        selected_copy_blocks = (selected_block,)
        source_context = f"### `{selected_block.block_id}`\n```text\n{selected_block.template}\n```"
    elif source_block_id:
        raise ValueError("natural_generate 不得指定 source_block_id")
    copywriting_prompt = copywriting_prompt.replace(
        "{{SOURCE_MODE_CONTEXT}}", _source_mode_context(copy_mode, source_context)
    )
    person_blocks = select_person_blocks(
        "|".join((brief.category, brief.product_name, current_temporal_context)),
        reference_path("person-prompt-source-blocks.md"),
    )
    person_context = render_person_block_context(person_blocks)
    avatar_template += person_context
    return PromptPackage(
        schema_version="1.1",
        template_version=TEMPLATE_VERSION,
        brief=brief,
        campaign=campaign,
        validation_config=validation_config,
        creative_brief=resolved_creative_brief,
        language_style=resolved_language_style,
        copy_mode=copy_mode,
        copywriting_prompt=copywriting_prompt,
        avatar_prompt_template=avatar_template,
        review_required=True,
        selected_copy_block_ids=tuple(block.block_id for block in selected_copy_blocks),
        copy_learning_context_character_count=len(source_context),
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
