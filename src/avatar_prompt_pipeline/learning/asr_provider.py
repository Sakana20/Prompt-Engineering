from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .models import AsrToken
from .store import atomic_write_json
from .validation import LearningValidationError

DEFAULT_FUNASR_PYTHON = Path("/Users/sakana/Desktop/Work/Codex/FunASR/.venv/bin/python")
DEFAULT_MODEL_DIR = Path("/Users/sakana/PyEnv/paraformer")
SUPPORTED_MEDIA_SUFFIXES = frozenset(
    {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".mp4", ".mov", ".mkv", ".webm"}
)


class AsrProviderError(RuntimeError):
    """Raised when the isolated ASR worker fails or violates its contract."""


@dataclass(frozen=True, slots=True)
class AsrWorkerConfig:
    python_executable: Path = DEFAULT_FUNASR_PYTHON
    model_dir: Path = DEFAULT_MODEL_DIR
    device: str = "mps"
    timeout_seconds: float = 900.0
    command_prefix: tuple[str, ...] | None = None

    def cache_fingerprint(self) -> str:
        parts = [
            str(self.python_executable.expanduser().resolve()),
            str(self.model_dir.expanduser().resolve()),
            self.device,
            "worker-schema-1.0",
        ]
        if self.command_prefix is not None:
            parts.extend(self.command_prefix)
        return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AsrWorkerResult:
    schema_version: str
    provider: str
    model: str
    source_media: str
    asr_audio: str
    audio_conversion: tuple[tuple[str, str], ...]
    text: str
    tokens: tuple[AsrToken, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "model": self.model,
            "source_media": self.source_media,
            "asr_audio": self.asr_audio,
            "audio_conversion": dict(self.audio_conversion),
            "text": self.text,
            "tokens": [
                {
                    "index": token.index,
                    "text": token.text,
                    "start_ms": token.start_ms,
                    "end_ms": token.end_ms,
                    "source": token.source,
                    "confidence": token.confidence,
                }
                for token in self.tokens
            ],
        }


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def cache_key(source_fingerprint: str, config: AsrWorkerConfig) -> str:
    return hashlib.sha256(
        f"{source_fingerprint}\0{config.cache_fingerprint()}".encode()
    ).hexdigest()


class ParaformerSubprocessProvider:
    def __init__(self, config: AsrWorkerConfig | None = None) -> None:
        self.config = config or AsrWorkerConfig()

    def transcribe(self, media_path: Path, work_dir: Path) -> AsrWorkerResult:
        source = media_path.expanduser().resolve()
        if not source.is_file():
            raise AsrProviderError(f"媒体文件不存在：{media_path}")
        if source.suffix.lower() not in SUPPORTED_MEDIA_SUFFIXES:
            raise AsrProviderError(f"不支持的媒体格式：{source.suffix}")
        resolved_work = work_dir.expanduser().resolve()
        resolved_work.mkdir(parents=True, exist_ok=True)
        output = resolved_work / "worker-result.json"
        if output.exists():
            output.unlink()
        worker = Path(__file__).resolve().with_name("funasr_worker.py")
        prefix = self.config.command_prefix or (
            str(self.config.python_executable.expanduser().resolve()),
            "-B",
            str(worker),
        )
        command = [
            *prefix,
            "--input",
            str(source),
            "--output",
            str(output),
            "--work-dir",
            str(resolved_work),
            "--model-dir",
            str(self.config.model_dir.expanduser().resolve()),
            "--device",
            self.config.device,
        ]
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            completed = subprocess.run(
                command,
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                env=environment,
                cwd=resolved_work,
            )
        except subprocess.TimeoutExpired as exc:
            raise AsrProviderError(
                f"Paraformer worker 超时({self.config.timeout_seconds:g} 秒)"
            ) from exc
        except OSError as exc:
            raise AsrProviderError("无法启动 Paraformer worker") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "无错误输出").strip()[-2000:]
            raise AsrProviderError(f"Paraformer worker 失败：{detail}")
        if not output.is_file():
            raise AsrProviderError("Paraformer worker 未生成结果 JSON")
        result = load_worker_result(output, expected_source=source)
        atomic_write_json(resolved_work / "worker-result.archived.json", result.to_dict())
        return result


def _required_string(data: Mapping[str, object], field: str, *, allow_empty: bool = False) -> str:
    value = data.get(field)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise AsrProviderError(f"worker JSON 字段 {field} 必须是非空字符串")
    return value.strip()


def _required_int(data: Mapping[str, object], field: str) -> int:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise AsrProviderError(f"worker token 字段 {field} 必须是整数")
    return value


def _parse_conversion(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict):
        raise AsrProviderError("worker JSON audio_conversion 必须是对象")
    pairs: list[tuple[str, str]] = []
    for key, item in value.items():
        if not isinstance(key, str):
            raise AsrProviderError("audio_conversion 键必须是字符串")
        if item is None or isinstance(item, (str, int, float, bool)):
            pairs.append((key, "" if item is None else str(item)))
        elif isinstance(item, list) and all(isinstance(part, str) for part in item):
            pairs.append((key, json.dumps(item, ensure_ascii=False)))
        else:
            raise AsrProviderError(f"audio_conversion.{key} 类型不受支持")
    return tuple(sorted(pairs))


def load_worker_result(path: Path, *, expected_source: Path | None = None) -> AsrWorkerResult:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AsrProviderError("Paraformer worker 返回了非法 JSON") from exc
    if not isinstance(raw, dict):
        raise AsrProviderError("worker JSON 顶层必须是对象")
    data = cast(dict[str, object], raw)
    if data.get("schema_version") != "1.0":
        raise AsrProviderError("worker JSON schema_version 必须是 1.0")
    if data.get("provider") != "paraformer-zh":
        raise AsrProviderError("worker JSON provider 必须是 paraformer-zh")
    text = _required_string(data, "text")
    source_media = _required_string(data, "source_media")
    if expected_source is not None and Path(source_media).resolve() != expected_source.resolve():
        raise AsrProviderError("worker JSON source_media 与输入不一致")
    raw_tokens = data.get("tokens")
    if not isinstance(raw_tokens, list) or not raw_tokens:
        raise AsrProviderError("worker JSON tokens 必须是非空数组")
    tokens: list[AsrToken] = []
    previous_end = 0
    for position, item in enumerate(raw_tokens):
        if not isinstance(item, dict):
            raise AsrProviderError("worker token 必须是对象")
        token_data = cast(dict[str, object], item)
        index = _required_int(token_data, "index")
        start_ms = _required_int(token_data, "start_ms")
        end_ms = _required_int(token_data, "end_ms")
        if index != position or start_ms < 0 or end_ms < start_ms or start_ms < previous_end:
            raise AsrProviderError("worker token 索引或时间轴无效")
        confidence = token_data.get("confidence")
        if confidence is not None and (
            isinstance(confidence, bool) or not isinstance(confidence, (int, float))
        ):
            raise AsrProviderError("worker token confidence 必须是数字或 null")
        tokens.append(
            AsrToken(
                index=index,
                text=_required_string(token_data, "text"),
                start_ms=start_ms,
                end_ms=end_ms,
                source=_required_string(token_data, "source"),
                confidence=float(confidence) if confidence is not None else None,
            )
        )
        previous_end = end_ms
    return AsrWorkerResult(
        schema_version="1.0",
        provider="paraformer-zh",
        model=_required_string(data, "model"),
        source_media=source_media,
        asr_audio=_required_string(data, "asr_audio"),
        audio_conversion=_parse_conversion(data.get("audio_conversion")),
        text=text,
        tokens=tuple(tokens),
    )


def discover_media(inputs: Sequence[Path]) -> tuple[Path, ...]:
    discovered: list[Path] = []
    seen: set[Path] = set()
    for supplied in inputs:
        path = supplied.expanduser().resolve()
        if path.is_dir():
            children = sorted(
                item.resolve()
                for item in path.iterdir()
                if item.is_file() and item.suffix.lower() in SUPPORTED_MEDIA_SUFFIXES
            )
        elif path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA_SUFFIXES:
            children = [path]
        elif path.exists():
            raise LearningValidationError(f"不支持的输入类型或媒体格式：{supplied}")
        else:
            raise LearningValidationError(f"输入不存在：{supplied}")
        for item in children:
            if item not in seen:
                discovered.append(item)
                seen.add(item)
    if not discovered:
        raise LearningValidationError("没有发现受支持的本地媒体文件")
    return tuple(discovered)


__all__ = [
    "SUPPORTED_MEDIA_SUFFIXES",
    "AsrProviderError",
    "AsrWorkerConfig",
    "AsrWorkerResult",
    "ParaformerSubprocessProvider",
    "cache_key",
    "discover_media",
    "file_fingerprint",
    "load_worker_result",
]
