from __future__ import annotations

from pathlib import Path

from .config import load_project_config
from .models import BenefitPoint, CampaignSpec

TAOBAO_DEFAULT_CONFIG_PATH = (
    Path(__file__).parents[2] / "configs" / "projects" / "taobao-12-no-threshold-redpacket.json"
)
TAOBAO_DEFAULT_CONFIG = load_project_config(TAOBAO_DEFAULT_CONFIG_PATH)

TAOBAO_DEFAULT_CAMPAIGN = TAOBAO_DEFAULT_CONFIG.campaign
TAOBAO_DEFAULT_BENEFIT = TAOBAO_DEFAULT_CAMPAIGN.benefit_points[0].text


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
