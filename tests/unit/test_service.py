from datetime import date

import pytest

from avatar_prompt_pipeline.models import (
    BenefitPoint,
    CampaignSpec,
    LanguageStyle,
    ProductBrief,
    ValidationConfig,
)
from avatar_prompt_pipeline.service import compose_prompt_package, render_avatar_prompt


def test_compose_prompt_package_injects_only_confirmed_product_context() -> None:
    brief = ProductBrief(
        category="雨靴",
        product_name="浅卡其色中筒雨靴",
        selling_points=("中筒款式",),
        forbidden_claims=("绝对防滑",),
    )

    package = compose_prompt_package(brief, reference_date=date(2026, 8, 5))

    assert "{{PRODUCT_CONTEXT}}" not in package.copywriting_prompt
    assert "商品名称：浅卡其色中筒雨靴" in package.copywriting_prompt
    assert "已确认卖点：中筒款式" in package.copywriting_prompt
    assert "禁止使用：绝对防滑" in package.copywriting_prompt
    assert "不要套用" not in package.copywriting_prompt
    assert "约占全文 20%" in package.copywriting_prompt
    assert "商品相关内容约占全文 50%" in package.copywriting_prompt
    assert "利益点与购买体验约占全文 30%" in package.copywriting_prompt
    assert "不要写成完整生活故事" in package.copywriting_prompt
    assert "不要单独写成播报口号" in package.copywriting_prompt
    assert "从完整正式学习库中按当前品类" in package.copywriting_prompt
    assert "【本次筛选的真人原文块】" in package.copywriting_prompt
    assert len(package.selected_copy_block_ids) == 4
    assert package.copy_learning_context_character_count < 7000
    assert "learn-006-winter" not in package.selected_copy_block_ids
    assert "learn-013-friends-at-home" not in package.selected_copy_block_ids
    assert "非改写序号优先为 `source_fill`" in package.copywriting_prompt
    assert "`human_rewrite` 的数量固定为" in package.copywriting_prompt
    assert "改用 `natural_generate`" in package.copywriting_prompt
    assert "至少保留其中两个可辨认的字眼或短语" in package.copywriting_prompt
    assert "不得写回“场景开场—商品承接—体验收束”" in package.copywriting_prompt
    assert "10 条始终包含 5 条 `human_rewrite`" in package.copywriting_prompt
    assert "同一批次不得重复原文块 ID" in package.copywriting_prompt
    assert "当前利益点" in package.copywriting_prompt
    assert "生成候选后必须使用与当前活动完全匹配的校验器检查" in package.copywriting_prompt
    assert "利益点[primary-benefit]" in package.copywriting_prompt
    assert "【语言风格】" in package.copywriting_prompt
    assert "当前本地日期：2026-08-05" in package.copywriting_prompt
    assert "当前月份：8月" in package.copywriting_prompt
    assert "按月份划分的当前季节：夏季" in package.copywriting_prompt
    assert "本次候选已标明 `source_fill` 季节兼容性" in package.copywriting_prompt
    assert "`human_rewrite` 可以参考跨季原文块" in package.copywriting_prompt
    assert "不能机械替换季节词" in package.copywriting_prompt
    assert "两个非季节性原字眼" in package.copywriting_prompt
    assert "`source_slot_values`" in package.copywriting_prompt
    assert "不阻断整批生成" in package.copywriting_prompt
    assert "标为“否，仅 human_rewrite”的块不得直接填槽" in package.copywriting_prompt
    assert "风格名称：product-led-conversational" in package.copywriting_prompt
    assert "禁止出现以下行动引导" in package.copywriting_prompt
    assert package.language_style.name == "product-led-conversational"
    assert package.template_version == "2026-08-13-selected-learning-context-v24"
    assert "{{SCRIPT}}" in package.avatar_prompt_template
    assert package.review_required is True


def test_compose_prompt_package_injects_configured_language_style() -> None:
    package = compose_prompt_package(
        ProductBrief(category="西瓜"),
        language_style=LanguageStyle(
            name="benefit-forward-natural",
            tone="自然直接地说明这次购买合适",
            point_of_view="像自己刚用到活动后分享",
            sentence_style="少铺垫，快速进入购买理由",
            emphasis=("先讲清活动利益点",),
            avoid_phrases=("错过就亏",),
            extra_rules=("不要夸张促销氛围",),
        ),
    )

    assert "风格名称：benefit-forward-natural" in package.copywriting_prompt
    assert "整体语气：自然直接地说明这次购买合适" in package.copywriting_prompt
    assert "表达重点：先讲清活动利益点" in package.copywriting_prompt
    assert "避免套话：错过就亏" in package.copywriting_prompt
    assert "额外规则：不要夸张促销氛围" in package.copywriting_prompt
    assert package.language_style.name == "benefit-forward-natural"


def test_compose_prompt_package_renders_validation_call_to_actions() -> None:
    package = compose_prompt_package(
        ProductBrief(category="咖啡"),
        CampaignSpec(
            benefit_points=(BenefitPoint(id="primary-benefit", text="最高25元无门槛红包"),),
            confirmed_claims=("可提及配送到家",),
        ),
        validation_config=ValidationConfig(call_to_actions=("直播间", "点击视频下方链接")),
    )

    assert "已确认可用信息：可提及配送到家" in package.copywriting_prompt
    assert "平台名必须逐字出现在每条文案中" in package.copywriting_prompt
    assert "禁止出现以下行动引导：直播间、点击视频下方链接" in package.copywriting_prompt


def test_compose_prompt_package_renders_numeric_redpacket_compliance_rule() -> None:
    package = compose_prompt_package(
        ProductBrief(category="西瓜"),
        validation_config=ValidationConfig(forbid_numeric_redpacket_amounts=True),
    )

    assert "禁止出现任何阿拉伯数字或中文数字的红包金额" in package.copywriting_prompt


def test_render_avatar_prompt_injects_script() -> None:
    rendered = render_avatar_prompt(
        "下班回家，[[NO_SPLIT]]最高12元无门槛红包[[/NO_SPLIT]]，门口的雨靴还沾着一点雨水。"
    )

    assert "{{SCRIPT}}" not in rendered
    assert "下班回家，最高12元无门槛红包，门口的雨靴还沾着一点雨水。" in rendered
    assert "[[NO_SPLIT]]" not in rendered
    assert "22-24 岁中国女生" in rendered
    assert "甜美、可爱、清冷、御姐、邻家、清爽" in rendered
    assert "禁止大妈、阿姨、中年女性、中老年或老气方向" in rendered
    assert "亚洲女生、亚洲女性、大妈、阿姨" in rendered
    assert "开头必须先写“竖屏9:16，固定中景，手机实拍，数字人口播首帧”" in rendered
    assert "目标长度 120-180 个中文字符" in rendered
    assert "主流日常审美" in rendered
    assert "通勤、休闲、甜酷、简约或轻运动风" in rendered
    assert "场景只作为背景" in rendered
    assert "人物面前桌上放商品" in rendered
    assert "商品不由人物手持" in rendered
    assert "人物不看商品" in rendered
    assert "不接触商品" in rendered
    assert "非商品区域无logo" in rendered
    assert "无字幕" in rendered
    assert "竖屏9:16" in rendered


def test_render_avatar_prompt_rejects_empty_script() -> None:
    with pytest.raises(ValueError, match="口播文案不能为空"):
        render_avatar_prompt("\x00  ")
