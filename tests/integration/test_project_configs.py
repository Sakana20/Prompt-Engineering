from pathlib import Path

import pytest

from avatar_prompt_pipeline.config import load_project_config
from avatar_prompt_pipeline.presets import TAOBAO_DEFAULT_CAMPAIGN, TAOBAO_DEFAULT_CONFIG_PATH

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


@pytest.mark.integration
def test_taobao_redpacket_project_configs_forbid_each_other() -> None:
    twelve = load_project_config(PROJECT_CONFIG_ROOT / "taobao-12-no-threshold-redpacket.json")
    twenty_five = load_project_config(PROJECT_CONFIG_ROOT / "taobao-25-no-threshold-redpacket.json")

    assert twelve.campaign.benefit_points[0].text == "最高12元无门槛红包"
    assert twelve.campaign.forbidden_expressions == ("最高25元无门槛红包",)
    assert twelve.language_style.name == "product-led-conversational"
    assert twenty_five.campaign.benefit_points[0].text == "最高25元无门槛红包"
    assert twenty_five.brief.category == "咖啡奶茶炸鸡等淘宝闪购商品"
    assert [benefit.text for benefit in twenty_five.campaign.benefit_points] == [
        "最高25元无门槛红包",
        "0.1元起",
        "还可以叠加九折津贴卡",
    ]
    assert twenty_five.campaign.no_split_phrases == ("最高25元无门槛红包，还可以叠加九折津贴卡",)
    assert twenty_five.campaign.forbidden_expressions == ("最高12元无门槛红包",)
    assert "可提及配送到家或外卖到家" in twenty_five.campaign.confirmed_claims
    assert "赶紧冲" not in twenty_five.validation_config.call_to_actions
    assert "直播间" in twenty_five.validation_config.call_to_actions
    assert twenty_five.language_style.name == "benefit-forward-promo"


@pytest.mark.integration
def test_taobao_default_preset_is_loaded_from_12_yuan_project_config() -> None:
    config = load_project_config(PROJECT_CONFIG_ROOT / "taobao-12-no-threshold-redpacket.json")

    assert (
        TAOBAO_DEFAULT_CONFIG_PATH == PROJECT_CONFIG_ROOT / "taobao-12-no-threshold-redpacket.json"
    )
    assert config.campaign == TAOBAO_DEFAULT_CAMPAIGN
