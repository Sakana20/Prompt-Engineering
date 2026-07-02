from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import PromptPackage


def serialize_package(package: PromptPackage) -> str:
    return json.dumps(package.to_dict(), ensure_ascii=False, indent=2) + "\n"


def write_package(path: str | Path, package: PromptPackage) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = serialize_package(package)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        temporary_path.replace(destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return destination
