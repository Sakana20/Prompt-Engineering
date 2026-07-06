import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).parents[2] / "prompt-engineering"


@pytest.mark.e2e
def test_skill_launcher_keeps_transparent_remainder_arguments() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "scripts" / "run_cli.py"),
            "--debug",
            "--python-executable",
            sys.executable,
            "--",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "'-m', 'avatar_prompt_pipeline.cli', '--help'" in completed.stdout
    assert "通用商品数字人 Prompt 编排工具" in completed.stdout
