from __future__ import annotations

import csv
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    DREAMINA_REQUIRED_FULL_SCRIPT_PHRASE,
    DREAMINA_REQUIRED_PRODUCT_INTERACTION_PHRASE,
    DREAMINA_REQUIRED_VIDEO_PROMPT_PHRASE,
)

IMAGE_NODE_ID_PLACEHOLDER = "{image_node_id}"
_NODE_ID_PATTERN = re.compile(r"^node_[A-Za-z0-9_-]+$")
_DREAMINA_VIDEO_REPLACEMENTS = (
    ("人物不看商品、不接触商品", "人物不看商品"),
    ("人物不看商品，不接触商品", "人物不看商品"),
    ("人物不看商品且不接触商品", "人物不看商品"),
    ("手机固定拍摄", "手机实拍"),
    ("固定中景", "中景"),
)
_DREAMINA_VIDEO_REMOVED_RESTRICTIONS = (
    "人物不接触商品",
    "人物不触碰商品",
    "不得触碰商品",
    "不能触碰商品",
    "不接触商品",
    "不触碰商品",
    "固定机位",
    "镜头固定",
    "禁止切镜",
    "不允许切镜",
    "不切镜",
    "一镜到底",
    "禁止运镜",
    "不允许运镜",
    "不运镜",
    "不推拉摇移",
    "商品不由人物手持",
    "禁止手持商品",
    "不得手持商品",
    "不能手持商品",
    "不拿起商品",
    "不得拿起商品",
    "不能拿起商品",
    "不递近镜头",
    "不用手持续展示包装",
    "远离人物双手",
    "商品只提供环境信息",
)


class DreaminaAdapterError(ValueError):
    """Raised when a Dreamina package cannot safely produce a video node draft."""


@dataclass(frozen=True, slots=True)
class DreaminaVideoNodeDraft:
    project_id: str
    task_id: str
    title: str
    image_node_id: str
    prompt: str
    mode: str
    model: str
    ratio: str
    resolution: str
    duration_seconds: float
    count: int

    def command(self, *, dry_run: bool = False) -> tuple[str, ...]:
        command = (
            "dreamina-canvas",
            "node",
            "create",
            "video",
            "--project-id",
            self.project_id,
            "--title",
            self.title,
            "--mode",
            self.mode,
            "--model",
            self.model,
            "--ratio",
            self.ratio,
            "--resolution",
            self.resolution,
            "--duration",
            str(self.duration_seconds),
            "--count",
            str(self.count),
            "--prompt",
            self.prompt,
            "--ref",
            f"node:{self.image_node_id}",
        )
        return (*command, "--dry-run") if dry_run else command


def _require_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise DreaminaAdapterError(f"Dreamina interface {field} 必须是 JSON 对象")
    return value


def _require_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DreaminaAdapterError(f"{field} 必须是非空字符串")
    return value.strip()


def _validate_node_id(value: str, *, field: str) -> str:
    node_id = _require_string(value, field=field)
    if not _NODE_ID_PATTERN.fullmatch(node_id):
        raise DreaminaAdapterError(f"{field} 必须是 Dreamina Node ID")
    return node_id


def remove_dreamina_video_restrictions(prompt: str) -> str:
    """Remove constraints that apply to static prompts but not Dreamina video synthesis."""
    cleaned = " ".join(prompt.replace("\x00", "").split())
    for old, new in _DREAMINA_VIDEO_REPLACEMENTS:
        cleaned = cleaned.replace(old, new)
    for phrase in _DREAMINA_VIDEO_REMOVED_RESTRICTIONS:
        cleaned = cleaned.replace(phrase, "")
    cleaned = re.sub(r"[，,]{2,}", "，", cleaned)
    cleaned = re.sub(r"[；;]{2,}", "；", cleaned)
    cleaned = cleaned.replace("，。", "。").replace("；。", "。").replace("。，", "。")
    return cleaned.strip(" ，,；;。")


def render_dreamina_video_prompt(prompt_template: str, *, image_node_id: str) -> str:
    node_id = _validate_node_id(image_node_id, field="image_node_id")
    cleaned_template = remove_dreamina_video_restrictions(prompt_template)
    if cleaned_template.count(IMAGE_NODE_ID_PLACEHOLDER) != 1:
        raise DreaminaAdapterError("video_prompt 必须且只能包含一个 {image_node_id} 占位符")
    prompt = cleaned_template.replace(IMAGE_NODE_ID_PLACEHOLDER, node_id)
    expected_reference = f"{{{{node:{node_id}}}}}"
    if expected_reference not in prompt:
        raise DreaminaAdapterError("video_prompt 未形成有效的图片节点正文引用")
    required_phrases = (
        DREAMINA_REQUIRED_FULL_SCRIPT_PHRASE,
        DREAMINA_REQUIRED_PRODUCT_INTERACTION_PHRASE,
        DREAMINA_REQUIRED_VIDEO_PROMPT_PHRASE,
    )
    missing = [phrase for phrase in required_phrases if phrase not in prompt]
    if missing:
        raise DreaminaAdapterError("video_prompt 缺少必检短语：" + "、".join(missing))
    return prompt


def _load_task_row(csv_path: Path, task_id: str) -> Mapping[str, str]:
    try:
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = [row for row in csv.DictReader(handle) if row.get("task_id") == task_id]
    except OSError as exc:
        raise DreaminaAdapterError(f"无法读取 Dreamina CSV：{csv_path}") from exc
    if len(rows) != 1:
        raise DreaminaAdapterError(f"Dreamina CSV 必须且只能包含一条 task_id={task_id} 的记录")
    return rows[0]


def _load_video_config(interface_path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(interface_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DreaminaAdapterError(f"无法读取 Dreamina interface：{interface_path}") from exc
    except json.JSONDecodeError as exc:
        raise DreaminaAdapterError(f"Dreamina interface 不是有效 JSON：{interface_path}") from exc
    root = _require_mapping(payload, field="root")
    if root.get("interface") != "dreamina_canvas":
        raise DreaminaAdapterError("interface 必须是 dreamina_canvas")
    nodes = _require_mapping(root.get("nodes"), field="nodes")
    return _require_mapping(nodes.get("video"), field="nodes.video")


def load_dreamina_video_node_draft(
    *,
    csv_path: str | Path,
    interface_path: str | Path,
    task_id: str,
    project_id: str,
    image_node_id: str,
    duration_seconds: float,
) -> DreaminaVideoNodeDraft:
    if not 4 <= duration_seconds <= 30:
        raise DreaminaAdapterError("duration_seconds 必须在 Dreamina 当前视频契约的 4-30 秒范围内")
    row = _load_task_row(Path(csv_path), task_id)
    video = _load_video_config(Path(interface_path))
    prompt = render_dreamina_video_prompt(
        _require_string(row.get("video_prompt"), field="video_prompt"),
        image_node_id=image_node_id,
    )
    return DreaminaVideoNodeDraft(
        project_id=_require_string(project_id, field="project_id"),
        task_id=task_id,
        title=_require_string(row.get("title"), field="title"),
        image_node_id=_validate_node_id(image_node_id, field="image_node_id"),
        prompt=prompt,
        mode=_require_string(video.get("mode"), field="nodes.video.mode"),
        model=_require_string(video.get("model"), field="nodes.video.model"),
        ratio=_require_string(row.get("aspect_ratio"), field="aspect_ratio"),
        resolution=_require_string(video.get("resolution"), field="nodes.video.resolution"),
        duration_seconds=duration_seconds,
        count=int(video.get("count", 1)),
    )


def save_dreamina_video_node(
    draft: DreaminaVideoNodeDraft,
    *,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        draft.command(dry_run=dry_run),
        check=False,
        capture_output=True,
        text=True,
    )


def render_command(command: Sequence[str]) -> list[str]:
    """Return a JSON-safe argv list without shell quoting or execution."""
    return list(command)
