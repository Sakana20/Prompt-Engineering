from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.publication import reference_path
from avatar_prompt_pipeline.models import ProductBrief
from avatar_prompt_pipeline.service import compose_prompt_package
from avatar_prompt_pipeline.source_blocks import published_copy_block_contracts


@pytest.mark.integration
def test_empty_learned_resources_keep_existing_prompt_compatible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AVATAR_PROMPT_PROJECT", str(tmp_path))
    refs = tmp_path / "prompt-engineering" / "references"
    refs.mkdir(parents=True)
    reference_path("volume-copy-source-blocks.md").write_text("# empty\n", encoding="utf-8")
    reference_path("person-prompt-source-blocks.md").write_text("# empty\n", encoding="utf-8")

    package = compose_prompt_package(ProductBrief(category="雨伞"))

    assert "【审核发布的文案块】" not in package.copywriting_prompt
    assert "【审核发布的 learned 人物变量块】" not in package.avatar_prompt_template


@pytest.mark.integration
def test_published_plain_copy_block_is_recognized_in_unified_resource(tmp_path: Path) -> None:
    resource = tmp_path / "volume-copy-source-blocks.md"
    resource.write_text(
        "## 审核发布的网页学习块\n\n"
        "### `learned-copy-001`\n\n"
        "```text\n[饮品名称]\n现在[已确认内容]\n```\n",
        encoding="utf-8",
    )
    contract = published_copy_block_contracts(resource)["learned-copy-001"]
    assert contract.minimum_source_slot_values == 2
    assert contract.solid_food_only is False


@pytest.mark.integration
def test_copy_registry_json_is_not_treated_as_a_formal_source_block(tmp_path: Path) -> None:
    resource = tmp_path / "volume-copy-source-blocks.md"
    resource.write_text(
        '## 审核发布的网页学习块\n\n```json\n{"block_id":"learned-copy-json-001"}\n```\n',
        encoding="utf-8",
    )

    assert published_copy_block_contracts(resource) == {}


@pytest.mark.integration
def test_published_copy_section_is_loaded_from_unified_volume_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AVATAR_PROMPT_PROJECT", str(tmp_path))
    refs = tmp_path / "prompt-engineering" / "references"
    refs.mkdir(parents=True)
    reference_path("volume-copy-source-blocks.md").write_text(
        "# 仅用于检测的旧库说明\n\n"
        "## 审核发布的网页学习块\n\n"
        "### `learned-copy-unified-001`\n\n"
        "```text\n[商品名]\n现在[已确认商品内容]\n```\n",
        encoding="utf-8",
    )
    reference_path("person-prompt-source-blocks.md").write_text("# empty\n", encoding="utf-8")

    package = compose_prompt_package(ProductBrief(category="饮品"))

    assert "【审核发布的文案块】" in package.copywriting_prompt
    assert "learned-copy-unified-001" in package.copywriting_prompt
    assert "仅用于检测的旧库说明" not in package.copywriting_prompt
