import csv
import json
from pathlib import Path

import pytest

from avatar_prompt_pipeline.dreamina import (
    DreaminaAdapterError,
    load_dreamina_video_node_draft,
    remove_dreamina_video_restrictions,
    render_dreamina_video_prompt,
)

VIDEO_PROMPT_TEMPLATE = (
    "以{{node:{image_node_id}}}为参考图生成视频。"
    "鼓励人物在口播过程中根据文案语义自然接触、拿起或使用商品，动作真实克制。"
    "必须严格按照以下口播文案逐字说完，不得省略、改写、截断或提前结束："
    "“这是需要完整说出的口播文案。”口型与口播内容同步，身体动作自然，不包含任何字幕。"
)


def _write_package_files(tmp_path: Path) -> tuple[Path, Path]:
    csv_path = tmp_path / "batch.dreamina.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("task_id", "title", "video_prompt", "aspect_ratio"),
        )
        writer.writeheader()
        writer.writerow(
            {
                "task_id": "TASK-001",
                "title": "数字人口播",
                "video_prompt": VIDEO_PROMPT_TEMPLATE,
                "aspect_ratio": "9:16",
            }
        )
    interface_path = tmp_path / "batch.dreamina.interface.json"
    interface_path.write_text(
        json.dumps(
            {
                "interface": "dreamina_canvas",
                "nodes": {
                    "video": {
                        "mode": "m2v",
                        "model": "seedance_2.0mini",
                        "resolution": "720p",
                        "count": 1,
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return csv_path, interface_path


def test_render_video_prompt_uses_real_image_node_and_preserves_required_constraints() -> None:
    prompt = render_dreamina_video_prompt(
        VIDEO_PROMPT_TEMPLATE,
        image_node_id="node_image_123",
    )

    assert "{{node:node_image_123}}" in prompt
    assert "{image_node_id}" not in prompt
    assert "必须严格按照以下口播文案逐字说完" in prompt
    assert "这是需要完整说出的口播文案" in prompt
    assert "鼓励人物在口播过程中根据文案语义自然接触、拿起或使用商品" in prompt
    assert "不得省略、改写、截断或提前结束" in prompt
    assert "不包含任何字幕" in prompt
    assert "固定机位" not in prompt
    assert "不切镜" not in prompt
    assert "不运镜" not in prompt


def test_dreamina_video_removes_product_touch_and_camera_restrictions_only() -> None:
    source = (
        "竖屏9:16，固定中景，手机固定拍摄，人物不看商品、不接触商品，"
        "商品不由人物手持，固定机位，不允许切镜，不切镜，一镜到底，"
        "不允许运镜，不运镜，不推拉摇移，身体稳定"
    )

    cleaned = remove_dreamina_video_restrictions(source)

    assert "人物不看商品" in cleaned
    assert "商品不由人物手持" not in cleaned
    assert "中景" in cleaned
    assert "手机实拍" in cleaned
    assert "身体稳定" in cleaned
    for removed in (
        "不接触商品",
        "不触碰商品",
        "固定机位",
        "镜头固定",
        "不允许切镜",
        "不切镜",
        "一镜到底",
        "不允许运镜",
        "不运镜",
        "不推拉摇移",
        "商品不由人物手持",
    ):
        assert removed not in cleaned


def test_runtime_render_removes_restrictions_from_legacy_package_prompt() -> None:
    legacy_prompt = VIDEO_PROMPT_TEMPLATE.replace(
        "自然口播。",
        "自然口播，人物不接触商品，固定机位，不切镜、不运镜。",
    )

    prompt = render_dreamina_video_prompt(legacy_prompt, image_node_id="node_image_123")

    assert "人物不接触商品" not in prompt
    assert "固定机位" not in prompt
    assert "不切镜" not in prompt
    assert "不运镜" not in prompt


def test_video_node_command_passes_prompt_and_image_reference_only(tmp_path: Path) -> None:
    csv_path, interface_path = _write_package_files(tmp_path)
    draft = load_dreamina_video_node_draft(
        csv_path=csv_path,
        interface_path=interface_path,
        task_id="TASK-001",
        project_id="project-123",
        image_node_id="node_image_123",
        duration_seconds=18,
    )

    command = draft.command()
    assert command[:4] == ("dreamina-canvas", "node", "create", "video")
    assert command[command.index("--prompt") + 1] == draft.prompt
    ref_values = [command[index + 1] for index, value in enumerate(command) if value == "--ref"]
    assert ref_values == ["node:node_image_123"]
    assert "--run" not in command
    assert "--dry-run" not in command
    assert draft.command(dry_run=True)[-1] == "--dry-run"


@pytest.mark.parametrize(
    ("prompt", "image_node_id", "message"),
    [
        (VIDEO_PROMPT_TEMPLATE.replace("{image_node_id}", "missing"), "node_image_123", "占位符"),
        (VIDEO_PROMPT_TEMPLATE, "image-123", "Node ID"),
        (
            VIDEO_PROMPT_TEMPLATE.replace("不包含任何字幕", "不要字幕"),
            "node_image_123",
            "缺少必检短语",
        ),
        (
            VIDEO_PROMPT_TEMPLATE.replace(
                "鼓励人物在口播过程中根据文案语义自然接触、拿起或使用商品，动作真实克制。",
                "",
            ),
            "node_image_123",
            "缺少必检短语",
        ),
    ],
)
def test_render_video_prompt_rejects_invalid_runtime_inputs(
    prompt: str, image_node_id: str, message: str
) -> None:
    with pytest.raises(DreaminaAdapterError, match=message):
        render_dreamina_video_prompt(prompt, image_node_id=image_node_id)
