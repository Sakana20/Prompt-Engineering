from __future__ import annotations

import copy
import csv
import json
import os
import tempfile
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import TextIO

from .models import (
    DEFAULT_LIBTV_FEMALE_VOICE_ID,
    DEFAULT_LIBTV_FEMALE_VOICE_LABEL,
    DEFAULT_LIBTV_MALE_VOICE_ID,
    DEFAULT_LIBTV_MALE_VOICE_LABEL,
    DEFAULT_LIBTV_VOICE_SPEED,
    DEFAULT_LIBTV_VOICE_VOLUME,
    CampaignSpec,
    LibtvOmniHumanTask,
    OceanengineTask,
)
from .presets import TAOBAO_DEFAULT_CAMPAIGN
from .validation import strip_no_split_markers, validate_copy

DEFAULT_OUTPUT_ROOT = Path("/Users/sakana/Desktop/Work/Codex/Prompt Engineering")

CSV_FIELDS = (
    "task_id",
    "person_prompt",
    "script",
    "aspect_ratio",
    "voice",
    "title",
    "notes",
)

LIBTV_OMNIHUMAN_CSV_FIELDS = (
    "task_id",
    "title",
    "notes",
    "image_prompt",
    "audio_prompt",
    "voice_label",
    "voice_id",
    "aspect_ratio",
)

LIBTV_OMNIHUMAN_INTERFACE_CONFIG: dict[str, object] = {
    "schema_version": "libtv-interface-config/v1",
    "interface": "libtv_omnihuman",
    "task_package": {
        "csv": "<task>.libtv.csv",
        "plan": "<task>.libtv.plan.md",
    },
    "defaults": {
        "target_width": 720,
        "target_height": 1280,
        "target_resolution": "720x1280",
        "voice_labels": {
            "female": DEFAULT_LIBTV_FEMALE_VOICE_LABEL,
            "male": DEFAULT_LIBTV_MALE_VOICE_LABEL,
        },
        "voice_ids": {
            DEFAULT_LIBTV_FEMALE_VOICE_LABEL: DEFAULT_LIBTV_FEMALE_VOICE_ID,
            DEFAULT_LIBTV_MALE_VOICE_LABEL: DEFAULT_LIBTV_MALE_VOICE_ID,
        },
        "voice_constraints": {
            "speed": DEFAULT_LIBTV_VOICE_SPEED,
            "volume": DEFAULT_LIBTV_VOICE_VOLUME,
        },
    },
    "nodes": {
        "image": {
            "name_template": "{task_id}-image",
            "type": "image",
            "model": "Z-image Turbo",
            "params": {
                "ratio": "9:16",
                "quality": "1K",
                "count": 1,
            },
            "prompt_field": "image_prompt",
        },
        "audio": {
            "name_template": "{task_id}-audio",
            "type": "audio",
            "model": "Minimax-speech-2.8-turbo",
            "params": {
                "speed": DEFAULT_LIBTV_VOICE_SPEED,
                "voicePitch": 0,
                "vol": DEFAULT_LIBTV_VOICE_VOLUME,
            },
            "prompt_field": "audio_prompt",
            "voice_label_field": "voice_label",
            "voice_id_field": "voice_id",
        },
        "video": {
            "name_template": "{task_id}-omnihuman-video",
            "type": "video",
            "model": "OmniHuman 1.5",
            "modeType": "audio2video",
            "inputs": ["image", "audio"],
            "params": {
                "ratio": "auto",
                "resolution": "auto",
                "fastMode": 0,
                "count": 1,
            },
        },
    },
    "acceptance": {
        "require_video_resolution": "720x1280",
        "check_actual_media_size": True,
        "on_resolution_mismatch": "fail_or_postprocess",
    },
    "execution_boundary": {
        "create_canvas": False,
        "create_nodes": False,
        "run_nodes": False,
        "requires_user_confirmation_for_paid_generation": True,
    },
}


def default_task_directory(task_name: str, *, date: str | None = None) -> Path:
    output_date = date or datetime.now().astimezone().strftime("%Y%m%d")
    return DEFAULT_OUTPUT_ROOT / output_date / task_name


def default_manuscript_path(
    task_name: str,
    task_id: str,
    *,
    date: str | None = None,
) -> Path:
    return default_task_directory(task_name, date=date) / f"{task_id}.smartsplit.txt"


def default_oceanengine_csv_path(task_name: str, *, date: str | None = None) -> Path:
    return default_task_directory(task_name, date=date) / f"{task_name}.csv"


def default_libtv_omnihuman_csv_path(task_name: str, *, date: str | None = None) -> Path:
    return default_task_directory(task_name, date=date) / f"{task_name}.libtv.csv"


def default_libtv_omnihuman_interface_path(task_name: str, *, date: str | None = None) -> Path:
    return default_task_directory(task_name, date=date) / f"{task_name}.libtv.interface.json"


def default_libtv_omnihuman_plan_path(task_name: str, *, date: str | None = None) -> Path:
    return default_task_directory(task_name, date=date) / f"{task_name}.libtv.plan.md"


def _write_atomic(destination: Path, writer: Callable[[TextIO], None]) -> Path:
    if destination.exists():
        raise FileExistsError(f"拒绝覆盖已有文件：{destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer(handle)
        temporary_path.replace(destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return destination


def _libtv_task_name_from_interface_path(path: Path) -> str:
    suffix = ".libtv.interface.json"
    if path.name.endswith(suffix):
        return path.name[: -len(suffix)]
    return path.stem


def libtv_omnihuman_interface_config(task_name: str) -> dict[str, object]:
    config = copy.deepcopy(LIBTV_OMNIHUMAN_INTERFACE_CONFIG)
    task_package = config["task_package"]
    if not isinstance(task_package, dict):
        raise TypeError("LibTV interface config task_package must be a dict")
    task_package["csv"] = f"{task_name}.libtv.csv"
    task_package["plan"] = f"{task_name}.libtv.plan.md"
    return config


def write_segmentation_manuscript(
    path: str | Path,
    marked_script: str,
    campaign: CampaignSpec = TAOBAO_DEFAULT_CAMPAIGN,
) -> Path:
    report = validate_copy(marked_script, campaign)
    if not report.is_valid:
        issue_codes = ", ".join(issue.code for issue in report.issues)
        raise ValueError(f"带标记稿件未通过口播校验：{issue_codes}")

    def write(handle: TextIO) -> None:
        handle.write(marked_script.strip())
        handle.write("\n")

    return _write_atomic(Path(path), write)


def write_libtv_omnihuman_csv(
    path: str | Path,
    tasks: Sequence[LibtvOmniHumanTask],
    campaign: CampaignSpec = TAOBAO_DEFAULT_CAMPAIGN,
) -> Path:
    if not tasks:
        raise ValueError("LibTV OmniHuman CSV 至少需要一个任务")
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("LibTV OmniHuman CSV 的 task_id 必须唯一")

    def write(handle: TextIO) -> None:
        csv_writer = csv.DictWriter(handle, fieldnames=LIBTV_OMNIHUMAN_CSV_FIELDS)
        csv_writer.writeheader()
        for task in tasks:
            report = validate_copy(task.marked_script, campaign)
            if not report.is_valid:
                issue_codes = ", ".join(issue.code for issue in report.issues)
                raise ValueError(f"任务 {task.task_id} 的口播未通过校验：{issue_codes}")
            csv_writer.writerow(
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "notes": task.notes,
                    "image_prompt": task.image_prompt,
                    "audio_prompt": strip_no_split_markers(task.marked_script),
                    "voice_label": task.voice_label,
                    "voice_id": task.voice_id,
                    "aspect_ratio": task.aspect_ratio,
                }
            )

    return _write_atomic(Path(path), write)


def write_libtv_omnihuman_interface_config(path: str | Path) -> Path:
    destination = Path(path)
    task_name = _libtv_task_name_from_interface_path(destination)

    def write(handle: TextIO) -> None:
        json.dump(
            libtv_omnihuman_interface_config(task_name),
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")

    return _write_atomic(destination, write)


def write_libtv_omnihuman_plan(
    path: str | Path,
    tasks: Sequence[LibtvOmniHumanTask],
) -> Path:
    if not tasks:
        raise ValueError("LibTV OmniHuman plan 至少需要一个任务")

    def write(handle: TextIO) -> None:
        handle.write("# LibTV OmniHuman 任务计划\n\n")
        handle.write("接口配置：`<task>.libtv.interface.json`\n\n")
        handle.write("执行边界：本计划不创建 LibTV 画布、不创建节点、不运行生成任务。\n\n")
        for task in tasks:
            handle.write(f"## {task.task_id}\n\n")
            handle.write(f"- title: {task.title}\n")
            handle.write(f"- notes: {task.notes}\n")
            handle.write(f"- voice_label: {task.voice_label}\n")
            handle.write(f"- voice_id: {task.voice_id or '待确认'}\n")
            handle.write(f"- aspect_ratio: {task.aspect_ratio}\n\n")
            handle.write("image:\n")
            handle.write(f"  node: {task.task_id}-image\n")
            handle.write("  source: interface JSON `nodes.image`\n")
            handle.write(f"  prompt: {task.image_prompt}\n\n")
            handle.write("audio:\n")
            handle.write(f"  node: {task.task_id}-audio\n")
            handle.write("  source: interface JSON `nodes.audio`\n")
            handle.write(f"  script: {strip_no_split_markers(task.marked_script)}\n\n")
            handle.write("video:\n")
            handle.write(f"  node: {task.task_id}-omnihuman-video\n")
            handle.write("  source: interface JSON `nodes.video`\n")
            handle.write("  inputs:\n")
            handle.write(f"    - {task.task_id}-image\n")
            handle.write(f"    - {task.task_id}-audio\n\n")

    return _write_atomic(Path(path), write)


def write_oceanengine_csv(
    path: str | Path,
    tasks: Sequence[OceanengineTask],
    campaign: CampaignSpec = TAOBAO_DEFAULT_CAMPAIGN,
) -> Path:
    if not tasks:
        raise ValueError("即创 CSV 至少需要一个任务")
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("即创 CSV 的 task_id 必须唯一")

    def write(handle: TextIO) -> None:
        csv_writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        csv_writer.writeheader()
        for task in tasks:
            report = validate_copy(task.marked_script, campaign)
            if not report.is_valid:
                issue_codes = ", ".join(issue.code for issue in report.issues)
                raise ValueError(f"任务 {task.task_id} 的口播未通过校验：{issue_codes}")
            csv_writer.writerow(
                {
                    "task_id": task.task_id,
                    "person_prompt": task.person_prompt,
                    "script": strip_no_split_markers(task.marked_script),
                    "aspect_ratio": task.aspect_ratio,
                    "voice": task.voice,
                    "title": task.title,
                    "notes": task.notes,
                }
            )

    return _write_atomic(Path(path), write)
