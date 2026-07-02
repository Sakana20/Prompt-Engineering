from __future__ import annotations

from .models import ProductBrief, PromptPackage
from .template_loader import TEMPLATE_VERSION, load_template
from .validation import strip_no_split_markers


def compose_prompt_package(brief: ProductBrief) -> PromptPackage:
    copywriting_template = load_template("copywriting_prompt.txt")
    avatar_template = load_template("avatar_prompt.txt")
    copywriting_prompt = copywriting_template.replace(
        "{{PRODUCT_CONTEXT}}", brief.product_context()
    )
    return PromptPackage(
        schema_version="1.0",
        template_version=TEMPLATE_VERSION,
        brief=brief,
        copywriting_prompt=copywriting_prompt,
        avatar_prompt_template=avatar_template,
        review_required=True,
    )


def render_avatar_prompt(script: str) -> str:
    cleaned_script = strip_no_split_markers(script.replace("\x00", "")).strip()
    if not cleaned_script:
        raise ValueError("口播文案不能为空")
    return load_template("avatar_prompt.txt").replace("{{SCRIPT}}", cleaned_script)
