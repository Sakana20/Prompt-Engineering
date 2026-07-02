"""Prompt orchestration for avatar video task packages."""

from .models import ProductBrief, PromptPackage
from .service import compose_prompt_package

__all__ = ["ProductBrief", "PromptPackage", "compose_prompt_package"]
