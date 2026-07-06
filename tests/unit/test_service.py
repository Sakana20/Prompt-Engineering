import pytest

from avatar_prompt_pipeline.models import (
    BenefitPoint,
    CampaignSpec,
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

    package = compose_prompt_package(brief)

    assert "{{PRODUCT_CONTEXT}}" not in package.copywriting_prompt
    assert "商品名称：浅卡其色中筒雨靴" in package.copywriting_prompt
    assert "已确认卖点：中筒款式" in package.copywriting_prompt
    assert "禁止使用：绝对防滑" in package.copywriting_prompt
    assert "不要套用" not in package.copywriting_prompt
    assert "约占全文 20%" in package.copywriting_prompt
    assert "商品相关内容约占全文 50%" in package.copywriting_prompt
    assert "利益点与购买体验约占全文 30%" in package.copywriting_prompt
    assert "不要写成完整生活故事" in package.copywriting_prompt
    assert "不要单独写成播报口号" in package.copywriting_prompt
    assert "利益点[primary-benefit]" in package.copywriting_prompt
    assert "【语言风格】" in package.copywriting_prompt
    assert "风格名称：product-led-conversational" in package.copywriting_prompt
    assert "禁止出现以下行动引导" in package.copywriting_prompt
    assert package.language_style.name == "product-led-conversational"
    assert package.template_version == "2026-07-03-generic-campaign-v1"
    assert "{{SCRIPT}}" in package.avatar_prompt_template
    assert package.review_required is True


def test_compose_prompt_package_injects_configured_language_style() -> None:
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

    assert "风格名称：benefit-forward-natural" in package.copywriting_prompt
    assert "整体语气：自然直接地说明这次购买合适" in package.copywriting_prompt
    assert "表达重点：先讲清活动利益点" in package.copywriting_prompt
    assert "避免套话：错过就亏" in package.copywriting_prompt
    assert "额外规则：不要夸张促销氛围" in package.copywriting_prompt
    assert package.language_style.name == "benefit-forward-natural"


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
    assert "禁止出现以下行动引导：直播间、点击视频下方链接" in package.copywriting_prompt


def test_render_avatar_prompt_injects_script() -> None:
    rendered = render_avatar_prompt(
        "下班回家，[[NO_SPLIT]]最高12元无门槛红包[[/NO_SPLIT]]，门口的雨靴还沾着一点雨水。"
    )

    assert "{{SCRIPT}}" not in rendered
    assert "下班回家，最高12元无门槛红包，门口的雨靴还沾着一点雨水。" in rendered
    assert "[[NO_SPLIT]]" not in rendered
    assert "竖屏 9:16" in rendered


def test_render_avatar_prompt_rejects_empty_script() -> None:
    with pytest.raises(ValueError, match="口播文案不能为空"):
        render_avatar_prompt("\x00  ")
