from dataclasses import FrozenInstanceError

import pytest

from avatar_prompt_pipeline.learning.models import (
    CandidateId,
    LearningStatus,
    PersonPromptLearningCandidate,
    Revision,
)


def test_person_candidate_is_frozen_and_has_distinct_kind() -> None:
    candidate = PersonPromptLearningCandidate(
        candidate_id=CandidateId("person-12345678"),
        status=LearningStatus.PENDING,
        revision=Revision(1),
        created_at="2026-08-11T10:00:00+08:00",
        updated_at="2026-08-11T10:00:00+08:00",
        source_label="人工样本",
        raw_prompt="年轻中国女生，清爽短发，日常通勤穿搭",
        edited_prompt="年轻中国女生，清爽短发，日常通勤穿搭",
    )

    assert candidate.kind == "person_prompt"
    with pytest.raises(FrozenInstanceError):
        candidate.edited_prompt = "changed"  # type: ignore[misc]
