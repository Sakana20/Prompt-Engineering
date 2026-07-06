import json
from pathlib import Path
from typing import Any

import pytest

from avatar_prompt_pipeline.cli import run
from avatar_prompt_pipeline.validation import REQUIRED_BENEFIT


@pytest.mark.e2e
def test_compose_cli_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    result = run(["compose", "--category", "雨靴", "--selling-point", "中筒款式"])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["brief"]["category"] == "雨靴"
    assert output["brief"]["selling_points"] == ["中筒款式"]
    assert output["campaign"]["benefit_points"][0]["text"] == REQUIRED_BENEFIT


@pytest.mark.e2e
def test_compose_cli_accepts_custom_and_no_benefit_campaigns(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run(
        [
            "compose",
            "--category",
            "雨伞",
            "--platform",
            "淘宝闪购",
            "--benefit-point",
            "淘宝闪购满20减5",
        ]
    )
    custom: dict[str, Any] = json.loads(capsys.readouterr().out)

    assert result == 0
    assert custom["campaign"]["benefit_points"][0]["text"] == "淘宝闪购满20减5"

    result = run(["compose", "--category", "雨伞", "--preset", "none"])
    no_benefit: dict[str, Any] = json.loads(capsys.readouterr().out)

    assert result == 0
    assert no_benefit["campaign"]["benefit_points"] == []


@pytest.mark.e2e
def test_compose_cli_uses_project_config_without_default_campaign(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "taobao-25-project.json"
    validation_path = tmp_path / "promo-validation.json"
    validation_path.write_text(
        json.dumps({"call_to_actions": ["直播间", "立即购买"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    config_path.write_text(
        json.dumps(
            {
                "project_id": "taobao-25-no-threshold-redpacket",
                "category": "西瓜",
                "platform": "淘宝闪购",
                "campaign_name": "25元无门槛红包项目",
                "benefit_points": [
                    {
                        "id": "primary-benefit",
                        "text": "最高25元无门槛红包",
                    }
                ],
                "campaign_forbidden_expressions": ["最高12元无门槛红包"],
                "validation_config_path": validation_path.name,
                "language_style": {
                    "name": "benefit-forward-promo",
                    "tone": "自然直接",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run(["compose", "--config", str(config_path)])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["brief"]["category"] == "西瓜"
    assert output["campaign"]["campaign_name"] == "25元无门槛红包项目"
    assert output["campaign"]["benefit_points"][0]["text"] == "最高25元无门槛红包"
    assert output["campaign"]["forbidden_expressions"] == ["最高12元无门槛红包"]
    assert output["validation_config"]["call_to_actions"] == ["直播间", "立即购买"]
    assert output["language_style"]["name"] == "benefit-forward-promo"
    assert "风格名称：benefit-forward-promo" in output["copywriting_prompt"]
    assert "禁止出现以下行动引导：直播间、立即购买" in output["copywriting_prompt"]
    assert (
        f"利益点[primary-benefit]：[[NO_SPLIT]]{REQUIRED_BENEFIT}"
        not in output["copywriting_prompt"]
    )


@pytest.mark.e2e
def test_validate_copy_cli_uses_project_config_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "taobao-25-project.json"
    validation_path = tmp_path / "promo-validation.json"
    validation_path.write_text(
        json.dumps({"call_to_actions": ["直播间", "立即购买"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    config_path.write_text(
        json.dumps(
            {
                "category": "西瓜",
                "benefit_points": [
                    {
                        "id": "primary-benefit",
                        "text": "最高25元无门槛红包",
                    }
                ],
                "campaign_forbidden_expressions": ["最高12元无门槛红包"],
                "validation_config_path": validation_path.name,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = (
        "下班回家路上想顺手买点水果，看到小区附近还有新鲜西瓜可选，"
        "[[NO_SPLIT]]最高25元无门槛红包[[/NO_SPLIT]]"
        "正好能用。这类水果适合切好放进冰箱，饭后端出来一家人分着吃，"
        "临时补一份也不用绕远路。"
    )

    result = run(["validate-copy", text, "--config", str(config_path)])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["is_valid"] is True

    previous_text = text.replace("最高25元无门槛红包", "最高12元无门槛红包")
    result = run(["validate-copy", previous_text, "--config", str(config_path)])

    output = json.loads(capsys.readouterr().out)
    assert result == 1
    assert any(issue["code"] == "MISSING_BENEFIT" for issue in output["issues"])
    assert any(issue["code"] == "BANNED_EXPRESSION" for issue in output["issues"])


@pytest.mark.e2e
def test_project_config_rejects_mixed_campaign_arguments(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "project.json"
    config_path.write_text(
        json.dumps({"category": "西瓜", "benefit_points": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="不要同时传入活动口径参数"):
        run(
            [
                "compose",
                "--config",
                str(config_path),
                "--benefit-point",
                "最高12元无门槛红包",
            ]
        )


@pytest.mark.e2e
def test_compose_cli_writes_requested_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "prompt-package.json"

    result = run(["compose", "--category", "雨靴", "--output", str(destination)])

    assert result == 0
    assert destination.is_file()
    assert "Prompt 包已写入" in capsys.readouterr().out


@pytest.mark.e2e
def test_validate_copy_cli_returns_failure_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run(["validate-copy", f"立即购买。{REQUIRED_BENEFIT}"])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 1
    assert output["is_valid"] is False
    assert any(issue["code"] == "CALL_TO_ACTION" for issue in output["issues"])
