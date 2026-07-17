import pytest

from avatar_prompt_pipeline.models import (
    BenefitPoint,
    CampaignSpec,
    IssueCode,
    ValidationConfig,
    VisualProfile,
)
from avatar_prompt_pipeline.validation import (
    MARKED_REQUIRED_BENEFIT,
    REQUIRED_BENEFIT,
    copy_similarity,
    count_spoken_characters,
    strip_no_split_markers,
    validate_batch_diversity,
    validate_copy,
    validate_visual_diversity,
    validate_visual_prompt,
    wrap_campaign_benefits,
    wrap_required_benefit,
)

VALID_COPY = (
    "下班赶上大雨，走到小区门口鞋子已经湿了一圈，临时买东西时我总怕选错款。"
    "淘宝闪购[[NO_SPLIT]]最高12元无门槛红包[[/NO_SPLIT]]"
    "这双雨靴是清爽的浅卡其色，中筒款日常穿着利落，放在玄关不占地方，"
    "雨天补一双省心不少。"
)


def test_valid_copy_passes_all_deterministic_rules() -> None:
    report = validate_copy(VALID_COPY)

    assert report.is_valid is True
    assert 80 <= report.character_count <= 100
    assert report.issues == ()


def test_required_highest_benefit_does_not_trigger_banned_single_character() -> None:
    report = validate_copy(VALID_COPY)

    assert not any(
        issue.code is IssueCode.BANNED_EXPRESSION and issue.value == "最" for issue in report.issues
    )


def test_no_split_markers_do_not_count_as_spoken_characters() -> None:
    assert count_spoken_characters(MARKED_REQUIRED_BENEFIT) == len(REQUIRED_BENEFIT)


def test_unwrapped_benefit_is_rejected() -> None:
    report = validate_copy(strip_no_split_markers(VALID_COPY))

    assert any(issue.code is IssueCode.MISSING_NO_SPLIT_MARKER for issue in report.issues)


def test_benefit_marker_helpers_are_idempotent_and_lossless() -> None:
    unwrapped = strip_no_split_markers(VALID_COPY)

    assert wrap_required_benefit(unwrapped) == VALID_COPY
    assert wrap_required_benefit(VALID_COPY) == VALID_COPY
    assert strip_no_split_markers(VALID_COPY) == unwrapped


def test_custom_benefit_replaces_hard_coded_validation_contract() -> None:
    campaign = CampaignSpec(benefit_points=(BenefitPoint(id="custom", text="淘宝闪购满20减5"),))
    custom_copy = VALID_COPY.replace(
        MARKED_REQUIRED_BENEFIT,
        "[[NO_SPLIT]]淘宝闪购满20减5[[/NO_SPLIT]]",
    )

    assert validate_copy(custom_copy, campaign).is_valid is True
    assert validate_copy(custom_copy).is_valid is False


def test_exact_benefit_can_be_embedded_in_taobao_context() -> None:
    campaign = CampaignSpec(
        platform="淘宝闪购",
        benefit_points=(BenefitPoint(id="custom", text="最高25元无门槛红包"),),
    )
    copy = (
        "下班路上想顺手买点水果，看到附近还有西瓜可选，淘宝闪购现在发了福利，有"
        "[[NO_SPLIT]]最高25元无门槛红包[[/NO_SPLIT]]可以用。"
        "买回来切几块放进果盘，饭后大家分着吃，临时补一份水果也不用绕远路。"
    )

    assert validate_copy(copy, campaign).is_valid is True


def test_call_to_action_rules_come_from_validation_config() -> None:
    campaign = CampaignSpec(
        platform="淘宝闪购",
        benefit_points=(BenefitPoint(id="custom", text="最高25元无门槛红包"),),
    )
    promo_validation = ValidationConfig(call_to_actions=("直播间", "立即购买"))
    copy = (
        "早八人想喝咖啡，淘宝闪购现在发了福利，有"
        "[[NO_SPLIT]]最高25元无门槛红包[[/NO_SPLIT]]可以用。"
        "选好附近门店后下单更省心，咖啡送到手边也不用特意绕路等待。"
        "点击左下角链接看看吧，喜欢就赶紧冲。"
    )

    assert validate_copy(copy, campaign, promo_validation).is_valid is True
    assert any(issue.code is IssueCode.CALL_TO_ACTION for issue in validate_copy(copy).issues)


def test_project_no_split_phrase_must_wrap_combined_benefit_text() -> None:
    campaign = CampaignSpec(
        platform="淘宝闪购",
        benefit_points=(
            BenefitPoint(
                id="primary-benefit",
                text="最高25元无门槛红包",
                no_split=False,
                priority=1,
            ),
            BenefitPoint(
                id="allowance-card-benefit",
                text="还可以叠加九折津贴卡",
                required=False,
                no_split=False,
                priority=2,
            ),
        ),
        no_split_phrases=("最高25元无门槛红包，还可以叠加九折津贴卡",),
    )
    copy = (
        "早八想喝霸王茶姬，淘宝闪购现在发福利，有"
        "[[NO_SPLIT]]最高25元无门槛红包，还可以叠加九折津贴卡[[/NO_SPLIT]]。"
        "附近门店配送到家，看到0.1元起的选择就顺手下单，官方链接就在左下角，今天想喝就赶紧冲。"
    )
    split_copy = copy.replace(
        "[[NO_SPLIT]]最高25元无门槛红包，还可以叠加九折津贴卡[[/NO_SPLIT]]",
        "[[NO_SPLIT]]最高25元无门槛红包[[/NO_SPLIT]]，"
        "[[NO_SPLIT]]还可以叠加九折津贴卡[[/NO_SPLIT]]",
    )

    assert validate_copy(copy, campaign, ValidationConfig(call_to_actions=())).is_valid is True
    assert any(
        issue.code is IssueCode.MISSING_NO_SPLIT_MARKER
        for issue in validate_copy(
            split_copy, campaign, ValidationConfig(call_to_actions=())
        ).issues
    )
    wrapped = wrap_campaign_benefits("最高25元无门槛红包，还可以叠加九折津贴卡，0.1元起", campaign)
    assert "[[NO_SPLIT]]0.1元起[[/NO_SPLIT]]" not in wrapped


def test_multiple_and_no_benefit_campaigns_are_supported() -> None:
    campaign = CampaignSpec(
        benefit_points=(
            BenefitPoint(id="first", text="活动利益点甲", priority=1),
            BenefitPoint(id="second", text="活动利益点乙", priority=2),
        )
    )
    copy = (
        "下班准备回家时想顺手买点日用品，这款收纳袋适合把桌面零碎集中放好，"
        "[[NO_SPLIT]]活动利益点甲[[/NO_SPLIT]]和"
        "[[NO_SPLIT]]活动利益点乙[[/NO_SPLIT]]都能用，"
        "拿回家放在柜子旁，需要整理时直接取出来，平时找东西也少翻几个抽屉。"
    )
    no_benefit_copy = (
        "换季收拾衣柜时，散在抽屉里的小物件总要重新归类。这款收纳袋可以把同类东西集中"
        "放在一起，整理完直接放进柜子，之后需要时按袋取出，不用每次把整个抽屉重新翻一遍，"
        "找起来也更清楚。"
    )

    assert validate_copy(copy, campaign).is_valid is True
    assert validate_copy(no_benefit_copy, CampaignSpec()).is_valid is True
    assert wrap_campaign_benefits("活动利益点甲", campaign).startswith("[[NO_SPLIT]]")


def test_configured_platform_is_required_in_copy() -> None:
    campaign = CampaignSpec(
        platform="淘宝闪购",
        benefit_points=(
            BenefitPoint(id="primary-benefit", text="最高25元无门槛红包", no_split=False),
        ),
    )
    copy_without_platform = (
        "早八想喝咖啡，看到附近门店还能送到家，"
        "现在有最高25元无门槛红包可以用。"
        "点好热拿铁后直接等配送，路上不用绕去门店，"
        "到工位就能喝上，上午开会前也不耽误时间，"
        "临时想喝一杯也不用打乱手头安排。"
    )

    report = validate_copy(copy_without_platform, campaign, ValidationConfig(call_to_actions=()))

    assert any(issue.code is IssueCode.MISSING_PLATFORM for issue in report.issues)


def test_malformed_no_split_tags_are_rejected() -> None:
    malformed = VALID_COPY.replace("[[/NO_SPLIT]]", "")

    assert any(
        issue.code is IssueCode.MALFORMED_NO_SPLIT_MARKER
        for issue in validate_copy(malformed).issues
    )


def test_previous_benefit_wording_is_rejected() -> None:
    previous_wording = VALID_COPY.replace(
        REQUIRED_BENEFIT,
        "高至12元无门槛红包",
    )

    report = validate_copy(previous_wording)

    assert any(issue.code is IssueCode.MISSING_BENEFIT for issue in report.issues)


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


def test_visual_prompt_requires_direct_eye_contact() -> None:
    valid_prompt = "年轻亚洲女生坐在餐桌旁，正面眼睛直视镜头，商品不由人物手持，竖屏9:16。"
    invalid_prompt = "年轻亚洲女生坐在餐桌旁，商品不由人物手持，身体朝向镜头，竖屏9:16。"

    assert validate_visual_prompt(valid_prompt) == ()
    issues = validate_visual_prompt(invalid_prompt)
    assert any(issue.code is IssueCode.MISSING_EYE_CONTACT for issue in issues)


def test_visual_prompt_requires_no_handheld_product_constraint() -> None:
    missing_constraint = "年轻亚洲女生坐在餐桌旁，正面眼睛直视镜头，桌面摆放商品，竖屏9:16。"
    handheld_product = (
        "年轻亚洲女生坐在餐桌旁，正面眼睛直视镜头，商品不由人物手持，人物手持商品，竖屏9:16。"
    )

    missing_issues = validate_visual_prompt(missing_constraint)
    handheld_issues = validate_visual_prompt(handheld_product)

    assert any(issue.code is IssueCode.MISSING_NO_HANDHELD_PRODUCT for issue in missing_issues)
    assert any(issue.code is IssueCode.HANDHELD_PRODUCT for issue in handheld_issues)
