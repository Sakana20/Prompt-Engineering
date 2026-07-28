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
    }
    for path in configs:
        config = load_project_config(path)
        assert config.project_id
        assert config.brief.category
        assert config.campaign.platform == "淘宝闪购"
        assert config.campaign.benefit_points[0].id == "primary-benefit"
        assert config.language_style.name
        assert config.language_style.tone
        assert any("眼睛必须直视镜头" in rule for rule in config.language_style.extra_rules)


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
    assert twelve.language_style.name == "need-first-infeed-conversational"
    assert "真实生活需求" in twelve.language_style.tone
    assert "红包只是让这次购买更顺手" in twelve.language_style.tone
    assert "先讲自己的处境，再自然提到淘宝闪购" in twelve.language_style.point_of_view
    assert "每条开头都要换一种钩子" in twelve.language_style.sentence_style
    assert any("生活需求占主要原因" in rule for rule in twelve.language_style.emphasis)
    assert any("不同人群、生活事件和表达方式" in rule for rule in twelve.language_style.emphasis)
    assert any("平台必须后置为解决方案" in rule for rule in twelve.language_style.extra_rules)
    assert any("红包成为唯一购买理由" in rule for rule in twelve.language_style.extra_rules)
    assert "我在淘宝闪购看" in twelve.language_style.avoid_phrases
    assert "看到红包就买了" in twelve.language_style.avoid_phrases
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
    assert twenty_five.language_style.name == "benefit-forward-promo"
    assert "行动引导必须出现，并且要自然落在口播结尾" in twenty_five.language_style.emphasis
    assert any("不要写披露语" in rule for rule in twenty_five.language_style.extra_rules)


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
