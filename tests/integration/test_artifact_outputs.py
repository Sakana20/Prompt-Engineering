import csv
import json
from pathlib import Path

import pytest

from avatar_prompt_pipeline.artifacts import (
    default_libtv_omnihuman_csv_path,
    default_libtv_omnihuman_interface_path,
    default_libtv_omnihuman_plan_path,
    default_manuscript_path,
    default_oceanengine_csv_path,
    write_libtv_omnihuman_csv,
    write_libtv_omnihuman_interface_config,
    write_libtv_omnihuman_plan,
    write_oceanengine_csv,
    write_segmentation_manuscript,
)
from avatar_prompt_pipeline.models import LibtvOmniHumanTask, OceanengineTask

MARKED_SCRIPT = (
    "午后收拾完桌面，打开冰箱才发现果盘已经空了。我看到"
    "淘宝闪购[[NO_SPLIT]]最高12元无门槛红包[[/NO_SPLIT]]，"
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
    assert default_libtv_omnihuman_csv_path("hami-melon-batch", date="20260702") == Path(
        "/Users/sakana/Desktop/Work/Codex/Prompt Engineering/20260702/"
        "hami-melon-batch/hami-melon-batch.libtv.csv"
    )
    assert default_libtv_omnihuman_interface_path("hami-melon-batch", date="20260702") == Path(
        "/Users/sakana/Desktop/Work/Codex/Prompt Engineering/20260702/"
        "hami-melon-batch/hami-melon-batch.libtv.interface.json"
    )
    assert default_libtv_omnihuman_plan_path("hami-melon-batch", date="20260702") == Path(
        "/Users/sakana/Desktop/Work/Codex/Prompt Engineering/20260702/"
        "hami-melon-batch/hami-melon-batch.libtv.plan.md"
    )


@pytest.mark.integration
def test_manuscript_and_oceanengine_csv_are_independent_artifacts(tmp_path: Path) -> None:
    manuscript_path = tmp_path / "manuscripts" / "HM-001.smartsplit.txt"
    csv_path = tmp_path / "oceanengine" / "hami-melon-batch.csv"
    task = OceanengineTask(
        task_id="HM-001",
        person_prompt=(
            "数字人口播首帧，年轻亚洲女生坐在餐桌旁，场景只作为背景，正面眼睛直视镜头，桌面放着哈密瓜，商品不由人物手持，人物不看商品、不接触商品，竖屏9:16。"
        ),
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


@pytest.mark.integration
def test_libtv_omnihuman_package_writers_are_independent(tmp_path: Path) -> None:
    csv_path = tmp_path / "libtv" / "hami-melon-batch.libtv.csv"
    interface_path = tmp_path / "libtv" / "hami-melon-batch.libtv.interface.json"
    plan_path = tmp_path / "libtv" / "hami-melon-batch.libtv.plan.md"
    task = LibtvOmniHumanTask(
        task_id="HM-001",
        image_prompt=(
            "数字人口播首帧，年轻亚洲女生坐在餐桌旁，场景只作为背景，正面眼睛直视镜头，桌面放着哈密瓜，商品不由人物手持，人物不看商品、不接触商品，竖屏9:16。"
        ),
        marked_script=MARKED_SCRIPT,
        title="哈密瓜居家水果场景",
        notes="哈密瓜+1",
    )

    written_csv = write_libtv_omnihuman_csv(csv_path, [task])
    assert not interface_path.exists()
    assert not plan_path.exists()

    with written_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [
        {
            "task_id": "HM-001",
            "title": "哈密瓜居家水果场景",
            "notes": "哈密瓜+1",
            "image_prompt": (
                "数字人口播首帧，年轻亚洲女生坐在餐桌旁，场景只作为背景，正面眼睛直视镜头，"
                "桌面放着哈密瓜，商品不由人物手持，人物不看商品、不接触商品，竖屏9:16。"
            ),
            "audio_prompt": MARKED_SCRIPT.replace("[[NO_SPLIT]]", "").replace("[[/NO_SPLIT]]", ""),
            "voice_label": "温暖闺蜜",
            "voice_id": "Chinese (Mandarin)_Warm_Bestie",
            "aspect_ratio": "9:16",
        }
    ]

    written_interface = write_libtv_omnihuman_interface_config(interface_path)
    interface_config = json.loads(written_interface.read_text(encoding="utf-8"))
    assert interface_config["interface"] == "libtv_omnihuman"
    assert interface_config["task_package"] == {
        "csv": "hami-melon-batch.libtv.csv",
        "plan": "hami-melon-batch.libtv.plan.md",
    }
    assert interface_config["defaults"]["target_resolution"] == "720x1280"
    assert interface_config["defaults"]["voice_labels"] == {
        "female": "温暖闺蜜",
        "male": "温润男声",
    }
    assert interface_config["defaults"]["voice_ids"]["温暖闺蜜"] == (
        "Chinese (Mandarin)_Warm_Bestie"
    )
    assert interface_config["defaults"]["voice_ids"]["温润男声"] == ("Chinese (Mandarin)_Gentleman")
    assert interface_config["defaults"]["voice_constraints"] == {
        "speed": 1.2,
        "volume": 8,
    }
    assert interface_config["nodes"]["audio"]["params"]["speed"] == 1.2
    assert interface_config["nodes"]["audio"]["params"]["vol"] == 8
    assert interface_config["nodes"]["video"]["model"] == "OmniHuman 1.5"
    assert interface_config["execution_boundary"]["run_nodes"] is False

    written_plan = write_libtv_omnihuman_plan(plan_path, [task])
    plan = written_plan.read_text(encoding="utf-8")
    assert "接口配置：`<task>.libtv.interface.json`" in plan
    assert "node: HM-001-image" in plan
    assert "voice_label: 温暖闺蜜" in plan
    assert "[[NO_SPLIT]]" not in plan


@pytest.mark.integration
def test_libtv_omnihuman_export_fills_blank_default_voice_fields(tmp_path: Path) -> None:
    csv_path = tmp_path / "libtv" / "hami-melon-batch.libtv.csv"
    plan_path = tmp_path / "libtv" / "hami-melon-batch.libtv.plan.md"
    task = LibtvOmniHumanTask(
        task_id="HM-001",
        image_prompt=(
            "数字人口播首帧，年轻亚洲女生坐在餐桌旁，场景只作为背景，正面眼睛直视镜头，桌面放着哈密瓜，商品不由人物手持，人物不看商品、不接触商品，竖屏9:16。"
        ),
        marked_script=MARKED_SCRIPT,
        title="哈密瓜居家水果场景",
        notes="哈密瓜+1",
        voice_label="",
        voice_id="",
    )

    written_csv = write_libtv_omnihuman_csv(csv_path, [task])
    written_plan = write_libtv_omnihuman_plan(plan_path, [task])

    with written_csv.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["voice_label"] == "温暖闺蜜"
    assert row["voice_id"] == "Chinese (Mandarin)_Warm_Bestie"
    plan = written_plan.read_text(encoding="utf-8")
    assert "- voice_label: 温暖闺蜜" in plan
    assert "- voice_id: Chinese (Mandarin)_Warm_Bestie" in plan


@pytest.mark.integration
def test_task_writers_reject_prompts_without_direct_eye_contact(tmp_path: Path) -> None:
    csv_path = tmp_path / "oceanengine" / "hami-melon-batch.csv"
    task = OceanengineTask(
        task_id="HM-001",
        person_prompt="年轻亚洲女生坐在餐桌旁，身体朝向镜头，桌面放着哈密瓜，竖屏9:16。",
        marked_script=MARKED_SCRIPT,
        aspect_ratio="9:16",
        voice="明朗女声",
        title="哈密瓜居家水果场景",
        notes="哈密瓜+1",
    )

    with pytest.raises(ValueError, match="MISSING_EYE_CONTACT"):
        write_oceanengine_csv(csv_path, [task])


@pytest.mark.integration
def test_task_writers_reject_prompts_with_handheld_product(tmp_path: Path) -> None:
    csv_path = tmp_path / "libtv" / "hami-melon-batch.libtv.csv"
    task = LibtvOmniHumanTask(
        task_id="HM-001",
        image_prompt=(
            "数字人口播首帧，年轻亚洲女生坐在餐桌旁，场景只作为背景，正面眼睛直视镜头，商品不由人物手持，人物不看商品、不接触商品，人物手持商品，竖屏9:16。"
        ),
        marked_script=MARKED_SCRIPT,
        title="哈密瓜居家水果场景",
        notes="哈密瓜+1",
    )

    with pytest.raises(ValueError, match="HANDHELD_PRODUCT"):
        write_libtv_omnihuman_csv(csv_path, [task])
