import json
from pathlib import Path

from avatar_prompt_pipeline.learning.models import (
    CandidateId,
    CandidateKind,
    CopyLearningCandidate,
    LearningStatus,
    Revision,
)
from avatar_prompt_pipeline.learning.preflight import inspect_learning_preflight
from avatar_prompt_pipeline.learning.publication import (
    load_publication_manifest,
    publish_manifest,
)
from avatar_prompt_pipeline.learning.service import LearningService


def _approved_copy(service: LearningService) -> CopyLearningCandidate:
    candidate = CopyLearningCandidate(
        candidate_id=CandidateId("copy-preflight-001"),
        status=LearningStatus.PENDING,
        revision=Revision(1),
        created_at="2026-08-12T10:00:00+08:00",
        updated_at="2026-08-12T10:00:00+08:00",
        source_media="sample.mp4",
        source_fingerprint="a" * 64,
        source_date="2026-08-12",
        asr_cache_key="b" * 64,
        provider="paraformer-zh",
        model="fake",
        raw_transcript="上班路上带一杯果汁很方便",
        edited_transcript="上班路上带一杯果汁很方便",
        category_family="beverage",
        consumption_need="commute",
        season="all",
        source_usage=("human_rewrite",),
    )
    service.store.create(candidate)
    ready = service.submit_review(
        CandidateKind.COPY,
        str(candidate.candidate_id),
        expected_revision=1,
    )
    approved = service.approve(
        CandidateKind.COPY,
        str(candidate.candidate_id),
        expected_revision=int(ready.revision),
    )
    assert isinstance(approved, CopyLearningCandidate)
    return approved


def _copy_manifest(candidate: CopyLearningCandidate) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "kind": "copy",
        "candidate_id": str(candidate.candidate_id),
        "revision": int(candidate.revision),
        "source_fingerprint": candidate.source_fingerprint,
        "copy_blocks": [
            {
                "block_id": "learned-preflight-copy-001",
                "template": "上班路上带一杯[商品名]很方便",
                "slots": [{"name": "商品名", "value_type": "confirmed_product_name"}],
                "category_families": ["beverage"],
                "consumption_needs": ["commute"],
                "seasons": ["all"],
                "allowed_modes": ["human_rewrite"],
                "removed_risks": [],
                "solid_food_only": False,
                "diversity_tags": {
                    "opening_type": "commute",
                    "rhythm": "short",
                    "need": "portable",
                    "emotion": "direct",
                },
            }
        ],
    }


def test_preflight_is_ready_when_no_approved_or_broken_published_candidates(
    tmp_path: Path,
) -> None:
    service = LearningService.from_root(tmp_path / "learning")

    report = inspect_learning_preflight(service.store, resource_root=tmp_path)

    assert report.ready_for_generation is True
    assert report.required_actions == ()
    assert report.approved_count == 0
    assert report.published_count == 0


def test_preflight_blocks_generation_and_exposes_approved_candidate(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    approved = _approved_copy(service)

    report = inspect_learning_preflight(service.store, resource_root=tmp_path)

    assert report.ready_for_generation is False
    assert report.required_actions == ("codex_publish_approved",)
    assert report.approved_copy == (approved,)
    payload = report.to_dict()
    approved_payload = payload["approved"]
    assert isinstance(approved_payload, dict)
    copy_payload = approved_payload["copy"]
    assert isinstance(copy_payload, list)
    assert copy_payload[0]["edited_transcript"] == approved.edited_transcript


def test_preflight_verifies_published_candidate_against_formal_resource(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    approved = _approved_copy(service)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(_copy_manifest(approved), ensure_ascii=False),
        encoding="utf-8",
    )
    publish_manifest(
        service.store,
        load_publication_manifest(manifest_path),
        root=tmp_path,
    )

    report = inspect_learning_preflight(service.store, resource_root=tmp_path)

    assert report.ready_for_generation is True
    assert report.approved_count == 0
    assert report.published_count == 1
    assert report.formal_copy_block_ids == ("learned-preflight-copy-001",)

    resource = tmp_path / "prompt-engineering" / "references" / "volume-copy-source-blocks.md"
    formal_text = resource.read_text(encoding="utf-8")
    published_section = formal_text.partition("## 审核发布的网页学习块")[2]
    assert (
        "### `learned-preflight-copy-001`\n\n"
        "```text\n上班路上带一杯[商品名]很方便\n```" in published_section
    )
    assert "```json" not in published_section
    assert str(approved.candidate_id) not in formal_text

    provenance_path = tmp_path / "learning" / "copy" / "published" / "provenance.jsonl"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["blocks"][0]["block_id"] == "learned-preflight-copy-001"
    assert provenance["blocks"][0]["category_families"] == ["beverage"]

    resource.unlink()
    broken = inspect_learning_preflight(service.store, resource_root=tmp_path)

    assert broken.ready_for_generation is False
    assert broken.required_actions == ("repair_published_resources",)
    assert broken.missing_copy_block_ids == ("learned-preflight-copy-001",)
