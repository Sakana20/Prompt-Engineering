from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..source_blocks import learned_person_blocks, published_copy_block_contracts
from .models import CandidateKind, LearningCandidate, LearningStatus
from .publication import COPY_RESOURCE_NAME, reference_path
from .store import LearningStore

PREFLIGHT_BLOCKED_EXIT_CODE = 3


def _candidate_payload(candidate: LearningCandidate) -> dict[str, object]:
    return {str(key): value for key, value in candidate.to_dict().items()}


def _person_block_ids(path: Path) -> tuple[str, ...]:
    block_ids: set[str] = set()
    for block in learned_person_blocks(path):
        if block.block_type in {"identity", "hair", "outfit", "scene"}:
            block_ids.add(block.block_id)
    return tuple(sorted(block_ids))


def _published_block_ids(candidates: tuple[LearningCandidate, ...]) -> tuple[str, ...]:
    return tuple(
        sorted({block_id for candidate in candidates for block_id in candidate.published_block_ids})
    )


@dataclass(frozen=True, slots=True)
class LearningPreflightReport:
    approved_copy: tuple[LearningCandidate, ...]
    approved_person: tuple[LearningCandidate, ...]
    published_copy: tuple[LearningCandidate, ...]
    published_person: tuple[LearningCandidate, ...]
    formal_copy_block_ids: tuple[str, ...]
    formal_person_block_ids: tuple[str, ...]
    missing_copy_block_ids: tuple[str, ...]
    missing_person_block_ids: tuple[str, ...]
    schema_version: str = "1.0"

    @property
    def approved_count(self) -> int:
        return len(self.approved_copy) + len(self.approved_person)

    @property
    def published_count(self) -> int:
        return len(self.published_copy) + len(self.published_person)

    @property
    def publication_required(self) -> bool:
        return self.approved_count > 0

    @property
    def published_resources_verified(self) -> bool:
        return not self.missing_copy_block_ids and not self.missing_person_block_ids

    @property
    def required_actions(self) -> tuple[str, ...]:
        actions: list[str] = []
        if not self.published_resources_verified:
            actions.append("repair_published_resources")
        if self.publication_required:
            actions.append("codex_publish_approved")
        return tuple(actions)

    @property
    def ready_for_generation(self) -> bool:
        return not self.required_actions

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "ready_for_generation": self.ready_for_generation,
            "publication_required": self.publication_required,
            "published_resources_verified": self.published_resources_verified,
            "required_actions": list(self.required_actions),
            "approved_count": self.approved_count,
            "published_count": self.published_count,
            "approved": {
                "copy": [_candidate_payload(candidate) for candidate in self.approved_copy],
                "person": [_candidate_payload(candidate) for candidate in self.approved_person],
            },
            "published": {
                "copy": [_candidate_payload(candidate) for candidate in self.published_copy],
                "person": [_candidate_payload(candidate) for candidate in self.published_person],
            },
            "formal_resources": {
                "copy_block_ids": list(self.formal_copy_block_ids),
                "person_block_ids": list(self.formal_person_block_ids),
                "missing_copy_block_ids": list(self.missing_copy_block_ids),
                "missing_person_block_ids": list(self.missing_person_block_ids),
            },
        }


def inspect_learning_preflight(
    store: LearningStore,
    *,
    resource_root: Path | None = None,
) -> LearningPreflightReport:
    approved_copy = store.list(CandidateKind.COPY, status=LearningStatus.APPROVED)
    approved_person = store.list(CandidateKind.PERSON, status=LearningStatus.APPROVED)
    published_copy = store.list(CandidateKind.COPY, status=LearningStatus.PUBLISHED)
    published_person = store.list(CandidateKind.PERSON, status=LearningStatus.PUBLISHED)

    copy_path = reference_path(COPY_RESOURCE_NAME, root=resource_root)
    person_path = reference_path("person-prompt-source-blocks.md", root=resource_root)
    formal_copy_block_ids = tuple(sorted(published_copy_block_contracts(copy_path)))
    formal_person_block_ids = _person_block_ids(person_path)
    expected_copy_block_ids = _published_block_ids(published_copy)
    expected_person_block_ids = _published_block_ids(published_person)

    return LearningPreflightReport(
        approved_copy=approved_copy,
        approved_person=approved_person,
        published_copy=published_copy,
        published_person=published_person,
        formal_copy_block_ids=formal_copy_block_ids,
        formal_person_block_ids=formal_person_block_ids,
        missing_copy_block_ids=tuple(
            sorted(set(expected_copy_block_ids) - set(formal_copy_block_ids))
        ),
        missing_person_block_ids=tuple(
            sorted(set(expected_person_block_ids) - set(formal_person_block_ids))
        ),
    )


__all__ = [
    "PREFLIGHT_BLOCKED_EXIT_CODE",
    "LearningPreflightReport",
    "inspect_learning_preflight",
]
