from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.models import CandidateKind
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
