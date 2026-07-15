from __future__ import annotations

from importlib.resources import files

TEMPLATE_VERSION = "2026-07-15-require-platform-v4"


def load_template(name: str) -> str:
    template = files("avatar_prompt_pipeline.templates").joinpath(name).read_text(encoding="utf-8")
    return template.strip()
