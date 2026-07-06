from __future__ import annotations

import csv
import os
import tempfile
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import TextIO

from .models import CampaignSpec, OceanengineTask
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
