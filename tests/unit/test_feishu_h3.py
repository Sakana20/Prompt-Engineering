from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from avatar_prompt_pipeline.batch import GeneratedTaskBatch, task_batch_from_mapping
from avatar_prompt_pipeline.feishu_h3 import (
    FeishuH3Error,
    build_draft_batch,
    load_interface_config,
    validate_publish_receipt_mapping,
)

ROOT = Path(__file__).resolve().parents[2]
INTERFACE_PATH = ROOT / "configs/interfaces/feishu-h3.json"


def _batch(*, aspect_ratio: str = "9:16", reference_url: str = "") -> GeneratedTaskBatch:
    return task_batch_from_mapping(
        {
            "task_name": "hami-melon-batch",
            "category": "哈密瓜",
            "tasks": [
                {
                    "task_id": "HM-001",
                    "marked_script": "[[NO_SPLIT]]口播正文[[/NO_SPLIT]]",
                    "avatar_prompt": "人物自然口播，固定机位。",
                    "identity_key": "人物一",
                    "outfit_key": "服装一",
                    "person_prompt": "竖屏真实生活化首帧",
                    "image_prompt": "年轻中国女生坐在餐桌旁，竖屏真实生活化",
                    "title": "哈密瓜居家场景",
                    "aspect_ratio": aspect_ratio,
                    "reference_image_url": reference_url,
                }
            ],
        }
    )


def test_draft_batch_locks_h3_defaults_and_does_not_persist_person_identity() -> None:
    config = load_interface_config(INTERFACE_PATH)

    draft = build_draft_batch(_batch(), config)
    payload: dict[str, Any] = draft.to_dict()
    task = payload["tasks"][0]
    record_values = {cell["field_key"]: cell["value"] for cell in task["feishu"]["record_values"]}

    assert record_values["status"] == ["草稿"]
    assert record_values["duration"] == ["15"]
    assert record_values["aspect_ratio"] == ["9:16"]
    assert record_values["resolution"] == ["720p"]
    assert record_values["generation_count"] == 1
    assert task["dreamina"]["model"] == "seedream_4.0"
    assert task["dreamina"]["resolution"] == "2K"
    assert task["dreamina"]["mode"] == "t2i"
    assert task["feishu"]["submitter"]["binding_key"] == "feishu_h3_submitter"
    assert "陈鼎琦" not in json.dumps(payload, ensure_ascii=False)
    assert payload["paid_image_generation_submitted"] is False
    assert payload["h3_generation_submitted"] is False


def test_draft_batch_selects_i2i_without_persisting_reference_url() -> None:
    draft = build_draft_batch(
        _batch(reference_url="https://private.example/reference.png"),
        load_interface_config(INTERFACE_PATH),
    )
    payload: dict[str, Any] = draft.to_dict()

    assert payload["tasks"][0]["dreamina"]["mode"] == "i2i"
    assert payload["tasks"][0]["dreamina"]["reference_binding_key"] == ("HM-001:reference_image")
    assert "private.example" not in json.dumps(payload)


def test_draft_batch_rejects_non_vertical_tasks() -> None:
    with pytest.raises(FeishuH3Error, match="aspect_ratio"):
        build_draft_batch(_batch(aspect_ratio="16:9"), load_interface_config(INTERFACE_PATH))


def test_receipt_requires_downloaded_files_and_draft_status(tmp_path: Path) -> None:
    csv_path = tmp_path / "batch.csv"
    image_path = tmp_path / "first-frame.png"
    csv_path.write_bytes(b"task_id\nHM-001\n")
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nvalid-image-bytes")

    def file_record(path: Path) -> dict[str, object]:
        return {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    submit_id = "123e4567-e89b-42d3-a456-426614174000"
    receipt: dict[str, Any] = {
        "schema_version": "feishu-h3-publish-receipt/v1",
        "draft_batch_fingerprint": "a" * 64,
        "csv": file_record(csv_path),
        "tasks": [
            {
                "task_id": "HM-001",
                "task_fingerprint": "b" * 64,
                "stage": "draft_created",
                "dreamina": {
                    "project_id": "123e4567-e89b-42d3-a456-426614174001",
                    "node_id": "node_first_frame",
                    "submit_id": submit_id,
                    "operation_ref": submit_id,
                    "resource_id": "123e4567-e89b-42d3-a456-426614174002",
                },
                "first_frame": {**file_record(image_path), "media_type": "image/png"},
                "feishu": {
                    "record_id": "recAbCd123",
                    "attachment_token": "box-token",
                    "status": "草稿",
                },
            }
        ],
    }

    assert validate_publish_receipt_mapping(receipt).is_valid
    receipt["tasks"][0]["feishu"]["status"] = "待生成"
    report = validate_publish_receipt_mapping(receipt)
    assert not report.is_valid
    assert any(issue.code == "UNSAFE_STATUS" for issue in report.issues)
