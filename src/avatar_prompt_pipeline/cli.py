from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .io import serialize_package, write_package
from .models import BriefValidationError, CampaignSpec, ProductBrief
from .presets import TAOBAO_DEFAULT_CAMPAIGN, campaign_from_benefits
from .service import compose_prompt_package
from .validation import validate_copy


def _add_campaign_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--preset",
        choices=("taobao-instant-commerce-default", "none"),
        default="taobao-instant-commerce-default",
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


def _campaign_from_args(args: argparse.Namespace) -> CampaignSpec:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通用商品数字人 Prompt 编排工具")
    commands = parser.add_subparsers(dest="command", required=True)
    compose = commands.add_parser("compose", help="根据商品资料生成 Prompt 包")
    compose.add_argument("--category", required=True, help="商品品类")
    compose.add_argument("--product-name", default="", help="具体商品名称")
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
    campaign = _campaign_from_args(args)
    if args.command == "validate-copy":
        report = validate_copy(args.text, campaign)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0 if report.is_valid else 1
    if args.command != "compose":
        raise AssertionError(f"未知命令：{args.command}")
    try:
        brief = ProductBrief(
            category=args.category,
            product_name=args.product_name,
            selling_points=tuple(args.selling_point),
            forbidden_claims=tuple(args.forbidden_claim),
        )
    except BriefValidationError as exc:
        raise SystemExit(str(exc)) from exc
    package = compose_prompt_package(brief, campaign)
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
