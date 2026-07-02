import json
from pathlib import Path
from typing import Any

import pytest

from avatar_prompt_pipeline.io import write_package
from avatar_prompt_pipeline.models import ProductBrief
from avatar_prompt_pipeline.service import compose_prompt_package


@pytest.mark.integration
def test_package_round_trip_to_utf8_json(tmp_path: Path) -> None:
    package = compose_prompt_package(
        ProductBrief(category="雨靴", selling_points=("适合日常雨天穿着",))
    )
    destination = write_package(tmp_path / "nested" / "rain-boots.json", package)

    decoded: dict[str, Any] = json.loads(destination.read_text(encoding="utf-8"))
    assert decoded["brief"]["category"] == "雨靴"
    assert decoded["review_required"] is True
    assert not list(destination.parent.glob("*.tmp"))
