#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

DEFAULT_PROJECT_ROOT = Path("/Users/sakana/Desktop/Work/Codex/Prompt Engineering")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transparent launcher for the avatar-prompts CLI.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(os.environ.get("AVATAR_PROMPT_PROJECT", DEFAULT_PROJECT_ROOT)),
        help="Prompt Engineering project root.",
    )
    parser.add_argument("--debug", action="store_true", help="Print the forwarded command.")
    parser.add_argument(
        "--python-executable",
        default=os.environ.get("AVATAR_PROMPT_PYTHON"),
        help="Run the installed module with this Python instead of invoking uv.",
    )
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="Arguments passed unchanged.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    forwarded = list(args.arguments)
    if forwarded[:1] == ["--"]:
        forwarded = forwarded[1:]
    command = (
        [args.python_executable, "-m", "avatar_prompt_pipeline.cli", *forwarded]
        if args.python_executable
        else ["uv", "run", "avatar-prompts", *forwarded]
    )
    if args.debug:
        print(f"[taobao-avatar-video] cwd={args.project_root}")
        print(f"[taobao-avatar-video] command={command!r}")
    completed = subprocess.run(command, cwd=args.project_root, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
