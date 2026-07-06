import json
from pathlib import Path
from typing import Any

import pytest

from avatar_prompt_pipeline.config import ProjectConfigError, load_project_config


def _write_config(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_project_config_builds_project_brief_and_campaign(tmp_path: Path) -> None:
    source = _write_config(
        tmp_path / "taobao-25.json",
        {
            "project_id": "taobao-25-no-threshold-redpacket",
            "category": "西瓜",
            "product_name": "麒麟西瓜",
            "selling_points": ["清甜多汁"],
            "forbidden_claims": ["包甜"],
            "platform": "淘宝闪购",
            "campaign_name": "25元无门槛红包项目",
            "benefit_points": [
                {
                    "id": "primary-benefit",
                    "text": "最高25元无门槛红包",
                }
            ],
            "campaign_forbidden_expressions": ["最高12元无门槛红包"],
            "no_split_phrases": ["最高25元无门槛红包，还可以叠加九折津贴卡"],
            "required_disclosures": ["以页面展示为准"],
            "confirmed_claims": ["可提及配送到家"],
            "language_style": {
                "name": "benefit-forward-natural",
                "tone": "自然直接",
                "point_of_view": "像自己刚用过活动后分享",
                "sentence_style": "少铺垫，快速进入购买理由",
                "emphasis": ["先讲清活动利益点"],
                "avoid_phrases": ["错过就亏"],
                "extra_rules": ["不要夸张促销氛围"],
            },
        },
    )

    config = load_project_config(source)

    assert config.project_id == "taobao-25-no-threshold-redpacket"
    assert config.brief.category == "西瓜"
    assert config.brief.product_name == "麒麟西瓜"
    assert config.brief.selling_points == ("清甜多汁",)
    assert config.brief.forbidden_claims == ("包甜",)
    assert config.campaign.platform == "淘宝闪购"
    assert config.campaign.campaign_name == "25元无门槛红包项目"
    assert config.campaign.benefit_points[0].text == "最高25元无门槛红包"
    assert config.campaign.benefit_points[0].priority == 1
    assert config.campaign.no_split_phrases == ("最高25元无门槛红包，还可以叠加九折津贴卡",)
    assert config.campaign.forbidden_expressions == ("最高12元无门槛红包",)
    assert config.campaign.required_disclosures == ("以页面展示为准",)
    assert config.campaign.confirmed_claims == ("可提及配送到家",)
    assert "点击左下角链接" in config.validation_config.call_to_actions
    assert config.language_style.name == "benefit-forward-natural"
    assert config.language_style.tone == "自然直接"
    assert config.language_style.emphasis == ("先讲清活动利益点",)
    assert config.language_style.avoid_phrases == ("错过就亏",)
    assert config.language_style.extra_rules == ("不要夸张促销氛围",)


def test_load_project_config_rejects_unknown_fields(tmp_path: Path) -> None:
    source = _write_config(
        tmp_path / "bad.json",
        {
            "category": "西瓜",
            "unknown": "value",
        },
    )

    with pytest.raises(ProjectConfigError, match="未知字段"):
        load_project_config(source)


def test_load_project_config_rejects_invalid_benefit_shape(tmp_path: Path) -> None:
    source = _write_config(
        tmp_path / "bad-benefit.json",
        {
            "category": "西瓜",
            "benefit_points": [{"id": "primary-benefit"}],
        },
    )

    with pytest.raises(ProjectConfigError, match="利益点 id 和 text 不能为空"):
        load_project_config(source)


def test_load_project_config_rejects_unknown_language_style_fields(tmp_path: Path) -> None:
    source = _write_config(
        tmp_path / "bad-style.json",
        {
            "category": "西瓜",
            "language_style": {"unknown": "value"},
        },
    )

    with pytest.raises(ProjectConfigError, match="language_style 包含未知字段"):
        load_project_config(source)


def test_load_project_config_uses_referenced_validation_config(tmp_path: Path) -> None:
    validation_path = _write_config(
        tmp_path / "promo-validation.json",
        {
            "call_to_actions": ["直播间"],
        },
    )
    source = _write_config(
        tmp_path / "project.json",
        {
            "category": "咖啡",
            "validation_config_path": validation_path.name,
        },
    )

    config = load_project_config(source)

    assert config.validation_config.call_to_actions == ("直播间",)
