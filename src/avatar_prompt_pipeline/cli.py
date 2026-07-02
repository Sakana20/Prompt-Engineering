from __future__ import annotations

import argparse
from collections.abc import Sequence

from .io import serialize_package, write_package
from .models import BriefValidationError, ProductBrief
from .service import compose_prompt_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="淘宝闪购数字人 Prompt 编排工具")
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
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
    package = compose_prompt_package(brief)
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
