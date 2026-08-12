from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from .asr_provider import (
    AsrProviderError,
    AsrWorkerConfig,
    AsrWorkerResult,
    ParaformerSubprocessProvider,
    cache_key,
    discover_media,
    file_fingerprint,
)
from .models import (
    CandidateId,
    CandidateKind,
    CopyLearningCandidate,
    LearningCandidate,
    LearningStatus,
    PersonPromptLearningCandidate,
    Revision,
)
from .options import validate_copy_learning_fields
from .store import LearningStore, atomic_write_json
from .text_cleanup import normalize_asr_editable_draft
from .validation import (
    LearningValidationError,
    allowed_transition,
    detect_risks,
    duplicate_warnings,
)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _candidate_id(prefix: str) -> CandidateId:
    return CandidateId(f"{prefix}-{uuid4().hex}")


def _clean_text(value: str, *, field: str) -> str:
    cleaned = value.replace("\x00", "").strip()
    if not cleaned:
        raise LearningValidationError(f"{field} 不能为空")
    return cleaned


def _clean_values(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


def _validate_submission_fields(candidate: LearningCandidate, *, action_label: str) -> None:
    if not isinstance(candidate, CopyLearningCandidate):
        return
    validate_copy_learning_fields(
        category_family=candidate.category_family,
        consumption_need=candidate.consumption_need,
        season=candidate.season,
        source_usage=candidate.source_usage,
    )
    missing: list[str] = []
    if not candidate.category_family:
        missing.append("品类族")
    if not candidate.consumption_need:
        missing.append("消费需求")
    if not candidate.source_usage:
        missing.append("来源块用途")
    if missing:
        raise LearningValidationError(f"{action_label}前请选择：" + "、".join(missing))


class LearningService:
    def __init__(
        self,
        store: LearningStore,
        *,
        asr_provider: ParaformerSubprocessProvider | None = None,
    ) -> None:
        self.store = store
        self.asr_provider = asr_provider or ParaformerSubprocessProvider()

    @classmethod
    def from_root(
        cls,
        root: str | Path,
        *,
        worker_config: AsrWorkerConfig | None = None,
    ) -> LearningService:
        return cls(
            LearningStore(root),
            asr_provider=ParaformerSubprocessProvider(worker_config),
        )

    def get(self, kind: CandidateKind, candidate_id: str) -> LearningCandidate:
        return self.store.get(kind, candidate_id)

    def list(
        self,
        kind: CandidateKind,
        *,
        status: LearningStatus | None = None,
    ) -> tuple[LearningCandidate, ...]:
        return self.store.list(kind, status=status)

    def add_person_prompt(
        self,
        text: str,
        *,
        source_label: str = "用户人工样本",
    ) -> PersonPromptLearningCandidate:
        prompt = _clean_text(text, field="人物 Prompt")
        label = source_label.replace("\x00", "").strip() or "用户人工样本"
        timestamp = _now()
        previous = tuple(
            (str(item.candidate_id), item.edited_prompt)
            for item in self.store.list(CandidateKind.PERSON)
            if isinstance(item, PersonPromptLearningCandidate)
        )
        candidate = PersonPromptLearningCandidate(
            candidate_id=_candidate_id("person"),
            status=LearningStatus.PENDING,
            revision=Revision(1),
            created_at=timestamp,
            updated_at=timestamp,
            source_label=label,
            raw_prompt=prompt,
            edited_prompt=prompt,
            risk_tags=detect_risks(prompt, kind=CandidateKind.PERSON),
            similarity_hits=duplicate_warnings(prompt, previous),
        )
        return self.store.create(candidate)  # type: ignore[return-value]

    def transcribe(
        self,
        inputs: tuple[Path, ...],
        *,
        source_date: date,
    ) -> dict[str, object]:
        media_files = discover_media(inputs)
        succeeded: list[str] = []
        reused: list[str] = []
        failed: list[dict[str, str]] = []
        existing = tuple(
            candidate
            for candidate in self.store.list(CandidateKind.COPY)
            if isinstance(candidate, CopyLearningCandidate)
        )
        by_cache_key = {candidate.asr_cache_key: candidate for candidate in existing}
        for media in media_files:
            fingerprint = file_fingerprint(media)
            item_cache_key = cache_key(fingerprint, self.asr_provider.config)
            cached = by_cache_key.get(item_cache_key)
            if cached is not None:
                reused.append(str(cached.candidate_id))
                continue
            work_dir = self.store.kind_root(CandidateKind.COPY) / "work" / item_cache_key
            try:
                result = self.asr_provider.transcribe(media, work_dir)
                candidate = self._copy_candidate(
                    media=media,
                    fingerprint=fingerprint,
                    item_cache_key=item_cache_key,
                    source_date=source_date,
                    result=result,
                )
                succeeded.append(str(candidate.candidate_id))
                by_cache_key[item_cache_key] = candidate
            except (AsrProviderError, OSError, LearningValidationError) as exc:
                report = {
                    "schema_version": "1.0",
                    "source_media": str(media),
                    "source_fingerprint": fingerprint,
                    "asr_cache_key": item_cache_key,
                    "error": str(exc)[-2000:],
                    "failed_at": _now(),
                }
                failure_path = (
                    self.store.kind_root(CandidateKind.COPY) / "failures" / f"{item_cache_key}.json"
                )
                atomic_write_json(failure_path, report)
                failed.append({"source_media": str(media), "error": str(exc)[-2000:]})
        return {
            "schema_version": "1.0",
            "kind": "copy",
            "date": source_date.isoformat(),
            "succeeded": len(succeeded),
            "reused": len(reused),
            "failed": len(failed),
            "candidate_ids": [*succeeded, *reused],
            "succeeded_candidate_ids": succeeded,
            "reused_candidate_ids": reused,
            "failures": failed,
        }

    def _copy_candidate(
        self,
        *,
        media: Path,
        fingerprint: str,
        item_cache_key: str,
        source_date: date,
        result: AsrWorkerResult,
    ) -> CopyLearningCandidate:
        transcript = _clean_text(result.text, field="ASR 识别全文")
        editable_draft = normalize_asr_editable_draft(transcript)
        timestamp = _now()
        previous = tuple(
            (str(item.candidate_id), item.edited_transcript)
            for item in self.store.list(CandidateKind.COPY)
            if isinstance(item, CopyLearningCandidate)
        )
        candidate = CopyLearningCandidate(
            candidate_id=_candidate_id("copy"),
            status=LearningStatus.PENDING,
            revision=Revision(1),
            created_at=timestamp,
            updated_at=timestamp,
            source_media=str(media.resolve()),
            source_fingerprint=fingerprint,
            source_date=source_date.isoformat(),
            asr_cache_key=item_cache_key,
            provider=result.provider,
            model=result.model,
            raw_transcript=transcript,
            edited_transcript=editable_draft,
            word_timeline=result.tokens,
            audio_conversion=result.audio_conversion,
            risk_tags=detect_risks(editable_draft, kind=CandidateKind.COPY),
            similarity_hits=duplicate_warnings(editable_draft, previous),
        )
        created = self.store.create(candidate)
        if not isinstance(created, CopyLearningCandidate):
            raise AssertionError("copy candidate store returned wrong type")
        return created

    def update(
        self,
        kind: CandidateKind,
        candidate_id: str,
        *,
        expected_revision: int,
        edited_text: str,
        structured_fields: dict[str, tuple[str, ...] | str] | None = None,
    ) -> LearningCandidate:
        current = self.store.get(kind, candidate_id)
        allowed_transition(current, LearningStatus.EDITING)
        edited = _clean_text(edited_text, field="edited 内容")
        fields = structured_fields or {}
        allowed_by_kind = {
            CandidateKind.COPY: {
                "category_family",
                "consumption_need",
                "season",
                "source_usage",
            },
            CandidateKind.PERSON: {
                "identity_traits",
                "hair_traits",
                "outfit_traits",
                "scene_traits",
                "forbidden_traits",
            },
        }
        unknown = set(fields) - allowed_by_kind[kind]
        if unknown:
            raise LearningValidationError("不允许编辑字段：" + "、".join(sorted(unknown)))
        if isinstance(current, CopyLearningCandidate):
            category_family = _field_string(fields, "category_family", current.category_family)
            consumption_need = _field_string(fields, "consumption_need", current.consumption_need)
            season = _field_string(fields, "season", current.season)
            source_usage = _field_tuple(fields, "source_usage", current.source_usage)
            validate_copy_learning_fields(
                category_family=category_family,
                consumption_need=consumption_need,
                season=season,
                source_usage=source_usage,
            )
            updated: LearningCandidate = replace(
                current,
                status=LearningStatus.EDITING,
                edited_transcript=edited,
                category_family=category_family,
                consumption_need=consumption_need,
                season=season,
                source_usage=source_usage,
                risk_tags=detect_risks(edited, kind=CandidateKind.COPY),
            )
        elif isinstance(current, PersonPromptLearningCandidate):
            updated = replace(
                current,
                status=LearningStatus.EDITING,
                edited_prompt=edited,
                identity_traits=_field_tuple(fields, "identity_traits", current.identity_traits),
                hair_traits=_field_tuple(fields, "hair_traits", current.hair_traits),
                outfit_traits=_field_tuple(fields, "outfit_traits", current.outfit_traits),
                scene_traits=_field_tuple(fields, "scene_traits", current.scene_traits),
                forbidden_traits=_field_tuple(fields, "forbidden_traits", current.forbidden_traits),
                risk_tags=detect_risks(edited, kind=CandidateKind.PERSON),
            )
        else:
            raise AssertionError("unknown candidate type")
        return self.store.save(
            updated,
            expected_revision=expected_revision,
            action="updated",
        )

    def submit_review(
        self, kind: CandidateKind, candidate_id: str, *, expected_revision: int
    ) -> LearningCandidate:
        current = self.store.get(kind, candidate_id)
        _validate_submission_fields(current, action_label="提交审核")
        allowed_transition(current, LearningStatus.READY_FOR_REVIEW)
        return self.store.save(
            replace(current, status=LearningStatus.READY_FOR_REVIEW),
            expected_revision=expected_revision,
            action="submitted_for_review",
        )

    def submit_learning(
        self, kind: CandidateKind, candidate_id: str, *, expected_revision: int
    ) -> LearningCandidate:
        current = self.store.get(kind, candidate_id)
        _validate_submission_fields(current, action_label="提交学习")
        if current.status not in {LearningStatus.PENDING, LearningStatus.EDITING}:
            raise LearningValidationError(f"不允许从 {current.status.value} 提交学习")
        return self.store.save(
            replace(
                current,
                status=LearningStatus.APPROVED,
                rejection_reason="",
            ),
            expected_revision=expected_revision,
            action="submitted_for_learning",
        )

    def approve(
        self, kind: CandidateKind, candidate_id: str, *, expected_revision: int
    ) -> LearningCandidate:
        current = self.store.get(kind, candidate_id)
        allowed_transition(current, LearningStatus.APPROVED)
        return self.store.save(
            replace(current, status=LearningStatus.APPROVED, rejection_reason=""),
            expected_revision=expected_revision,
            action="approved",
        )

    def reject(
        self,
        kind: CandidateKind,
        candidate_id: str,
        *,
        expected_revision: int,
        reason: str,
    ) -> LearningCandidate:
        current = self.store.get(kind, candidate_id)
        allowed_transition(current, LearningStatus.REJECTED)
        clean_reason = _clean_text(reason, field="驳回原因")
        return self.store.save(
            replace(current, status=LearningStatus.REJECTED, rejection_reason=clean_reason),
            expected_revision=expected_revision,
            action="rejected",
            details=(clean_reason,),
        )

    def delete(
        self,
        kind: CandidateKind,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> LearningCandidate:
        current = self.store.get(kind, candidate_id)
        if current.status in {LearningStatus.APPROVED, LearningStatus.PUBLISHED}:
            raise LearningValidationError("已批准或已发布的候选不能删除")
        return self.store.archive(
            kind,
            candidate_id,
            expected_revision=expected_revision,
        )


def _field_string(fields: dict[str, tuple[str, ...] | str], field: str, default: str) -> str:
    value = fields.get(field, default)
    if not isinstance(value, str):
        raise LearningValidationError(f"{field} 必须是字符串")
    return value.strip()


def _field_tuple(
    fields: dict[str, tuple[str, ...] | str],
    field: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = fields.get(field, default)
    if not isinstance(value, tuple) or not all(isinstance(item, str) for item in value):
        raise LearningValidationError(f"{field} 必须是字符串数组")
    return _clean_values(value)


__all__ = ["LearningService"]
