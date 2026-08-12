from __future__ import annotations

import argparse
import importlib
import json
import os
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Protocol, cast


class _Preparation(Protocol):
    asr_path: Path

    def to_dict(self) -> dict[str, Any]: ...


class _Timeline(Protocol):
    audio: Any
    asr: Any
    tokens: list[Any]


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def run_worker(
    *,
    input_path: Path,
    output_path: Path,
    work_dir: Path,
    model_dir: Path,
    device: str,
) -> None:
    source = input_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    work = work_dir.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"输入媒体不存在：{source}")
    if not _inside(output, work):
        raise ValueError("--output 必须位于 --work-dir 内")
    work.mkdir(parents=True, exist_ok=True)
    audio_module = importlib.import_module("funasr_timeline.audio")
    service_module = importlib.import_module("funasr_timeline.asr.paraformer_zh_service")
    prepare = cast(Any, audio_module).prepare_audio_for_asr
    service_type = cast(Any, service_module).ParaformerZhAsrService
    preparation = cast(_Preparation, prepare(source, work))
    if not _inside(preparation.asr_path, work) and preparation.asr_path.resolve() != source:
        raise RuntimeError("音频转换结果必须位于 Prompt Engineering work-dir 内")
    timeline = cast(
        _Timeline,
        service_type(model_dir=model_dir.expanduser().resolve(), device=device).transcribe(
            preparation.asr_path
        ),
    )
    tokens: list[dict[str, object]] = []
    for token in timeline.tokens:
        if is_dataclass(token) and not isinstance(token, type):
            raw = asdict(token)
        else:
            raw = {
                "index": token.index,
                "text": token.text,
                "start_ms": token.start_ms,
                "end_ms": token.end_ms,
                "confidence": getattr(token, "confidence", None),
                "source": getattr(token, "source", "paraformer-zh"),
            }
        raw["source"] = str(raw.get("source") or "paraformer-zh")
        tokens.append(cast(dict[str, object], raw))
    payload = {
        "schema_version": "1.0",
        "provider": "paraformer-zh",
        "model": str(timeline.asr.model or f"paraformer-zh:{model_dir.resolve()}"),
        "source_media": str(source),
        "asr_audio": str(preparation.asr_path.resolve()),
        "audio_conversion": preparation.to_dict(),
        "text": str(timeline.asr.text),
        "tokens": tokens,
    }
    _atomic_json(output, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt Engineering Paraformer bridge worker")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--device", default="mps")
    args = parser.parse_args()
    run_worker(
        input_path=args.input,
        output_path=args.output,
        work_dir=args.work_dir,
        model_dir=args.model_dir,
        device=str(args.device),
    )


if __name__ == "__main__":
    main()
