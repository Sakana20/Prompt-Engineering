from __future__ import annotations

import re
from collections.abc import Sequence

from .models import CandidateKind, LearningCandidate, LearningStatus

SAFE_CANDIDATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,95}$")

COPY_RISK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("price", re.compile(r"(?:[0-9一二三四五六七八九十百]+(?:元|块|毛)|起步价|低至)")),
    ("promotion", re.compile(r"红包|优惠券|满减|折扣|补贴|免单|赠品")),
    ("platform_or_delivery", re.compile(r"淘宝|京东|抖音|外卖|配送|送到家|小时达")),
    ("action_call", re.compile(r"下单|购买|点链接|领取|快冲|赶紧冲")),
    ("claim", re.compile(r"销量|第一|最|治愈|治疗|功效|绝对")),
)
PERSON_RISK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("logo_or_brand", re.compile(r"logo|品牌|商标", re.IGNORECASE)),
    ("age", re.compile(r"未成年|儿童|中年|老年|大妈|阿姨")),
    ("exposure", re.compile(r"暴露|透视|低胸|超短")),
    ("real_person", re.compile(r"明星|网红|某某本人|一模一样|复刻")),
    ("fixed_constraint", re.compile(r"竖屏9:16|固定中景|直视镜头|无字幕|不手持商品")),
)


class LearningValidationError(ValueError):
    """Raised when learning data or a state transition is invalid."""


def validate_candidate_id(value: str) -> str:
    if not SAFE_CANDIDATE_ID.fullmatch(value):
        raise LearningValidationError("candidate_id 只能使用安全 ASCII 字母、数字、短横线和下划线")
    return value


def kind_from_cli(value: str) -> CandidateKind:
    try:
        return CandidateKind(value)
    except ValueError as exc:
        raise LearningValidationError("kind 只能是 copy 或 person") from exc


def validate_expected_revision(value: int) -> int:
    if value < 1:
        raise LearningValidationError("expected_revision 必须大于等于 1")
    return value


def allowed_transition(
    candidate: LearningCandidate,
    target: LearningStatus,
) -> None:
    allowed: dict[LearningStatus, frozenset[LearningStatus]] = {
        LearningStatus.PENDING: frozenset(
            {LearningStatus.EDITING, LearningStatus.READY_FOR_REVIEW}
        ),
        LearningStatus.EDITING: frozenset(
            {LearningStatus.EDITING, LearningStatus.READY_FOR_REVIEW}
        ),
        LearningStatus.READY_FOR_REVIEW: frozenset(
            {LearningStatus.APPROVED, LearningStatus.REJECTED}
        ),
        LearningStatus.REJECTED: frozenset({LearningStatus.EDITING}),
        LearningStatus.APPROVED: frozenset({LearningStatus.PUBLISHED}),
        LearningStatus.PUBLISHED: frozenset(),
    }
    if target not in allowed[candidate.status]:
        raise LearningValidationError(f"不允许从 {candidate.status.value} 转为 {target.value}")


def detect_risks(text: str, *, kind: CandidateKind) -> tuple[str, ...]:
    patterns = COPY_RISK_PATTERNS if kind is CandidateKind.COPY else PERSON_RISK_PATTERNS
    return tuple(name for name, pattern in patterns if pattern.search(text))


def duplicate_warnings(text: str, previous_texts: Sequence[tuple[str, str]]) -> tuple[str, ...]:
    normalized = "".join(text.split())
    warnings: list[str] = []
    for candidate_id, previous in previous_texts:
        other = "".join(previous.split())
        if normalized and normalized == other:
            warnings.append(f"exact:{candidate_id}")
            continue
        left = {normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))}
        right = {other[index : index + 2] for index in range(max(0, len(other) - 1))}
        union = left | right
        similarity = len(left & right) / len(union) if union else 0.0
        if similarity >= 0.72:
            warnings.append(f"similar:{candidate_id}:{similarity:.2f}")
    return tuple(warnings)
