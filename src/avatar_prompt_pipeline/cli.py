from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .artifacts import (
    write_audit_json,
    write_libtv_omnihuman_csv,
    write_libtv_omnihuman_interface_config,
    write_libtv_omnihuman_plan,
    write_oceanengine_csv,
    write_review_markdown,
    write_segmentation_manuscript,
)
from .batch import (
    GeneratedTaskBatch,
    TaskBatchError,
    load_task_batch,
    write_task_batch_template,
)
from .config import ProjectConfig, ProjectConfigError, load_project_config
from .io import serialize_package, write_package
from .models import BriefValidationError, CampaignSpec, ProductBrief, ValidationIssue
from .presets import TAOBAO_DEFAULT_CAMPAIGN, campaign_from_benefits
from .service import compose_prompt_package
from .validation import (
    DEFAULT_VALIDATION_CONFIG,
    validate_batch_diversity,
    validate_copy,
    validate_copy_mix,
    validate_source_logic,
    validate_visual_diversity,
    validate_visual_prompt,
)

DEFAULT_OUTPUT_ROOT = Path("/Users/sakana/Desktop/Work/Codex/Prompt Engineering")
PACKAGE_FORMATS = (
    "json",
    "markdown",
    "segmentation_manuscript",
    "csv",
    "libtv_omnihuman_package",
)


def _add_campaign_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--preset",
        choices=("taobao-instant-commerce-default", "none"),
        default=None,
        help="活动预设；none 表示不自动加入利益点",
    )
    parser.add_argument("--platform", default="", help="平台名称")
    parser.add_argument("--campaign-name", default="", help="活动名称")
    parser.add_argument(
        "--benefit-point",
        action="append",
        default=[],
        help="已确认利益点，可重复传入；提供后覆盖预设利益点",
    )
    parser.add_argument("--config", help="项目配置 JSON；传入后使用配置中的商品和活动口径")


def _has_campaign_overrides(args: argparse.Namespace) -> bool:
    return bool(
        args.platform or args.campaign_name or args.benefit_point or args.preset is not None
    )


def _load_config_from_args(args: argparse.Namespace) -> ProjectConfig | None:
    if not args.config:
        return None
    if _has_campaign_overrides(args):
        raise SystemExit("使用 --config 时不要同时传入活动口径参数")
    try:
        return load_project_config(args.config)
    except ProjectConfigError as exc:
        raise SystemExit(str(exc)) from exc


def _campaign_from_args(
    args: argparse.Namespace, config: ProjectConfig | None = None
) -> CampaignSpec:
    if config is not None:
        return config.campaign
    benefit_points = tuple(str(value) for value in args.benefit_point)
    if benefit_points:
        return campaign_from_benefits(
            benefit_points,
            platform=str(args.platform),
            campaign_name=str(args.campaign_name),
        )
    if args.preset == "none":
        return CampaignSpec(
            platform=str(args.platform),
            campaign_name=str(args.campaign_name),
        )
    return TAOBAO_DEFAULT_CAMPAIGN


def _brief_from_args(args: argparse.Namespace, config: ProjectConfig | None = None) -> ProductBrief:
    if config is not None:
        if args.category or args.product_name or args.selling_point or args.forbidden_claim:
            raise SystemExit("使用 --config 时不要同时传入商品资料参数")
        return config.brief
    if not args.category:
        raise SystemExit("compose 需要 --category，或传入包含 category 的 --config")
    try:
        return ProductBrief(
            category=args.category,
            product_name=args.product_name or "",
            selling_points=tuple(args.selling_point),
            forbidden_claims=tuple(args.forbidden_claim),
        )
    except BriefValidationError as exc:
        raise SystemExit(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通用商品数字人 Prompt 编排工具")
    commands = parser.add_subparsers(dest="command", required=True)
    init_batch = commands.add_parser("init-batch", help="创建仅需填写的任务清单模板")
    init_batch.add_argument("--task-name", required=True, help="任务目录名")
    init_batch.add_argument("--category", required=True, help="真实商品品类")
    init_batch.add_argument("--count", type=int, default=1, help="任务数量，默认 1")
    init_batch.add_argument("--task-prefix", default="TASK", help="ASCII task_id 前缀")
    init_batch.add_argument("--output", type=Path, required=True, help="模板 JSON 输出路径")
    compose = commands.add_parser("compose", help="根据商品资料生成 Prompt 包")
    compose.add_argument("--category", help="商品品类")
    compose.add_argument("--product-name", default=None, help="具体商品名称")
    compose.add_argument(
        "--selling-point", action="append", default=[], help="已确认真实卖点，可重复传入"
    )
    compose.add_argument(
        "--forbidden-claim", action="append", default=[], help="禁止使用的信息，可重复传入"
    )
    compose.add_argument("--output", help="输出 JSON 路径；省略时打印到标准输出")
    _add_campaign_arguments(compose)
    validate = commands.add_parser("validate-copy", help="校验一段已生成口播")
    validate.add_argument("text", help="待校验口播正文")
    _add_campaign_arguments(validate)
    validate_batch = commands.add_parser("validate-batch", help="校验 Codex 生成的任务清单")
    validate_batch.add_argument("--input", required=True, help="生成结果 JSON 清单")
    _add_campaign_arguments(validate_batch)
    package = commands.add_parser("package", help="校验并输出 Skill 任务产物")
    package.add_argument("--input", required=True, help="生成结果 JSON 清单")
    package.add_argument(
        "--format",
        action="append",
        choices=PACKAGE_FORMATS,
        required=True,
        help="输出格式，可重复传入",
    )
    package.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="输出根目录；目录层级固定为 <日期>/<任务名>",
    )
    package.add_argument("--date", help="输出日期，格式 YYYYMMDD；默认使用本地日期")
    _add_campaign_arguments(package)
    export_csv = commands.add_parser("export-csv", help="从已填写清单生成 Oceanengine CSV")
    export_csv.add_argument("--input", required=True, help="已填写的任务清单 JSON")
    export_csv.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="输出根目录；目录层级固定为 <日期>/<任务名>",
    )
    export_csv.add_argument("--date", help="输出日期，格式 YYYYMMDD；默认使用本地日期")
    _add_campaign_arguments(export_csv)
    return parser


def _load_batch(path: str) -> GeneratedTaskBatch:
    try:
        return load_task_batch(path)
    except TaskBatchError as exc:
        raise SystemExit(str(exc)) from exc


def _issues_to_dict(issues: Sequence[ValidationIssue]) -> list[dict[str, object]]:
    return [asdict(issue) for issue in issues]


def _validate_generated_batch(
    batch: GeneratedTaskBatch,
    campaign: CampaignSpec,
    config: ProjectConfig | None,
) -> dict[str, object]:
    validation_config = (
        config.validation_config if config is not None else DEFAULT_VALIDATION_CONFIG
    )
    task_reports: list[dict[str, object]] = []
    for task in batch.tasks:
        copy_report = validate_copy(task.marked_script, campaign, validation_config)
        source_logic_issues = validate_source_logic(
            task.marked_script,
            category=batch.category,
            copy_mode=task.copy_mode,
            source_block_id=task.source_block_id,
            source_slot_values=task.source_slot_values,
            campaign=campaign,
        )
        person_issues = validate_visual_prompt(task.person_prompt)
        image_issues = validate_visual_prompt(task.image_prompt)
        task_reports.append(
            {
                "task_id": task.task_id,
                "copy_mode": task.copy_mode,
                "source_block_id": task.source_block_id,
                "source_slot_values": (
                    list(task.source_slot_values) if task.source_slot_values is not None else None
                ),
                "rewrite_anchor_phrases": list(task.rewrite_anchor_phrases),
                "copy": copy_report.to_dict(),
                "source_logic_issues": _issues_to_dict(source_logic_issues),
                "person_prompt_issues": _issues_to_dict(person_issues),
                "image_prompt_issues": _issues_to_dict(image_issues),
                "is_valid": (
                    not copy_report.issues
                    and not source_logic_issues
                    and not person_issues
                    and not image_issues
                ),
            }
        )
    copy_diversity = validate_batch_diversity([task.marked_script for task in batch.tasks])
    copy_mix = validate_copy_mix(
        [task.copy_mode for task in batch.tasks],
        [task.source_block_id for task in batch.tasks],
        [task.marked_script for task in batch.tasks],
        [task.rewrite_anchor_phrases for task in batch.tasks],
    )
    visual_diversity = validate_visual_diversity([task.visual_profile() for task in batch.tasks])
    is_valid = all(bool(report["is_valid"]) for report in task_reports)
    is_valid = is_valid and not copy_diversity and not copy_mix and not visual_diversity
    return {
        "schema_version": "1.0",
        "task_name": batch.task_name,
        "category": batch.category,
        "is_valid": is_valid,
        "tasks": task_reports,
        "copy_diversity_issues": _issues_to_dict(copy_diversity),
        "copy_mix_issues": _issues_to_dict(copy_mix),
        "visual_diversity_issues": _issues_to_dict(visual_diversity),
    }


def _output_date(value: str | None) -> str:
    if value is None:
        return datetime.now().astimezone().strftime("%Y%m%d")
    if len(value) != 8 or not value.isdigit():
        raise SystemExit("--date 必须使用 YYYYMMDD 格式")
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise SystemExit("--date 不是有效日期") from exc
    return value


def _package_destinations(
    batch: GeneratedTaskBatch, formats: Sequence[str], output_root: Path, date: str
) -> dict[str, tuple[Path, ...]]:
    directory = output_root / date / batch.task_name
    destinations: dict[str, tuple[Path, ...]] = {}
    if "json" in formats:
        destinations["json"] = (directory / f"{batch.task_name}.audit.json",)
    if "markdown" in formats:
        destinations["markdown"] = (directory / f"{batch.task_name}.review.md",)
    if "segmentation_manuscript" in formats:
        destinations["segmentation_manuscript"] = tuple(
            directory / f"{task.task_id}.smartsplit.txt" for task in batch.tasks
        )
    if "csv" in formats:
        destinations["csv"] = (directory / f"{batch.task_name}.csv",)
    if "libtv_omnihuman_package" in formats:
        destinations["libtv_omnihuman_package"] = (
            directory / f"{batch.task_name}.libtv.csv",
            directory / f"{batch.task_name}.libtv.interface.json",
            directory / f"{batch.task_name}.libtv.plan.md",
        )
    collisions = [path for paths in destinations.values() for path in paths if path.exists()]
    if collisions:
        rendered = "、".join(str(path) for path in collisions)
        raise SystemExit(f"拒绝覆盖已有文件：{rendered}")
    return destinations


def _write_selected_formats(
    *,
    batch: GeneratedTaskBatch,
    campaign: CampaignSpec,
    config: ProjectConfig | None,
    report: dict[str, object],
    destinations: dict[str, tuple[Path, ...]],
) -> list[Path]:
    validation_config = (
        config.validation_config if config is not None else DEFAULT_VALIDATION_CONFIG
    )
    written: list[Path] = []
    if paths := destinations.get("json"):
        payload = {
            "batch": batch.to_dict(),
            "campaign": asdict(campaign),
            "validation_config": asdict(validation_config),
            "validation": report,
            "review_required": True,
        }
        written.append(write_audit_json(paths[0], payload))
    if paths := destinations.get("markdown"):
        written.append(
            write_review_markdown(
                paths[0],
                task_name=batch.task_name,
                category=batch.category,
                campaign=campaign,
                tasks=batch.tasks,
            )
        )
    if paths := destinations.get("segmentation_manuscript"):
        for path, task in zip(paths, batch.tasks, strict=True):
            written.append(
                write_segmentation_manuscript(path, task.marked_script, campaign, validation_config)
            )
    oceanengine_tasks = tuple(
        task.oceanengine_task(notes=batch.notes_for(index))
        for index, task in enumerate(batch.tasks)
    )
    if paths := destinations.get("csv"):
        written.append(
            write_oceanengine_csv(paths[0], oceanengine_tasks, campaign, validation_config)
        )
    if paths := destinations.get("libtv_omnihuman_package"):
        libtv_tasks = tuple(
            task.libtv_task(notes=batch.notes_for(index)) for index, task in enumerate(batch.tasks)
        )
        written.append(
            write_libtv_omnihuman_csv(paths[0], libtv_tasks, campaign, validation_config)
        )
        written.append(write_libtv_omnihuman_interface_config(paths[1]))
        written.append(write_libtv_omnihuman_plan(paths[2], libtv_tasks))
    return written


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init-batch":
        try:
            destination = write_task_batch_template(
                args.output,
                task_name=str(args.task_name),
                category=str(args.category),
                count=int(args.count),
                task_prefix=str(args.task_prefix),
            )
        except (FileExistsError, TaskBatchError) as exc:
            raise SystemExit(str(exc)) from exc
        print(
            json.dumps(
                {
                    "template": str(destination),
                    "task_count": int(args.count),
                    "next_step": "填写 JSON 字段后运行 avatar-prompts export-csv",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    config = _load_config_from_args(args)
    campaign = _campaign_from_args(args, config)
    validation_config = (
        config.validation_config if config is not None else DEFAULT_VALIDATION_CONFIG
    )
    if args.command == "validate-copy":
        report = validate_copy(args.text, campaign, validation_config)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0 if report.is_valid else 1
    if args.command in {"validate-batch", "package", "export-csv"}:
        batch = _load_batch(str(args.input))
        if config is not None and config.brief.category != batch.category:
            raise SystemExit(
                f"任务清单 category 与项目配置不一致：{batch.category} != {config.brief.category}"
            )
        batch_report = _validate_generated_batch(batch, campaign, config)
        if args.command == "validate-batch":
            print(json.dumps(batch_report, ensure_ascii=False, indent=2))
            return 0 if batch_report["is_valid"] else 1
        if not batch_report["is_valid"]:
            print(json.dumps(batch_report, ensure_ascii=False, indent=2))
            return 1
        formats = (
            ("csv",)
            if args.command == "export-csv"
            else tuple(dict.fromkeys(str(value) for value in args.format))
        )
        date = _output_date(args.date)
        destinations = _package_destinations(batch, formats, args.output_root, date)
        written = _write_selected_formats(
            batch=batch,
            campaign=campaign,
            config=config,
            report=batch_report,
            destinations=destinations,
        )
        print(
            json.dumps(
                {
                    "is_valid": True,
                    "review_required": True,
                    "written": [str(path) for path in written],
                    "paid_generation_submitted": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command != "compose":
        raise AssertionError(f"未知命令：{args.command}")
    brief = _brief_from_args(args, config)
    package = compose_prompt_package(
        brief,
        campaign,
        validation_config=validation_config,
        language_style=config.language_style if config is not None else None,
    )
    if args.output:
        destination = write_package(args.output, package)
        print(f"Prompt 包已写入：{destination}")
    else:
        print(serialize_package(package), end="")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
