from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date

from .models import (
    CampaignSpec,
    CopyValidationReport,
    IssueCode,
    ValidationConfig,
    ValidationIssue,
    VisualProfile,
)
from .presets import TAOBAO_DEFAULT_BENEFIT, TAOBAO_DEFAULT_CAMPAIGN

DEFAULT_VALIDATION_CONFIG = ValidationConfig()
REQUIRED_BENEFIT = TAOBAO_DEFAULT_BENEFIT
NO_SPLIT_OPEN = "[[NO_SPLIT]]"
NO_SPLIT_CLOSE = "[[/NO_SPLIT]]"
MARKED_REQUIRED_BENEFIT = f"{NO_SPLIT_OPEN}{REQUIRED_BENEFIT}{NO_SPLIT_CLOSE}"
MIN_COPY_CHARACTERS = DEFAULT_VALIDATION_CONFIG.min_characters
MAX_COPY_CHARACTERS = DEFAULT_VALIDATION_CONFIG.max_characters
BANNED_EXPRESSIONS = DEFAULT_VALIDATION_CONFIG.banned_expressions
CALLS_TO_ACTION = DEFAULT_VALIDATION_CONFIG.call_to_actions
FORMAT_PREFIXES = DEFAULT_VALIDATION_CONFIG.format_prefixes
MAX_VISUAL_PROMPT_CHARACTERS = 180
MIN_VISUAL_PROMPT_CHARACTERS = 120
FRONTLOADED_FRAME_STYLE = "竖屏9:16，固定中景，手机实拍"
FRONTLOADED_FRAME_STYLE_WINDOW = 25
NO_HANDHELD_PRODUCT_PHRASES = (
    "不手持商品",
    "人物不手持商品",
    "不要手持商品",
    "禁止手持商品",
    "商品不由人物手持",
    "商品不被人物手持",
    "不拿起商品",
    "不要拿起商品",
    "无手持商品",
)
HANDHELD_PRODUCT_PATTERNS = (
    "人物手持商品",
    "人物手持",
    "手持商品",
    "手持包装",
    "拿着商品",
    "拿着包装",
    "拿起商品",
    "拿起包装",
    "手里拿着",
    "手上拿着",
    "手拿商品",
    "手拿包装",
    "递近镜头展示商品",
    "持续展示包装",
)
PROHIBITED_BODY_ACTION_PATTERNS = (
    "眨眼",
    "点头",
    "手势",
    "挥手",
    "重心变化",
    "身体重心",
)
LOGO_SCOPE_PHRASES = (
    "非商品区域无logo",
    "非商品区域无 logo",
    "其他地方不得包含logo",
    "其他地方不得包含 logo",
)
PROHIBITED_NON_PRODUCT_LOGO_PATTERNS = (
    "背景logo",
    "背景 logo",
    "墙面logo",
    "墙面 logo",
    "衣服logo",
    "衣服 logo",
    "服装logo",
    "服装 logo",
    "人物logo",
    "人物 logo",
    "道具logo",
    "道具 logo",
)
NO_SUBTITLES_PHRASES = (
    "无字幕",
    "没有字幕",
    "不得出现字幕",
    "不出现字幕",
)
PROHIBITED_SUBTITLE_PATTERNS = (
    "添加字幕",
    "带字幕",
    "字幕条",
    "字幕文本",
    "屏幕字幕",
    "画面字幕",
)
FRONT_TABLE_PRODUCT_PLACEMENT_PHRASES = (
    "人物面前桌上",
    "人物面前的桌上",
    "人物面前桌面",
    "人物面前的桌面",
    "人物面前台面",
    "人物面前的台面",
    "面前桌上",
    "面前的桌子上",
    "面前桌面",
    "面前台面",
)
PROHIBITED_BEHIND_PRODUCT_PLACEMENT_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"商品.{0,8}身后",
        r"身后.{0,8}商品",
        r"商品.{0,8}背后",
        r"背后.{0,8}商品",
        r"商品.{0,8}背景里",
        r"背景里.{0,8}商品",
        r"商品.{0,8}背景中",
        r"背景中.{0,8}商品",
        r"商品.{0,8}远处",
        r"远处.{0,8}商品",
        r"商品.{0,8}侧后方",
        r"侧后方.{0,8}商品",
        r"商品.{0,8}画面边缘",
        r"画面边缘.{0,8}商品",
    )
)
TALKING_HEAD_FRAME_PHRASES = (
    "数字人口播首帧",
    "口播首帧",
    "正面口播首帧",
)
BACKGROUND_ONLY_SCENE_PHRASES = (
    "场景只作为背景",
    "场景仅作为背景",
    "作为背景",
    "背景前",
)
NO_PRODUCT_GAZE_OR_CONTACT_PHRASES = (
    "人物不看商品",
    "不看商品",
)
NO_PRODUCT_CONTACT_PHRASES = (
    "不接触商品",
    "人物不接触商品",
    "不触碰商品",
)
REQUIRED_PERSON_DEMOGRAPHIC_PHRASES = (
    "中国女生",
    "中国女性",
)
PROHIBITED_PERSON_STYLE_PATTERNS = (
    "亚洲女生",
    "亚洲女性",
    "大妈",
    "阿姨",
    "中年女性",
    "中老年",
    "老年女性",
    "老气",
)
UNCONFIRMED_STARTING_PRICE_PATTERN = re.compile(r"(?:\d+(?:\.\d+)?元?|几块钱)起")
SEASON_NAMES = {
    "spring": "春季",
    "summer": "夏季",
    "autumn": "秋季",
    "winter": "冬季",
}
SEASON_TERMS = {
    "spring": ("春天", "春日", "春季", "开春", "暮春"),
    "summer": ("夏天", "夏日", "夏季", "盛夏", "炎炎夏日", "酷暑", "大热天", "天气炎热"),
    "autumn": ("秋天", "秋日", "秋季", "深秋", "入秋"),
    "winter": ("冬天", "冬日", "冬季", "寒冬", "寒冷", "天一冷", "天气冷", "冷飕飕"),
}
CURRENT_WEATHER_PATTERN = re.compile(
    r"(?:今天|现在|这会儿|外面|最近|刚好|刚刚|这两天).{0,4}"
    r"(?:下雨|下雪|刮风|降温|升温|大太阳|大晴天|阴天)"
)


def season_for_month(month: int) -> str:
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    if month in (12, 1, 2):
        return "winter"
    raise ValueError("月份必须在 1 到 12 之间")


def temporal_context(reference_date: date | None = None) -> str:
    resolved_date = reference_date or date.today()
    season = season_for_month(resolved_date.month)
    return (
        f"当前本地日期：{resolved_date.isoformat()}\n"
        f"当前月份：{resolved_date.month}月\n"
        f"按月份划分的当前季节：{SEASON_NAMES[season]}\n"
        "不得使用其他季节的场景或明显相反的冷热描述。"
        "今天下雨、外面降温等实时天气只能来自当前任务明确确认的资料；未提供时不要写。"
    )


def strip_no_split_markers(text: str) -> str:
    return text.replace(NO_SPLIT_OPEN, "").replace(NO_SPLIT_CLOSE, "")


def wrap_required_benefit(text: str) -> str:
    if MARKED_REQUIRED_BENEFIT in text:
        return text
    return text.replace(REQUIRED_BENEFIT, MARKED_REQUIRED_BENEFIT)


def wrap_campaign_benefits(text: str, campaign: CampaignSpec) -> str:
    wrapped = text
    for phrase in campaign.no_split_phrases:
        marked = f"{NO_SPLIT_OPEN}{phrase}{NO_SPLIT_CLOSE}"
        if marked not in wrapped:
            wrapped = wrapped.replace(phrase, marked)
    for benefit in campaign.benefit_points:
        marked = f"{NO_SPLIT_OPEN}{benefit.text}{NO_SPLIT_CLOSE}"
        if benefit.no_split and marked not in wrapped:
            wrapped = wrapped.replace(benefit.text, marked)
    return wrapped


def count_spoken_characters(text: str) -> int:
    return len(re.sub(r"\s+", "", strip_no_split_markers(text)))


def validate_copy(
    text: str,
    campaign: CampaignSpec = TAOBAO_DEFAULT_CAMPAIGN,
    validation_config: ValidationConfig = DEFAULT_VALIDATION_CONFIG,
    *,
    reference_date: date | None = None,
) -> CopyValidationReport:
    cleaned = text.replace("\x00", "").strip()
    count = count_spoken_characters(cleaned)
    issues: list[ValidationIssue] = []
    if count < validation_config.min_characters:
        issues.append(
            ValidationIssue(
                IssueCode.TOO_SHORT,
                f"口播少于 {validation_config.min_characters} 字",
                str(count),
            )
        )
    if count > validation_config.max_characters:
        issues.append(
            ValidationIssue(
                IssueCode.TOO_LONG,
                f"口播超过 {validation_config.max_characters} 字",
                str(count),
            )
        )
    if cleaned.count(NO_SPLIT_OPEN) != cleaned.count(NO_SPLIT_CLOSE):
        issues.append(
            ValidationIssue(
                IssueCode.MALFORMED_NO_SPLIT_MARKER,
                "NO_SPLIT 标签必须成对出现",
            )
        )
    expression_scope = strip_no_split_markers(cleaned)
    if campaign.platform and campaign.platform not in cleaned:
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_PLATFORM,
                "缺少活动平台名",
                campaign.platform,
            )
        )
    for phrase in campaign.no_split_phrases:
        marked = f"{NO_SPLIT_OPEN}{phrase}{NO_SPLIT_CLOSE}"
        if marked not in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.MISSING_NO_SPLIT_MARKER,
                    "组合保护片段必须使用 NO_SPLIT 标签完整包裹",
                    marked,
                )
            )
    for benefit in campaign.benefit_points:
        if benefit.required and benefit.exact_match and benefit.text not in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.MISSING_BENEFIT,
                    f"缺少必填利益点：{benefit.id}",
                    benefit.text,
                )
            )
            continue
        marked = f"{NO_SPLIT_OPEN}{benefit.text}{NO_SPLIT_CLOSE}"
        if benefit.required and benefit.no_split and marked not in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.MISSING_NO_SPLIT_MARKER,
                    f"利益点 {benefit.id} 必须使用 NO_SPLIT 标签完整包裹",
                    marked,
                )
            )
        if benefit.text in expression_scope:
            expression_scope = expression_scope.replace(benefit.text, "")
    for disclosure in campaign.required_disclosures:
        if disclosure not in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.MISSING_DISCLOSURE,
                    "缺少必须披露内容",
                    disclosure,
                )
            )
    promotion_scope = expression_scope
    for confirmed_text in (
        *campaign.no_split_phrases,
        *campaign.required_disclosures,
        *campaign.confirmed_claims,
    ):
        promotion_scope = promotion_scope.replace(confirmed_text, "")
    if unconfirmed_promotion := UNCONFIRMED_STARTING_PRICE_PATTERN.search(promotion_scope):
        issues.append(
            ValidationIssue(
                IssueCode.UNCONFIRMED_PROMOTION,
                "出现当前活动未确认的起步价或低价利益点",
                unconfirmed_promotion.group(0),
            )
        )

    current_season = season_for_month((reference_date or date.today()).month)
    mismatched_season: str | None = None
    for season, terms in SEASON_TERMS.items():
        if season == current_season:
            continue
        mismatched_season = next((term for term in terms if term in expression_scope), None)
        if mismatched_season is not None:
            break
    if mismatched_season is not None:
        issues.append(
            ValidationIssue(
                IssueCode.SEASON_MISMATCH,
                f"季节表达与当前{SEASON_NAMES[current_season]}不符",
                mismatched_season,
            )
        )

    weather_scope = expression_scope
    for confirmed_text in campaign.confirmed_claims:
        weather_scope = weather_scope.replace(confirmed_text, "")
    if unconfirmed_weather := CURRENT_WEATHER_PATTERN.search(weather_scope):
        issues.append(
            ValidationIssue(
                IssueCode.UNCONFIRMED_CURRENT_WEATHER,
                "出现当前任务未确认的实时天气描述",
                unconfirmed_weather.group(0),
            )
        )

    banned_expressions = (*validation_config.banned_expressions, *campaign.forbidden_expressions)
    for expression in banned_expressions:
        if expression in expression_scope:
            issues.append(ValidationIssue(IssueCode.BANNED_EXPRESSION, "出现禁止表达", expression))
    for expression in validation_config.call_to_actions:
        if expression in cleaned:
            issues.append(ValidationIssue(IssueCode.CALL_TO_ACTION, "出现行动引导", expression))
    if "\n" in cleaned or cleaned.startswith(validation_config.format_prefixes):
        issues.append(
            ValidationIssue(
                IssueCode.FORMAT_VIOLATION,
                "最终口播必须是单段正文，不能包含标题、列表或换行",
            )
        )
    return CopyValidationReport(character_count=count, issues=tuple(issues))


def _bigrams(text: str) -> set[str]:
    normalized = re.sub(r"[\W_]+", "", text)
    return {normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))}


def copy_similarity(left: str, right: str) -> float:
    left_bigrams = _bigrams(left)
    right_bigrams = _bigrams(right)
    union = left_bigrams | right_bigrams
    if not union:
        return 1.0 if left.strip() == right.strip() else 0.0
    return len(left_bigrams & right_bigrams) / len(union)


def validate_batch_diversity(
    copies: Sequence[str], *, similarity_threshold: float = 0.72
) -> tuple[ValidationIssue, ...]:
    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("相似度阈值必须在 0 到 1 之间")
    issues: list[ValidationIssue] = []
    for left_index, left in enumerate(copies):
        for right_index in range(left_index + 1, len(copies)):
            right = copies[right_index]
            pair = f"{left_index + 1},{right_index + 1}"
            if left.strip() == right.strip():
                issues.append(ValidationIssue(IssueCode.DUPLICATE_COPY, "批次存在重复文案", pair))
                continue
            similarity = copy_similarity(left, right)
            if similarity >= similarity_threshold:
                issues.append(
                    ValidationIssue(
                        IssueCode.HIGH_SIMILARITY,
                        f"批次文案相似度过高：{similarity:.2f}",
                        pair,
                    )
                )
    return tuple(issues)


def validate_visual_diversity(
    profiles: Sequence[VisualProfile],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    seen_identities: dict[str, int] = {}
    seen_outfits: dict[str, int] = {}
    for index, profile in enumerate(profiles, start=1):
        identity = profile.identity_key.strip()
        outfit = profile.outfit_key.strip()
        if not identity or not outfit:
            raise ValueError("人物身份键和服装键不能为空")
        if identity in seen_identities:
            issues.append(
                ValidationIssue(
                    IssueCode.DUPLICATE_PERSON,
                    "批次存在重复人物",
                    f"{seen_identities[identity]},{index}",
                )
            )
        else:
            seen_identities[identity] = index
        if outfit in seen_outfits:
            issues.append(
                ValidationIssue(
                    IssueCode.DUPLICATE_OUTFIT,
                    "批次存在重复服装",
                    f"{seen_outfits[outfit]},{index}",
                )
            )
        else:
            seen_outfits[outfit] = index
    return tuple(issues)


def validate_visual_prompt(prompt: str) -> tuple[ValidationIssue, ...]:
    cleaned = prompt.replace("\x00", "").strip()
    visual_count = len(re.sub(r"\s+", "", cleaned))
    issues: list[ValidationIssue] = []
    if visual_count < MIN_VISUAL_PROMPT_CHARACTERS:
        issues.append(
            ValidationIssue(
                IssueCode.VISUAL_PROMPT_TOO_SHORT,
                f"人物 Prompt 少于 {MIN_VISUAL_PROMPT_CHARACTERS} 字",
                str(visual_count),
            )
        )
    if visual_count > MAX_VISUAL_PROMPT_CHARACTERS:
        issues.append(
            ValidationIssue(
                IssueCode.VISUAL_PROMPT_TOO_LONG,
                f"人物 Prompt 超过 {MAX_VISUAL_PROMPT_CHARACTERS} 字",
                str(visual_count),
            )
        )
    if FRONTLOADED_FRAME_STYLE not in cleaned[:FRONTLOADED_FRAME_STYLE_WINDOW]:
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_FRONTLOADED_FRAME_STYLE,
                "人物 Prompt 必须在开头前置竖屏9:16、固定中景和手机实拍",
                FRONTLOADED_FRAME_STYLE,
            )
        )
    if not any(phrase in cleaned for phrase in TALKING_HEAD_FRAME_PHRASES):
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_TALKING_HEAD_FRAME,
                "人物 Prompt 必须明确是数字人口播首帧",
                "数字人口播首帧",
            )
        )
    if not any(phrase in cleaned for phrase in BACKGROUND_ONLY_SCENE_PHRASES):
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_BACKGROUND_ONLY_SCENE,
                "人物 Prompt 必须明确场景只作为背景",
                "场景只作为背景",
            )
        )
    if "直视镜头" not in cleaned:
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_EYE_CONTACT,
                "人物 Prompt 必须明确包含直视镜头",
                "直视镜头",
            )
        )
    if not any(phrase in cleaned for phrase in REQUIRED_PERSON_DEMOGRAPHIC_PHRASES):
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_PERSON_DEMOGRAPHIC,
                "人物 Prompt 必须明确人物为中国女生",
                "中国女生",
            )
        )
    for pattern in PROHIBITED_PERSON_STYLE_PATTERNS:
        if pattern in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.PROHIBITED_PERSON_STYLE,
                    "人物 Prompt 不能使用旧地域口径或大妈、阿姨、中老年方向",
                    pattern,
                )
            )
    if not any(phrase in cleaned for phrase in NO_PRODUCT_GAZE_OR_CONTACT_PHRASES) or not any(
        phrase in cleaned for phrase in NO_PRODUCT_CONTACT_PHRASES
    ):
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_NO_PRODUCT_GAZE_OR_CONTACT,
                "人物 Prompt 必须明确人物不看商品且不接触商品",
                "人物不看商品、不接触商品",
            )
        )
    if not any(phrase in cleaned for phrase in NO_HANDHELD_PRODUCT_PHRASES):
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_NO_HANDHELD_PRODUCT,
                "人物 Prompt 必须明确包含不手持商品约束",
                "不手持商品",
            )
        )
    handheld_scope = cleaned
    for allowed_phrase in NO_HANDHELD_PRODUCT_PHRASES:
        handheld_scope = handheld_scope.replace(allowed_phrase, "")
    for pattern in HANDHELD_PRODUCT_PATTERNS:
        if pattern in handheld_scope:
            issues.append(
                ValidationIssue(
                    IssueCode.HANDHELD_PRODUCT,
                    "人物 Prompt 不能让人物手持商品",
                    pattern,
                )
            )
    if not any(phrase in cleaned for phrase in LOGO_SCOPE_PHRASES):
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_LOGO_SCOPE,
                "人物 Prompt 必须明确仅商品可包含 logo，非商品区域无 logo",
                "非商品区域无logo",
            )
        )
    for pattern in PROHIBITED_NON_PRODUCT_LOGO_PATTERNS:
        if pattern in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.PROHIBITED_NON_PRODUCT_LOGO,
                    "人物 Prompt 不能在商品之外的位置包含 logo",
                    pattern,
                )
            )
    if not any(phrase in cleaned for phrase in NO_SUBTITLES_PHRASES):
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_NO_SUBTITLES,
                "人物 Prompt 必须明确无字幕",
                "无字幕",
            )
        )
    subtitle_scope = cleaned
    for allowed_phrase in NO_SUBTITLES_PHRASES:
        subtitle_scope = subtitle_scope.replace(allowed_phrase, "")
    for pattern in PROHIBITED_SUBTITLE_PATTERNS:
        if pattern in subtitle_scope:
            issues.append(
                ValidationIssue(
                    IssueCode.PROHIBITED_SUBTITLES,
                    "人物 Prompt 不能出现字幕",
                    pattern,
                )
            )
    if not any(phrase in cleaned for phrase in FRONT_TABLE_PRODUCT_PLACEMENT_PHRASES):
        issues.append(
            ValidationIssue(
                IssueCode.MISSING_FRONT_TABLE_PRODUCT_PLACEMENT,
                "人物 Prompt 必须明确商品放在人物面前的桌面或台面上",
                "人物面前桌上",
            )
        )
    for placement_pattern in PROHIBITED_BEHIND_PRODUCT_PLACEMENT_PATTERNS:
        if placement_pattern.search(cleaned):
            issues.append(
                ValidationIssue(
                    IssueCode.PROHIBITED_BEHIND_PRODUCT_PLACEMENT,
                    "人物 Prompt 不能把商品放在人物身后、背景里、远处或侧后方",
                    placement_pattern.pattern,
                )
            )
    for pattern in PROHIBITED_BODY_ACTION_PATTERNS:
        if pattern in cleaned:
            issues.append(
                ValidationIssue(
                    IssueCode.PROHIBITED_BODY_ACTION,
                    "人物 Prompt 仅允许自然微笑，不能包含眨眼、点头、手势或重心变化",
                    pattern,
                )
            )
    return tuple(issues)
