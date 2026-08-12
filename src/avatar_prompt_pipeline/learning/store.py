from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import cast

from .models import (
    AsrToken,
    AuditEvent,
    CandidateId,
    CandidateKind,
    CopyLearningCandidate,
    LearningCandidate,
    LearningStatus,
    PersonPromptLearningCandidate,
    Revision,
)
from .validation import LearningValidationError, validate_candidate_id


class CandidateNotFoundError(FileNotFoundError):
    """Raised when a candidate does not exist in its isolated store."""


class RevisionConflictError(RuntimeError):
    """Raised when optimistic concurrency detects a stale revision."""


class ImmutableContentError(LearningValidationError):
    """Raised when an operation attempts to change immutable source content."""


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str) -> None:
    _atomic_bytes(path, text.encode("utf-8"))


def atomic_write_json(path: Path, payload: object) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    atomic_write_text(path, rendered)


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LearningValidationError(f"{field} 必须是字符串数组")
    return tuple(value)


def _required_string(data: Mapping[str, object], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str):
        raise LearningValidationError(f"{field} 必须是字符串")
    return value


def _required_int(data: Mapping[str, object], field: str) -> int:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise LearningValidationError(f"{field} 必须是整数")
    return value


def _copy_from_dict(data: Mapping[str, object]) -> CopyLearningCandidate:
    raw_tokens = data.get("word_timeline", [])
    if not isinstance(raw_tokens, list):
        raise LearningValidationError("word_timeline 必须是数组")
    tokens: list[AsrToken] = []
    for item in raw_tokens:
        if not isinstance(item, dict):
            raise LearningValidationError("word_timeline 条目必须是对象")
        token_data = cast(dict[str, object], item)
        confidence = token_data.get("confidence")
        if confidence is not None and not isinstance(confidence, (int, float)):
            raise LearningValidationError("token confidence 必须是数字或 null")
        tokens.append(
            AsrToken(
                index=_required_int(token_data, "index"),
                text=_required_string(token_data, "text"),
                start_ms=_required_int(token_data, "start_ms"),
                end_ms=_required_int(token_data, "end_ms"),
                source=_required_string(token_data, "source"),
                confidence=float(confidence) if confidence is not None else None,
            )
        )
    raw_conversion = data.get("audio_conversion", [])
    if not isinstance(raw_conversion, list):
        raise LearningValidationError("audio_conversion 必须是键值数组")
    conversion: list[tuple[str, str]] = []
    for item in raw_conversion:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(value, str) for value in item)
        ):
            raise LearningValidationError("audio_conversion 条目必须是两个字符串")
        conversion.append((item[0], item[1]))
    return CopyLearningCandidate(
        candidate_id=CandidateId(validate_candidate_id(_required_string(data, "candidate_id"))),
        status=LearningStatus(_required_string(data, "status")),
        revision=Revision(_required_int(data, "revision")),
        created_at=_required_string(data, "created_at"),
        updated_at=_required_string(data, "updated_at"),
        source_media=_required_string(data, "source_media"),
        source_fingerprint=_required_string(data, "source_fingerprint"),
        source_date=_required_string(data, "source_date"),
        asr_cache_key=_required_string(data, "asr_cache_key"),
        provider=_required_string(data, "provider"),
        model=_required_string(data, "model"),
        raw_transcript=_required_string(data, "raw_transcript"),
        edited_transcript=_required_string(data, "edited_transcript"),
        word_timeline=tuple(tokens),
        audio_conversion=tuple(conversion),
        risk_tags=_string_tuple(data.get("risk_tags", []), "risk_tags"),
        similarity_hits=_string_tuple(data.get("similarity_hits", []), "similarity_hits"),
        category_family=_required_string(data, "category_family"),
        consumption_need=_required_string(data, "consumption_need"),
        season=_required_string(data, "season"),
        source_usage=_string_tuple(data.get("source_usage", []), "source_usage"),
        published_block_ids=_string_tuple(
            data.get("published_block_ids", []), "published_block_ids"
        ),
        rejection_reason=_required_string(data, "rejection_reason"),
        schema_version=_required_string(data, "schema_version"),
    )


def _person_from_dict(data: Mapping[str, object]) -> PersonPromptLearningCandidate:
    return PersonPromptLearningCandidate(
        candidate_id=CandidateId(validate_candidate_id(_required_string(data, "candidate_id"))),
        status=LearningStatus(_required_string(data, "status")),
        revision=Revision(_required_int(data, "revision")),
        created_at=_required_string(data, "created_at"),
        updated_at=_required_string(data, "updated_at"),
        source_label=_required_string(data, "source_label"),
        raw_prompt=_required_string(data, "raw_prompt"),
        edited_prompt=_required_string(data, "edited_prompt"),
        identity_traits=_string_tuple(data.get("identity_traits", []), "identity_traits"),
        hair_traits=_string_tuple(data.get("hair_traits", []), "hair_traits"),
        outfit_traits=_string_tuple(data.get("outfit_traits", []), "outfit_traits"),
        scene_traits=_string_tuple(data.get("scene_traits", []), "scene_traits"),
        forbidden_traits=_string_tuple(data.get("forbidden_traits", []), "forbidden_traits"),
        risk_tags=_string_tuple(data.get("risk_tags", []), "risk_tags"),
        similarity_hits=_string_tuple(data.get("similarity_hits", []), "similarity_hits"),
        published_block_ids=_string_tuple(
            data.get("published_block_ids", []), "published_block_ids"
        ),
        rejection_reason=_required_string(data, "rejection_reason"),
        schema_version=_required_string(data, "schema_version"),
    )


class LearningStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def kind_root(self, kind: CandidateKind) -> Path:
        return self.root / kind.value

    def candidate_directory(self, kind: CandidateKind, candidate_id: str) -> Path:
        safe_id = validate_candidate_id(candidate_id)
        path = self.kind_root(kind) / "candidates" / safe_id
        try:
            path.resolve().relative_to(self.root)
        except ValueError as exc:
            raise LearningValidationError("候选路径超出 learning root") from exc
        return path

    def _candidate_path(self, kind: CandidateKind, candidate_id: str) -> Path:
        return self.candidate_directory(kind, candidate_id) / "candidate.json"

    def get(self, kind: CandidateKind, candidate_id: str) -> LearningCandidate:
        path = self._candidate_path(kind, candidate_id)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CandidateNotFoundError(f"候选不存在：{kind.value}/{candidate_id}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise LearningValidationError(f"候选文件损坏：{kind.value}/{candidate_id}") from exc
        if not isinstance(raw, dict):
            raise LearningValidationError("candidate.json 顶层必须是对象")
        data = cast(dict[str, object], raw)
        parsed_kind = data.get("kind")
        expected = "copy_transcript" if kind is CandidateKind.COPY else "person_prompt"
        if parsed_kind != expected:
            raise LearningValidationError("候选 kind 与目录不一致")
        return _copy_from_dict(data) if kind is CandidateKind.COPY else _person_from_dict(data)

    def list(
        self,
        kind: CandidateKind,
        *,
        status: LearningStatus | None = None,
    ) -> tuple[LearningCandidate, ...]:
        candidates_root = self.kind_root(kind) / "candidates"
        if not candidates_root.is_dir():
            return ()
        candidates: list[LearningCandidate] = []
        for directory in sorted(candidates_root.iterdir()):
            if not directory.is_dir() or not validate_candidate_id_or_false(directory.name):
                continue
            candidate = self.get(kind, directory.name)
            if status is None or candidate.status is status:
                candidates.append(candidate)
        return tuple(sorted(candidates, key=lambda item: item.updated_at, reverse=True))

    def create(self, candidate: LearningCandidate) -> LearningCandidate:
        kind = (
            CandidateKind.COPY
            if isinstance(candidate, CopyLearningCandidate)
            else CandidateKind.PERSON
        )
        directory = self.candidate_directory(kind, str(candidate.candidate_id))
        if directory.exists():
            raise FileExistsError(f"拒绝覆盖已有候选：{candidate.candidate_id}")
        directory.mkdir(parents=True, exist_ok=False)
        files: dict[Path, bytes] = {
            directory / "candidate.json": _json_payload(candidate.to_dict()),
        }
        if isinstance(candidate, CopyLearningCandidate):
            files.update(
                {
                    directory / "raw_transcript.txt": candidate.raw_transcript.encode("utf-8"),
                    directory / "edited_transcript.txt": candidate.edited_transcript.encode(
                        "utf-8"
                    ),
                    directory / "word_timeline.json": _json_payload(
                        [asdict_token(token) for token in candidate.word_timeline]
                    ),
                    directory / "source.json": _json_payload(
                        {
                            "source_media": candidate.source_media,
                            "source_fingerprint": candidate.source_fingerprint,
                            "source_date": candidate.source_date,
                            "asr_cache_key": candidate.asr_cache_key,
                        }
                    ),
                    directory / "asr_report.json": _json_payload(
                        {
                            "provider": candidate.provider,
                            "model": candidate.model,
                            "audio_conversion": candidate.audio_conversion,
                            "risk_tags": candidate.risk_tags,
                        }
                    ),
                }
            )
        else:
            files.update(
                {
                    directory / "raw_prompt.txt": candidate.raw_prompt.encode("utf-8"),
                    directory / "edited_prompt.txt": candidate.edited_prompt.encode("utf-8"),
                }
            )
        event = AuditEvent(
            candidate_id=candidate.candidate_id,
            kind=kind,
            revision=candidate.revision,
            action="created",
            occurred_at=candidate.created_at,
            from_status=None,
            to_status=candidate.status,
        )
        files[directory / "audit" / f"{int(candidate.revision):06d}.json"] = _json_payload(
            event.to_dict()
        )
        _commit_new_files(files)
        return candidate

    def save(
        self,
        candidate: LearningCandidate,
        *,
        expected_revision: int,
        action: str,
        details: Sequence[str] = (),
    ) -> LearningCandidate:
        kind = (
            CandidateKind.COPY
            if isinstance(candidate, CopyLearningCandidate)
            else CandidateKind.PERSON
        )
        current = self.get(kind, str(candidate.candidate_id))
        if int(current.revision) != expected_revision:
            raise RevisionConflictError(
                f"revision 冲突：expected={expected_revision},actual={int(current.revision)}"
            )
        _ensure_same_immutable_content(current, candidate)
        new_revision = Revision(expected_revision + 1)
        updated = replace(candidate, revision=new_revision, updated_at=_now())
        directory = self.candidate_directory(kind, str(candidate.candidate_id))
        event = AuditEvent(
            candidate_id=candidate.candidate_id,
            kind=kind,
            revision=new_revision,
            action=action,
            occurred_at=updated.updated_at,
            from_status=current.status,
            to_status=updated.status,
            details=tuple(details),
        )
        files: dict[Path, bytes] = {
            directory / "candidate.json": _json_payload(updated.to_dict()),
            directory / "audit" / f"{int(new_revision):06d}.json": _json_payload(event.to_dict()),
        }
        if isinstance(updated, CopyLearningCandidate):
            files[directory / "edited_transcript.txt"] = updated.edited_transcript.encode("utf-8")
        else:
            files[directory / "edited_prompt.txt"] = updated.edited_prompt.encode("utf-8")
        _transactional_replace(files)
        return updated

    def archive(
        self,
        kind: CandidateKind,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> LearningCandidate:
        current = self.get(kind, candidate_id)
        if int(current.revision) != expected_revision:
            raise RevisionConflictError(
                f"revision 冲突：expected={expected_revision},actual={int(current.revision)}"
            )
        directory = self.candidate_directory(kind, candidate_id)
        archive_root = self.kind_root(kind) / "trash"
        archived = archive_root / candidate_id
        if archived.exists():
            raise FileExistsError(f"回收目录已存在同名候选：{candidate_id}")
        archive_root.mkdir(parents=True, exist_ok=True)
        deletion_record = directory / "deletion.json"
        atomic_write_json(
            deletion_record,
            {
                "schema_version": "1.0",
                "action": "archived",
                "candidate_id": candidate_id,
                "kind": kind.value,
                "revision": int(current.revision),
                "status": current.status.value,
                "archived_at": _now(),
            },
        )
        try:
            directory.replace(archived)
        except BaseException:
            deletion_record.unlink(missing_ok=True)
            raise
        return current


def asdict_token(token: AsrToken) -> dict[str, object]:
    return {
        "index": token.index,
        "text": token.text,
        "start_ms": token.start_ms,
        "end_ms": token.end_ms,
        "source": token.source,
        "confidence": token.confidence,
    }


def _json_payload(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _commit_new_files(files: Mapping[Path, bytes]) -> None:
    written: list[Path] = []
    try:
        for path, payload in files.items():
            if path.exists():
                raise FileExistsError(f"拒绝覆盖已有文件：{path}")
            _atomic_bytes(path, payload)
            written.append(path)
    except BaseException:
        for path in reversed(written):
            path.unlink(missing_ok=True)
        raise


def _transactional_replace(files: Mapping[Path, bytes]) -> None:
    originals = {path: path.read_bytes() if path.exists() else None for path in files}
    replaced: list[Path] = []
    try:
        for path, payload in files.items():
            _atomic_bytes(path, payload)
            replaced.append(path)
    except BaseException:
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                _atomic_bytes(path, original)
        raise


def transactional_replace(files: Mapping[Path, bytes]) -> None:
    """Atomically replace a related set of files with rollback on failure."""
    _transactional_replace(files)


def _ensure_same_immutable_content(
    current: LearningCandidate,
    updated: LearningCandidate,
) -> None:
    if type(current) is not type(updated):
        raise ImmutableContentError("不能改变候选 kind")
    if isinstance(current, CopyLearningCandidate) and isinstance(updated, CopyLearningCandidate):
        immutable = (
            current.raw_transcript == updated.raw_transcript
            and current.source_fingerprint == updated.source_fingerprint
            and current.source_media == updated.source_media
            and current.word_timeline == updated.word_timeline
        )
    elif isinstance(current, PersonPromptLearningCandidate) and isinstance(
        updated, PersonPromptLearningCandidate
    ):
        immutable = current.raw_prompt == updated.raw_prompt
    else:
        immutable = False
    if not immutable:
        raise ImmutableContentError("raw_transcript/raw_prompt 和来源字段不可修改")


def validate_candidate_id_or_false(value: str) -> bool:
    try:
        validate_candidate_id(value)
    except LearningValidationError:
        return False
    return True


__all__ = [
    "CandidateNotFoundError",
    "ImmutableContentError",
    "LearningStore",
    "RevisionConflictError",
    "atomic_write_json",
    "atomic_write_text",
    "transactional_replace",
]
