import csv
from pathlib import Path

import pytest

from avatar_prompt_pipeline.validation import validate_batch_diversity, validate_copy

BATCH_PATH = Path(__file__).parents[1] / "cases" / "watermelon_batch_20260702.csv"


@pytest.mark.integration
def test_watermelon_batch_matches_prompt_and_copy_contract() -> None:
    with BATCH_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 5
    assert len({row["task_id"] for row in rows}) == 5
    assert all(row["person_prompt"].strip() for row in rows)
    assert all(row["aspect_ratio"] == "9:16" for row in rows)
    assert all(row["voice"] == "明朗女声" for row in rows)
    assert [row["notes"] for row in rows] == [f"西瓜+{index}" for index in range(1, 6)]

    reports = [validate_copy(row["script"]) for row in rows]
    assert all(report.is_valid for report in reports)
    assert validate_batch_diversity([row["script"] for row in rows]) == ()
