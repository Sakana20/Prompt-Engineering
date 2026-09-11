from pathlib import Path

import pytest

from avatar_prompt_pipeline.config import load_project_config
from avatar_prompt_pipeline.presets import TAOBAO_DEFAULT_CAMPAIGN, TAOBAO_DEFAULT_CONFIG_PATH
from avatar_prompt_pipeline.validation import validate_copy

PROJECT_CONFIG_ROOT = Path(__file__).parents[2] / "configs" / "projects"
EXPECTED_ENDING_CALL_TO_ACTIONS = (
    "点下方链接看看。",
    "链接在下面，还没吃饭的宝宝们点进去看看。",
    "点开下面的链接看看吧。",
    "点链接进去瞧瞧吧。",
    "下方链接，没想好吃什么的点进去看看。",
    "链接放底下了，饿了的宝宝点开看看。",
    "下面链接，点进去挑挑看。",
    "点开下方链接，进去逛逛吧。",
    "链接在底下，感兴趣的宝宝点进去看看。",
)


@pytest.mark.integration
def test_repository_project_configs_are_loadable() -> None:
    configs = sorted(PROJECT_CONFIG_ROOT.glob("*.json"))

    assert {path.name for path in configs} == {
        "taobao-12-no-threshold-redpacket.json",
        "taobao-25-no-threshold-redpacket.json",
        "taobao-instant-commerce-compliance.json",
        "taobao-instant-commerce-regular.json",
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
    assert twelve.validation_config.required_ending_call_to_actions == ()
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
    assert (
        twenty_five.validation_config.required_ending_call_to_actions
        == EXPECTED_ENDING_CALL_TO_ACTIONS
    )
    assert "即时外卖用户" in twenty_five.creative_brief.audience
    assert any(
        preference.startswith("结尾自然使用项目校验配置")
        for preference in twenty_five.creative_brief.preferences
    )


@pytest.mark.integration
def test_taobao_25_project_allows_natural_call_to_action() -> None:
    config = load_project_config(PROJECT_CONFIG_ROOT / "taobao-25-no-threshold-redpacket.json")
    copy = (
        "0.1元起一杯瑞幸咖啡，早八人看到真的很难不心动。现在上淘宝闪购有"
        "[[NO_SPLIT]]最高25元无门槛红包，还可以叠加九折津贴卡[[/NO_SPLIT]]，"
        "附近门店能配送到家，早上赶时间也不用专门绕路。点下方链接看看。"
    )

    assert validate_copy(copy, config.campaign, config.validation_config).is_valid is True


@pytest.mark.integration
def test_taobao_regular_project_uses_25_yuan_benefit_without_allowance_card() -> None:
    config = load_project_config(PROJECT_CONFIG_ROOT / "taobao-instant-commerce-regular.json")
    valid_copy = (
        "早八想喝咖啡的看过来，淘宝闪购现在有"
        "[[NO_SPLIT]]最高25元无门槛红包[[/NO_SPLIT]]，"
        "附近门店能配送到公司，早上赶时间不用专门绕路排队，午后想喝也能直接在附近门店里挑一挑，"
        "想给自己补一杯的，点开下方链接，进去逛逛吧。"
    )

    assert config.project_id == "taobao-instant-commerce-regular"
    assert config.campaign.campaign_name == "淘宝闪购常规"
    assert [benefit.text for benefit in config.campaign.benefit_points] == [
        "最高25元无门槛红包",
        "0.1元起",
    ]
    assert config.campaign.no_split_phrases == ("最高25元无门槛红包",)
    assert config.campaign.forbidden_expressions == (
        "最高12元无门槛红包",
        "9折津贴卡",
        "九折津贴卡",
    )
    assert (
        config.validation_config.required_ending_call_to_actions == EXPECTED_ENDING_CALL_TO_ACTIONS
    )
    assert validate_copy(valid_copy, config.campaign, config.validation_config).is_valid is True
    for forbidden in ("9折津贴卡", "九折津贴卡"):
        report = validate_copy(
            valid_copy.replace(
                "点开下方链接，进去逛逛吧。",
                f"还能叠加{forbidden}。点下方链接看看。",
            ),
            config.campaign,
            config.validation_config,
        )
        assert any(issue.code.value == "BANNED_EXPRESSION" for issue in report.issues)


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
        "早八人想喝咖啡的看过来，[[NO_SPLIT]]淘宝闪购有大额红包[[/NO_SPLIT]]，"
        "看到附近瑞幸还有活动价，我直接选了杯拿铁。"
        "外卖送到公司不用绕路，上班前就能喝到，"
        "想给自己补一杯的，点开下面的链接看看吧。"
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
    assert config.campaign.no_split_phrases == ("淘宝闪购有大额红包",)
    assert config.validation_config.call_to_actions == ()
    assert (
        config.validation_config.required_ending_call_to_actions == EXPECTED_ENDING_CALL_TO_ACTIONS
    )
    assert config.validation_config.forbid_numeric_redpacket_amounts is True
    assert "只使用已确认的美食外卖场景" in config.creative_brief.preferences
    assert compliant_report.is_valid is True
    assert any(issue.code.value == "NUMERIC_REDPACKET_AMOUNT" for issue in numeric_report.issues)
