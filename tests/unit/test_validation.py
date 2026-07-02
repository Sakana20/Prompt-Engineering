import pytest

from avatar_prompt_pipeline.models import IssueCode, VisualProfile
from avatar_prompt_pipeline.validation import (
    REQUIRED_BENEFIT,
    copy_similarity,
    validate_batch_diversity,
    validate_copy,
    validate_visual_diversity,
)

VALID_COPY = (
    "下班赶上大雨，走到小区门口鞋子已经湿了一圈，临时买东西时我总怕选错款。"
    "淘宝闪购，最高12元无门槛红包天天享。"
    "这双雨靴是清爽的浅卡其色，中筒款日常穿着利落，放在玄关也不占地方，"
    "红包结算时直接抵扣，雨天补一双省心不少。"
)


def test_valid_copy_passes_all_deterministic_rules() -> None:
    report = validate_copy(VALID_COPY)

    assert report.is_valid is True
    assert 80 <= report.character_count <= 120
    assert report.issues == ()


def test_required_highest_benefit_does_not_trigger_banned_single_character() -> None:
    report = validate_copy(VALID_COPY)

    assert not any(
        issue.code is IssueCode.BANNED_EXPRESSION and issue.value == "最" for issue in report.issues
    )


def test_copy_reports_multiple_actionable_issues() -> None:
    report = validate_copy("姐妹们，立即购买，点击视频下方链接。")

    codes = {issue.code for issue in report.issues}
    assert IssueCode.TOO_SHORT in codes
    assert IssueCode.MISSING_BENEFIT in codes
    assert IssueCode.BANNED_EXPRESSION in codes
    assert IssueCode.CALL_TO_ACTION in codes


def test_copy_rejects_multiline_or_list_format() -> None:
    report = validate_copy(f"- 下班回家先收拾玄关。\n{REQUIRED_BENEFIT}")

    assert any(issue.code is IssueCode.FORMAT_VIOLATION for issue in report.issues)


def test_batch_diversity_detects_duplicates_and_high_similarity() -> None:
    slightly_changed = VALID_COPY.replace("清爽的浅卡其色", "耐看的浅卡其色")

    issues = validate_batch_diversity([VALID_COPY, VALID_COPY, slightly_changed])

    assert any(issue.code is IssueCode.DUPLICATE_COPY for issue in issues)
    assert any(issue.code is IssueCode.HIGH_SIMILARITY for issue in issues)


def test_similarity_threshold_must_be_a_probability() -> None:
    with pytest.raises(ValueError, match="相似度阈值"):
        validate_batch_diversity(["甲", "乙"], similarity_threshold=1.1)


def test_copy_similarity_is_symmetric() -> None:
    assert copy_similarity("雨天出门穿雨靴", "雨天通勤穿雨靴") == copy_similarity(
        "雨天通勤穿雨靴", "雨天出门穿雨靴"
    )


def test_visual_diversity_accepts_unique_people_and_outfits() -> None:
    profiles = [
        VisualProfile("圆脸短发", "黄色针织衫+白色长裤"),
        VisualProfile("长脸高马尾", "蓝色衬衫+卡其半裙"),
    ]

    assert validate_visual_diversity(profiles) == ()


def test_visual_diversity_reports_reused_person_and_outfit() -> None:
    profiles = [
        VisualProfile("圆脸短发", "黄色针织衫+白色长裤"),
        VisualProfile("圆脸短发", "黄色针织衫+白色长裤"),
    ]

    codes = {issue.code for issue in validate_visual_diversity(profiles)}
    assert codes == {IssueCode.DUPLICATE_PERSON, IssueCode.DUPLICATE_OUTFIT}


def test_visual_diversity_rejects_empty_keys() -> None:
    with pytest.raises(ValueError, match="不能为空"):
        validate_visual_diversity([VisualProfile("", "蓝色连衣裙")])
