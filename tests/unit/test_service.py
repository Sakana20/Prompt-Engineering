from datetime import date

import pytest

from avatar_prompt_pipeline.models import (
    BenefitPoint,
    CampaignSpec,
    CreativeBrief,
    LanguageStyle,
    ProductBrief,
    ValidationConfig,
)
from avatar_prompt_pipeline.service import compose_prompt_package, render_avatar_prompt


def test_compose_prompt_package_injects_only_confirmed_product_context() -> None:
    brief = ProductBrief(
        category="雨靴",
        product_name="浅卡其色中筒雨靴",
        selling_points=("中筒款式",),
        forbidden_claims=("绝对防滑",),
    )

    package = compose_prompt_package(brief, reference_date=date(2026, 8, 5))

    assert "{{PRODUCT_CONTEXT}}" not in package.copywriting_prompt
    assert "商品名称：浅卡其色中筒雨靴" in package.copywriting_prompt
    assert "已确认卖点：中筒款式" in package.copywriting_prompt
    assert "禁止使用：绝对防滑" in package.copywriting_prompt
    assert "不要套用" not in package.copywriting_prompt
    assert "约占全文 20%" not in package.copywriting_prompt
    assert "商品相关内容约占全文 50%" not in package.copywriting_prompt
    assert "利益点与购买体验约占全文 30%" not in package.copywriting_prompt
    assert "【本次筛选的真人原文块】" not in package.copywriting_prompt
    assert package.selected_copy_block_ids == ()
    assert package.copy_learning_context_character_count == 0
    assert "本条模式：natural_generate" in package.copywriting_prompt
    assert "source_slot_values" not in package.copywriting_prompt
    assert "rewrite_anchor_phrases" not in package.copywriting_prompt
    assert "利益点[primary-benefit]" in package.copywriting_prompt
    assert "【受众与传播目标】" in package.copywriting_prompt
    assert "当前本地日期：2026-08-05" in package.copywriting_prompt
    assert "当前月份：8月" in package.copywriting_prompt
    assert "按月份划分的当前季节：夏季" in package.copywriting_prompt
    assert "受众：日常消费用户" in package.copywriting_prompt
    assert "禁止出现以下行动引导" in package.copywriting_prompt
    assert package.language_style.name == "product-led-conversational"
    assert package.copy_mode == "natural_generate"
    assert package.template_version == "2026-08-13-gpt-5-6-lean-copy-prompt-v25"
    assert "{{SCRIPT}}" in package.avatar_prompt_template
    assert package.review_required is True


def test_compose_prompt_package_converts_legacy_language_style_to_creative_brief() -> None:
    package = compose_prompt_package(
        ProductBrief(category="西瓜"),
        language_style=LanguageStyle(
            name="benefit-forward-natural",
            tone="自然直接地说明这次购买合适",
            point_of_view="像自己刚用到活动后分享",
            sentence_style="少铺垫，快速进入购买理由",
            emphasis=("先讲清活动利益点",),
            avoid_phrases=("错过就亏",),
            extra_rules=("不要夸张促销氛围",),
        ),
    )

    assert "表达声音：自然直接地说明这次购买合适" in package.copywriting_prompt
    assert "传播目标：先讲清活动利益点" in package.copywriting_prompt
    assert "创意偏好：先讲清活动利益点；不要夸张促销氛围" in package.copywriting_prompt
    assert "避免套话：错过就亏" not in package.copywriting_prompt
    assert package.language_style.name == "benefit-forward-natural"


def test_compose_prompt_package_uses_explicit_creative_brief() -> None:
    package = compose_prompt_package(
        ProductBrief(category="西瓜"),
        creative_brief=CreativeBrief(
            audience="夏季水果用户",
            communication_goal="让饭后分享需求自然成立",
            voice="轻松直接",
            preferences=("从具体动作进入",),
        ),
    )

    assert "受众：夏季水果用户" in package.copywriting_prompt
    assert "传播目标：让饭后分享需求自然成立" in package.copywriting_prompt
    assert "创意偏好：从具体动作进入" in package.copywriting_prompt


def test_compose_prompt_package_injects_only_selected_source_mode_block() -> None:
    package = compose_prompt_package(
        ProductBrief(category="炸鸡", product_name="脆皮炸鸡"),
        copy_mode="human_rewrite",
        source_block_id="learn-008-evening",
        reference_date=date(2026, 8, 5),
    )

    assert package.selected_copy_block_ids == ("learn-008-evening",)
    assert "本条模式：human_rewrite" in package.copywriting_prompt
    assert "### `learn-008-evening`" in package.copywriting_prompt
    assert "本来晚上不想吃的" in package.copywriting_prompt
    assert "source_fill" not in package.copywriting_prompt


def test_compose_source_fill_rejects_incompatible_source_block() -> None:
    with pytest.raises(ValueError, match="learn-005-not-hungry 不适用于 source_fill：品类不兼容"):
        compose_prompt_package(
            ProductBrief(category="咖啡"),
            copy_mode="source_fill",
            source_block_id="learn-005-not-hungry",
        )


def test_compose_prompt_package_renders_validation_call_to_actions() -> None:
    package = compose_prompt_package(
        ProductBrief(category="咖啡"),
        CampaignSpec(
            benefit_points=(BenefitPoint(id="primary-benefit", text="最高25元无门槛红包"),),
            confirmed_claims=("可提及配送到家",),
        ),
        validation_config=ValidationConfig(call_to_actions=("直播间", "点击视频下方链接")),
    )

    assert "已确认可用信息：可提及配送到家" in package.copywriting_prompt
    assert "平台：未指定" in package.copywriting_prompt
    assert "禁止出现以下行动引导：直播间、点击视频下方链接" in package.copywriting_prompt


def test_compose_prompt_package_renders_numeric_redpacket_compliance_rule() -> None:
    package = compose_prompt_package(
        ProductBrief(category="西瓜"),
        validation_config=ValidationConfig(forbid_numeric_redpacket_amounts=True),
    )

    assert "禁止出现任何阿拉伯数字或中文数字的红包金额" in package.copywriting_prompt


def test_render_avatar_prompt_injects_script() -> None:
    rendered = render_avatar_prompt(
        "下班回家，[[NO_SPLIT]]最高12元无门槛红包[[/NO_SPLIT]]，门口的雨靴还沾着一点雨水。"
    )

    assert "{{SCRIPT}}" not in rendered
    assert "下班回家，最高12元无门槛红包，门口的雨靴还沾着一点雨水。" in rendered
    assert "[[NO_SPLIT]]" not in rendered
    assert "22-24 岁中国女生" in rendered
    assert "甜美、可爱、清冷、御姐、邻家、清爽" in rendered
    assert "禁止大妈、阿姨、中年女性、中老年或老气方向" in rendered
    assert "亚洲女生、亚洲女性、大妈、阿姨" in rendered
    assert "开头必须先写“竖屏9:16，固定中景，手机实拍，数字人口播首帧”" in rendered
    assert "目标长度 120-180 个中文字符" in rendered
    assert "主流日常审美" in rendered
    assert "通勤、休闲、甜酷、简约或轻运动风" in rendered
    assert "场景只作为背景" in rendered
    assert "人物面前桌上放商品" in rendered
    assert "商品不由人物手持" in rendered
    assert "人物不看商品" in rendered
    assert "不接触商品" in rendered
    assert "非商品区域无logo" in rendered
    assert "无字幕" in rendered
    assert "竖屏9:16" in rendered


def test_render_avatar_prompt_rejects_empty_script() -> None:
    with pytest.raises(ValueError, match="口播文案不能为空"):
        render_avatar_prompt("\x00  ")
