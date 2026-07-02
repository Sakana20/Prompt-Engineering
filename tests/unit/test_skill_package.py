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


def test_skill_ui_prompt_explicitly_invokes_skill() -> None:
    metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert 'default_prompt: "使用 $taobao-avatar-video ' in metadata
