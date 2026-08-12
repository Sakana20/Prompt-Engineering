from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.funasr_worker import run_worker


@pytest.mark.integration
def test_worker_rejects_output_outside_prompt_owned_work_dir(tmp_path: Path) -> None:
    media = tmp_path / "sample.mp3"
    media.write_bytes(b"audio")
    with pytest.raises(ValueError, match="work-dir"):
        run_worker(
            input_path=media,
            output_path=tmp_path / "outside.json",
            work_dir=tmp_path / "work",
            model_dir=tmp_path / "model",
            device="cpu",
        )


@pytest.mark.integration
def test_worker_source_has_no_cross_repo_sys_path_or_shell_true() -> None:
    source = (
        Path(__file__).parents[2] / "src/avatar_prompt_pipeline/learning/funasr_worker.py"
    ).read_text(encoding="utf-8")
    assert "sys.path" not in source
    assert "shell=True" not in source
