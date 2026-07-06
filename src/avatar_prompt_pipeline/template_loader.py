from __future__ import annotations

from importlib.resources import files

TEMPLATE_VERSION = "2026-07-03-generic-campaign-v1"


def load_template(name: str) -> str:
    template = files("avatar_prompt_pipeline.templates").joinpath(name).read_text(encoding="utf-8")
    return template.strip()
