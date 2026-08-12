import sys
from datetime import date
from pathlib import Path

import pytest

from avatar_prompt_pipeline.learning.asr_provider import (
    AsrProviderError,
    AsrWorkerConfig,
    ParaformerSubprocessProvider,
)
from avatar_prompt_pipeline.learning.models import CandidateKind, CopyLearningCandidate
from avatar_prompt_pipeline.learning.service import LearningService
from avatar_prompt_pipeline.learning.store import LearningStore


def _worker(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_default_worker_uses_isolated_python_and_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    venv_python = tmp_path / "funasr-venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.symlink_to(sys.executable)
    config = AsrWorkerConfig(python_executable=venv_python)
    worker = Path("/tmp/prompt-owned-worker.py")

    expected_python = str(venv_python.absolute())
    assert config.worker_prefix(worker) == (
        expected_python,
        "-I",
        "-B",
        "/tmp/prompt-owned-worker.py",
    )
    preflight = config.preflight_command()
    assert preflight is not None
    assert preflight[:4] == (expected_python, "-I", "-B", "-c")
    assert Path(preflight[0]).is_symlink()
    assert Path(preflight[0]).resolve() != Path(preflight[0])
    assert "funasr_timeline.audio" in preflight[4]
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/wrong-parent-environment")
    monkeypatch.setenv("__PYVENV_LAUNCHER__", "/tmp/wrong-parent-python")
    monkeypatch.setenv("PYTHONEXECUTABLE", "/tmp/wrong-python")
    environment = ParaformerSubprocessProvider._worker_environment()
    assert "VIRTUAL_ENV" not in environment
    assert "__PYVENV_LAUNCHER__" not in environment
    assert "PYTHONEXECUTABLE" not in environment


@pytest.mark.integration
def test_default_worker_preflight_failure_is_reported_per_media(tmp_path: Path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"video")
    provider = ParaformerSubprocessProvider(
        AsrWorkerConfig(
            python_executable=tmp_path / "missing-python",
            model_dir=tmp_path / "model",
            timeout_seconds=5,
        )
    )
    service = LearningService(LearningStore(tmp_path / "learning"), asr_provider=provider)

    result = service.transcribe((media,), source_date=date(2026, 8, 12))

    assert result["succeeded"] == 0
    assert result["failed"] == 1
    failures = result["failures"]
    assert isinstance(failures, list)
    assert "无法启动 FunASR Python 环境预检" in str(failures[0]["error"])
    assert not (tmp_path / "learning" / "copy" / "candidates").exists()


@pytest.mark.integration
def test_injected_asr_worker_success_and_archive(tmp_path: Path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"video")
    script = _worker(
        tmp_path / "fake_worker.py",
        """import argparse, json
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('input','output','work-dir','model-dir','device'):
    p.add_argument('--'+name, required=True)
a=p.parse_args()
payload={'schema_version':'1.0','provider':'paraformer-zh','model':'fake','source_media':str(Path(a.input).resolve()),'asr_audio':str(Path(a.input).resolve()),'audio_conversion':{},'text':'测试识别','tokens':[{'index':0,'text':'测试','start_ms':0,'end_ms':120,'source':'paraformer-zh'}]}
Path(a.output).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
""",
    )
    config = AsrWorkerConfig(command_prefix=(sys.executable, str(script)), timeout_seconds=5)

    result = ParaformerSubprocessProvider(config).transcribe(media, tmp_path / "work")

    assert result.text == "测试识别"
    assert (tmp_path / "work" / "worker-result.archived.json").is_file()


@pytest.mark.integration
def test_injected_asr_worker_rejects_invalid_json_and_times_out(tmp_path: Path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"video")
    invalid = _worker(
        tmp_path / "invalid.py",
        """import argparse
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('input','output','work-dir','model-dir','device'):
    p.add_argument('--'+name, required=True)
a=p.parse_args(); Path(a.output).write_text('not-json', encoding='utf-8')
""",
    )
    with pytest.raises(AsrProviderError, match="非法 JSON"):
        ParaformerSubprocessProvider(
            AsrWorkerConfig(command_prefix=(sys.executable, str(invalid)), timeout_seconds=5)
        ).transcribe(media, tmp_path / "invalid-work")

    slow = _worker(
        tmp_path / "slow.py",
        "import time\ntime.sleep(2)\n",
    )
    with pytest.raises(AsrProviderError, match="超时"):
        ParaformerSubprocessProvider(
            AsrWorkerConfig(command_prefix=(sys.executable, str(slow)), timeout_seconds=0.05)
        ).transcribe(media, tmp_path / "slow-work")


@pytest.mark.integration
def test_transcribe_cache_reuses_copy_candidate_without_creating_person(tmp_path: Path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"video")
    marker = tmp_path / "calls.txt"
    script = _worker(
        tmp_path / "cache_worker.py",
        f"""import argparse, json
from pathlib import Path
p=argparse.ArgumentParser()
for name in ('input','output','work-dir','model-dir','device'):
    p.add_argument('--'+name, required=True)
a=p.parse_args(); marker=Path({str(marker)!r})
marker.write_text((marker.read_text() if marker.exists() else '')+'call\\n')
payload={{
    'schema_version':'1.0',
    'provider':'paraformer-zh',
    'model':'fake',
    'source_media':str(Path(a.input).resolve()),
    'asr_audio':str(Path(a.input).resolve()),
    'audio_conversion':{{}},
    'text':'缓 存 ASR 识 别\uff01\uff01',
    'tokens':[{{
        'index':0,
        'text':'缓存',
        'start_ms':0,
        'end_ms':100,
        'source':'paraformer-zh',
    }}],
}}
Path(a.output).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
""",
    )
    provider = ParaformerSubprocessProvider(
        AsrWorkerConfig(command_prefix=(sys.executable, str(script)), timeout_seconds=5)
    )
    service = LearningService(LearningStore(tmp_path / "learning"), asr_provider=provider)

    first = service.transcribe((media,), source_date=date(2026, 8, 11))
    second = service.transcribe((media,), source_date=date(2026, 8, 11))

    assert first["succeeded"] == 1
    assert second["reused"] == 1
    assert marker.read_text().splitlines() == ["call"]
    candidate_ids = first["candidate_ids"]
    assert isinstance(candidate_ids, list)
    candidate = service.get(CandidateKind.COPY, str(candidate_ids[0]))
    assert isinstance(candidate, CopyLearningCandidate)
    assert candidate.raw_transcript == "缓 存 ASR 识 别\uff01\uff01"
    assert candidate.edited_transcript == "缓存ASR识别\uff01"
    candidate_root = tmp_path / "learning" / "copy" / "candidates" / str(candidate.candidate_id)
    assert (candidate_root / "raw_transcript.txt").read_text(encoding="utf-8") == (
        "缓 存 ASR 识 别\uff01\uff01"
    )
    assert (candidate_root / "edited_transcript.txt").read_text(encoding="utf-8") == (
        "缓存ASR识别\uff01"
    )
    service.delete(
        CandidateKind.COPY,
        str(candidate.candidate_id),
        expected_revision=int(candidate.revision),
    )
    regenerated = service.transcribe((media,), source_date=date(2026, 8, 11))
    regenerated_ids = regenerated["candidate_ids"]
    assert isinstance(regenerated_ids, list)
    assert regenerated["succeeded"] == 1
    assert regenerated_ids != candidate_ids
    assert marker.read_text().splitlines() == ["call", "call"]
    assert (tmp_path / "learning" / "copy" / "trash" / str(candidate.candidate_id)).is_dir()
    assert not (tmp_path / "learning" / "person").exists()
