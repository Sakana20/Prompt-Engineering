from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from .models import (
    CandidateKind,
    CopyLearningCandidate,
    LearningCandidate,
    LearningStatus,
    PersonPromptLearningCandidate,
)
from .store import LearningStore, RevisionConflictError, transactional_replace
from .validation import LearningValidationError, allowed_transition, detect_risks

BLOCK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,95}$")
COPY_RESOURCE_NAME = "volume-copy-source-blocks.md"
PUBLISHED_COPY_SECTION_HEADING = "## 审核发布的网页学习块"
FIXED_PERSON_CONSTRAINTS = (
    "竖屏9:16",
    "固定中景",
    "直视镜头",
    "商品不由人物手持",
    "人物不看商品",
    "人物不接触商品",
    "非商品区域无logo",
    "无字幕",
)


@dataclass(frozen=True, slots=True)
class CopySlot:
    name: str
    value_type: str


@dataclass(frozen=True, slots=True)
class CopyDiversityTags:
    opening_type: str
    rhythm: str
    need: str
    emotion: str


@dataclass(frozen=True, slots=True)
class LearnedCopyBlock:
    block_id: str
    template: str
    slots: tuple[CopySlot, ...]
    category_families: tuple[str, ...]
    consumption_needs: tuple[str, ...]
    seasons: tuple[str, ...]
    allowed_modes: tuple[str, ...]
    removed_risks: tuple[str, ...]
    diversity_tags: CopyDiversityTags
    solid_food_only: bool = False

    def registry_dict(self, source_candidate_id: str) -> dict[str, object]:
        return {
            "block_id": self.block_id,
            "source_candidate_id": source_candidate_id,
            "template": self.template,
            "slots": [{"name": slot.name, "value_type": slot.value_type} for slot in self.slots],
            "category_families": list(self.category_families),
            "consumption_needs": list(self.consumption_needs),
            "seasons": list(self.seasons),
            "allowed_modes": list(self.allowed_modes),
            "removed_risks": list(self.removed_risks),
            "diversity_tags": {
                "opening_type": self.diversity_tags.opening_type,
                "rhythm": self.diversity_tags.rhythm,
                "need": self.diversity_tags.need,
                "emotion": self.diversity_tags.emotion,
            },
            "solid_food_only": self.solid_food_only,
            "minimum_source_slot_values": max(1, len(self.slots)),
        }


@dataclass(frozen=True, slots=True)
class LearnedPersonBlock:
    block_id: str
    block_type: str
    description: str
    compatible_with: tuple[str, ...]
    incompatible_with: tuple[str, ...]
    removed_constraints: tuple[str, ...]
    removed_risks: tuple[str, ...]
    diversity_tags: tuple[str, ...]

    def registry_dict(self, source_candidate_id: str) -> dict[str, object]:
        return {
            "block_id": self.block_id,
            "source_candidate_id": source_candidate_id,
            "block_type": self.block_type,
            "description": self.description,
            "compatible_with": list(self.compatible_with),
            "incompatible_with": list(self.incompatible_with),
            "removed_constraints": list(self.removed_constraints),
            "removed_risks": list(self.removed_risks),
            "diversity_tags": list(self.diversity_tags),
        }


@dataclass(frozen=True, slots=True)
class PublicationManifest:
    kind: CandidateKind
    candidate_id: str
    revision: int
    source_fingerprint: str
    copy_blocks: tuple[LearnedCopyBlock, ...] = ()
    person_blocks: tuple[LearnedPersonBlock, ...] = ()
    schema_version: str = "1.0"


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise LearningValidationError(f"{context} 必须是 JSON 对象")
    return cast(dict[str, object], value)


def _string(data: Mapping[str, object], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise LearningValidationError(f"{field} 必须是非空字符串")
    return value.strip()


def _strings(
    data: Mapping[str, object], field: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    value = data.get(field)
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        requirement = "字符串数组" if allow_empty else "非空字符串数组"
        raise LearningValidationError(f"{field} 必须是{requirement}")
    return tuple(dict.fromkeys(item.strip() for item in value))


def _block_id(data: Mapping[str, object]) -> str:
    block_id = _string(data, "block_id")
    if not BLOCK_ID_PATTERN.fullmatch(block_id):
        raise LearningValidationError("block_id 只能使用小写字母、数字和短横线")
    return block_id


def _copy_block(data: Mapping[str, object]) -> LearnedCopyBlock:
    raw_slots = data.get("slots")
    if not isinstance(raw_slots, list) or not raw_slots:
        raise LearningValidationError("copy block slots 必须是非空数组")
    slots = tuple(
        CopySlot(name=_string(item_data, "name"), value_type=_string(item_data, "value_type"))
        for item_data in (_mapping(item, "slot") for item in raw_slots)
    )
    raw_tags = _mapping(data.get("diversity_tags"), "diversity_tags")
    allowed_modes = _strings(data, "allowed_modes")
    if not set(allowed_modes) <= {"source_fill", "human_rewrite"}:
        raise LearningValidationError("allowed_modes 只能包含 source_fill/human_rewrite")
    solid_food_only = data.get("solid_food_only", False)
    if not isinstance(solid_food_only, bool):
        raise LearningValidationError("solid_food_only 必须是布尔值")
    return LearnedCopyBlock(
        block_id=_block_id(data),
        template=_string(data, "template"),
        slots=slots,
        category_families=_strings(data, "category_families"),
        consumption_needs=_strings(data, "consumption_needs"),
        seasons=_strings(data, "seasons"),
        allowed_modes=allowed_modes,
        removed_risks=_strings(data, "removed_risks", allow_empty=True),
        diversity_tags=CopyDiversityTags(
            opening_type=_string(raw_tags, "opening_type"),
            rhythm=_string(raw_tags, "rhythm"),
            need=_string(raw_tags, "need"),
            emotion=_string(raw_tags, "emotion"),
        ),
        solid_food_only=solid_food_only,
    )


def _person_block(data: Mapping[str, object]) -> LearnedPersonBlock:
    block_type = _string(data, "block_type")
    if block_type not in {"identity", "hair", "outfit", "scene"}:
        raise LearningValidationError("block_type 只能是 identity/hair/outfit/scene")
    return LearnedPersonBlock(
        block_id=_block_id(data),
        block_type=block_type,
        description=_string(data, "description"),
        compatible_with=_strings(data, "compatible_with", allow_empty=True),
        incompatible_with=_strings(data, "incompatible_with", allow_empty=True),
        removed_constraints=_strings(data, "removed_constraints", allow_empty=True),
        removed_risks=_strings(data, "removed_risks", allow_empty=True),
        diversity_tags=_strings(data, "diversity_tags"),
    )


def load_publication_manifest(path: str | Path) -> PublicationManifest:
    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LearningValidationError(f"无法读取发布清单：{source}") from exc
    data = _mapping(raw, "发布清单")
    if data.get("schema_version") != "1.0":
        raise LearningValidationError("发布清单 schema_version 必须是 1.0")
    try:
        kind = CandidateKind(_string(data, "kind"))
    except ValueError as exc:
        raise LearningValidationError("发布清单 kind 只能是 copy/person") from exc
    revision = data.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise LearningValidationError("发布清单 revision 必须是正整数")
    raw_copy = data.get("copy_blocks", [])
    raw_person = data.get("person_blocks", [])
    if not isinstance(raw_copy, list) or not isinstance(raw_person, list):
        raise LearningValidationError("copy_blocks/person_blocks 必须是数组")
    copy_blocks = tuple(_copy_block(_mapping(item, "copy block")) for item in raw_copy)
    person_blocks = tuple(_person_block(_mapping(item, "person block")) for item in raw_person)
    if kind is CandidateKind.COPY and (not copy_blocks or person_blocks):
        raise LearningValidationError("copy 发布清单只能包含非空 copy_blocks")
    if kind is CandidateKind.PERSON and (not person_blocks or copy_blocks):
        raise LearningValidationError("person 发布清单只能包含非空 person_blocks")
    block_ids = [block.block_id for block in copy_blocks]
    block_ids.extend(block.block_id for block in person_blocks)
    if len(block_ids) != len(set(block_ids)):
        raise LearningValidationError("发布清单 block_id 必须唯一")
    return PublicationManifest(
        kind=kind,
        candidate_id=_string(data, "candidate_id"),
        revision=revision,
        source_fingerprint=str(data.get("source_fingerprint", "")).strip(),
        copy_blocks=copy_blocks,
        person_blocks=person_blocks,
    )


def project_root() -> Path:
    configured = os.environ.get("AVATAR_PROMPT_PROJECT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    module_root = Path(__file__).resolve().parents[3]
    if (module_root / "prompt-engineering").is_dir():
        return module_root
    return Path.cwd().resolve()


def reference_path(name: str, *, root: Path | None = None) -> Path:
    base = root or project_root()
    return base / "prompt-engineering" / "references" / name


def _resource_text(path: Path, title: str) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return f"# {title}\n\n本资源仅接收经人工批准并由学习发布清单校验的内容。\n"


def _validate_manifest(candidate: LearningCandidate, manifest: PublicationManifest) -> None:
    if candidate.status is not LearningStatus.APPROVED:
        raise LearningValidationError("只有 approved 候选可以发布")
    if str(candidate.candidate_id) != manifest.candidate_id:
        raise LearningValidationError("发布清单 candidate_id 与候选不一致")
    if int(candidate.revision) != manifest.revision:
        raise RevisionConflictError(
            f"revision 冲突：expected={manifest.revision},actual={int(candidate.revision)}"
        )
    if isinstance(candidate, CopyLearningCandidate):
        if manifest.kind is not CandidateKind.COPY:
            raise LearningValidationError("发布清单 kind 与文案候选不一致")
        if candidate.source_fingerprint != manifest.source_fingerprint:
            raise LearningValidationError("发布清单 source_fingerprint 与候选不一致")
        for block in manifest.copy_blocks:
            remaining_risks = detect_risks(block.template, kind=CandidateKind.COPY)
            if remaining_risks:
                raise LearningValidationError(
                    "文案学习块仍包含不可进入正式资源的风险：" + "、".join(remaining_risks)
                )
            if not set(candidate.risk_tags) <= set(block.removed_risks):
                raise LearningValidationError("发布清单未登记候选全部风险项的删除结果")
    elif isinstance(candidate, PersonPromptLearningCandidate):
        if manifest.kind is not CandidateKind.PERSON:
            raise LearningValidationError("发布清单 kind 与人物候选不一致")
        block_types = {block.block_type for block in manifest.person_blocks}
        if block_types != {"identity", "hair", "outfit", "scene"}:
            raise LearningValidationError("人物发布清单必须同时包含四类描述块")
        for person_block in manifest.person_blocks:
            repeated = tuple(
                term for term in FIXED_PERSON_CONSTRAINTS if term in person_block.description
            )
            if repeated:
                raise LearningValidationError(
                    "人物学习块不得覆盖或重复固定画面约束：" + "、".join(repeated)
                )
            risks = detect_risks(person_block.description, kind=CandidateKind.PERSON)
            if risks:
                raise LearningValidationError("人物学习块仍包含风险：" + "、".join(risks))
    else:
        raise AssertionError("unknown candidate type")


def publish_manifest(
    store: LearningStore,
    manifest: PublicationManifest,
    *,
    root: Path | None = None,
) -> LearningCandidate:
    candidate = store.get(manifest.kind, manifest.candidate_id)
    _validate_manifest(candidate, manifest)
    allowed_transition(candidate, LearningStatus.PUBLISHED)
    copy_path = reference_path(COPY_RESOURCE_NAME, root=root)
    person_path = reference_path("person-prompt-source-blocks.md", root=root)
    contract_path = reference_path("person-prompt-block-contracts.md", root=root)
    targets: dict[Path, bytes] = {}
    block_ids: tuple[str, ...]
    if manifest.kind is CandidateKind.COPY:
        current = _resource_text(copy_path, "真人跑量原文块")
        _ensure_no_block_collision(current, [block.block_id for block in manifest.copy_blocks])
        additions = "".join(_copy_markdown(block) for block in manifest.copy_blocks)
        if PUBLISHED_COPY_SECTION_HEADING not in current:
            additions = (
                PUBLISHED_COPY_SECTION_HEADING
                + "\n\n本节只接收人工批准并经 Codex 语义清理、发布校验的新增文案块。\n\n"
                + additions
            )
        targets[copy_path] = (current.rstrip() + "\n\n" + additions.strip() + "\n").encode("utf-8")
        block_ids = tuple(block.block_id for block in manifest.copy_blocks)
    else:
        current = _resource_text(person_path, "审核发布的人物 Prompt 学习块")
        _ensure_no_block_collision(current, [block.block_id for block in manifest.person_blocks])
        additions = "".join(
            _person_markdown(block, manifest.candidate_id) for block in manifest.person_blocks
        )
        targets[person_path] = (current.rstrip() + "\n\n" + additions.strip() + "\n").encode(
            "utf-8"
        )
        if not contract_path.exists():
            targets[contract_path] = _person_contract_text().encode("utf-8")
        block_ids = tuple(block.block_id for block in manifest.person_blocks)
    provenance_path = store.kind_root(manifest.kind) / "published" / "provenance.jsonl"
    provenance = provenance_path.read_text(encoding="utf-8") if provenance_path.exists() else ""
    registry_blocks = (
        [block.registry_dict(manifest.candidate_id) for block in manifest.copy_blocks]
        if manifest.kind is CandidateKind.COPY
        else [block.registry_dict(manifest.candidate_id) for block in manifest.person_blocks]
    )
    record = json.dumps(
        {
            "schema_version": "1.0",
            "kind": manifest.kind.value,
            "candidate_id": manifest.candidate_id,
            "revision": manifest.revision,
            "block_ids": list(block_ids),
            "blocks": registry_blocks,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    targets[provenance_path] = (provenance + record + "\n").encode("utf-8")
    originals = {path: path.read_bytes() if path.exists() else None for path in targets}
    transactional_replace(targets)
    try:
        published = store.save(
            replace(
                candidate,
                status=LearningStatus.PUBLISHED,
                published_block_ids=block_ids,
            ),
            expected_revision=manifest.revision,
            action="published",
            details=block_ids,
        )
    except BaseException:
        rollback = {path: payload for path, payload in originals.items() if payload is not None}
        transactional_replace(rollback)
        for path, payload in originals.items():
            if payload is None:
                path.unlink(missing_ok=True)
        raise
    return published


def _ensure_no_block_collision(text: str, block_ids: Sequence[str]) -> None:
    for block_id in block_ids:
        if f'"block_id": "{block_id}"' in text or f"`{block_id}`" in text:
            raise LearningValidationError(f"block_id 已存在：{block_id}")


def _copy_markdown(block: LearnedCopyBlock) -> str:
    return f"### `{block.block_id}`\n\n```text\n{block.template.strip()}\n```\n\n"


def _person_markdown(block: LearnedPersonBlock, candidate_id: str) -> str:
    return (
        f"## `{block.block_id}`\n\n"
        f"来源候选：`{candidate_id}`。\n\n"
        "```json\n"
        + json.dumps(
            block.registry_dict(candidate_id), ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n```\n\n"
    )


def _person_contract_text() -> str:
    return """# 人物 Prompt 学习块合约

- learned 块只补充 identity、hair、outfit、scene 四类可学习变量。
- 固定中景、直视镜头、商品前置摆放、不手持、不看不接触商品、非商品区域无 logo
  和无字幕始终由生产模板提供。
- 禁止具体真人复刻、未成年人、中老年、暴露、大面积 logo、夸张或土味方向。
- 同批 identity_key 与 outfit_key 继续保持唯一；学习块不能取消现有 validator。
"""


__all__ = [
    "COPY_RESOURCE_NAME",
    "PUBLISHED_COPY_SECTION_HEADING",
    "LearnedCopyBlock",
    "LearnedPersonBlock",
    "PublicationManifest",
    "load_publication_manifest",
    "project_root",
    "publish_manifest",
    "reference_path",
]
