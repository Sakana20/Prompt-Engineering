from __future__ import annotations

import json
from pathlib import Path

import pytest

from avatar_prompt_pipeline.batch import task_batch_from_mapping
from avatar_prompt_pipeline.feishu_h3 import (
    build_draft_batch,
    load_interface_config,
    write_draft_batch,
)


@pytest.mark.integration
def test_feishu_h3_manifest_is_atomic_and_refuses_overwrite(tmp_path: Path) -> None:
    batch = task_batch_from_mapping(
        {
            "task_name": "draft-batch",
            "category": "水果",
            "tasks": [
                {
                    "task_id": "TASK-001",
                    "marked_script": "完整口播正文",
                    "avatar_prompt": "完整视频生成提示词",
                    "identity_key": "identity",
                    "outfit_key": "outfit",
                    "person_prompt": "真实生活化人物首帧",
                    "title": "水果场景",
                }
            ],
        }
    )
    root = Path(__file__).resolve().parents[2]
    draft = build_draft_batch(
        batch, load_interface_config(root / "configs/interfaces/feishu-h3.json")
    )
    destination = tmp_path / "nested" / "draft.json"

    assert write_draft_batch(destination, draft) == destination
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["batch_fingerprint"] == draft.batch_fingerprint
    assert payload["tasks"][0]["csv_row_number"] == 2
    assert not list(destination.parent.glob("*.tmp"))
    with pytest.raises(FileExistsError, match="拒绝覆盖"):
        write_draft_batch(destination, draft)
