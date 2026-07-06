"""Prompt orchestration for avatar video task packages."""

from .artifacts import (
    default_manuscript_path,
    default_oceanengine_csv_path,
    default_task_directory,
    write_oceanengine_csv,
    write_segmentation_manuscript,
)
from .models import (
    AvatarVideoPrompt,
    BenefitPoint,
    CampaignSpec,
    CopyValidationReport,
    GeneratedScript,
    OceanengineTask,
    ProductBrief,
    PromptPackage,
    VisualProfile,
)
from .service import compose_prompt_package
from .validation import (
    strip_no_split_markers,
    validate_batch_diversity,
    validate_copy,
    validate_visual_diversity,
    wrap_campaign_benefits,
    wrap_required_benefit,
)

__all__ = [
    "AvatarVideoPrompt",
    "BenefitPoint",
    "CampaignSpec",
    "CopyValidationReport",
    "GeneratedScript",
    "OceanengineTask",
    "ProductBrief",
    "PromptPackage",
    "VisualProfile",
    "compose_prompt_package",
    "default_manuscript_path",
    "default_oceanengine_csv_path",
    "default_task_directory",
    "strip_no_split_markers",
    "validate_batch_diversity",
    "validate_copy",
    "validate_visual_diversity",
    "wrap_campaign_benefits",
    "wrap_required_benefit",
    "write_oceanengine_csv",
    "write_segmentation_manuscript",
]
