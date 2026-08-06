from __future__ import annotations

from importlib.resources import files

TEMPLATE_VERSION = "2026-08-06-adaptive-three-mode-v19"


def load_template(name: str) -> str:
    template = files("avatar_prompt_pipeline.templates").joinpath(name).read_text(encoding="utf-8")
    return template.strip()
