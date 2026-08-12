from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, NewType

CandidateId = NewType("CandidateId", str)
Revision = NewType("Revision", int)


class CandidateKind(StrEnum):
    COPY = "copy"
    PERSON = "person"


class LearningStatus(StrEnum):
    PENDING = "pending"
    EDITING = "editing"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    candidate_id: CandidateId
    kind: CandidateKind
    revision: Revision
    action: str
    occurred_at: str
    from_status: LearningStatus | None
    to_status: LearningStatus
    details: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AsrToken:
    index: int
    text: str
    start_ms: int
    end_ms: int
    source: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class CopyLearningCandidate:
    candidate_id: CandidateId
    status: LearningStatus
    revision: Revision
    created_at: str
    updated_at: str
    source_media: str
    source_fingerprint: str
    source_date: str
    asr_cache_key: str
    provider: str
    model: str
    raw_transcript: str
    edited_transcript: str
    word_timeline: tuple[AsrToken, ...] = ()
    audio_conversion: tuple[tuple[str, str], ...] = ()
    risk_tags: tuple[str, ...] = ()
    similarity_hits: tuple[str, ...] = ()
    category_family: str = ""
    consumption_need: str = ""
    season: str = "all"
    source_usage: tuple[str, ...] = ()
    published_block_ids: tuple[str, ...] = ()
    rejection_reason: str = ""
    schema_version: str = "1.0"
    kind: str = field(default="copy_transcript", init=False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PersonPromptLearningCandidate:
    candidate_id: CandidateId
    status: LearningStatus
    revision: Revision
    created_at: str
    updated_at: str
    source_label: str
    raw_prompt: str
    edited_prompt: str
    identity_traits: tuple[str, ...] = ()
    hair_traits: tuple[str, ...] = ()
    outfit_traits: tuple[str, ...] = ()
    scene_traits: tuple[str, ...] = ()
    forbidden_traits: tuple[str, ...] = ()
    risk_tags: tuple[str, ...] = ()
    similarity_hits: tuple[str, ...] = ()
    published_block_ids: tuple[str, ...] = ()
    rejection_reason: str = ""
    schema_version: str = "1.0"
    kind: str = field(default="person_prompt", init=False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


LearningCandidate = CopyLearningCandidate | PersonPromptLearningCandidate
