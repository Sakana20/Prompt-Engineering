import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from avatar_prompt_pipeline.cli import build_parser, default_daily_media_directory, run
from avatar_prompt_pipeline.learning.models import CandidateKind
from avatar_prompt_pipeline.learning.service import LearningService


def _approve_person_candidate(service: LearningService) -> tuple[str, int]:
    candidate = service.add_person_prompt("年轻鹅蛋脸女生，栗棕短发，米白针织衫")
    review = service.submit_review(
        CandidateKind.PERSON,
        str(candidate.candidate_id),
        expected_revision=int(candidate.revision),
    )
    approved = service.approve(
        CandidateKind.PERSON,
        str(candidate.candidate_id),
        expected_revision=int(review.revision),
    )
    return str(approved.candidate_id), int(approved.revision)


def _person_publication_payload(candidate_id: str, revision: int) -> dict[str, object]:
    descriptions = {
        "identity": "年轻鹅蛋脸，眉眼清爽，邻家审美",
        "hair": "栗棕色锁骨短发，轻薄刘海",
        "outfit": "米白针织衫搭配深蓝半裙，简约通勤",
        "scene": "自然光居家餐厅背景，布置干净生活化",
    }
    return {
        "schema_version": "1.0",
        "kind": "person",
        "candidate_id": candidate_id,
        "revision": revision,
        "person_blocks": [
            {
                "block_id": f"person-{block_type}-e2e",
                "block_type": block_type,
                "description": description,
                "compatible_with": [],
                "incompatible_with": [],
                "removed_constraints": [],
                "removed_risks": [],
                "diversity_tags": [block_type, "clean"],
            }
            for block_type, description in descriptions.items()
        ],
    }


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
        "learning-preflight",
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
    generation_commands = {
        "compose",
        "init-batch",
        "validate-copy",
        "validate-batch",
        "package",
        "export-csv",
    }
    for entry in schema["oneOf"]:
        command = entry.get("properties", {}).get("command", {}).get("const")
        if command in generation_commands:
            assert "learning_root" in entry["properties"]


@pytest.mark.e2e
def test_learning_preflight_gates_approved_candidates_before_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "learning"
    monkeypatch.setenv("AVATAR_PROMPT_PROJECT", str(tmp_path))

    result = run(["learning-preflight", "--learning-root", str(root)])
    ready: dict[str, Any] = json.loads(capsys.readouterr().out)

    assert result == 0
    assert ready["ready_for_generation"] is True

    service = LearningService.from_root(root)
    _approve_person_candidate(service)

    result = run(["learning-preflight", "--learning-root", str(root)])
    blocked: dict[str, Any] = json.loads(capsys.readouterr().out)

    assert result == 3
    assert blocked["ready_for_generation"] is False
    assert blocked["required_actions"] == ["codex_publish_approved"]
    assert blocked["approved_count"] == 1
    assert blocked["approved"]["person"][0]["edited_prompt"].startswith("年轻鹅蛋脸")


@pytest.mark.e2e
@pytest.mark.parametrize(
    "command",
    ["compose", "init-batch", "validate-copy", "validate-batch", "package", "export-csv"],
)
def test_every_generation_command_stops_for_codex_publication(
    command: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "learning"
    monkeypatch.setenv("AVATAR_PROMPT_PROJECT", str(tmp_path))
    _approve_person_candidate(LearningService.from_root(root))
    missing_input = tmp_path / "must-not-be-read.json"
    template = tmp_path / "must-not-be-written.json"
    arguments = {
        "compose": ["compose", "--category", "雨伞"],
        "init-batch": [
            "init-batch",
            "--task-name",
            "blocked",
            "--category",
            "雨伞",
            "--output",
            str(template),
        ],
        "validate-copy": ["validate-copy", "待校验文案"],
        "validate-batch": ["validate-batch", "--input", str(missing_input)],
        "package": ["package", "--input", str(missing_input), "--format", "json"],
        "export-csv": ["export-csv", "--input", str(missing_input)],
    }[command]
    arguments.extend(["--learning-root", str(root)])

    result = run(arguments)
    blocked: dict[str, Any] = json.loads(capsys.readouterr().out)

    assert result == 3
    assert blocked["generation_blocked"] is True
    assert blocked["blocked_command"] == command
    assert blocked["codex_semantic_processing_required"] is True
    assert blocked["required_actions"] == ["codex_publish_approved"]
    assert blocked["approved"]["person"][0]["edited_prompt"].startswith("年轻鹅蛋脸")
    assert not template.exists()


@pytest.mark.e2e
def test_generation_resumes_only_after_codex_manifest_is_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "learning"
    monkeypatch.setenv("AVATAR_PROMPT_PROJECT", str(tmp_path))
    candidate_id, revision = _approve_person_candidate(LearningService.from_root(root))

    result = run(["compose", "--category", "雨伞", "--learning-root", str(root)])
    blocked: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 3
    assert blocked["blocked_command"] == "compose"

    manifest = tmp_path / "publication.json"
    manifest.write_text(
        json.dumps(_person_publication_payload(candidate_id, revision), ensure_ascii=False),
        encoding="utf-8",
    )
    result = run(
        [
            "learning-publish",
            "--kind",
            "person",
            "--candidate-id",
            candidate_id,
            "--expected-revision",
            str(revision),
            "--manifest",
            str(manifest),
            "--learning-root",
            str(root),
        ]
    )
    published: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert published["status"] == "published"

    result = run(["compose", "--category", "雨伞", "--learning-root", str(root)])
    generated: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert generated["brief"]["category"] == "雨伞"


@pytest.mark.e2e
def test_learning_transcribe_uses_user_configured_daily_media_default() -> None:
    parser = build_parser()
    args = parser.parse_args(["learning-transcribe", "--date", "2026-08-12"])

    assert args.input is None
    assert default_daily_media_directory(datetime(2026, 8, 12)) == Path(
        "/Users/sakana/Desktop/Work/2026/08.12/淘宝闪购/素材"
    )
