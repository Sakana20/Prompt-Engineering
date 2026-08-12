import pytest

from avatar_prompt_pipeline.learning.options import (
    copy_learning_field_options,
    validate_copy_learning_fields,
)
from avatar_prompt_pipeline.learning.validation import LearningValidationError


def test_copy_learning_options_are_labeled_and_machine_stable() -> None:
    options = copy_learning_field_options()

    assert [item["value"] for item in options["category_family"]] == [
        "",
        "beverage",
        "other",
    ]
    assert {item["label"] for item in options["source_usage"]} == {
        "直接填槽",
        "AI 改写参考",
    }
    assert all(item["description"] for values in options.values() for item in values)


def test_copy_learning_options_reject_free_form_values() -> None:
    with pytest.raises(LearningValidationError, match="品类族"):
        validate_copy_learning_fields(
            category_family="用户随便填写",
            consumption_need="meal",
            season="all",
            source_usage=("source_fill",),
        )

    with pytest.raises(LearningValidationError, match="来源块用途"):
        validate_copy_learning_fields(
            category_family="beverage",
            consumption_need="commute",
            season="summer",
            source_usage=("natural_generate",),
        )
