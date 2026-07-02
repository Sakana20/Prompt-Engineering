import pytest

from avatar_prompt_pipeline.models import BriefValidationError, ProductBrief


def test_product_brief_cleans_input_and_reports_production_readiness() -> None:
    brief = ProductBrief(
        category="  雨靴\n",
        product_name=" 浅卡其色  中筒雨靴 ",
        selling_points=(" 浅卡其配色 ", "", "中筒款式"),
    )

    assert brief.category == "雨靴"
    assert brief.product_name == "浅卡其色 中筒雨靴"
    assert brief.selling_points == ("浅卡其配色", "中筒款式")
    assert brief.is_draft_only is False


def test_product_brief_without_selling_points_is_draft_only() -> None:
    brief = ProductBrief(category="雨靴")

    assert brief.is_draft_only is True
    assert "不得补充具体商品事实" in brief.product_context()


def test_product_brief_rejects_empty_category() -> None:
    with pytest.raises(BriefValidationError, match="商品品类不能为空"):
        ProductBrief(category=" \x00 ")
