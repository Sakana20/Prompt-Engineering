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
                    "text": "淘宝闪购最高25元无门槛红包",
                }
            ],
            "campaign_forbidden_expressions": ["12元无门槛红包"],
            "required_disclosures": ["以页面展示为准"],
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
    assert config.campaign.benefit_points[0].text == "淘宝闪购最高25元无门槛红包"
    assert config.campaign.benefit_points[0].priority == 1
    assert config.campaign.forbidden_expressions == ("12元无门槛红包",)
    assert config.campaign.required_disclosures == ("以页面展示为准",)


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
