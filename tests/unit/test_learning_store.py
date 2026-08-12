from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.models import CandidateKind
from avatar_prompt_pipeline.learning.service import LearningService
from avatar_prompt_pipeline.learning.store import RevisionConflictError
from avatar_prompt_pipeline.learning.validation import LearningValidationError


def test_store_isolates_kinds_and_preserves_raw_content(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    person = service.add_person_prompt("圆脸女生，黑色短发，白衬衫配牛仔裤")

    updated = service.update(
        CandidateKind.PERSON,
        str(person.candidate_id),
        expected_revision=1,
        edited_text="鹅蛋脸女生，黑色短发，米白衬衫配牛仔裤",
    )

    directory = tmp_path / "learning" / "person" / "candidates" / str(person.candidate_id)
    assert (directory / "raw_prompt.txt").read_text(encoding="utf-8") == person.raw_prompt
    assert updated.revision == 2
    assert not (tmp_path / "learning" / "copy").exists()
    with pytest.raises(RevisionConflictError):
        service.update(
            CandidateKind.PERSON,
            str(person.candidate_id),
            expected_revision=1,
            edited_text="过期写入",
        )


def test_store_rejects_path_traversal(tmp_path: Path) -> None:
    service = LearningService.from_root(tmp_path / "learning")
    with pytest.raises(LearningValidationError):
        service.get(CandidateKind.PERSON, "../outside")
