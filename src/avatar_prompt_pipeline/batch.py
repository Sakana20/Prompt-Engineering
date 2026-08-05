from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .models import (
    DEFAULT_LIBTV_FEMALE_VOICE_ID,
    DEFAULT_LIBTV_FEMALE_VOICE_LABEL,
    LibtvOmniHumanTask,
    OceanengineTask,
    VisualProfile,
)

_TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_ALLOWED_BATCH_KEYS = {"schema_version", "task_name", "category", "tasks"}
_ALLOWED_TASK_KEYS = {
    "task_id",
    "marked_script",
    "avatar_prompt",
    "identity_key",
    "outfit_key",
    "person_prompt",
    "image_prompt",
    "title",
    "aspect_ratio",
    "voice",
    "voice_label",
    "voice_id",
    "reference_image_uri",
    "reference_image_url",
    "reference_image_pid",
}


class TaskBatchError(ValueError):
    """Raised when a generated task batch cannot be packaged safely."""


def _clean(value: str) -> str:
    return " ".join(value.replace("\x00", "").split())


def _validate_task_name(value: str) -> str:
    task_name = _clean(value)
    if not task_name:
        raise TaskBatchError("task_name 不能为空")
    if task_name in {".", ".."} or "/" in task_name or "\\" in task_name:
        raise TaskBatchError("task_name 必须是单个安全目录名")
    return task_name


def _expect_mapping(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TaskBatchError(f"{context}必须是 JSON 对象")
    return {str(key): item for key, item in value.items()}


def _expect_string(
    data: dict[str, Any],
    field: str,
    *,
    required: bool = False,
    default: str = "",
    preserve_format: bool = False,
) -> str:
    value = data.get(field, default)
    if not isinstance(value, str):
        raise TaskBatchError(f"{field} 必须是字符串")
    cleaned = value.replace("\x00", "").strip() if preserve_format else _clean(value)
    if required and not cleaned:
        raise TaskBatchError(f"{field} 不能为空")
    return cleaned


@dataclass(frozen=True, slots=True)
class GeneratedTaskRecord:
    task_id: str
    marked_script: str
    avatar_prompt: str
    identity_key: str
    outfit_key: str
    person_prompt: str
    image_prompt: str
    title: str
    aspect_ratio: str = "9:16"
    voice: str = "明朗女声"
    voice_label: str = DEFAULT_LIBTV_FEMALE_VOICE_LABEL
    voice_id: str = DEFAULT_LIBTV_FEMALE_VOICE_ID
    reference_image_uri: str = ""
    reference_image_url: str = ""
    reference_image_pid: str = ""

    def __post_init__(self) -> None:
        if not _TASK_ID_PATTERN.fullmatch(self.task_id):
            raise TaskBatchError("task_id 只能包含字母、数字、短横线和下划线")
        if self.aspect_ratio not in {"9:16", "16:9", "1:1"}:
            raise TaskBatchError("aspect_ratio 必须是 9:16、16:9 或 1:1")

    def visual_profile(self) -> VisualProfile:
        return VisualProfile(identity_key=self.identity_key, outfit_key=self.outfit_key)

    def oceanengine_task(self, *, notes: str) -> OceanengineTask:
        return OceanengineTask(
            task_id=self.task_id,
            person_prompt=self.person_prompt,
            marked_script=self.marked_script,
            aspect_ratio=self.aspect_ratio,
            voice=self.voice,
            title=self.title,
            notes=notes,
            reference_image_uri=self.reference_image_uri,
            reference_image_url=self.reference_image_url,
            reference_image_pid=self.reference_image_pid,
        )

    def libtv_task(self, *, notes: str) -> LibtvOmniHumanTask:
        return LibtvOmniHumanTask(
            task_id=self.task_id,
            image_prompt=self.image_prompt,
            marked_script=self.marked_script,
            title=self.title,
            notes=notes,
            voice_label=self.voice_label,
            voice_id=self.voice_id,
            aspect_ratio=self.aspect_ratio,
        )


@dataclass(frozen=True, slots=True)
class GeneratedTaskBatch:
    schema_version: str
    task_name: str
    category: str
    tasks: tuple[GeneratedTaskRecord, ...]

    def __post_init__(self) -> None:
        _validate_task_name(self.task_name)
        if not self.tasks:
            raise TaskBatchError("tasks 至少需要一个任务")
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise TaskBatchError("task_id 必须在批次内唯一")

    def notes_for(self, index: int) -> str:
        return f"{self.category}+{index + 1}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _task_from_mapping(data: dict[str, Any], *, index: int) -> GeneratedTaskRecord:
    unknown_keys = set(data) - _ALLOWED_TASK_KEYS
    if unknown_keys:
        unknown = "、".join(sorted(unknown_keys))
        raise TaskBatchError(f"tasks[{index}] 包含未知字段：{unknown}")
    person_prompt = _expect_string(data, "person_prompt", required=True, preserve_format=True)
    image_prompt = _expect_string(data, "image_prompt", preserve_format=True) or person_prompt
    return GeneratedTaskRecord(
        task_id=_expect_string(data, "task_id", required=True),
        marked_script=_expect_string(data, "marked_script", required=True, preserve_format=True),
        avatar_prompt=_expect_string(data, "avatar_prompt", required=True, preserve_format=True),
        identity_key=_expect_string(data, "identity_key", required=True),
        outfit_key=_expect_string(data, "outfit_key", required=True),
        person_prompt=person_prompt,
        image_prompt=image_prompt,
        title=_expect_string(data, "title", required=True),
        aspect_ratio=_expect_string(data, "aspect_ratio", default="9:16"),
        voice=_expect_string(data, "voice", default="明朗女声"),
        voice_label=_expect_string(data, "voice_label", default=DEFAULT_LIBTV_FEMALE_VOICE_LABEL),
        voice_id=_expect_string(data, "voice_id", default=DEFAULT_LIBTV_FEMALE_VOICE_ID),
        reference_image_uri=_expect_string(data, "reference_image_uri"),
        reference_image_url=_expect_string(data, "reference_image_url"),
        reference_image_pid=_expect_string(data, "reference_image_pid"),
    )


def task_batch_from_mapping(data: dict[str, Any]) -> GeneratedTaskBatch:
    unknown_keys = set(data) - _ALLOWED_BATCH_KEYS
    if unknown_keys:
        unknown = "、".join(sorted(unknown_keys))
        raise TaskBatchError(f"任务清单包含未知字段：{unknown}")
    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list):
        raise TaskBatchError("tasks 必须是数组")
    tasks = tuple(
        _task_from_mapping(_expect_mapping(item, context=f"tasks[{index}]"), index=index)
        for index, item in enumerate(raw_tasks)
    )
    return GeneratedTaskBatch(
        schema_version=_expect_string(data, "schema_version", default="1.0"),
        task_name=_expect_string(data, "task_name", required=True),
        category=_expect_string(data, "category", required=True),
        tasks=tasks,
    )


def load_task_batch(path: str | Path) -> GeneratedTaskBatch:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TaskBatchError(f"无法读取任务清单：{source}") from exc
    except json.JSONDecodeError as exc:
        raise TaskBatchError(f"任务清单不是有效 JSON：{source}") from exc
    return task_batch_from_mapping(_expect_mapping(data, context="任务清单"))


def task_batch_template(
    *, task_name: str, category: str, count: int, task_prefix: str = "TASK"
) -> dict[str, Any]:
    safe_task_name = _validate_task_name(task_name)
    clean_category = _clean(category)
    clean_prefix = _clean(task_prefix)
    if not clean_category:
        raise TaskBatchError("category 不能为空")
    if count < 1:
        raise TaskBatchError("count 必须大于等于 1")
    if not _TASK_ID_PATTERN.fullmatch(clean_prefix):
        raise TaskBatchError("task_prefix 只能包含字母、数字、短横线和下划线")
    tasks = []
    for index in range(1, count + 1):
        tasks.append(
            {
                "task_id": f"{clean_prefix}-{index:03d}",
                "marked_script": "",
                "avatar_prompt": "",
                "identity_key": "",
                "outfit_key": "",
                "person_prompt": "",
                "title": "",
                "aspect_ratio": "9:16",
                "voice": "明朗女声",
                "voice_label": DEFAULT_LIBTV_FEMALE_VOICE_LABEL,
                "voice_id": DEFAULT_LIBTV_FEMALE_VOICE_ID,
                "reference_image_uri": "",
                "reference_image_url": "",
                "reference_image_pid": "",
            }
        )
    return {
        "schema_version": "1.0",
        "task_name": safe_task_name,
        "category": clean_category,
        "tasks": tasks,
    }


def write_task_batch_template(
    path: str | Path,
    *,
    task_name: str,
    category: str,
    count: int,
    task_prefix: str = "TASK",
) -> Path:
    destination = Path(path)
    if destination.exists():
        raise FileExistsError(f"拒绝覆盖已有文件：{destination}")
    payload = task_batch_template(
        task_name=task_name,
        category=category,
        count=count,
        task_prefix=task_prefix,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary_path.replace(destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return destination
