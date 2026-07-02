import csv
from pathlib import Path

import pytest

from avatar_prompt_pipeline.models import VisualProfile
from avatar_prompt_pipeline.validation import (
    validate_batch_diversity,
    validate_copy,
    validate_visual_diversity,
)

BATCH_PATH = Path(__file__).parents[1] / "cases" / "honey_peach_batch_20260702.csv"
VISUAL_PROFILES = [
    VisualProfile("圆脸-黑色齐下巴短发", "浅米色短袖针织上衣-白色居家长裤"),
    VisualProfile("鹅蛋脸-栗色双麻花辫", "浅绿色宽松短袖-米白色休闲长裤"),
    VisualProfile("偏长脸-黑色高马尾", "雾蓝色短袖衬衫-卡其色直筒长裤"),
    VisualProfile("心形脸-深棕色半扎长卷发", "白色短袖T恤-浅黄色薄外套-卡其休闲长裤"),
    VisualProfile("方圆脸-茶棕色齐肩直发", "浅粉色短袖上衣-米色半身裙"),
]


@pytest.mark.integration
def test_honey_peach_batch_matches_prompt_and_copy_contract() -> None:
    with BATCH_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 5
    assert len({row["task_id"] for row in rows}) == 5
    assert all(row["person_prompt"].strip() for row in rows)
    assert all(row["aspect_ratio"] == "9:16" for row in rows)
    assert all(row["voice"] == "明朗女声" for row in rows)
    assert [row["notes"] for row in rows] == [f"水蜜桃+{index}" for index in range(1, 6)]

    reports = [validate_copy(row["script"]) for row in rows]
    assert all(report.is_valid for report in reports)
    assert validate_batch_diversity([row["script"] for row in rows]) == ()
    assert validate_visual_diversity(VISUAL_PROFILES) == ()
    assert all("保持相同" not in row["person_prompt"] for row in rows)
