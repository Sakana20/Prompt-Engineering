from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.models import (
    CandidateId,
    CandidateKind,
    CopyLearningCandidate,
    LearningStatus,
    Revision,
)
from avatar_prompt_pipeline.learning.service import LearningService
from avatar_prompt_pipeline.learning.validation import LearningValidationError, detect_risks


def test_state_machine_accepts_review_path_and_rejects_auto_approval(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    candidate = service.add_person_prompt("年轻圆脸女生，黑色短发，简约通勤服装")

    with pytest.raises(LearningValidationError, match="不允许"):
        service.approve(
            CandidateKind.PERSON,
            str(candidate.candidate_id),
            expected_revision=1,
        )

    ready = service.submit_review(
        CandidateKind.PERSON,
        str(candidate.candidate_id),
        expected_revision=1,
    )
    approved = service.approve(
        CandidateKind.PERSON,
        str(candidate.candidate_id),
        expected_revision=2,
    )
    assert ready.status.value == "ready_for_review"
    assert approved.status.value == "approved"


def test_risk_detection_keeps_asr_claims_out_of_fact_layer() -> None:
    risks = detect_risks(
        "淘宝红包低至9元，销量第一，赶紧下单",
        kind=CandidateKind.COPY,
    )
    assert {"price", "promotion", "platform_or_delivery", "action_call", "claim"} <= set(risks)


def test_copy_submission_requires_controlled_classification_fields(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    candidate = CopyLearningCandidate(
        candidate_id=CandidateId("copy-classification-001"),
        status=LearningStatus.PENDING,
        revision=Revision(1),
        created_at="2026-08-12T10:00:00+08:00",
        updated_at="2026-08-12T10:00:00+08:00",
        source_media=str(tmp_path / "sample.mp4"),
        source_fingerprint="a" * 64,
        source_date="2026-08-12",
        asr_cache_key="b" * 64,
        provider="paraformer-zh",
        model="fake",
        raw_transcript="这杯果汁很适合通勤时喝",
        edited_transcript="这杯果汁很适合通勤时喝",
    )
    service.store.create(candidate)

    with pytest.raises(LearningValidationError, match="提交学习前请选择"):
        service.submit_learning(
            CandidateKind.COPY,
            str(candidate.candidate_id),
            expected_revision=1,
        )

    updated = service.update(
        CandidateKind.COPY,
        str(candidate.candidate_id),
        expected_revision=1,
        edited_text=candidate.edited_transcript,
        structured_fields={
            "category_family": "beverage",
            "consumption_need": "commute",
            "season": "all",
            "source_usage": ("human_rewrite",),
        },
    )
    approved = service.submit_learning(
        CandidateKind.COPY,
        str(candidate.candidate_id),
        expected_revision=int(updated.revision),
    )

    assert approved.status is LearningStatus.APPROVED


def test_submit_learning_is_explicit_single_user_approval(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    candidate = service.add_person_prompt("年轻圆脸女生，黑色短发，简约通勤服装")

    approved = service.submit_learning(
        CandidateKind.PERSON,
        str(candidate.candidate_id),
        expected_revision=1,
    )

    assert approved.status is LearningStatus.APPROVED
    assert int(approved.revision) == 2
    with pytest.raises(LearningValidationError, match="不允许从 approved 提交学习"):
        service.submit_learning(
            CandidateKind.PERSON,
            str(candidate.candidate_id),
            expected_revision=2,
        )
