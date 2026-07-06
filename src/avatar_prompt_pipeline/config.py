from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import BenefitPoint, BriefValidationError, CampaignSpec, ProductBrief


class ProjectConfigError(ValueError):
    """Raised when a project configuration file is unsafe or invalid."""


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    project_id: str
    brief: ProductBrief
    campaign: CampaignSpec


_ALLOWED_TOP_LEVEL_KEYS = {
    "project_id",
    "category",
    "product_name",
    "selling_points",
    "forbidden_claims",
    "platform",
    "campaign_name",
    "benefit_points",
    "campaign_forbidden_expressions",
    "forbidden_expressions",
    "required_disclosures",
}

_ALLOWED_BENEFIT_KEYS = {
    "id",
    "text",
    "required",
    "exact_match",
    "no_split",
    "priority",
}


def _expect_mapping(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectConfigError(f"{context} 必须是 JSON object")
    return value


def _expect_string(value: Any, *, field: str, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ProjectConfigError(f"{field} 必须是字符串")
    return value


def _expect_string_tuple(value: Any, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProjectConfigError(f"{field} 必须是字符串数组")
    items: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str):
            raise ProjectConfigError(f"{field}[{index}] 必须是字符串")
        items.append(item)
    return tuple(items)


def _expect_bool(value: Any, *, field: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ProjectConfigError(f"{field} 必须是布尔值")
    return value


def _expect_int(value: Any, *, field: str, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int):
        raise ProjectConfigError(f"{field} 必须是整数")
    return value


def _parse_benefit_points(value: Any) -> tuple[BenefitPoint, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProjectConfigError("benefit_points 必须是数组")
    benefits: list[BenefitPoint] = []
    for index, item in enumerate(value, start=1):
        benefit_data = _expect_mapping(item, context=f"benefit_points[{index}]")
        unknown_keys = set(benefit_data) - _ALLOWED_BENEFIT_KEYS
        if unknown_keys:
            unknown = "、".join(sorted(unknown_keys))
            raise ProjectConfigError(f"benefit_points[{index}] 包含未知字段：{unknown}")
        try:
            benefits.append(
                BenefitPoint(
                    id=_expect_string(benefit_data.get("id"), field=f"benefit_points[{index}].id"),
                    text=_expect_string(
                        benefit_data.get("text"), field=f"benefit_points[{index}].text"
                    ),
                    required=_expect_bool(
                        benefit_data.get("required"),
                        field=f"benefit_points[{index}].required",
                        default=True,
                    ),
                    exact_match=_expect_bool(
                        benefit_data.get("exact_match"),
                        field=f"benefit_points[{index}].exact_match",
                        default=True,
                    ),
                    no_split=_expect_bool(
                        benefit_data.get("no_split"),
                        field=f"benefit_points[{index}].no_split",
                        default=True,
                    ),
                    priority=_expect_int(
                        benefit_data.get("priority"),
                        field=f"benefit_points[{index}].priority",
                        default=index,
                    ),
                )
            )
        except BriefValidationError as exc:
            raise ProjectConfigError(str(exc)) from exc
    return tuple(benefits)


def project_config_from_mapping(data: dict[str, Any]) -> ProjectConfig:
    unknown_keys = set(data) - _ALLOWED_TOP_LEVEL_KEYS
    if unknown_keys:
        unknown = "、".join(sorted(unknown_keys))
        raise ProjectConfigError(f"项目配置包含未知字段：{unknown}")
    try:
        brief = ProductBrief(
            category=_expect_string(data.get("category"), field="category"),
            product_name=_expect_string(data.get("product_name"), field="product_name"),
            selling_points=_expect_string_tuple(data.get("selling_points"), field="selling_points"),
            forbidden_claims=_expect_string_tuple(
                data.get("forbidden_claims"), field="forbidden_claims"
            ),
        )
        forbidden_expressions = data.get(
            "campaign_forbidden_expressions", data.get("forbidden_expressions")
        )
        campaign = CampaignSpec(
            platform=_expect_string(data.get("platform"), field="platform"),
            campaign_name=_expect_string(data.get("campaign_name"), field="campaign_name"),
            benefit_points=_parse_benefit_points(data.get("benefit_points")),
            forbidden_expressions=_expect_string_tuple(
                forbidden_expressions, field="campaign_forbidden_expressions"
            ),
            required_disclosures=_expect_string_tuple(
                data.get("required_disclosures"), field="required_disclosures"
            ),
        )
    except BriefValidationError as exc:
        raise ProjectConfigError(str(exc)) from exc
    return ProjectConfig(
        project_id=_expect_string(data.get("project_id"), field="project_id"),
        brief=brief,
        campaign=campaign,
    )


def load_project_config(path: str | Path) -> ProjectConfig:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProjectConfigError(f"无法读取项目配置：{source}") from exc
    except json.JSONDecodeError as exc:
        raise ProjectConfigError(f"项目配置不是有效 JSON：{source}") from exc
    return project_config_from_mapping(_expect_mapping(data, context="项目配置"))
