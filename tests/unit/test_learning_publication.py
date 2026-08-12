import json
from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.models import CandidateKind
from avatar_prompt_pipeline.learning.publication import (
    load_publication_manifest,
    publish_manifest,
)
from avatar_prompt_pipeline.learning.service import LearningService
from avatar_prompt_pipeline.learning.validation import LearningValidationError


def _approved_person(service: LearningService) -> tuple[str, int]:
    candidate = service.add_person_prompt("鹅蛋脸女生，栗棕长发，米白针织衫配深蓝半裙")
    ready = service.submit_review(
        CandidateKind.PERSON, str(candidate.candidate_id), expected_revision=1
    )
    approved = service.approve(
        CandidateKind.PERSON, str(candidate.candidate_id), expected_revision=int(ready.revision)
    )
    return str(approved.candidate_id), int(approved.revision)


def _person_manifest(candidate_id: str, revision: int) -> dict[str, object]:
    blocks = []
    descriptions = {
        "identity": "年轻鹅蛋脸，眉眼清爽，邻家审美",
        "hair": "栗棕色锁骨长发，轻薄刘海",
        "outfit": "米白针织衫搭配深蓝半裙，简约通勤",
        "scene": "自然光居家餐厅背景，布置干净生活化",
    }
    for block_type, description in descriptions.items():
        blocks.append(
            {
                "block_id": f"person-{block_type}-001",
                "block_type": block_type,
                "description": description,
                "compatible_with": [],
                "incompatible_with": [],
                "removed_constraints": [],
                "removed_risks": [],
                "diversity_tags": [block_type, "clean"],
            }
        )
    return {
        "schema_version": "1.0",
        "kind": "person",
        "candidate_id": candidate_id,
        "revision": revision,
        "person_blocks": blocks,
    }


def test_only_approved_candidate_publishes_four_person_resources(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    candidate_id, revision = _approved_person(service)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(_person_manifest(candidate_id, revision), ensure_ascii=False),
        encoding="utf-8",
    )

    published = publish_manifest(
        service.store,
        load_publication_manifest(manifest_path),
        root=tmp_path,
    )

    resource = tmp_path / "prompt-engineering" / "references" / "person-prompt-source-blocks.md"
    assert published.status.value == "published"
    assert len(published.published_block_ids) == 4
    assert "person-identity-001" in resource.read_text(encoding="utf-8")


def test_unapproved_candidate_cannot_publish(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    candidate = service.add_person_prompt("圆脸女生，黑色短发，蓝色衬衫")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(_person_manifest(str(candidate.candidate_id), 1), ensure_ascii=False),
        encoding="utf-8",
    )
    with pytest.raises(LearningValidationError, match="approved"):
        publish_manifest(service.store, load_publication_manifest(manifest_path), root=tmp_path)


def test_publication_rolls_back_resources_when_candidate_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    candidate_id, revision = _approved_person(service)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(_person_manifest(candidate_id, revision), ensure_ascii=False),
        encoding="utf-8",
    )

    def fail_save(*args: object, **kwargs: object) -> None:
        raise OSError("simulated candidate commit failure")

    monkeypatch.setattr(service.store, "save", fail_save)
    with pytest.raises(OSError, match="simulated"):
        publish_manifest(service.store, load_publication_manifest(manifest_path), root=tmp_path)

    refs = tmp_path / "prompt-engineering" / "references"
    assert not (refs / "person-prompt-source-blocks.md").exists()
    assert not (refs / "person-prompt-block-contracts.md").exists()
