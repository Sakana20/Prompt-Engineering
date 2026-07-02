import json
from pathlib import Path

SKILL_ROOT = Path(__file__).parents[2] / "taobao-avatar-video"


def test_skill_has_required_frontmatter_and_runtime_resources() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert skill.startswith("---\nname: taobao-avatar-video\n")
    assert "description:" in skill.split("---", maxsplit=2)[1]
    assert "Do not call another LLM." in skill
    assert (SKILL_ROOT / "agents" / "openai.yaml").is_file()
    assert (SKILL_ROOT / "references" / "copywriting-rules.md").is_file()
    assert (SKILL_ROOT / "references" / "avatar-rules.md").is_file()
    assert (SKILL_ROOT / "references" / "oceanengine-contract.md").is_file()
    assert (SKILL_ROOT / "references" / "runtime.md").is_file()
    assert (SKILL_ROOT / "scripts" / "run_cli.py").is_file()
    assert "$smartsplit" not in skill.lower()
    assert "invoke smartsplit" not in skill.lower()
    assert "<task_id>.smartsplit.txt" in skill
    assert "Prompt Engineering/<YYYYMMDD>/<task>/<task>.csv" in skill


def test_skill_ui_prompt_explicitly_invokes_skill() -> None:
    metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert 'default_prompt: "使用 $taobao-avatar-video ' in metadata


def test_copywriting_rules_keep_lifestyle_setup_subordinate_to_product() -> None:
    rules = (SKILL_ROOT / "references" / "copywriting-rules.md").read_text(encoding="utf-8")

    assert "商品导向的生活化分享" in rules
    assert "约占全文 20%" in rules
    assert "商品内容约占全文 50%" in rules
    assert "利益点和购买体验约占全文 30%" in rules


def test_cli_schema_covers_every_existing_cli_parameter() -> None:
    schema = json.loads(
        (SKILL_ROOT / "references" / "cli-parameters.schema.json").read_text(encoding="utf-8")
    )
    compose = schema["oneOf"][0]["properties"]
    validate = schema["oneOf"][1]["properties"]

    assert set(compose) == {
        "command",
        "category",
        "product_name",
        "selling_point",
        "forbidden_claim",
        "output",
    }
    assert set(validate) == {"command", "text"}
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
