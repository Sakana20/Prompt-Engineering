import csv
from pathlib import Path

import pytest

from avatar_prompt_pipeline.models import VisualProfile
from avatar_prompt_pipeline.validation import (
    validate_batch_diversity,
    validate_copy,
    validate_visual_diversity,
    wrap_required_benefit,
)

BATCH_PATH = Path(__file__).parents[1] / "cases" / "watermelon_batch_20260702.csv"
VISUAL_PROFILES = [
    VisualProfile("圆脸-黑色齐耳短发", "浅黄色短袖棉质上衣-米白色居家长裤"),
    VisualProfile("鹅蛋脸-栗棕色微卷锁骨发", "浅豆绿色短袖针织衫-白色休闲长裤"),
    VisualProfile("偏长脸-黑色高马尾", "雾蓝色短袖衬衫-米色直筒长裤"),
    VisualProfile("心形脸-深棕色长直发", "浅杏色短袖上衣-浅棕色半身裙"),
    VisualProfile("方圆脸-深棕色侧编发", "白色短袖T恤-浅绿色薄衬衫-卡其色休闲长裤"),
]


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

    assert all("[[NO_SPLIT]]" not in row["script"] for row in rows)
    reports = [validate_copy(wrap_required_benefit(row["script"])) for row in rows]
    assert all(report.is_valid for report in reports)
    assert validate_batch_diversity([row["script"] for row in rows]) == ()
    assert validate_visual_diversity(VISUAL_PROFILES) == ()
    assert all("保持相同" not in row["person_prompt"] for row in rows)
