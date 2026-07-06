from __future__ import annotations

from .models import BenefitPoint, CampaignSpec

TAOBAO_DEFAULT_BENEFIT = "淘宝闪购最高12元无门槛红包"

TAOBAO_DEFAULT_CAMPAIGN = CampaignSpec(
    platform="淘宝闪购",
    campaign_name="默认红包活动",
    benefit_points=(
        BenefitPoint(
            id="primary-benefit",
            text=TAOBAO_DEFAULT_BENEFIT,
        ),
    ),
)


def campaign_from_benefits(
    benefit_texts: tuple[str, ...],
    *,
    platform: str = "",
    campaign_name: str = "",
) -> CampaignSpec:
    return CampaignSpec(
        platform=platform,
        campaign_name=campaign_name,
        benefit_points=tuple(
            BenefitPoint(id=f"benefit-{index}", text=text, priority=index)
            for index, text in enumerate(benefit_texts, start=1)
        ),
    )
