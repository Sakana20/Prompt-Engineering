from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.publication import reference_path
from avatar_prompt_pipeline.models import ProductBrief
from avatar_prompt_pipeline.service import compose_prompt_package
from avatar_prompt_pipeline.source_blocks import (
    learned_copy_blocks,
    learned_person_blocks,
    published_copy_block_contracts,
    select_copy_blocks,
    select_person_blocks,
)


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

    assert "【本次筛选的真人原文块】" not in package.copywriting_prompt
    assert "【本次筛选的人物学习块】" not in package.avatar_prompt_template


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

    package = compose_prompt_package(
        ProductBrief(category="饮品"),
        copy_mode="human_rewrite",
        source_block_id="learned-copy-unified-001",
    )

    assert "本条模式：human_rewrite" in package.copywriting_prompt
    assert "learned-copy-unified-001" in package.copywriting_prompt
    assert "仅用于检测的旧库说明" not in package.copywriting_prompt


@pytest.mark.integration
def test_copy_resource_injects_only_bounded_task_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AVATAR_PROMPT_PROJECT", str(tmp_path))
    refs = tmp_path / "prompt-engineering" / "references"
    refs.mkdir(parents=True)
    copy_resource = reference_path("volume-copy-source-blocks.md")
    rendered_blocks = [
        f"### `learned-copy-{index:03d}`\n\n```text\n[饮品名称]\n饮品描述 {index}\n```\n"
        for index in range(40)
    ]
    copy_resource.write_text("# 文案学习块\n\n" + "\n".join(rendered_blocks), encoding="utf-8")
    reference_path("person-prompt-source-blocks.md").write_text("# empty\n", encoding="utf-8")

    package = compose_prompt_package(
        ProductBrief(category="咖啡", product_name="冰咖啡"),
        copy_mode="source_fill",
        source_block_id="learned-copy-000",
    )
    selected = select_copy_blocks("咖啡", "冰咖啡|夏季", copy_resource)

    assert len(learned_copy_blocks(copy_resource)) == 40
    assert len(selected) == 4
    assert package.selected_copy_block_ids == ("learned-copy-000",)
    assert package.copy_learning_context_character_count < 7000
    assert "learned-copy-000" in package.copywriting_prompt
    unselected_ids = {block.block_id for block in learned_copy_blocks(copy_resource)} - set(
        package.selected_copy_block_ids
    )
    assert all(block_id not in package.copywriting_prompt for block_id in unselected_ids)

    batch_selected = select_copy_blocks("咖啡", "冰咖啡|夏季", copy_resource, batch_size=10)
    assert len(batch_selected) == 7


@pytest.mark.integration
def test_person_resource_uses_plain_blocks_and_injects_only_bounded_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AVATAR_PROMPT_PROJECT", str(tmp_path))
    refs = tmp_path / "prompt-engineering" / "references"
    refs.mkdir(parents=True)
    reference_path("volume-copy-source-blocks.md").write_text("# empty\n", encoding="utf-8")
    person_resource = reference_path("person-prompt-source-blocks.md")
    rendered_blocks = []
    for index in range(20):
        for block_type in ("identity", "hair", "outfit", "scene"):
            rendered_blocks.append(
                f"### `person-{index:02d}-{block_type}` · `{block_type}`\n\n"
                f"```text\n{block_type} 描述 {index}\n```\n"
            )
    person_resource.write_text("# 人物学习块\n\n" + "\n".join(rendered_blocks), encoding="utf-8")

    package = compose_prompt_package(ProductBrief(category="雨伞"))
    selected = select_person_blocks("雨伞", person_resource)

    assert len(learned_person_blocks(person_resource)) == 80
    assert len(selected) == 10
    assert len(package.selected_person_block_ids) == 10
    assert package.person_learning_context_character_count < 4500
    assert "【本次筛选的人物学习块】" in package.avatar_prompt_template
    assert (
        sum(
            block_id in package.avatar_prompt_template
            for block_id in package.selected_person_block_ids
        )
        == 10
    )
    assert "```json" not in package.avatar_prompt_template
    unselected_ids = {block.block_id for block in learned_person_blocks(person_resource)} - set(
        package.selected_person_block_ids
    )
    assert all(block_id not in package.avatar_prompt_template for block_id in unselected_ids)
