import json
from pathlib import Path

import pytest

from avatar_prompt_pipeline.batch import (
    TaskBatchError,
    load_task_batch,
    task_batch_from_mapping,
    task_batch_template,
    write_task_batch_template,
)


def test_task_batch_builds_notes_and_reuses_person_prompt_for_libtv() -> None:
    batch = task_batch_from_mapping(
        {
            "task_name": "hami-melon-batch",
            "category": "哈密瓜",
            "tasks": [
                {
                    "task_id": "HM-001",
                    "marked_script": "已校验口播",
                    "avatar_prompt": "完整数字人 Prompt",
                    "identity_key": "圆脸-黑色短发",
                    "outfit_key": "白衬衫-蓝牛仔裤",
                    "person_prompt": "静态人物 Prompt",
                    "title": "哈密瓜居家场景",
                }
            ],
        }
    )

    assert batch.notes_for(0) == "哈密瓜+1"
    assert batch.tasks[0].image_prompt == "静态人物 Prompt"
    assert batch.tasks[0].oceanengine_task(notes=batch.notes_for(0)).notes == "哈密瓜+1"


def test_task_batch_rejects_unknown_fields_and_unsafe_names() -> None:
    with pytest.raises(TaskBatchError, match="未知字段"):
        task_batch_from_mapping(
            {"task_name": "batch", "category": "水果", "tasks": [], "unknown": True}
        )
    with pytest.raises(TaskBatchError, match="安全目录名"):
        task_batch_from_mapping(
            {
                "task_name": "../batch",
                "category": "水果",
                "tasks": [
                    {
                        "task_id": "TASK-1",
                        "marked_script": "文案",
                        "avatar_prompt": "视频 Prompt",
                        "identity_key": "人物一",
                        "outfit_key": "服装一",
                        "person_prompt": "首帧 Prompt",
                        "title": "任务",
                    }
                ],
            }
        )


def test_load_task_batch_rejects_duplicate_task_ids(tmp_path: Path) -> None:
    task = {
        "task_id": "TASK-1",
        "marked_script": "文案",
        "avatar_prompt": "视频 Prompt",
        "identity_key": "人物一",
        "outfit_key": "服装一",
        "person_prompt": "首帧 Prompt",
        "title": "任务",
    }
    source = tmp_path / "batch.json"
    source.write_text(
        json.dumps(
            {"task_name": "batch", "category": "水果", "tasks": [task, task]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(TaskBatchError, match="task_id 必须在批次内唯一"):
        load_task_batch(source)


def test_task_batch_template_is_fill_only_and_uses_deterministic_ids(tmp_path: Path) -> None:
    destination = tmp_path / "input" / "hami.tasks.json"

    written = write_task_batch_template(
        destination,
        task_name="hami-batch",
        category="哈密瓜",
        count=2,
        task_prefix="HM",
    )
    payload = json.loads(written.read_text(encoding="utf-8"))

    assert [task["task_id"] for task in payload["tasks"]] == ["HM-001", "HM-002"]
    assert payload["tasks"][0]["marked_script"] == ""
    assert payload["tasks"][0]["person_prompt"] == ""
    assert payload["tasks"][0]["copy_mode"] == "source_fill"
    assert payload["tasks"][1]["copy_mode"] == "human_rewrite"
    assert payload["tasks"][0]["source_block_id"] == ""
    assert payload["tasks"][0]["source_slot_values"] == []
    assert payload["tasks"][1]["rewrite_anchor_phrases"] == []
    assert "notes" not in payload["tasks"][0]

    with pytest.raises(FileExistsError, match="拒绝覆盖"):
        write_task_batch_template(
            destination,
            task_name="hami-batch",
            category="哈密瓜",
            count=2,
            task_prefix="HM",
        )


def test_task_batch_template_rejects_invalid_count_and_prefix() -> None:
    with pytest.raises(TaskBatchError, match="count"):
        task_batch_template(task_name="batch", category="水果", count=0)
    with pytest.raises(TaskBatchError, match="task_prefix"):
        task_batch_template(task_name="batch", category="水果", count=1, task_prefix="水果")


def test_task_batch_rejects_non_string_rewrite_anchors() -> None:
    payload = task_batch_template(task_name="batch", category="水果", count=1)
    task = payload["tasks"][0]
    task.update(
        {
            "marked_script": "文案",
            "avatar_prompt": "视频 Prompt",
            "identity_key": "人物一",
            "outfit_key": "服装一",
            "person_prompt": "首帧 Prompt",
            "title": "任务",
            "source_block_id": "learn-001",
            "rewrite_anchor_phrases": [1, 2],
        }
    )

    with pytest.raises(TaskBatchError, match="rewrite_anchor_phrases"):
        task_batch_from_mapping(payload)
