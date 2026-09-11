from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .batch import GeneratedTaskBatch, GeneratedTaskRecord

FEISHU_H3_INTERFACE_SCHEMA_VERSION = "feishu-h3-interface/v1"
FEISHU_H3_DRAFT_BATCH_SCHEMA_VERSION = "feishu-h3-draft-batch/v1"
FEISHU_H3_RECEIPT_SCHEMA_VERSION = "feishu-h3-publish-receipt/v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_NODE_ID_PATTERN = re.compile(r"^node_[A-Za-z0-9_-]+$")
_RECORD_ID_PATTERN = re.compile(r"^rec[A-Za-z0-9]+$")
_IMAGE_MEDIA_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

_REQUIRED_FIELD_TYPES = {
    "task_name": "text",
    "status": "select",
    "project_name": "text",
    "generation_type": "select",
    "prompt": "text",
    "negative_prompt": "text",
    "duration": "select",
    "aspect_ratio": "select",
    "resolution": "select",
    "generation_count": "number",
    "random_seed": "number",
    "first_frame": "attachment",
    "operations_note": "text",
    "submitter": "user",
}

type CellValue = str | int | tuple[str, ...]


class FeishuH3Error(ValueError):
    """Raised when an H3 draft plan or receipt is unsafe or malformed."""


def _clean(value: str) -> str:
    return value.replace("\x00", "").strip()


def _plain_script(value: str) -> str:
    return _clean(value.replace("[[NO_SPLIT]]", "").replace("[[/NO_SPLIT]]", ""))


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise FeishuH3Error(f"{field} 必须是 JSON 对象")
    return value


def _sequence(value: Any, *, field: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise FeishuH3Error(f"{field} 必须是 JSON 数组")
    return value


def _string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not (cleaned := _clean(value)):
        raise FeishuH3Error(f"{field} 必须是非空字符串")
    return cleaned


def _string_allow_empty(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise FeishuH3Error(f"{field} 必须是字符串")
    return _clean(value)


def _integer(value: Any, *, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise FeishuH3Error(f"{field} 必须是大于等于 {minimum} 的整数")
    return value


def _boolean(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise FeishuH3Error(f"{field} 必须是布尔值")
    return value


def _reject_unknown(data: Mapping[str, Any], allowed: set[str], *, field: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        rendered = "、".join(sorted(str(item) for item in unknown))
        raise FeishuH3Error(f"{field} 包含未知字段：{rendered}")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, payload: object) -> Path:
    if path.exists():
        raise FileExistsError(f"拒绝覆盖已有文件：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return path


@dataclass(frozen=True, slots=True)
class FeishuFieldBinding:
    key: str
    field_id: str
    name: str
    field_type: str

    def __post_init__(self) -> None:
        expected_type = _REQUIRED_FIELD_TYPES.get(self.key)
        if expected_type is None:
            raise FeishuH3Error(f"未知飞书字段绑定：{self.key}")
        if self.field_type != expected_type:
            raise FeishuH3Error(
                f"fields.{self.key}.type 必须是 {expected_type}，实际为 {self.field_type}"
            )
        if not self.field_id.startswith("fld"):
            raise FeishuH3Error(f"fields.{self.key}.id 必须是飞书 field_id")
        if not _clean(self.name):
            raise FeishuH3Error(f"fields.{self.key}.name 不能为空")


@dataclass(frozen=True, slots=True)
class FeishuH3Defaults:
    draft_status: str
    ready_status: str
    generation_type: str
    duration_seconds: str
    aspect_ratio: str
    resolution: str
    generation_count: int
    negative_prompt: str

    def __post_init__(self) -> None:
        expected: tuple[tuple[str, object, object], ...] = (
            ("draft_status", self.draft_status, "草稿"),
            ("ready_status", self.ready_status, "待生成"),
            ("generation_type", self.generation_type, "首帧图生视频"),
            ("duration_seconds", self.duration_seconds, "15"),
            ("aspect_ratio", self.aspect_ratio, "9:16"),
            ("resolution", self.resolution, "720p"),
            ("generation_count", self.generation_count, 1),
        )
        for field, actual, required in expected:
            if actual != required:
                raise FeishuH3Error(f"defaults.{field} 必须固定为 {required}")


@dataclass(frozen=True, slots=True)
class DreaminaFirstFrameConfig:
    requested_model: str
    canonical_model: str
    ratio: str
    resolution: str
    count: int
    prompt_max_chars: int
    modes: tuple[str, ...]
    max_reference_images: int
    discovery_required_before_execution: bool

    def __post_init__(self) -> None:
        expected: tuple[tuple[str, object, object], ...] = (
            ("requested_model", self.requested_model, "seedream4.0"),
            ("canonical_model", self.canonical_model, "seedream_4.0"),
            ("ratio", self.ratio, "9:16"),
            ("resolution", self.resolution, "2K"),
            ("count", self.count, 1),
            ("prompt_max_chars", self.prompt_max_chars, 2000),
            ("modes", self.modes, ("t2i", "i2i")),
            ("max_reference_images", self.max_reference_images, 6),
            ("discovery_required_before_execution", self.discovery_required_before_execution, True),
        )
        for field, actual, required in expected:
            if actual != required:
                raise FeishuH3Error(f"dreamina.{field} 必须固定为 {required}")


@dataclass(frozen=True, slots=True)
class FeishuH3ExecutionBoundary:
    create_csv: bool
    generate_first_frames: bool
    download_first_frames: bool
    create_feishu_drafts: bool
    submit_h3: bool
    requires_user_confirmation_for_image_credits: bool
    requires_user_confirmation_for_h3_submission: bool

    def __post_init__(self) -> None:
        if not all(
            (
                self.create_csv,
                self.generate_first_frames,
                self.download_first_frames,
                self.create_feishu_drafts,
                self.requires_user_confirmation_for_image_credits,
                self.requires_user_confirmation_for_h3_submission,
            )
        ):
            raise FeishuH3Error("execution_boundary 缺少必需的生成、下载或人工确认边界")
        if self.submit_h3:
            raise FeishuH3Error("execution_boundary.submit_h3 必须是 false")


@dataclass(frozen=True, slots=True)
class FeishuH3InterfaceConfig:
    schema_version: str
    interface: str
    base_token: str
    table_id: str
    view_id: str
    submitter_binding_key: str
    fields: tuple[FeishuFieldBinding, ...]
    defaults: FeishuH3Defaults
    dreamina: DreaminaFirstFrameConfig
    execution_boundary: FeishuH3ExecutionBoundary

    def __post_init__(self) -> None:
        if self.schema_version != FEISHU_H3_INTERFACE_SCHEMA_VERSION:
            raise FeishuH3Error(f"schema_version 必须是 {FEISHU_H3_INTERFACE_SCHEMA_VERSION}")
        if self.interface != "feishu_h3":
            raise FeishuH3Error("interface 必须是 feishu_h3")
        if not self.base_token or not self.table_id.startswith("tbl"):
            raise FeishuH3Error("base_token/table_id 不是有效的飞书 Base 坐标")
        if not self.view_id.startswith("vew"):
            raise FeishuH3Error("view_id 必须是飞书 view_id")
        if not self.submitter_binding_key:
            raise FeishuH3Error("submitter_binding_key 不能为空")
        keys = [binding.key for binding in self.fields]
        if len(keys) != len(set(keys)):
            raise FeishuH3Error("fields 不能包含重复 key")
        if set(keys) != set(_REQUIRED_FIELD_TYPES):
            missing = sorted(set(_REQUIRED_FIELD_TYPES) - set(keys))
            extra = sorted(set(keys) - set(_REQUIRED_FIELD_TYPES))
            raise FeishuH3Error(f"fields 不完整：missing={missing}, extra={extra}")

    def field(self, key: str) -> FeishuFieldBinding:
        for binding in self.fields:
            if binding.key == key:
                return binding
        raise AssertionError(f"缺少已校验字段绑定：{key}")


@dataclass(frozen=True, slots=True)
class FeishuCellDraft:
    field_key: str
    field_id: str
    field_name: str
    value: CellValue

    def to_dict(self) -> dict[str, object]:
        value: object = list(self.value) if isinstance(self.value, tuple) else self.value
        return {
            "field_key": self.field_key,
            "field_id": self.field_id,
            "field_name": self.field_name,
            "value": value,
        }


@dataclass(frozen=True, slots=True)
class RuntimeCellBinding:
    field_key: str
    field_id: str
    field_name: str
    binding_key: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class DreaminaFirstFramePlan:
    business_key: str
    title: str
    mode: str
    model: str
    ratio: str
    resolution: str
    count: int
    prompt: str
    reference_binding_key: str
    discovery_required: bool
    credit_confirmation_required_when_quoted: bool
    terminal_resource_required: bool
    download_required: bool


@dataclass(frozen=True, slots=True)
class FeishuH3DraftTask:
    task_id: str
    task_fingerprint: str
    csv_row_number: int
    dreamina: DreaminaFirstFramePlan
    cells: tuple[FeishuCellDraft, ...]
    first_frame: RuntimeCellBinding
    submitter: RuntimeCellBinding

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "task_fingerprint": self.task_fingerprint,
            "csv_row_number": self.csv_row_number,
            "dreamina": asdict(self.dreamina),
            "feishu": {
                "record_values": [cell.to_dict() for cell in self.cells],
                "first_frame": asdict(self.first_frame),
                "submitter": asdict(self.submitter),
            },
        }


@dataclass(frozen=True, slots=True)
class FeishuH3DraftBatch:
    schema_version: str
    source_schema_version: str
    task_name: str
    category: str
    interface_schema_version: str
    base_token: str
    table_id: str
    view_id: str
    batch_fingerprint: str
    tasks: tuple[FeishuH3DraftTask, ...]
    runtime_checks_required: tuple[str, ...]
    paid_image_generation_submitted: bool = False
    h3_generation_submitted: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_schema_version": self.source_schema_version,
            "task_name": self.task_name,
            "category": self.category,
            "interface_schema_version": self.interface_schema_version,
            "base_token": self.base_token,
            "table_id": self.table_id,
            "view_id": self.view_id,
            "batch_fingerprint": self.batch_fingerprint,
            "tasks": [task.to_dict() for task in self.tasks],
            "runtime_checks_required": list(self.runtime_checks_required),
            "paid_image_generation_submitted": self.paid_image_generation_submitted,
            "h3_generation_submitted": self.h3_generation_submitted,
        }


def _load_field_binding(key: str, value: Any) -> FeishuFieldBinding:
    data = _mapping(value, field=f"fields.{key}")
    _reject_unknown(data, {"id", "name", "type"}, field=f"fields.{key}")
    return FeishuFieldBinding(
        key=key,
        field_id=_string(data.get("id"), field=f"fields.{key}.id"),
        name=_string(data.get("name"), field=f"fields.{key}.name"),
        field_type=_string(data.get("type"), field=f"fields.{key}.type"),
    )


def interface_config_from_mapping(value: Any) -> FeishuH3InterfaceConfig:
    root = _mapping(value, field="interface")
    _reject_unknown(
        root,
        {
            "schema_version",
            "interface",
            "base",
            "submitter_binding_key",
            "fields",
            "defaults",
            "dreamina",
            "execution_boundary",
        },
        field="interface",
    )
    base = _mapping(root.get("base"), field="base")
    _reject_unknown(base, {"base_token", "table_id", "view_id"}, field="base")
    fields = _mapping(root.get("fields"), field="fields")
    defaults = _mapping(root.get("defaults"), field="defaults")
    _reject_unknown(
        defaults,
        {
            "draft_status",
            "ready_status",
            "generation_type",
            "duration_seconds",
            "aspect_ratio",
            "resolution",
            "generation_count",
            "negative_prompt",
        },
        field="defaults",
    )
    dreamina = _mapping(root.get("dreamina"), field="dreamina")
    _reject_unknown(
        dreamina,
        {
            "requested_model",
            "canonical_model",
            "ratio",
            "resolution",
            "count",
            "prompt_max_chars",
            "modes",
            "max_reference_images",
            "discovery_required_before_execution",
        },
        field="dreamina",
    )
    modes = tuple(
        _string(item, field="dreamina.modes[]")
        for item in _sequence(dreamina.get("modes"), field="dreamina.modes")
    )
    execution = _mapping(root.get("execution_boundary"), field="execution_boundary")
    execution_keys = {
        "create_csv",
        "generate_first_frames",
        "download_first_frames",
        "create_feishu_drafts",
        "submit_h3",
        "requires_user_confirmation_for_image_credits",
        "requires_user_confirmation_for_h3_submission",
    }
    _reject_unknown(execution, execution_keys, field="execution_boundary")
    return FeishuH3InterfaceConfig(
        schema_version=_string(root.get("schema_version"), field="schema_version"),
        interface=_string(root.get("interface"), field="interface"),
        base_token=_string(base.get("base_token"), field="base.base_token"),
        table_id=_string(base.get("table_id"), field="base.table_id"),
        view_id=_string(base.get("view_id"), field="base.view_id"),
        submitter_binding_key=_string(
            root.get("submitter_binding_key"), field="submitter_binding_key"
        ),
        fields=tuple(_load_field_binding(str(key), item) for key, item in fields.items()),
        defaults=FeishuH3Defaults(
            draft_status=_string(defaults.get("draft_status"), field="defaults.draft_status"),
            ready_status=_string(defaults.get("ready_status"), field="defaults.ready_status"),
            generation_type=_string(
                defaults.get("generation_type"), field="defaults.generation_type"
            ),
            duration_seconds=_string(
                defaults.get("duration_seconds"), field="defaults.duration_seconds"
            ),
            aspect_ratio=_string(defaults.get("aspect_ratio"), field="defaults.aspect_ratio"),
            resolution=_string(defaults.get("resolution"), field="defaults.resolution"),
            generation_count=_integer(
                defaults.get("generation_count"), field="defaults.generation_count", minimum=1
            ),
            negative_prompt=_string_allow_empty(
                defaults.get("negative_prompt"), field="defaults.negative_prompt"
            ),
        ),
        dreamina=DreaminaFirstFrameConfig(
            requested_model=_string(
                dreamina.get("requested_model"), field="dreamina.requested_model"
            ),
            canonical_model=_string(
                dreamina.get("canonical_model"), field="dreamina.canonical_model"
            ),
            ratio=_string(dreamina.get("ratio"), field="dreamina.ratio"),
            resolution=_string(dreamina.get("resolution"), field="dreamina.resolution"),
            count=_integer(dreamina.get("count"), field="dreamina.count", minimum=1),
            prompt_max_chars=_integer(
                dreamina.get("prompt_max_chars"), field="dreamina.prompt_max_chars", minimum=1
            ),
            modes=modes,
            max_reference_images=_integer(
                dreamina.get("max_reference_images"),
                field="dreamina.max_reference_images",
                minimum=1,
            ),
            discovery_required_before_execution=_boolean(
                dreamina.get("discovery_required_before_execution"),
                field="dreamina.discovery_required_before_execution",
            ),
        ),
        execution_boundary=FeishuH3ExecutionBoundary(
            create_csv=_boolean(execution.get("create_csv"), field="execution_boundary.create_csv"),
            generate_first_frames=_boolean(
                execution.get("generate_first_frames"),
                field="execution_boundary.generate_first_frames",
            ),
            download_first_frames=_boolean(
                execution.get("download_first_frames"),
                field="execution_boundary.download_first_frames",
            ),
            create_feishu_drafts=_boolean(
                execution.get("create_feishu_drafts"),
                field="execution_boundary.create_feishu_drafts",
            ),
            submit_h3=_boolean(execution.get("submit_h3"), field="execution_boundary.submit_h3"),
            requires_user_confirmation_for_image_credits=_boolean(
                execution.get("requires_user_confirmation_for_image_credits"),
                field=("execution_boundary.requires_user_confirmation_for_image_credits"),
            ),
            requires_user_confirmation_for_h3_submission=_boolean(
                execution.get("requires_user_confirmation_for_h3_submission"),
                field=("execution_boundary.requires_user_confirmation_for_h3_submission"),
            ),
        ),
    )


def load_interface_config(path: str | Path) -> FeishuH3InterfaceConfig:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FeishuH3Error(f"无法读取飞书 H3 interface：{source}") from exc
    except json.JSONDecodeError as exc:
        raise FeishuH3Error(f"飞书 H3 interface 不是有效 JSON：{source}") from exc
    return interface_config_from_mapping(payload)


def _has_reference_image(task: GeneratedTaskRecord) -> bool:
    return any((task.reference_image_uri, task.reference_image_url, task.reference_image_pid))


def _cell(
    config: FeishuH3InterfaceConfig,
    field_key: str,
    value: CellValue,
) -> FeishuCellDraft:
    binding = config.field(field_key)
    return FeishuCellDraft(
        field_key=field_key,
        field_id=binding.field_id,
        field_name=binding.name,
        value=value,
    )


def _runtime_binding(
    config: FeishuH3InterfaceConfig,
    field_key: str,
    binding_key: str,
) -> RuntimeCellBinding:
    binding = config.field(field_key)
    return RuntimeCellBinding(
        field_key=field_key,
        field_id=binding.field_id,
        field_name=binding.name,
        binding_key=binding_key,
    )


def _task_fingerprint(
    task: GeneratedTaskRecord,
    *,
    batch: GeneratedTaskBatch,
    config: FeishuH3InterfaceConfig,
    reference_image_required: bool,
) -> str:
    return _fingerprint(
        {
            "source_schema_version": batch.schema_version,
            "task_name": batch.task_name,
            "category": batch.category,
            "task_id": task.task_id,
            "marked_script": task.marked_script,
            "avatar_prompt": task.avatar_prompt,
            "image_prompt": task.image_prompt,
            "title": task.title,
            "reference_image_required": reference_image_required,
            "interface_schema_version": config.schema_version,
            "defaults": asdict(config.defaults),
            "dreamina": asdict(config.dreamina),
        }
    )


def build_draft_batch(
    batch: GeneratedTaskBatch,
    config: FeishuH3InterfaceConfig,
) -> FeishuH3DraftBatch:
    tasks: list[FeishuH3DraftTask] = []
    for index, task in enumerate(batch.tasks):
        if task.aspect_ratio != config.defaults.aspect_ratio:
            raise FeishuH3Error(
                f"task_id={task.task_id} 的 aspect_ratio 必须固定为 {config.defaults.aspect_ratio}"
            )
        image_prompt = _clean(task.image_prompt)
        if len(image_prompt) > config.dreamina.prompt_max_chars:
            raise FeishuH3Error(
                f"task_id={task.task_id} 的 image_prompt 超过 Dreamina "
                f"{config.dreamina.prompt_max_chars} 字符上限"
            )
        reference_image_required = _has_reference_image(task)
        mode = "i2i" if reference_image_required else "t2i"
        if mode not in config.dreamina.modes:
            raise FeishuH3Error(f"task_id={task.task_id} 所需 Dreamina mode={mode} 未启用")
        task_fingerprint = _task_fingerprint(
            task,
            batch=batch,
            config=config,
            reference_image_required=reference_image_required,
        )
        h3_prompt = _plain_script(task.avatar_prompt)
        notes = (
            f"task_id={task.task_id}; batch={batch.task_name}; "
            f"schema={batch.schema_version}; fingerprint={task_fingerprint}"
        )
        cells: list[FeishuCellDraft] = [
            _cell(config, "task_name", f"{task.title} [{task.task_id}]"),
            _cell(config, "status", (config.defaults.draft_status,)),
            _cell(config, "project_name", batch.task_name),
            _cell(config, "generation_type", (config.defaults.generation_type,)),
            _cell(config, "prompt", h3_prompt),
            _cell(config, "duration", (config.defaults.duration_seconds,)),
            _cell(config, "aspect_ratio", (config.defaults.aspect_ratio,)),
            _cell(config, "resolution", (config.defaults.resolution,)),
            _cell(config, "generation_count", config.defaults.generation_count),
            _cell(config, "operations_note", notes),
        ]
        if config.defaults.negative_prompt:
            cells.append(_cell(config, "negative_prompt", config.defaults.negative_prompt))
        tasks.append(
            FeishuH3DraftTask(
                task_id=task.task_id,
                task_fingerprint=task_fingerprint,
                csv_row_number=index + 2,
                dreamina=DreaminaFirstFramePlan(
                    business_key=f"{batch.task_name}:{task.task_id}:first-frame",
                    title=f"{task.task_id}-h3-first-frame",
                    mode=mode,
                    model=config.dreamina.canonical_model,
                    ratio=config.dreamina.ratio,
                    resolution=config.dreamina.resolution,
                    count=config.dreamina.count,
                    prompt=image_prompt,
                    reference_binding_key=(
                        f"{task.task_id}:reference_image" if reference_image_required else ""
                    ),
                    discovery_required=config.dreamina.discovery_required_before_execution,
                    credit_confirmation_required_when_quoted=True,
                    terminal_resource_required=True,
                    download_required=True,
                ),
                cells=tuple(cells),
                first_frame=_runtime_binding(
                    config,
                    "first_frame",
                    f"{task.task_id}:dreamina_downloaded_first_frame",
                ),
                submitter=_runtime_binding(
                    config,
                    "submitter",
                    config.submitter_binding_key,
                ),
            )
        )
    batch_fingerprint = _fingerprint(
        {
            "schema_version": FEISHU_H3_DRAFT_BATCH_SCHEMA_VERSION,
            "source_schema_version": batch.schema_version,
            "task_name": batch.task_name,
            "category": batch.category,
            "interface_schema_version": config.schema_version,
            "base_token": config.base_token,
            "table_id": config.table_id,
            "tasks": [task.task_fingerprint for task in tasks],
        }
    )
    return FeishuH3DraftBatch(
        schema_version=FEISHU_H3_DRAFT_BATCH_SCHEMA_VERSION,
        source_schema_version=batch.schema_version,
        task_name=batch.task_name,
        category=batch.category,
        interface_schema_version=config.schema_version,
        base_token=config.base_token,
        table_id=config.table_id,
        view_id=config.view_id,
        batch_fingerprint=batch_fingerprint,
        tasks=tuple(tasks),
        runtime_checks_required=(
            "dreamina_schema_and_seedream_4.0_catalog",
            "dreamina_account_and_credit_quote",
            "feishu_base_field_schema_and_enum_options",
            "feishu_submitter_unique_resolution",
            "feishu_duplicate_task_fingerprint",
        ),
    )


def write_draft_batch(path: str | Path, batch: FeishuH3DraftBatch) -> Path:
    return _atomic_write_json(Path(path), batch.to_dict())


@dataclass(frozen=True, slots=True)
class ReceiptValidationIssue:
    code: str
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class ReceiptValidationReport:
    schema_version: str
    task_count: int
    issues: tuple[ReceiptValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "task_count": self.task_count,
            "is_valid": self.is_valid,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _validate_file(
    data: Mapping[str, Any],
    *,
    field: str,
    issues: list[ReceiptValidationIssue],
    additional_fields: frozenset[str] = frozenset(),
) -> None:
    allowed = {"path", "size_bytes", "sha256"} | additional_fields
    unknown = set(data) - allowed
    if unknown:
        issues.append(
            ReceiptValidationIssue(
                "UNKNOWN_FIELD", field, f"包含未知字段：{'、'.join(sorted(unknown))}"
            )
        )
    path_value = data.get("path")
    sha_value = data.get("sha256")
    size_value = data.get("size_bytes")
    if not isinstance(path_value, str) or not path_value.strip():
        issues.append(ReceiptValidationIssue("INVALID_PATH", f"{field}.path", "路径不能为空"))
        return
    path = Path(path_value)
    if not path.is_file():
        issues.append(ReceiptValidationIssue("FILE_NOT_FOUND", f"{field}.path", str(path)))
        return
    actual_size = path.stat().st_size
    if not isinstance(size_value, int) or isinstance(size_value, bool) or size_value <= 0:
        issues.append(ReceiptValidationIssue("INVALID_SIZE", f"{field}.size_bytes", "必须是正整数"))
    elif actual_size != size_value:
        issues.append(
            ReceiptValidationIssue(
                "SIZE_MISMATCH",
                f"{field}.size_bytes",
                f"声明 {size_value}，实际 {actual_size}",
            )
        )
    if not isinstance(sha_value, str) or not _SHA256_PATTERN.fullmatch(sha_value):
        issues.append(
            ReceiptValidationIssue("INVALID_SHA256", f"{field}.sha256", "必须是小写 SHA-256")
        )
    elif _file_sha256(path) != sha_value:
        issues.append(
            ReceiptValidationIssue("SHA256_MISMATCH", f"{field}.sha256", "文件摘要不一致")
        )


def _detected_image_media_type(path: Path) -> str:
    with path.open("rb") as stream:
        header = stream.read(12)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    return ""


def _validate_image_file(
    data: Mapping[str, Any],
    *,
    field: str,
    issues: list[ReceiptValidationIssue],
) -> None:
    _validate_file(
        data,
        field=field,
        issues=issues,
        additional_fields=frozenset({"media_type"}),
    )
    media_type = data.get("media_type")
    if not isinstance(media_type, str) or media_type not in _IMAGE_MEDIA_TYPES:
        issues.append(
            ReceiptValidationIssue(
                "INVALID_IMAGE_MEDIA_TYPE",
                f"{field}.media_type",
                "必须是 image/png、image/jpeg 或 image/webp",
            )
        )
        return
    path_value = data.get("path")
    if not isinstance(path_value, str) or not Path(path_value).is_file():
        return
    detected = _detected_image_media_type(Path(path_value))
    if detected != media_type:
        issues.append(
            ReceiptValidationIssue(
                "IMAGE_FORMAT_MISMATCH",
                f"{field}.media_type",
                f"声明 {media_type}，文件签名为 {detected or 'unknown'}",
            )
        )


def _match_or_issue(
    value: Any,
    pattern: re.Pattern[str],
    *,
    field: str,
    code: str,
    issues: list[ReceiptValidationIssue],
) -> None:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        issues.append(ReceiptValidationIssue(code, field, "格式不合法"))


def validate_publish_receipt_mapping(value: Any) -> ReceiptValidationReport:
    issues: list[ReceiptValidationIssue] = []
    try:
        root = _mapping(value, field="receipt")
    except FeishuH3Error as exc:
        return ReceiptValidationReport(
            schema_version=FEISHU_H3_RECEIPT_SCHEMA_VERSION,
            task_count=0,
            issues=(ReceiptValidationIssue("INVALID_ROOT", "receipt", str(exc)),),
        )
    allowed_root = {"schema_version", "draft_batch_fingerprint", "csv", "tasks"}
    unknown_root = set(root) - allowed_root
    if unknown_root:
        issues.append(
            ReceiptValidationIssue(
                "UNKNOWN_FIELD", "receipt", f"包含未知字段：{'、'.join(sorted(unknown_root))}"
            )
        )
    if root.get("schema_version") != FEISHU_H3_RECEIPT_SCHEMA_VERSION:
        issues.append(
            ReceiptValidationIssue(
                "INVALID_SCHEMA_VERSION",
                "schema_version",
                f"必须是 {FEISHU_H3_RECEIPT_SCHEMA_VERSION}",
            )
        )
    _match_or_issue(
        root.get("draft_batch_fingerprint"),
        _SHA256_PATTERN,
        field="draft_batch_fingerprint",
        code="INVALID_FINGERPRINT",
        issues=issues,
    )
    csv_value = root.get("csv")
    if isinstance(csv_value, dict):
        _validate_file(csv_value, field="csv", issues=issues)
    else:
        issues.append(ReceiptValidationIssue("INVALID_CSV", "csv", "必须是 JSON 对象"))
    raw_tasks = root.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        issues.append(ReceiptValidationIssue("INVALID_TASKS", "tasks", "必须是非空数组"))
        raw_tasks = []
    seen_task_ids: set[str] = set()
    for index, raw_task in enumerate(raw_tasks):
        field = f"tasks[{index}]"
        if not isinstance(raw_task, dict):
            issues.append(ReceiptValidationIssue("INVALID_TASK", field, "必须是 JSON 对象"))
            continue
        allowed_task = {
            "task_id",
            "task_fingerprint",
            "stage",
            "dreamina",
            "first_frame",
            "feishu",
        }
        unknown_task = set(raw_task) - allowed_task
        if unknown_task:
            issues.append(
                ReceiptValidationIssue(
                    "UNKNOWN_FIELD", field, f"包含未知字段：{'、'.join(sorted(unknown_task))}"
                )
            )
        task_id = raw_task.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            issues.append(ReceiptValidationIssue("INVALID_TASK_ID", f"{field}.task_id", "不能为空"))
        elif task_id in seen_task_ids:
            issues.append(ReceiptValidationIssue("DUPLICATE_TASK_ID", f"{field}.task_id", task_id))
        else:
            seen_task_ids.add(task_id)
        _match_or_issue(
            raw_task.get("task_fingerprint"),
            _SHA256_PATTERN,
            field=f"{field}.task_fingerprint",
            code="INVALID_FINGERPRINT",
            issues=issues,
        )
        if raw_task.get("stage") != "draft_created":
            issues.append(
                ReceiptValidationIssue("INCOMPLETE_STAGE", f"{field}.stage", "必须是 draft_created")
            )
        dreamina = raw_task.get("dreamina")
        if isinstance(dreamina, dict):
            allowed_dreamina = {
                "project_id",
                "node_id",
                "submit_id",
                "operation_ref",
                "resource_id",
            }
            if unknown := set(dreamina) - allowed_dreamina:
                issues.append(
                    ReceiptValidationIssue(
                        "UNKNOWN_FIELD",
                        f"{field}.dreamina",
                        f"包含未知字段：{'、'.join(sorted(unknown))}",
                    )
                )
            _match_or_issue(
                dreamina.get("project_id"),
                _UUID_PATTERN,
                field=f"{field}.dreamina.project_id",
                code="INVALID_PROJECT_ID",
                issues=issues,
            )
            _match_or_issue(
                dreamina.get("node_id"),
                _NODE_ID_PATTERN,
                field=f"{field}.dreamina.node_id",
                code="INVALID_NODE_ID",
                issues=issues,
            )
            _match_or_issue(
                dreamina.get("submit_id"),
                _UUID_PATTERN,
                field=f"{field}.dreamina.submit_id",
                code="INVALID_SUBMIT_ID",
                issues=issues,
            )
            _match_or_issue(
                dreamina.get("operation_ref"),
                _UUID_PATTERN,
                field=f"{field}.dreamina.operation_ref",
                code="INVALID_OPERATION_REF",
                issues=issues,
            )
            _match_or_issue(
                dreamina.get("resource_id"),
                _UUID_PATTERN,
                field=f"{field}.dreamina.resource_id",
                code="INVALID_RESOURCE_ID",
                issues=issues,
            )
            if dreamina.get("submit_id") != dreamina.get("operation_ref"):
                issues.append(
                    ReceiptValidationIssue(
                        "OPERATION_REF_MISMATCH",
                        f"{field}.dreamina.operation_ref",
                        "必须与 submit_id 相同",
                    )
                )
        else:
            issues.append(
                ReceiptValidationIssue("INVALID_DREAMINA", f"{field}.dreamina", "必须是对象")
            )
        first_frame = raw_task.get("first_frame")
        if isinstance(first_frame, dict):
            _validate_image_file(first_frame, field=f"{field}.first_frame", issues=issues)
        else:
            issues.append(
                ReceiptValidationIssue("INVALID_FIRST_FRAME", f"{field}.first_frame", "必须是对象")
            )
        feishu = raw_task.get("feishu")
        if isinstance(feishu, dict):
            allowed_feishu = {"record_id", "attachment_token", "status"}
            if unknown := set(feishu) - allowed_feishu:
                issues.append(
                    ReceiptValidationIssue(
                        "UNKNOWN_FIELD",
                        f"{field}.feishu",
                        f"包含未知字段：{'、'.join(sorted(unknown))}",
                    )
                )
            _match_or_issue(
                feishu.get("record_id"),
                _RECORD_ID_PATTERN,
                field=f"{field}.feishu.record_id",
                code="INVALID_RECORD_ID",
                issues=issues,
            )
            if not isinstance(feishu.get("attachment_token"), str) or not feishu.get(
                "attachment_token"
            ):
                issues.append(
                    ReceiptValidationIssue(
                        "INVALID_ATTACHMENT_TOKEN",
                        f"{field}.feishu.attachment_token",
                        "不能为空",
                    )
                )
            if feishu.get("status") != "草稿":
                issues.append(
                    ReceiptValidationIssue("UNSAFE_STATUS", f"{field}.feishu.status", "必须是草稿")
                )
        else:
            issues.append(ReceiptValidationIssue("INVALID_FEISHU", f"{field}.feishu", "必须是对象"))
    return ReceiptValidationReport(
        schema_version=FEISHU_H3_RECEIPT_SCHEMA_VERSION,
        task_count=len(raw_tasks),
        issues=tuple(issues),
    )


def validate_publish_receipt(path: str | Path) -> ReceiptValidationReport:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FeishuH3Error(f"无法读取飞书 H3 发布回执：{source}") from exc
    except json.JSONDecodeError as exc:
        raise FeishuH3Error(f"飞书 H3 发布回执不是有效 JSON：{source}") from exc
    return validate_publish_receipt_mapping(payload)
