import pytest

from avatar_prompt_pipeline.models import ProductBrief
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
    assert "整段只围绕一个生活片段" in package.copywriting_prompt
    assert "与当前场景直接相关的使用动作" in package.copywriting_prompt
    assert "不要单独写成播报口号" in package.copywriting_prompt
    assert package.template_version == "2026-07-02-natural-v4"
    assert "{{SCRIPT}}" in package.avatar_prompt_template
    assert package.review_required is True


def test_render_avatar_prompt_injects_script() -> None:
    rendered = render_avatar_prompt(
        "下班回家，[[NO_SPLIT]]淘宝闪购最高12元无门槛红包[[/NO_SPLIT]]，门口的雨靴还沾着一点雨水。"
    )

    assert "{{SCRIPT}}" not in rendered
    assert "下班回家，淘宝闪购最高12元无门槛红包，门口的雨靴还沾着一点雨水。" in rendered
    assert "[[NO_SPLIT]]" not in rendered
    assert "竖屏 9:16" in rendered


def test_render_avatar_prompt_rejects_empty_script() -> None:
    with pytest.raises(ValueError, match="口播文案不能为空"):
        render_avatar_prompt("\x00  ")
