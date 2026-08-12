import pytest

from avatar_prompt_pipeline.learning.text_cleanup import normalize_asr_editable_draft


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "以 前 上 班 我 忍 气 吞 声 现 在 我 直 接 黑 化",
            "以前上班我忍气吞声现在我直接黑化",
        ),
        ("这 杯 苹 果 c 喝 完", "这杯苹果c喝完"),
        ("iPhone 15 Pro 真 好 喝", "iPhone 15 Pro真好喝"),
        ("你 好 ，， 世 界 \uff01\uff01", "你好，世界\uff01"),
        ("  hello\tworld\n中 文  ", "hello world中文"),
    ],
)
def test_normalize_asr_editable_draft(raw: str, expected: str) -> None:
    assert normalize_asr_editable_draft(raw) == expected
