from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .config import ProjectConfig, ProjectConfigError, load_project_config
from .io import serialize_package, write_package
from .models import BriefValidationError, CampaignSpec, ProductBrief
from .presets import TAOBAO_DEFAULT_CAMPAIGN, campaign_from_benefits
from .service import compose_prompt_package
from .validation import DEFAULT_VALIDATION_CONFIG, validate_copy


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
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = _load_config_from_args(args)
    campaign = _campaign_from_args(args, config)
    validation_config = (
        config.validation_config if config is not None else DEFAULT_VALIDATION_CONFIG
    )
    if args.command == "validate-copy":
        report = validate_copy(args.text, campaign, validation_config)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0 if report.is_valid else 1
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
