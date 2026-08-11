from dataclasses import replace
from datetime import date

import pytest

from avatar_prompt_pipeline.models import (
    BenefitPoint,
    CampaignSpec,
    IssueCode,
    ValidationConfig,
    VisualProfile,
)
from avatar_prompt_pipeline.presets import TAOBAO_DEFAULT_CAMPAIGN
from avatar_prompt_pipeline.validation import (
    MARKED_REQUIRED_BENEFIT,
    REQUIRED_BENEFIT,
    copy_similarity,
    count_spoken_characters,
    strip_no_split_markers,
    temporal_context,
    validate_batch_diversity,
    validate_copy,
    validate_copy_mix,
    validate_source_logic,
    validate_visual_diversity,
    validate_visual_prompt,
    wrap_campaign_benefits,
)

VALID_COPY = (
    "下班赶上大雨，走到小区门口鞋子已经湿了一圈，临时买东西时我总怕选错款。"
    "[[NO_SPLIT]]淘宝闪购有最高12元无门槛红包[[/NO_SPLIT]]"
    "这双雨靴是清爽的浅卡其色，中筒款日常穿着利落，放在玄关不占地方，"
    "雨天补一双省心不少。"
)
VALID_VISUAL_PROMPT = (
    "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
    "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着商品，商品不由人物手持，"
    "人物不看商品、不接触商品，非商品区域无logo，无字幕。"
    "自然光照明，真实肤色和皮肤纹理，人物居中坐定，背景轻微虚化，整体年轻自然干净生活化。"
)


def test_valid_copy_passes_all_deterministic_rules() -> None:
    report = validate_copy(VALID_COPY)

    assert report.is_valid is True
    assert 80 <= report.character_count <= 100
    assert report.issues == ()


def test_copy_requires_campaign_disclosures() -> None:
    campaign = CampaignSpec(required_disclosures=("活动规则以页面展示为准",))

    report = validate_copy(VALID_COPY, campaign)

    assert any(issue.code is IssueCode.MISSING_DISCLOSURE for issue in report.issues)


def test_copy_rejects_unconfirmed_starting_price_from_style_samples() -> None:
    report = validate_copy(f"{VALID_COPY}，几块钱起")

    assert any(issue.code is IssueCode.UNCONFIRMED_PROMOTION for issue in report.issues)


def test_copy_allows_starting_price_when_current_campaign_confirms_it() -> None:
    campaign = CampaignSpec(
        benefit_points=(
            BenefitPoint(
                id="current-price",
                text="9.9元起",
                no_split=False,
            ),
        )
    )
    text = VALID_COPY.replace(
        "[[NO_SPLIT]]淘宝闪购有最高12元无门槛红包[[/NO_SPLIT]]",
        "9.9元起",
    )

    report = validate_copy(text, campaign)

    assert not any(issue.code is IssueCode.UNCONFIRMED_PROMOTION for issue in report.issues)


@pytest.mark.parametrize(
    "numeric_benefit",
    (
        "12元无门槛红包",
        "12.5元红包",
        "十二元大额红包",
        "红包最高25元",
        "红包金额二十五元",
    ),
)
def test_compliance_validation_rejects_numeric_redpacket_amounts(
    numeric_benefit: str,
) -> None:
    campaign = CampaignSpec(
        platform="淘宝闪购",
        benefit_points=(BenefitPoint(id="primary-benefit", text="大额红包", no_split=False),),
        no_split_phrases=("淘宝闪购有大额红包",),
    )
    text = (
        "下班回家想补点水果，[[NO_SPLIT]]淘宝闪购有大额红包[[/NO_SPLIT]]，"
        f"页面还写着{numeric_benefit}。西瓜切好放进果盘，饭后大家分着吃。"
    )
    config = ValidationConfig(
        min_characters=1,
        max_characters=200,
        banned_expressions=(),
        call_to_actions=(),
        forbid_numeric_redpacket_amounts=True,
    )

    report = validate_copy(text, campaign, config)

    assert any(issue.code is IssueCode.NUMERIC_REDPACKET_AMOUNT for issue in report.issues)


def test_compliance_validation_allows_fuzzy_benefit_and_unrelated_numeric_price() -> None:
    campaign = CampaignSpec(
        platform="淘宝闪购",
        benefit_points=(BenefitPoint(id="primary-benefit", text="大额红包", no_split=False),),
        no_split_phrases=("淘宝闪购有大额红包",),
        confirmed_claims=("商品价格12元",),
    )
    text = (
        "下班回家想补点水果，[[NO_SPLIT]]淘宝闪购有大额红包[[/NO_SPLIT]]，"
        "页面显示商品价格12元。西瓜切好放进果盘，饭后大家分着吃，买起来是福利价。"
    )
    config = ValidationConfig(
        min_characters=1,
        max_characters=200,
        banned_expressions=(),
        call_to_actions=(),
        forbid_numeric_redpacket_amounts=True,
    )

    report = validate_copy(text, campaign, config)

    assert not any(issue.code is IssueCode.NUMERIC_REDPACKET_AMOUNT for issue in report.issues)


@pytest.mark.parametrize(
    ("month", "expected_season"),
    [(3, "春季"), (6, "夏季"), (9, "秋季"), (12, "冬季")],
)
def test_temporal_context_uses_local_month_seasons(month: int, expected_season: str) -> None:
    context = temporal_context(date(2026, month, 1))

    assert f"当前月份：{month}月" in context
    assert f"当前季节：{expected_season}" in context


def test_summer_copy_rejects_winter_wording() -> None:
    text = VALID_COPY.replace("下班赶上大雨", "寒冷的冬天里")

    report = validate_copy(text, reference_date=date(2026, 8, 5))

    assert any(issue.code is IssueCode.SEASON_MISMATCH for issue in report.issues)


def test_winter_copy_allows_winter_wording() -> None:
    text = VALID_COPY.replace("下班赶上大雨", "寒冷的冬天里")

    report = validate_copy(text, reference_date=date(2026, 12, 5))

    assert not any(issue.code is IssueCode.SEASON_MISMATCH for issue in report.issues)


def test_summer_adapted_rewrite_passes_season_rule() -> None:
    text = VALID_COPY.replace("下班赶上大雨", "盛夏午后想喝点冰的")

    report = validate_copy(text, reference_date=date(2026, 8, 5))

    assert not any(issue.code is IssueCode.SEASON_MISMATCH for issue in report.issues)


def test_unconfirmed_current_weather_is_rejected() -> None:
    text = VALID_COPY.replace("下班赶上大雨", "今天下雨")

    report = validate_copy(text, reference_date=date(2026, 8, 5))

    assert any(issue.code is IssueCode.UNCONFIRMED_CURRENT_WEATHER for issue in report.issues)


def test_confirmed_current_weather_is_allowed() -> None:
    campaign = replace(TAOBAO_DEFAULT_CAMPAIGN, confirmed_claims=("今天下雨",))
    text = VALID_COPY.replace("下班赶上大雨", "今天下雨")

    report = validate_copy(text, campaign, reference_date=date(2026, 8, 5))

    assert not any(issue.code is IssueCode.UNCONFIRMED_CURRENT_WEATHER for issue in report.issues)


def test_copy_mix_accepts_exact_five_five_split_for_ten_tasks() -> None:
    modes = ["source_fill" if index % 2 == 0 else "human_rewrite" for index in range(10)]
    sources = [f"learn-{index:03d}" for index in range(10)]

    assert validate_copy_mix(modes, sources) == ()


def test_copy_mix_accepts_natural_fallback_with_exact_rewrite_half() -> None:
    modes = ["natural_generate" if index % 2 == 0 else "human_rewrite" for index in range(10)]
    sources = [
        "" if mode == "natural_generate" else f"learn-{index:03d}"
        for index, mode in enumerate(modes)
    ]

    assert validate_copy_mix(modes, sources) == ()


def test_copy_mix_rejects_source_metadata_on_natural_generate() -> None:
    issues = validate_copy_mix(
        ["natural_generate", "human_rewrite"],
        ["learn-001-combination", "learn-002-eating-order"],
        ["自然生成", "谁懂，真的太幸福了"],
        [("伪锚点",), ("谁懂", "太幸福了")],
    )

    assert any(issue.code is IssueCode.UNEXPECTED_SOURCE_METADATA for issue in issues)


def test_copy_mix_rejects_wrong_rewrite_ratio() -> None:
    modes = ["source_fill"] * 6 + ["human_rewrite"] * 4
    sources = [f"learn-{index:03d}" for index in range(10)]

    issues = validate_copy_mix(modes, sources)

    assert any(issue.code is IssueCode.COPY_MODE_RATIO_MISMATCH for issue in issues)


def test_copy_mix_rejects_missing_mode_and_source() -> None:
    issues = validate_copy_mix(["source_fill", "", "human_rewrite"], ["learn-001", "", ""])

    assert any(issue.code is IssueCode.MISSING_COPY_MODE for issue in issues)
    assert any(issue.code is IssueCode.MISSING_SOURCE_BLOCK_ID for issue in issues)


def test_copy_mix_rejects_duplicate_source_within_same_mode() -> None:
    issues = validate_copy_mix(
        ["source_fill", "human_rewrite", "source_fill", "human_rewrite"],
        ["learn-001", "learn-001", "learn-001", "learn-002"],
    )

    assert any(issue.code is IssueCode.DUPLICATE_SOURCE_BLOCK for issue in issues)


def test_copy_mix_accepts_rewrite_anchors_that_appear_in_script() -> None:
    issues = validate_copy_mix(
        ["source_fill", "human_rewrite"],
        ["learn-001", "learn-002"],
        ["原文填槽", "谁懂，今天就是想吃这一口，真是太幸福了"],
        [(), ("谁懂", "太幸福了")],
    )

    assert issues == ()


def test_copy_mix_allows_cross_season_source_with_nonseasonal_anchors() -> None:
    issues = validate_copy_mix(
        ["source_fill", "human_rewrite"],
        ["learn-001-combination", "learn-006-winter"],
        ["原文填槽", "盛夏吃上一份冰凉甜品，就是快乐的标配，听见挖冰沙的声音就开心"],
        [(), ("就是快乐的标配", "声音")],
    )

    assert issues == ()


def test_copy_mix_rejects_missing_or_unmatched_rewrite_anchors() -> None:
    issues = validate_copy_mix(
        ["source_fill", "human_rewrite"],
        ["learn-001", "learn-002"],
        ["原文填槽", "谁懂，今天就是想吃这一口"],
        [(), ("谁懂", "太幸福了")],
    )

    assert any(issue.code is IssueCode.INVALID_REWRITE_ANCHORS for issue in issues)


def test_beverage_rejects_food_only_source_fill_and_hunger_logic() -> None:
    issues = validate_source_logic(
        "不是瑞幸咖啡点不起，什么你说你不饿，人是铁饭是钢，一顿不吃饿的慌。",
        category="瑞幸咖啡",
        copy_mode="source_fill",
        source_block_id="learn-005-not-hungry",
        source_slot_values=("瑞幸咖啡", "早上想喝一杯"),
    )

    codes = {issue.code for issue in issues}
    assert IssueCode.SOURCE_BLOCK_INCOMPATIBLE in codes
    assert IssueCode.PRODUCT_LOGIC_MISMATCH in codes


def test_beverage_rewrite_can_reuse_non_category_language_without_hunger_logic() -> None:
    issues = validate_source_logic(
        "不是咖啡点不起，而是早上赶时间也想喝上一杯。",
        category="咖啡",
        copy_mode="human_rewrite",
        source_block_id="learn-005-not-hungry",
        source_slot_values=None,
    )

    assert issues == ()


def test_source_logic_rejects_unknown_source_block_id() -> None:
    issues = validate_source_logic(
        "谁懂，今天就是想吃这一口。",
        category="炸鸡",
        copy_mode="human_rewrite",
        source_block_id="learn-999-unknown",
        source_slot_values=None,
    )

    assert any(issue.code is IssueCode.SOURCE_BLOCK_INCOMPATIBLE for issue in issues)


def test_combination_block_rejects_campaign_facts_in_product_slots() -> None:
    issues = validate_source_logic(
        "蜜雪冰城现在奶茶加配送到家再加淘宝闪购外加最高12元无门槛红包都给你配好了。",
        category="蜜雪冰城奶茶",
        copy_mode="source_fill",
        source_block_id="learn-001-combination",
        source_slot_values=("蜜雪冰城", "奶茶", "配送到家", "淘宝闪购"),
    )

    assert any(issue.code is IssueCode.CAMPAIGN_IN_PRODUCT_SLOT for issue in issues)


def test_combination_block_rejects_campaign_facts_in_coordination_text() -> None:
    issues = validate_source_logic(
        "蜜雪冰城现在奶茶加珍珠再加椰果外加配送到家，淘宝闪购有红包。",
        category="蜜雪冰城奶茶",
        copy_mode="source_fill",
        source_block_id="learn-001-combination",
        source_slot_values=("蜜雪冰城", "奶茶", "珍珠", "椰果"),
    )

    assert any(issue.code is IssueCode.CAMPAIGN_IN_PRODUCT_SLOT for issue in issues)


def test_new_source_fill_rejects_empty_source_slot_values() -> None:
    issues = validate_source_logic(
        "谁懂，本来晚上不想吃的，但是点了一份哈密瓜，真的是太幸福了。",
        category="哈密瓜",
        copy_mode="source_fill",
        source_block_id="learn-008-evening",
        source_slot_values=(),
    )

    assert any(issue.code is IssueCode.INVALID_SOURCE_BINDINGS for issue in issues)


def test_legacy_source_fill_without_source_slot_field_remains_readable() -> None:
    issues = validate_source_logic(
        "谁懂，本来晚上不想吃的，但是点了一份哈密瓜，真的是太幸福了。",
        category="哈密瓜",
        copy_mode="source_fill",
        source_block_id="learn-008-evening",
        source_slot_values=None,
    )

    assert issues == ()


def test_combination_block_accepts_product_components_and_separate_campaign_sentence() -> None:
    issues = validate_source_logic(
        "北京烤鸭现在整只烤鸭加椒盐鸭架再加荷叶饼外加甜面酱，"
        "送到手还是温热的，葱丝黄瓜条都给你配好了。"
        "淘宝闪购有最高12元无门槛红包。",
        category="烤鸭套餐",
        copy_mode="source_fill",
        source_block_id="learn-001-combination",
        source_slot_values=(
            "北京烤鸭",
            "整只烤鸭",
            "椒盐鸭架",
            "荷叶饼",
            "甜面酱",
            "送到手还是温热的",
            "葱丝黄瓜条",
        ),
    )

    assert issues == ()


def test_visual_prompt_rejects_prompt_shorter_than_contract() -> None:
    prompt = VALID_VISUAL_PROMPT.replace(
        "自然光照明，真实肤色和皮肤纹理，人物居中坐定，背景轻微虚化，整体年轻自然干净生活化。",
        "",
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.VISUAL_PROMPT_TOO_SHORT in codes


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


def test_campaign_marker_helpers_are_idempotent_and_lossless() -> None:
    unwrapped = strip_no_split_markers(VALID_COPY)

    assert wrap_campaign_benefits(unwrapped, campaign=TAOBAO_DEFAULT_CAMPAIGN) == VALID_COPY
    assert wrap_campaign_benefits(VALID_COPY, campaign=TAOBAO_DEFAULT_CAMPAIGN) == VALID_COPY
    assert strip_no_split_markers(VALID_COPY) == unwrapped


def test_custom_benefit_replaces_hard_coded_validation_contract() -> None:
    campaign = CampaignSpec(benefit_points=(BenefitPoint(id="custom", text="淘宝闪购满20减5"),))
    custom_copy = VALID_COPY.replace(
        "[[NO_SPLIT]]淘宝闪购有最高12元无门槛红包[[/NO_SPLIT]]",
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
        confirmed_claims=("0.1元起", "附近门店配送到家"),
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
    valid_prompt = VALID_VISUAL_PROMPT
    invalid_prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，人物面前桌上放着商品，商品不由人物手持，人物不看商品、不接触商品，"
        "身体朝向镜头，非商品区域无logo，无字幕。"
    )

    assert validate_visual_prompt(valid_prompt) == ()
    issues = validate_visual_prompt(invalid_prompt)
    assert any(issue.code is IssueCode.MISSING_EYE_CONTACT for issue in issues)


def test_visual_prompt_requires_chinese_young_woman_demographic() -> None:
    prompt = VALID_VISUAL_PROMPT.replace("年轻中国女生", "年轻亚洲女生")

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.MISSING_PERSON_DEMOGRAPHIC in codes
    assert IssueCode.PROHIBITED_PERSON_STYLE in codes


def test_visual_prompt_rejects_auntie_or_middle_aged_style() -> None:
    prompt = VALID_VISUAL_PROMPT.replace("年轻中国女生", "中国女生，大妈感")

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.PROHIBITED_PERSON_STYLE in codes


def test_visual_prompt_requires_no_handheld_product_constraint() -> None:
    missing_constraint = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着商品，人物不看商品、不接触商品，"
        "非商品区域无logo，无字幕。"
    )
    handheld_product = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着商品，商品不由人物手持，"
        "人物不看商品、不接触商品，人物手持商品，非商品区域无logo，无字幕。"
    )

    missing_issues = validate_visual_prompt(missing_constraint)
    handheld_issues = validate_visual_prompt(handheld_product)

    assert any(issue.code is IssueCode.MISSING_NO_HANDHELD_PRODUCT for issue in missing_issues)
    assert any(issue.code is IssueCode.HANDHELD_PRODUCT for issue in handheld_issues)


def test_visual_prompt_requires_talking_head_frame_and_background_scene() -> None:
    prompt = (
        "竖屏9:16，固定中景，手机实拍，年轻中国女生在玄关准备通勤，正面眼睛直视镜头，"
        "人物面前桌上放着商品，商品不由人物手持，人物不看商品、不接触商品，"
        "非商品区域无logo，无字幕。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.MISSING_TALKING_HEAD_FRAME in codes
    assert IssueCode.MISSING_BACKGROUND_ONLY_SCENE in codes


def test_visual_prompt_requires_no_product_gaze_or_contact() -> None:
    prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着商品，商品不由人物手持，"
        "非商品区域无logo，无字幕。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.MISSING_NO_PRODUCT_GAZE_OR_CONTACT in codes


def test_visual_prompt_rejects_prohibited_body_actions() -> None:
    prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，自然微笑，轻微点头并做少量手势，"
        "人物面前桌上放着商品，商品不由人物手持，人物不看商品、不接触商品，"
        "非商品区域无logo，无字幕。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.PROHIBITED_BODY_ACTION in codes


def test_visual_prompt_requires_logo_scope_and_no_subtitles() -> None:
    prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着商品，商品不由人物手持，"
        "人物不看商品、不接触商品。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.MISSING_LOGO_SCOPE in codes
    assert IssueCode.MISSING_NO_SUBTITLES in codes


def test_visual_prompt_rejects_overlong_prompt() -> None:
    prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着商品，商品不由人物手持，"
        "人物不看商品、不接触商品，非商品区域无logo，无字幕。"
        "真实摄影，手机实拍，生活记录，自然光，暖色调，真实曝光，真实白平衡，真实肤色，"
        "轻微背景虚化，保留真实皮肤纹理，不过度磨皮，不过度锐化，不过度美颜，HDR，8K，"
        "电影级真实摄影但没有商业广告摆拍感，干净通透。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.VISUAL_PROMPT_TOO_LONG in codes


def test_visual_prompt_requires_frontloaded_frame_style() -> None:
    prompt = (
        "数字人口播首帧，年轻中国女生坐在餐桌旁，场景只作为背景，正面眼睛直视镜头，"
        "商品不由人物手持，人物不看商品、不接触商品，非商品区域无logo，无字幕，"
        "竖屏9:16，固定中景，手机实拍。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.MISSING_FRONTLOADED_FRAME_STYLE in codes


def test_visual_prompt_requires_front_table_product_placement() -> None:
    prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，桌面摆放商品，商品不由人物手持，"
        "人物不看商品、不接触商品，非商品区域无logo，无字幕。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.MISSING_FRONT_TABLE_PRODUCT_PLACEMENT in codes


def test_visual_prompt_rejects_product_behind_person() -> None:
    prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着商品，商品不由人物手持，"
        "人物不看商品、不接触商品，非商品区域无logo，无字幕，商品在人物身后。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.PROHIBITED_BEHIND_PRODUCT_PLACEMENT in codes


def test_visual_prompt_rejects_non_product_logo_and_subtitles() -> None:
    prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，"
        "人物面前桌上放着商品，商品不由人物手持，人物不看商品、不接触商品，非商品区域无logo，无字幕，"
        "背景logo清晰，画面字幕位于底部。"
    )

    codes = {issue.code for issue in validate_visual_prompt(prompt)}

    assert IssueCode.PROHIBITED_NON_PRODUCT_LOGO in codes
    assert IssueCode.PROHIBITED_SUBTITLES in codes
