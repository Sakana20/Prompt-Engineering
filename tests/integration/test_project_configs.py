from pathlib import Path

import pytest

from avatar_prompt_pipeline.config import load_project_config
from avatar_prompt_pipeline.presets import TAOBAO_DEFAULT_CAMPAIGN, TAOBAO_DEFAULT_CONFIG_PATH
from avatar_prompt_pipeline.validation import validate_copy

PROJECT_CONFIG_ROOT = Path(__file__).parents[2] / "configs" / "projects"


@pytest.mark.integration
def test_repository_project_configs_are_loadable() -> None:
    configs = sorted(PROJECT_CONFIG_ROOT.glob("*.json"))

    assert {path.name for path in configs} == {
        "taobao-12-no-threshold-redpacket.json",
        "taobao-25-no-threshold-redpacket.json",
        "taobao-instant-commerce-compliance.json",
    }
    for path in configs:
        config = load_project_config(path)
        assert config.project_id
        assert config.brief.category
        assert config.campaign.platform == "淘宝闪购"
        assert config.campaign.benefit_points[0].id == "primary-benefit"
        assert config.creative_brief.audience
        assert config.creative_brief.communication_goal
        assert config.creative_brief.voice
        assert len(config.creative_brief.preferences) <= 3


@pytest.mark.integration
def test_taobao_redpacket_project_configs_forbid_each_other() -> None:
    twelve = load_project_config(PROJECT_CONFIG_ROOT / "taobao-12-no-threshold-redpacket.json")
    twenty_five = load_project_config(PROJECT_CONFIG_ROOT / "taobao-25-no-threshold-redpacket.json")

    assert twelve.campaign.benefit_points[0].text == "最高12元无门槛红包"
    assert twelve.campaign.benefit_points[0].required is True
    assert twelve.campaign.benefit_points[0].exact_match is True
    assert twelve.campaign.benefit_points[0].no_split is False
    assert twelve.campaign.no_split_phrases == ("淘宝闪购有最高12元无门槛红包",)
    assert twelve.campaign.forbidden_expressions == ("最高25元无门槛红包",)
    assert twelve.creative_brief.audience == "日常即时零售用户"
    assert "真实购买需求" in twelve.creative_brief.communication_goal
    assert "红包只是促成购买的补充理由" in twelve.creative_brief.preferences
    assert twenty_five.campaign.benefit_points[0].text == "最高25元无门槛红包"
    assert twenty_five.brief.category == "咖啡奶茶炸鸡等淘宝闪购商品"
    assert [benefit.text for benefit in twenty_five.campaign.benefit_points] == [
        "最高25元无门槛红包",
        "0.1元起",
        "还可以叠加九折津贴卡",
    ]
    assert twenty_five.campaign.no_split_phrases == ("最高25元无门槛红包，还可以叠加九折津贴卡",)
    assert twenty_five.campaign.forbidden_expressions == ("最高12元无门槛红包",)
    assert twenty_five.campaign.required_disclosures == ()
    assert "必须披露" not in twenty_five.campaign.campaign_context()
    assert "价格、津贴和商品范围以实际活动页面为准" not in twenty_five.campaign.campaign_context()
    assert "可提及配送到家或外卖到家" in twenty_five.campaign.confirmed_claims
    assert twenty_five.validation_config.call_to_actions == ()
    assert "即时外卖用户" in twenty_five.creative_brief.audience
    assert "结尾自然给出行动引导" in twenty_five.creative_brief.preferences


@pytest.mark.integration
def test_taobao_25_project_allows_natural_call_to_action() -> None:
    config = load_project_config(PROJECT_CONFIG_ROOT / "taobao-25-no-threshold-redpacket.json")
    copy = (
        "0.1元起一杯瑞幸咖啡，早八人看到真的很难不心动。现在上淘宝闪购有"
        "[[NO_SPLIT]]最高25元无门槛红包，还可以叠加九折津贴卡[[/NO_SPLIT]]，"
        "附近门店能配送到家，官方链接就在左下角，赶紧冲吧。"
    )

    assert validate_copy(copy, config.campaign, config.validation_config).is_valid is True


@pytest.mark.integration
def test_taobao_default_preset_is_loaded_from_12_yuan_project_config() -> None:
    config = load_project_config(PROJECT_CONFIG_ROOT / "taobao-12-no-threshold-redpacket.json")

    assert (
        TAOBAO_DEFAULT_CONFIG_PATH == PROJECT_CONFIG_ROOT / "taobao-12-no-threshold-redpacket.json"
    )
    assert config.campaign == TAOBAO_DEFAULT_CAMPAIGN


@pytest.mark.integration
def test_taobao_compliance_project_uses_fuzzy_benefit_and_rejects_amounts() -> None:
    config = load_project_config(PROJECT_CONFIG_ROOT / "taobao-instant-commerce-compliance.json")
    compliant_copy = (
        "早八人想喝咖啡的看过来，淘宝闪购现在有大额红包，"
        "看到附近瑞幸还有活动价，我直接选了杯拿铁。"
        "外卖送到公司不用绕路，上班前就能喝到，"
        "想给自己补一杯的，官方链接就在左下角。"
    )

    compliant_report = validate_copy(compliant_copy, config.campaign, config.validation_config)
    numeric_report = validate_copy(
        compliant_copy.replace("大额红包", "二十五元大额红包"),
        config.campaign,
        config.validation_config,
    )

    assert config.campaign.benefit_points[0].text == "大额红包"
    assert config.brief.category == "咖啡奶茶炸鸡等淘宝闪购美食外卖商品"
    assert [benefit.text for benefit in config.campaign.benefit_points] == [
        "大额红包",
        "优惠价",
        "活动价",
    ]
    assert "可提及配送到家或外卖到家" in config.campaign.confirmed_claims
    assert config.campaign.no_split_phrases == ()
    assert config.validation_config.call_to_actions == ()
    assert config.validation_config.forbid_numeric_redpacket_amounts is True
    assert "只使用已确认的美食外卖场景" in config.creative_brief.preferences
    assert compliant_report.is_valid is True
    assert any(issue.code.value == "NUMERIC_REDPACKET_AMOUNT" for issue in numeric_report.issues)
