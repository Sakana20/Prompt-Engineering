import pytest

from avatar_prompt_pipeline.models import (
    BenefitPoint,
    BriefValidationError,
    CampaignSpec,
    ProductBrief,
)


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


def test_campaign_orders_and_renders_configured_benefits() -> None:
    campaign = CampaignSpec(
        platform=" 淘宝闪购 ",
        benefit_points=(
            BenefitPoint(id="second", text="第二条利益点", priority=2),
            BenefitPoint(id="first", text="第一条利益点", priority=1),
        ),
    )

    assert [benefit.id for benefit in campaign.benefit_points] == ["first", "second"]
    assert "[[NO_SPLIT]]第一条利益点[[/NO_SPLIT]]" in campaign.campaign_context()


def test_campaign_supports_no_benefit_and_rejects_more_than_three() -> None:
    assert "不得自行创造促销" in CampaignSpec().campaign_context()

    with pytest.raises(BriefValidationError, match="最多支持 3 条"):
        CampaignSpec(
            benefit_points=tuple(
                BenefitPoint(id=str(index), text=f"利益点{index}") for index in range(4)
            )
        )
