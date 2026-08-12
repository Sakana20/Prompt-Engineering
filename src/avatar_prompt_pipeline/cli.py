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
from .learning.asr_provider import AsrProviderError, AsrWorkerConfig
from .learning.models import CandidateKind, LearningCandidate, LearningStatus
from .learning.preflight import PREFLIGHT_BLOCKED_EXIT_CODE, inspect_learning_preflight
from .learning.publication import load_publication_manifest, publish_manifest
from .learning.service import LearningService
from .learning.store import CandidateNotFoundError, RevisionConflictError
from .learning.validation import LearningValidationError
from .models import BriefValidationError, CampaignSpec, ProductBrief, ValidationIssue
from .presets import TAOBAO_DEFAULT_CAMPAIGN, campaign_from_benefits
from .service import compose_prompt_package
from .validation import (
    DEFAULT_VALIDATION_CONFIG,
    validate_batch_diversity,
    validate_copy,
    validate_copy_mix,
    validate_learning_diversity,
    validate_source_logic,
    validate_visual_diversity,
    validate_visual_prompt,
)

DEFAULT_OUTPUT_ROOT = Path("/Users/sakana/Desktop/Work/Codex/Prompt Engineering")
DEFAULT_LEARNING_ROOT = Path(__file__).resolve().parents[2] / "learning"
DEFAULT_DAILY_MEDIA_ROOT = Path("/Users/sakana/Desktop/Work/2026")
DEFAULT_DAILY_MEDIA_SUFFIX = Path("淘宝闪购/素材")
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
    transcribe = commands.add_parser(
        "learning-transcribe", help="从显式本地媒体创建 ASR 文案学习候选"
    )
    transcribe.add_argument(
        "--input",
        type=Path,
        action="append",
        help=(
            "显式媒体文件或一级目录，可重复；省略时使用当天 "
            "/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材"
        ),
    )
    transcribe.add_argument("--learning-root", type=Path, default=DEFAULT_LEARNING_ROOT)
    transcribe.add_argument("--date", help="来源日期 YYYY-MM-DD；默认本地日期")
    transcribe.add_argument(
        "--funasr-python",
        type=Path,
        default=AsrWorkerConfig().python_executable,
        help="FunASR 既有虚拟环境 Python",
    )
    transcribe.add_argument("--model-dir", type=Path, default=AsrWorkerConfig().model_dir)
    transcribe.add_argument("--device", default="mps")
    transcribe.add_argument("--timeout", type=float, default=900.0)
    add_person = commands.add_parser(
        "learning-add-person-prompt", help="按需创建独立人物 Prompt 学习候选"
    )
    person_input = add_person.add_mutually_exclusive_group(required=True)
    person_input.add_argument("--text")
    person_input.add_argument("--input", type=Path)
    add_person.add_argument("--source-label", default="用户人工样本")
    add_person.add_argument("--learning-root", type=Path, default=DEFAULT_LEARNING_ROOT)
    learning_preflight = commands.add_parser(
        "learning-preflight",
        help="生成前检查 approved 候选、published 候选和正式学习资源",
    )
    learning_preflight.add_argument("--learning-root", type=Path, default=DEFAULT_LEARNING_ROOT)
    learning_list = commands.add_parser("learning-list", help="列出学习候选")
    _add_learning_kind(learning_list)
    learning_list.add_argument("--status", choices=tuple(status.value for status in LearningStatus))
    learning_list.add_argument("--learning-root", type=Path, default=DEFAULT_LEARNING_ROOT)
    update = commands.add_parser("learning-update", help="按 revision 保存候选编辑稿")
    _add_learning_candidate_arguments(update)
    update.add_argument("--edited-file", type=Path, required=True)
    submit = commands.add_parser("learning-submit-review", help="提交学习候选审核")
    _add_learning_candidate_arguments(submit)
    approve = commands.add_parser("learning-approve", help="批准待审学习候选")
    _add_learning_candidate_arguments(approve)
    reject = commands.add_parser("learning-reject", help="驳回待审学习候选")
    _add_learning_candidate_arguments(reject)
    reject.add_argument("--reason", required=True)
    publish = commands.add_parser("learning-publish", help="校验 Codex 发布清单并原子发布")
    _add_learning_candidate_arguments(publish)
    publish.add_argument("--manifest", type=Path, required=True)
    return parser


def _add_learning_kind(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kind", choices=("copy", "person"), required=True)


def _add_learning_candidate_arguments(parser: argparse.ArgumentParser) -> None:
    _add_learning_kind(parser)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--expected-revision", type=int, required=True)
    parser.add_argument("--learning-root", type=Path, default=DEFAULT_LEARNING_ROOT)


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
    learning_diversity = validate_learning_diversity(
        opening_types=[task.opening_type for task in batch.tasks],
        rhythm_types=[task.rhythm_type for task in batch.tasks],
        need_types=[task.need_type for task in batch.tasks],
        emotion_types=[task.emotion_type for task in batch.tasks],
        identity_tags=[task.identity_tags for task in batch.tasks],
        outfit_tags=[task.outfit_tags for task in batch.tasks],
    )
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
        "learning_diversity_warnings": _issues_to_dict(learning_diversity),
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
    if str(args.command).startswith("learning-"):
        return _run_learning_command(args)
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


def _learning_date(value: str | None) -> datetime:
    if value is None:
        return datetime.now().astimezone()
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise LearningValidationError("--date 必须是有效的 YYYY-MM-DD") from exc
    return parsed.astimezone()


def default_daily_media_directory(moment: datetime) -> Path:
    """Resolve the user-configured daily media directory for a local date."""
    return DEFAULT_DAILY_MEDIA_ROOT / moment.strftime("%m.%d") / DEFAULT_DAILY_MEDIA_SUFFIX


def _candidate_json(candidate: object) -> dict[str, object]:
    to_dict = getattr(candidate, "to_dict", None)
    if not callable(to_dict):
        raise AssertionError("candidate lacks to_dict")
    result = to_dict()
    if not isinstance(result, dict):
        raise AssertionError("candidate to_dict must return dict")
    return result


def _run_learning_command(args: argparse.Namespace) -> int:
    try:
        if args.command == "learning-transcribe":
            config = AsrWorkerConfig(
                python_executable=args.funasr_python,
                model_dir=args.model_dir,
                device=str(args.device),
                timeout_seconds=float(args.timeout),
            )
            if config.timeout_seconds <= 0:
                raise LearningValidationError("--timeout 必须大于 0")
            source_moment = _learning_date(args.date)
            inputs = (
                tuple(args.input) if args.input else (default_daily_media_directory(source_moment),)
            )
            service = LearningService.from_root(args.learning_root, worker_config=config)
            result = service.transcribe(
                inputs,
                source_date=source_moment.date(),
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            failed = result["failed"]
            if isinstance(failed, bool) or not isinstance(failed, int):
                raise AssertionError("transcribe failed count must be int")
            return 0 if failed == 0 else 1
        service = LearningService.from_root(args.learning_root)
        if args.command == "learning-preflight":
            report = inspect_learning_preflight(service.store)
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
            return 0 if report.ready_for_generation else PREFLIGHT_BLOCKED_EXIT_CODE
        if args.command == "learning-add-person-prompt":
            if args.text is not None:
                text = str(args.text)
            else:
                try:
                    text = args.input.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    raise LearningValidationError("人物 Prompt 输入必须是可读 UTF-8 文本") from exc
            person_candidate = service.add_person_prompt(text, source_label=str(args.source_label))
            print(json.dumps(_candidate_json(person_candidate), ensure_ascii=False, indent=2))
            return 0
        kind = CandidateKind(str(args.kind))
        if args.command == "learning-list":
            status = LearningStatus(str(args.status)) if args.status else None
            candidates = service.list(kind, status=status)
            print(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "kind": kind.value,
                        "count": len(candidates),
                        "candidates": [_candidate_json(candidate) for candidate in candidates],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        candidate_id = str(args.candidate_id)
        expected_revision = int(args.expected_revision)
        candidate: LearningCandidate
        if args.command == "learning-update":
            try:
                edited = args.edited_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise LearningValidationError("edited-file 必须是可读 UTF-8 文本") from exc
            candidate = service.update(
                kind,
                candidate_id,
                expected_revision=expected_revision,
                edited_text=edited,
            )
        elif args.command == "learning-submit-review":
            candidate = service.submit_review(
                kind, candidate_id, expected_revision=expected_revision
            )
        elif args.command == "learning-approve":
            candidate = service.approve(kind, candidate_id, expected_revision=expected_revision)
        elif args.command == "learning-reject":
            candidate = service.reject(
                kind,
                candidate_id,
                expected_revision=expected_revision,
                reason=str(args.reason),
            )
        elif args.command == "learning-publish":
            manifest = load_publication_manifest(args.manifest)
            if (
                manifest.kind is not kind
                or manifest.candidate_id != candidate_id
                or manifest.revision != expected_revision
            ):
                raise LearningValidationError(
                    "CLI kind/candidate-id/expected-revision 必须与发布清单完全一致"
                )
            candidate = publish_manifest(service.store, manifest)
        else:
            raise AssertionError(f"未知学习命令：{args.command}")
        print(json.dumps(_candidate_json(candidate), ensure_ascii=False, indent=2))
        return 0
    except (LearningValidationError, RevisionConflictError, AsrProviderError) as exc:
        print(
            json.dumps(
                {"is_valid": False, "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    except CandidateNotFoundError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
