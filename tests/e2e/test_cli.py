import csv
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from avatar_prompt_pipeline import cli as cli_module
from avatar_prompt_pipeline.cli import run
from avatar_prompt_pipeline.dreamina import DreaminaVideoNodeDraft
from avatar_prompt_pipeline.validation import REQUIRED_BENEFIT


@pytest.fixture(autouse=True)
def _isolated_generation_learning_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "DEFAULT_LEARNING_ROOT", tmp_path / "learning")


@pytest.mark.e2e
def test_compose_cli_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    result = run(["compose", "--category", "雨靴", "--selling-point", "中筒款式"])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["brief"]["category"] == "雨靴"
    assert output["brief"]["selling_points"] == ["中筒款式"]
    assert output["campaign"]["benefit_points"][0]["text"] == REQUIRED_BENEFIT


@pytest.mark.e2e
def test_compose_cli_accepts_custom_and_no_benefit_campaigns(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run(
        [
            "compose",
            "--category",
            "雨伞",
            "--platform",
            "淘宝闪购",
            "--benefit-point",
            "淘宝闪购满20减5",
        ]
    )
    custom: dict[str, Any] = json.loads(capsys.readouterr().out)

    assert result == 0
    assert custom["campaign"]["benefit_points"][0]["text"] == "淘宝闪购满20减5"

    result = run(["compose", "--category", "雨伞", "--preset", "none"])
    no_benefit: dict[str, Any] = json.loads(capsys.readouterr().out)

    assert result == 0
    assert no_benefit["campaign"]["benefit_points"] == []


@pytest.mark.e2e
def test_compose_cli_uses_project_config_without_default_campaign(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "taobao-25-project.json"
    validation_path = tmp_path / "promo-validation.json"
    validation_path.write_text(
        json.dumps(
            {
                "call_to_actions": ["直播间", "立即购买"],
                "required_ending_call_to_actions": ["点下方链接看看。"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    config_path.write_text(
        json.dumps(
            {
                "project_id": "taobao-25-no-threshold-redpacket",
                "category": "西瓜",
                "platform": "淘宝闪购",
                "campaign_name": "25元无门槛红包项目",
                "benefit_points": [
                    {
                        "id": "primary-benefit",
                        "text": "最高25元无门槛红包",
                    }
                ],
                "campaign_forbidden_expressions": ["最高12元无门槛红包"],
                "validation_config_path": validation_path.name,
                "language_style": {
                    "name": "benefit-forward-promo",
                    "tone": "自然直接",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run(["compose", "--config", str(config_path)])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["brief"]["category"] == "西瓜"
    assert output["campaign"]["campaign_name"] == "25元无门槛红包项目"
    assert output["campaign"]["benefit_points"][0]["text"] == "最高25元无门槛红包"
    assert output["campaign"]["forbidden_expressions"] == ["最高12元无门槛红包"]
    assert output["validation_config"]["call_to_actions"] == ["直播间", "立即购买"]
    assert output["validation_config"]["required_ending_call_to_actions"] == ["点下方链接看看。"]
    assert output["language_style"]["name"] == "benefit-forward-promo"
    assert "表达声音：自然直接" in output["copywriting_prompt"]
    assert output["copy_mode"] == "natural_generate"
    assert "禁止出现以下行动引导：直播间、立即购买" in output["copywriting_prompt"]
    assert "正文必须以以下任一完整行动引导语收尾" in output["copywriting_prompt"]
    assert (
        f"利益点[primary-benefit]：[[NO_SPLIT]]{REQUIRED_BENEFIT}"
        not in output["copywriting_prompt"]
    )


@pytest.mark.e2e
def test_compose_cli_accepts_dynamic_source_mode(capsys: pytest.CaptureFixture[str]) -> None:
    result = run(
        [
            "compose",
            "--category",
            "炸鸡",
            "--copy-mode",
            "human_rewrite",
            "--source-block-id",
            "learn-008-evening",
        ]
    )

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["copy_mode"] == "human_rewrite"
    assert output["selected_copy_block_ids"] == ["learn-008-evening"]
    assert "本条模式：human_rewrite" in output["copywriting_prompt"]


@pytest.mark.e2e
def test_validate_copy_cli_uses_project_config_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "taobao-25-project.json"
    validation_path = tmp_path / "promo-validation.json"
    validation_path.write_text(
        json.dumps({"call_to_actions": ["直播间", "立即购买"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    config_path.write_text(
        json.dumps(
            {
                "category": "西瓜",
                "benefit_points": [
                    {
                        "id": "primary-benefit",
                        "text": "最高25元无门槛红包",
                    }
                ],
                "campaign_forbidden_expressions": ["最高12元无门槛红包"],
                "validation_config_path": validation_path.name,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = (
        "下班回家路上想顺手买点水果，看到小区附近还有新鲜西瓜可选，"
        "[[NO_SPLIT]]最高25元无门槛红包[[/NO_SPLIT]]"
        "正好能用。这类水果适合切好放进冰箱，饭后端出来一家人分着吃，"
        "临时补一份也不用绕远路。"
    )

    result = run(["validate-copy", text, "--config", str(config_path)])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["is_valid"] is True

    previous_text = text.replace("最高25元无门槛红包", "最高12元无门槛红包")
    result = run(["validate-copy", previous_text, "--config", str(config_path)])

    output = json.loads(capsys.readouterr().out)
    assert result == 1
    assert any(issue["code"] == "MISSING_BENEFIT" for issue in output["issues"])
    assert any(issue["code"] == "BANNED_EXPRESSION" for issue in output["issues"])


@pytest.mark.e2e
def test_project_config_rejects_mixed_campaign_arguments(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "project.json"
    config_path.write_text(
        json.dumps({"category": "西瓜", "benefit_points": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="不要同时传入活动口径参数"):
        run(
            [
                "compose",
                "--config",
                str(config_path),
                "--benefit-point",
                "最高12元无门槛红包",
            ]
        )


@pytest.mark.e2e
def test_compose_cli_writes_requested_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "prompt-package.json"

    result = run(["compose", "--category", "雨靴", "--output", str(destination)])

    assert result == 0
    assert destination.is_file()
    assert "Prompt 包已写入" in capsys.readouterr().out


@pytest.mark.e2e
def test_validate_copy_cli_returns_failure_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run(["validate-copy", f"立即购买。{REQUIRED_BENEFIT}"])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 1
    assert output["is_valid"] is False
    assert any(issue["code"] == "CALL_TO_ACTION" for issue in output["issues"])


@pytest.mark.e2e
def test_package_cli_validates_and_writes_selected_skill_outputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marked_script = (
        "午后收拾完桌面，打开冰箱才发现果盘已经空了。我看到"
        "[[NO_SPLIT]]淘宝闪购有最高12元无门槛红包[[/NO_SPLIT]]，"
        "就买了个哈密瓜。送到后切几块装进盘里，坐在沙发上慢慢吃，"
        "剩下的用保鲜盒收好，晚上家里人回来还能一起分。"
    )
    person_prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，人物约占画面二分之一，年轻中国女生坐在餐桌旁，"
        "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着哈密瓜，商品不由人物手持，"
        "人物不看商品、不接触商品，非商品区域无logo，无字幕。"
        "自然光照明，真实肤色和皮肤纹理，人物居中坐定，背景轻微虚化，整体年轻自然干净生活化。"
    )
    source = tmp_path / "generated.json"
    source.write_text(
        json.dumps(
            {
                "task_name": "hami-melon-batch",
                "category": "哈密瓜",
                "tasks": [
                    {
                        "task_id": "HM-001",
                        "marked_script": marked_script,
                        "avatar_prompt": "年轻中国女生在餐桌旁自然口播，全程直视镜头。",
                        "identity_key": "圆脸-黑色短发",
                        "outfit_key": "白衬衫-蓝牛仔裤",
                        "person_prompt": person_prompt,
                        "title": "哈密瓜居家水果场景",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run(
        [
            "package",
            "--input",
            str(source),
            "--format",
            "json",
            "--format",
            "segmentation_manuscript",
            "--format",
            "csv",
            "--output-root",
            str(tmp_path / "output"),
            "--date",
            "20260805",
        ]
    )

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    task_directory = tmp_path / "output" / "20260805" / "hami-melon-batch"
    assert result == 0
    assert output["paid_generation_submitted"] is False
    assert (task_directory / "hami-melon-batch.audit.json").is_file()
    assert (task_directory / "HM-001.smartsplit.txt").is_file()
    assert (task_directory / "hami-melon-batch.csv").is_file()
    assert not (task_directory / "hami-melon-batch.libtv.csv").exists()


@pytest.mark.e2e
def test_package_cli_writes_dreamina_canvas_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marked_script = (
        "午后收拾完桌面，打开冰箱才发现果盘已经空了。我看到"
        "[[NO_SPLIT]]淘宝闪购有最高12元无门槛红包[[/NO_SPLIT]]，"
        "就买了个哈密瓜。送到后切几块装进盘里，坐在沙发上慢慢吃，"
        "剩下的用保鲜盒收好，晚上家里人回来还能一起分。"
    )
    person_prompt = (
        "竖屏9:16，固定中景，手机实拍，数字人口播首帧，人物约占画面二分之一，"
        "年轻中国女生坐在餐桌旁，场景只作为背景，正面眼睛直视镜头，人物面前桌上放着哈密瓜，"
        "商品不由人物手持，人物不看商品、不接触商品，非商品区域无logo，无字幕。"
        "自然光照明，真实肤色和皮肤纹理，人物居中坐定，背景轻微虚化，整体年轻自然干净生活化。"
    )
    source = tmp_path / "generated.json"
    source.write_text(
        json.dumps(
            {
                "task_name": "hami-melon-batch",
                "category": "哈密瓜",
                "tasks": [
                    {
                        "task_id": "HM-001",
                        "marked_script": marked_script,
                        "avatar_prompt": (
                            "年轻中国女生在餐桌旁自然口播，全程直视镜头，人物不接触商品，"
                            "固定机位，不切镜、不运镜。"
                        ),
                        "identity_key": "圆脸-黑色短发",
                        "outfit_key": "白衬衫-蓝牛仔裤",
                        "person_prompt": person_prompt,
                        "title": "哈密瓜居家水果场景",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run(
        [
            "package",
            "--input",
            str(source),
            "--format",
            "dreamina_canvas_package",
            "--output-root",
            str(tmp_path / "output"),
            "--date",
            "20260805",
        ]
    )

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    task_directory = tmp_path / "output" / "20260805" / "hami-melon-batch"
    csv_path = task_directory / "hami-melon-batch.dreamina.csv"
    interface_path = task_directory / "hami-melon-batch.dreamina.interface.json"
    plan_path = task_directory / "hami-melon-batch.dreamina.plan.md"
    assert result == 0
    assert output["written"] == [str(csv_path), str(interface_path), str(plan_path)]
    assert output["paid_generation_submitted"] is False
    assert not (task_directory / "hami-melon-batch.csv").exists()
    assert not (task_directory / "hami-melon-batch.libtv.csv").exists()

    with csv_path.open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert "audio_prompt" not in row
    assert "dreamina_voice_name" not in row
    assert "年轻中国女生在餐桌旁自然口播" not in row["video_prompt"]
    assert "以{{node:{image_node_id}}}为参考图生成视频" in row["video_prompt"]
    assert "{{node:{image_node_id}}}" in row["video_prompt"]
    assert "必须严格按照以下口播文案逐字说完" in row["video_prompt"]
    assert "鼓励人物在口播过程中根据文案语义自然接触、拿起或使用商品" in row["video_prompt"]
    assert (
        marked_script.replace("[[NO_SPLIT]]", "").replace("[[/NO_SPLIT]]", "")
        in row["video_prompt"]
    )
    assert "不得省略、改写、截断或提前结束" in row["video_prompt"]
    assert "固定机位" not in row["video_prompt"]
    assert "不切镜" not in row["video_prompt"]
    assert "不运镜" not in row["video_prompt"]
    assert "不接触商品" not in row["video_prompt"]
    assert "商品不由人物手持" not in row["video_prompt"]
    assert row["video_prompt"].count("不包含任何字幕") == 1
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    assert interface["schema_version"] == "dreamina-interface-config/v3"
    assert "audio" not in interface["nodes"]
    assert interface["nodes"]["video"]["inputs"] == ["image"]


@pytest.mark.e2e
def test_save_dreamina_video_node_cli_binds_real_nodes_and_forwards_prompt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                "video_prompt": (
                    "以{{node:{image_node_id}}}为参考图生成视频。"
                    "鼓励人物在口播过程中根据文案语义自然接触、拿起或使用商品，动作真实克制。"
                    "必须严格按照以下口播文案逐字说完，不得省略、改写、截断或提前结束："
                    "“这是需要完整说出的口播文案。”口型与口播内容同步，"
                    "身体动作自然，不包含任何字幕。"
                ),
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
            }
        ),
        encoding="utf-8",
    )
    captured_command: tuple[str, ...] = ()

    def fake_save(
        draft: DreaminaVideoNodeDraft, *, dry_run: bool = False
    ) -> subprocess.CompletedProcess[str]:
        nonlocal captured_command
        captured_command = draft.command(dry_run=dry_run)
        return subprocess.CompletedProcess(captured_command, 0, '{"ok":true}\n', "")

    monkeypatch.setattr(cli_module, "save_dreamina_video_node", fake_save)

    result = run(
        [
            "save-dreamina-video-node",
            "--input",
            str(csv_path),
            "--interface",
            str(interface_path),
            "--task-id",
            "TASK-001",
            "--project-id",
            "project-123",
            "--image-node-id",
            "node_image_123",
            "--duration",
            "18",
            "--dry-run",
        ]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True}
    assert "{{node:node_image_123}}" in captured_command[captured_command.index("--prompt") + 1]
    ref_values = [
        captured_command[index + 1]
        for index, value in enumerate(captured_command)
        if value == "--ref"
    ]
    assert ref_values == ["node:node_image_123"]
    assert captured_command[-1] == "--dry-run"
    assert "--run" not in captured_command


@pytest.mark.e2e
def test_validate_batch_cli_rejects_duplicate_visual_profiles(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "generated.json"
    task = {
        "marked_script": "短文案",
        "avatar_prompt": "完整 Prompt",
        "identity_key": "重复人物",
        "outfit_key": "重复服装",
        "person_prompt": "不完整首帧 Prompt",
        "title": "测试",
    }
    source.write_text(
        json.dumps(
            {
                "task_name": "bad-batch",
                "category": "水果",
                "tasks": [
                    {**task, "task_id": "TASK-1"},
                    {**task, "task_id": "TASK-2"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run(["validate-batch", "--input", str(source), "--preset", "none"])

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 1
    assert output["is_valid"] is False
    assert output["visual_diversity_issues"][0]["code"] == "DUPLICATE_PERSON"

    output_root = tmp_path / "must-not-exist"
    result = run(
        [
            "package",
            "--input",
            str(source),
            "--format",
            "json",
            "--output-root",
            str(output_root),
            "--preset",
            "none",
        ]
    )

    assert result == 1
    assert not output_root.exists()


@pytest.mark.e2e
def test_agent_can_fill_template_and_export_csv_without_writing_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    template = tmp_path / "hami.tasks.json"
    result = run(
        [
            "init-batch",
            "--task-name",
            "hami-batch",
            "--category",
            "哈密瓜",
            "--count",
            "1",
            "--task-prefix",
            "HM",
            "--output",
            str(template),
        ]
    )
    init_output: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert result == 0
    assert init_output["next_step"].endswith("avatar-prompts export-csv")

    payload: dict[str, Any] = json.loads(template.read_text(encoding="utf-8"))
    task = payload["tasks"][0]
    task.update(
        {
            "marked_script": (
                "午后收拾完桌面，打开冰箱才发现果盘已经空了。我看到"
                "[[NO_SPLIT]]淘宝闪购有最高12元无门槛红包[[/NO_SPLIT]]，"
                "就买了个哈密瓜。送到后切几块装进盘里，坐在沙发上慢慢吃，"
                "剩下的用保鲜盒收好，晚上家里人回来还能一起分。"
            ),
            "avatar_prompt": "年轻中国女生在餐桌旁自然口播，全程直视镜头。",
            "identity_key": "圆脸-黑色短发",
            "outfit_key": "白衬衫-蓝牛仔裤",
            "person_prompt": (
                "竖屏9:16，固定中景，手机实拍，数字人口播首帧，人物约占画面二分之一，年轻中国女生坐在餐桌旁，"
                "场景只作为背景，正面眼睛直视镜头，人物面前桌上放着哈密瓜，"
                "商品不由人物手持，人物不看商品、不接触商品，非商品区域无logo，无字幕。"
                "自然光照明，真实肤色和皮肤纹理，人物居中坐定，背景轻微虚化，"
                "整体年轻自然干净生活化。"
            ),
            "title": "哈密瓜居家水果场景",
            "source_block_id": "",
            "source_slot_values": [],
        }
    )
    template.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    output_root = tmp_path / "output"
    result = run(
        [
            "export-csv",
            "--input",
            str(template),
            "--output-root",
            str(output_root),
            "--date",
            "20260805",
        ]
    )
    export_output: dict[str, Any] = json.loads(capsys.readouterr().out)
    csv_path = output_root / "20260805" / "hami-batch" / "hami-batch.csv"

    assert result == 0
    assert export_output["written"] == [str(csv_path)]
    assert csv_path.is_file()
    assert "[[NO_SPLIT]]" not in csv_path.read_text(encoding="utf-8")


@pytest.mark.e2e
def test_feishu_h3_cli_renders_reviewable_draft_without_external_submission(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "batch.json"
    source.write_text(
        json.dumps(
            {
                "task_name": "h3-draft-batch",
                "category": "水果",
                "tasks": [
                    {
                        "task_id": "TASK-001",
                        "marked_script": "完整口播正文",
                        "avatar_prompt": "人物自然口播，固定机位。",
                        "identity_key": "identity",
                        "outfit_key": "outfit",
                        "person_prompt": "竖屏真实生活化人物首帧",
                        "title": "水果场景",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    interface = Path(__file__).resolve().parents[2] / "configs/interfaces/feishu-h3.json"
    destination = tmp_path / "h3-draft.json"

    def valid_batch_report(_batch: object, _campaign: object, _config: object) -> dict[str, object]:
        return {"is_valid": True}

    monkeypatch.setattr(cli_module, "_validate_generated_batch", valid_batch_report)
    result = run(
        [
            "render-feishu-h3-drafts",
            "--input",
            str(source),
            "--interface",
            str(interface),
            "--output",
            str(destination),
            "--preset",
            "none",
        ]
    )

    output: dict[str, Any] = json.loads(capsys.readouterr().out)
    manifest: dict[str, Any] = json.loads(destination.read_text(encoding="utf-8"))
    assert result == 0
    assert output["review_required"] is True
    assert output["paid_image_generation_submitted"] is False
    assert output["h3_generation_submitted"] is False
    assert manifest["tasks"][0]["dreamina"]["model"] == "seedream_4.0"
    status = next(
        cell
        for cell in manifest["tasks"][0]["feishu"]["record_values"]
        if cell["field_key"] == "status"
    )
    assert status["value"] == ["草稿"]
