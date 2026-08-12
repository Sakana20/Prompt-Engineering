import json
from pathlib import Path

SKILL_ROOT = Path(__file__).parents[2] / "prompt-engineering"


def test_skill_has_required_frontmatter_and_runtime_resources() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert skill.startswith("---\nname: prompt-engineering\n")
    assert "description:" in skill.split("---", maxsplit=2)[1]
    assert "Do not call another LLM." in skill
    assert (SKILL_ROOT / "agents" / "openai.yaml").is_file()
    assert (SKILL_ROOT / "references" / "copywriting-rules.md").is_file()
    assert (SKILL_ROOT / "references" / "volume-copy-source-blocks.md").is_file()
    assert (SKILL_ROOT / "references" / "source-block-contracts.md").is_file()
    assert not (SKILL_ROOT / "references" / "volume-copy-style.md").exists()
    assert not (SKILL_ROOT / "references" / "volume-copy-fragments.md").exists()
    assert (SKILL_ROOT / "references" / "campaign-contract.md").is_file()
    assert (SKILL_ROOT / "references" / "avatar-rules.md").is_file()
    assert (SKILL_ROOT / "references" / "oceanengine-contract.md").is_file()
    assert (SKILL_ROOT / "references" / "runtime.md").is_file()
    assert (SKILL_ROOT / "references" / "generated-task-batch.schema.json").is_file()
    assert (SKILL_ROOT / "references" / "copy-learning-candidate.schema.json").is_file()
    assert (SKILL_ROOT / "references" / "person-prompt-learning-candidate.schema.json").is_file()
    assert (SKILL_ROOT / "references" / "learning-publication.schema.json").is_file()
    assert (SKILL_ROOT / "references" / "learned-copy-source-blocks.md").is_file()
    assert (SKILL_ROOT / "references" / "person-prompt-source-blocks.md").is_file()
    assert (SKILL_ROOT / "references" / "person-prompt-block-contracts.md").is_file()
    assert (SKILL_ROOT / "references" / "validation-config.schema.json").is_file()
    assert (SKILL_ROOT / "scripts" / "run_cli.py").is_file()
    assert "$smartsplit" not in skill.lower()
    assert "invoke smartsplit" not in skill.lower()
    assert "<task_id>.smartsplit.txt" in skill
    assert "Prompt Engineering/<YYYYMMDD>/<task>/<task>.csv" in skill
    assert "/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材" in skill
    assert "创建 ASR 候选" in skill
    assert "Preserve the FunASR `.venv/bin/python` symlink path" in skill
    assert "never resolve it to the base interpreter" in skill
    assert "Preserve the ASR transcript and token timeline verbatim" in skill
    assert "Never\n  infer missing punctuation, correct words, change case" in skill
    copy_candidate_schema = json.loads(
        (SKILL_ROOT / "references" / "copy-learning-candidate.schema.json").read_text(
            encoding="utf-8"
        )
    )
    copy_properties = copy_candidate_schema["properties"]
    assert "Verbatim ASR text" in copy_properties["raw_transcript"]["description"]
    assert "deterministic whitespace" in copy_properties["edited_transcript"]["description"]
    assert copy_properties["category_family"]["enum"] == ["", "beverage", "other"]
    assert set(copy_properties["source_usage"]["items"]["enum"]) == {
        "source_fill",
        "human_rewrite",
    }
    assert "browser-supplied" in skill
    assert "filesystem path" in skill


def test_skill_ui_prompt_explicitly_invokes_skill() -> None:
    metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert 'default_prompt: "使用 $prompt-engineering ' in metadata
    assert "商品和利益点" in metadata


def test_copywriting_rules_keep_lifestyle_setup_subordinate_to_product() -> None:
    rules = (SKILL_ROOT / "references" / "copywriting-rules.md").read_text(encoding="utf-8")

    assert "商品导向的生活化分享" in rules
    assert "约占全文 20%" in rules
    assert "商品内容约占全文 50%" in rules
    assert "利益点和购买体验约占全文 30%" in rules
    assert "`floor(N/2)`" in rules
    assert "`source_fill`" in rules
    assert "`human_rewrite`" in rules
    assert "`human_rewrite` 固定为 `floor(N/2)`" in rules
    assert "`natural_generate`" in rules
    assert "保留至少两个可辨认字眼或短语" in rules


def test_volume_copy_guidance_never_embeds_sample_benefits() -> None:
    guidance = "\n".join(
        [
            (SKILL_ROOT / "references" / "volume-copy-source-blocks.md").read_text(
                encoding="utf-8"
            ),
            (
                SKILL_ROOT.parents[0]
                / "src"
                / "avatar_prompt_pipeline"
                / "templates"
                / "copywriting_prompt.txt"
            ).read_text(encoding="utf-8"),
        ]
    )

    for sample_benefit in ("最高66元红包", "最高28元红包", "9.9起", "几块钱起"):
        assert sample_benefit not in guidance
    assert "当前利益点按 `CampaignSpec` 单独插入" in guidance
    assert "必须使用与当前活动完全匹配的校验器" in guidance
    assert "不得改写、润色、扩句、调整原句顺序" in guidance
    assert "轨道内不得重复 `source_block_id`" in guidance
    assert "不得先总结风格" in guidance
    assert "10 条时始终是 5 条 `human_rewrite`" in guidance


def test_volume_copy_library_preserves_human_source_blocks() -> None:
    blocks = (SKILL_ROOT / "references" / "volume-copy-source-blocks.md").read_text(
        encoding="utf-8"
    )
    production_prompt = (
        SKILL_ROOT.parents[0]
        / "src"
        / "avatar_prompt_pipeline"
        / "templates"
        / "copywriting_prompt.txt"
    ).read_text(encoding="utf-8")
    source_ids = {
        line.split("`", maxsplit=2)[1]
        for line in blocks.splitlines()
        if line.startswith("### `learn-")
    }
    prompt_ids = {
        line.split("`", maxsplit=2)[1]
        for line in production_prompt.splitlines()
        if line.startswith("- `learn-")
    }

    assert len(source_ids) >= 10
    assert prompt_ids == source_ids
    assert "什么你说你不饿\n不你就是饿了" in blocks
    assert "如果人间烟火气有背景音乐\n那一定是[已确认食用动作]的声音" in blocks
    assert "这天一冷\n只想和好朋友\n窝在家里吃[商品名]聊八卦" in blocks
    assert "只填方括号" in blocks
    assert "不总结文风，也不仿写新句子" in blocks


def test_generated_batch_schema_exposes_copy_mix_audit_fields() -> None:
    schema = json.loads(
        (SKILL_ROOT / "references" / "generated-task-batch.schema.json").read_text(encoding="utf-8")
    )
    task_properties = schema["properties"]["tasks"]["items"]["properties"]

    assert task_properties["copy_mode"]["enum"] == [
        "source_fill",
        "human_rewrite",
        "natural_generate",
    ]
    assert "source_block_id" in task_properties
    assert "rewrite_anchor_phrases" in task_properties
    assert "source_slot_values" in task_properties


def test_cli_schema_covers_every_existing_cli_parameter() -> None:
    schema = json.loads(
        (SKILL_ROOT / "references" / "cli-parameters.schema.json").read_text(encoding="utf-8")
    )
    compose = schema["oneOf"][0]["properties"]
    validate = schema["oneOf"][1]["properties"]
    validate_batch = schema["oneOf"][2]["properties"]
    package = schema["oneOf"][3]["properties"]
    init_batch = schema["oneOf"][4]["properties"]
    export_csv = schema["oneOf"][5]["properties"]

    assert set(compose) == {
        "command",
        "category",
        "product_name",
        "selling_point",
        "forbidden_claim",
        "preset",
        "platform",
        "campaign_name",
        "benefit_point",
        "config",
        "output",
    }
    assert set(validate) == {
        "command",
        "text",
        "preset",
        "platform",
        "campaign_name",
        "benefit_point",
        "config",
    }
    assert set(validate_batch) == {
        "command",
        "input",
        "preset",
        "platform",
        "campaign_name",
        "benefit_point",
        "config",
    }
    assert set(package) == {
        "command",
        "input",
        "format",
        "output_root",
        "date",
        "preset",
        "platform",
        "campaign_name",
        "benefit_point",
        "config",
    }
    assert set(init_batch) == {
        "command",
        "task_name",
        "category",
        "count",
        "task_prefix",
        "output",
    }
    assert set(export_csv) == {
        "command",
        "input",
        "output_root",
        "date",
        "preset",
        "platform",
        "campaign_name",
        "benefit_point",
        "config",
    }
    assert set(schema["$defs"]["launcher"]["properties"]) == {
        "project_root",
        "debug",
        "python_executable",
        "arguments",
    }


def test_skill_config_schema_preserves_runtime_capabilities() -> None:
    schema = json.loads(
        (SKILL_ROOT / "references" / "skill-config.schema.json").read_text(encoding="utf-8")
    )
    properties = schema["properties"]

    assert {"batch", "debug", "plugin_directories", "plugins"} <= properties.keys()
    assert set(properties["output_formats"]["items"]["enum"]) == {
        "text",
        "json",
        "csv",
        "markdown",
        "segmentation_manuscript",
        "libtv_omnihuman_package",
    }
    assert {
        "output_root",
        "output_date",
        "task_name",
        "manuscript_output_directory",
        "oceanengine_csv_output_path",
        "oceanengine_csv_output_directory",
    } <= properties.keys()
    assert properties["output_root"]["default"].endswith("/Codex/Prompt Engineering")
    assert "project_id" in properties
    assert "confirmed_claims" in properties
    assert "validation_config_path" in properties
    assert "language_style" in properties
    assert "avoid_phrases" in properties["language_style"]["properties"]


def test_validation_config_schema_exposes_numeric_redpacket_rule() -> None:
    schema = json.loads(
        (SKILL_ROOT / "references" / "validation-config.schema.json").read_text(encoding="utf-8")
    )

    rule = schema["properties"]["forbid_numeric_redpacket_amounts"]
    assert rule["type"] == "boolean"
    assert rule["default"] is False


def test_single_skill_is_generalized_with_campaign_contract() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    config = json.loads(
        (SKILL_ROOT / "references" / "skill-config.schema.json").read_text(encoding="utf-8")
    )
    cli = json.loads(
        (SKILL_ROOT / "references" / "cli-parameters.schema.json").read_text(encoding="utf-8")
    )

    assert skill.startswith("---\nname: prompt-engineering\n")
    assert "zero to three user-confirmed benefit points" in skill
    assert "Compatibility defaults" in skill
    assert config["properties"]["benefit_points"]["maxItems"] == 3
    assert "benefit_point" in cli["oneOf"][0]["properties"]
    assert "config" in cli["oneOf"][0]["properties"]
