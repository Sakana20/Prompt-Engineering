import csv
from pathlib import Path

import pytest

from avatar_prompt_pipeline.artifacts import (
    default_manuscript_path,
    default_oceanengine_csv_path,
    write_oceanengine_csv,
    write_segmentation_manuscript,
)
from avatar_prompt_pipeline.models import OceanengineTask

MARKED_SCRIPT = (
    "午后收拾完桌面，打开冰箱才发现果盘已经空了。我看到"
    "[[NO_SPLIT]]淘宝闪购最高12元无门槛红包[[/NO_SPLIT]]，"
    "就买了个哈密瓜。送到后切几块装进盘里，坐在沙发上慢慢吃，"
    "剩下的用保鲜盒收好，晚上家里人回来还能一起分。"
)


def test_default_artifact_paths_use_date_and_task_hierarchy() -> None:
    assert default_manuscript_path("hami-melon-batch", "HM-001", date="20260702") == Path(
        "/Users/sakana/Desktop/Work/Codex/Prompt Engineering/20260702/"
        "hami-melon-batch/HM-001.smartsplit.txt"
    )
    assert default_oceanengine_csv_path("hami-melon-batch", date="20260702") == Path(
        "/Users/sakana/Desktop/Work/Codex/Prompt Engineering/20260702/"
        "hami-melon-batch/hami-melon-batch.csv"
    )


@pytest.mark.integration
def test_manuscript_and_oceanengine_csv_are_independent_artifacts(tmp_path: Path) -> None:
    manuscript_path = tmp_path / "manuscripts" / "HM-001.smartsplit.txt"
    csv_path = tmp_path / "oceanengine" / "hami-melon-batch.csv"
    task = OceanengineTask(
        task_id="HM-001",
        person_prompt="年轻亚洲女生坐在餐桌旁，桌面放着哈密瓜，竖屏9:16。",
        marked_script=MARKED_SCRIPT,
        aspect_ratio="9:16",
        voice="明朗女声",
        title="哈密瓜居家水果场景",
        notes="哈密瓜+1",
    )

    written_manuscript = write_segmentation_manuscript(manuscript_path, task.marked_script)

    assert written_manuscript.read_text(encoding="utf-8") == f"{MARKED_SCRIPT}\n"
    assert "[[NO_SPLIT]]" in written_manuscript.read_text(encoding="utf-8")
    assert not csv_path.exists()

    written_csv = write_oceanengine_csv(csv_path, [task])

    with written_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["script"] == MARKED_SCRIPT.replace("[[NO_SPLIT]]", "").replace(
        "[[/NO_SPLIT]]", ""
    )
    assert "[[NO_SPLIT]]" not in rows[0]["script"]
    assert manuscript_path.read_text(encoding="utf-8") == f"{MARKED_SCRIPT}\n"


@pytest.mark.integration
def test_artifact_writers_refuse_to_overwrite_existing_files(tmp_path: Path) -> None:
    manuscript_path = tmp_path / "HM-001.smartsplit.txt"
    write_segmentation_manuscript(manuscript_path, MARKED_SCRIPT)

    with pytest.raises(FileExistsError, match="拒绝覆盖"):
        write_segmentation_manuscript(manuscript_path, MARKED_SCRIPT)
