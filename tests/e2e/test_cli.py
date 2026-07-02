import json
from pathlib import Path
from typing import Any

import pytest

from avatar_prompt_pipeline.cli import run


@pytest.mark.e2e
def test_compose_cli_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    result = run(["compose", "--category", "雨靴", "--selling-point", "中筒款式"])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["brief"]["category"] == "雨靴"
    assert output["brief"]["selling_points"] == ["中筒款式"]


@pytest.mark.e2e
def test_compose_cli_writes_requested_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "prompt-package.json"

    result = run(["compose", "--category", "雨靴", "--output", str(destination)])

    assert result == 0
    assert destination.is_file()
    assert "Prompt 包已写入" in capsys.readouterr().out
