"""Prompt orchestration for avatar video task packages."""

from .artifacts import (
    default_manuscript_path,
    default_oceanengine_csv_path,
    default_task_directory,
    write_oceanengine_csv,
    write_segmentation_manuscript,
)
from .batch import (
    GeneratedTaskBatch,
    GeneratedTaskRecord,
    load_task_batch,
    task_batch_template,
    write_task_batch_template,
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
    validate_copy_mix,
    validate_visual_diversity,
    validate_visual_prompt,
    wrap_campaign_benefits,
    wrap_required_benefit,
)

__all__ = [
    "AvatarVideoPrompt",
    "BenefitPoint",
    "CampaignSpec",
    "CopyValidationReport",
    "GeneratedScript",
    "GeneratedTaskBatch",
    "GeneratedTaskRecord",
    "OceanengineTask",
    "ProductBrief",
    "PromptPackage",
    "VisualProfile",
    "compose_prompt_package",
    "default_manuscript_path",
    "default_oceanengine_csv_path",
    "default_task_directory",
    "load_task_batch",
    "strip_no_split_markers",
    "task_batch_template",
    "validate_batch_diversity",
    "validate_copy",
    "validate_copy_mix",
    "validate_visual_diversity",
    "validate_visual_prompt",
    "wrap_campaign_benefits",
    "wrap_required_benefit",
    "write_oceanengine_csv",
    "write_segmentation_manuscript",
    "write_task_batch_template",
]
