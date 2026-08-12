import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from avatar_prompt_pipeline.cli import build_parser, default_daily_media_directory, run


@pytest.mark.e2e
def test_learning_person_cli_isolated_lifecycle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "learning"
    result = run(
        [
            "learning-add-person-prompt",
            "--text",
            "年轻圆脸女生，黑色短发，白衬衫配牛仔裤",
            "--learning-root",
            str(root),
        ]
    )
    created: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert created["kind"] == "person_prompt"
    assert not (root / "copy").exists()

    edited = tmp_path / "edited.txt"
    edited.write_text("年轻鹅蛋脸女生，栗棕短发，米白衬衫配牛仔裤", encoding="utf-8")
    result = run(
        [
            "learning-update",
            "--kind",
            "person",
            "--candidate-id",
            created["candidate_id"],
            "--expected-revision",
            "1",
            "--edited-file",
            str(edited),
            "--learning-root",
            str(root),
        ]
    )
    updated: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert updated["revision"] == 2
    assert updated["raw_prompt"] == created["raw_prompt"]


@pytest.mark.e2e
def test_help_and_cli_schema_cover_all_learning_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    schema = json.loads(
        (
            Path(__file__).parents[2] / "prompt-engineering/references/cli-parameters.schema.json"
        ).read_text(encoding="utf-8")
    )
    commands = {
        "learning-transcribe",
        "learning-add-person-prompt",
        "learning-list",
        "learning-update",
        "learning-submit-review",
        "learning-approve",
        "learning-reject",
        "learning-publish",
    }
    schema_commands = {
        entry.get("properties", {}).get("command", {}).get("const") for entry in schema["oneOf"]
    }
    transcribe_schema = next(
        entry
        for entry in schema["oneOf"]
        if entry.get("properties", {}).get("command", {}).get("const") == "learning-transcribe"
    )
    assert all(command in help_text for command in commands)
    assert commands <= schema_commands
    assert transcribe_schema["required"] == ["command"]
    assert "<MM.DD>/淘宝闪购/素材" in transcribe_schema["properties"]["input"]["description"]


@pytest.mark.e2e
def test_learning_transcribe_uses_user_configured_daily_media_default() -> None:
    parser = build_parser()
    args = parser.parse_args(["learning-transcribe", "--date", "2026-08-12"])

    assert args.input is None
    assert default_daily_media_directory(datetime(2026, 8, 12)) == Path(
        "/Users/sakana/Desktop/Work/2026/08.12/淘宝闪购/素材"
    )
