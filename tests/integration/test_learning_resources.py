import json
from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.publication import reference_path
from avatar_prompt_pipeline.models import ProductBrief
from avatar_prompt_pipeline.service import compose_prompt_package
from avatar_prompt_pipeline.source_blocks import learned_source_block_contracts


@pytest.mark.integration
def test_empty_learned_resources_keep_existing_prompt_compatible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AVATAR_PROMPT_PROJECT", str(tmp_path))
    refs = tmp_path / "prompt-engineering" / "references"
    refs.mkdir(parents=True)
    reference_path("learned-copy-source-blocks.md").write_text("# empty\n", encoding="utf-8")
    reference_path("person-prompt-source-blocks.md").write_text("# empty\n", encoding="utf-8")

    package = compose_prompt_package(ProductBrief(category="雨伞"))

    assert "审核发布的 learned 文案块" not in package.copywriting_prompt
    assert "【审核发布的 learned 人物变量块】" not in package.avatar_prompt_template


@pytest.mark.integration
def test_learned_copy_registry_is_recognized(tmp_path: Path) -> None:
    resource = tmp_path / "learned-copy-source-blocks.md"
    resource.write_text(
        "```json\n"
        + json.dumps(
            {
                "block_id": "learned-copy-001",
                "solid_food_only": False,
                "minimum_source_slot_values": 2,
            }
        )
        + "\n```\n",
        encoding="utf-8",
    )
    contract = learned_source_block_contracts(resource)["learned-copy-001"]
    assert contract.minimum_source_slot_values == 2
