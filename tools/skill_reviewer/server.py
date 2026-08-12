from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import re
import sqlite3
import tempfile
import uuid
from datetime import date, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from avatar_prompt_pipeline.learning.asr_provider import SUPPORTED_MEDIA_SUFFIXES
from avatar_prompt_pipeline.learning.models import CandidateKind, LearningStatus
from avatar_prompt_pipeline.learning.service import LearningService
from avatar_prompt_pipeline.learning.store import (
    CandidateNotFoundError,
    RevisionConflictError,
)
from avatar_prompt_pipeline.learning.validation import LearningValidationError

APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(tempfile.gettempdir()) / "prompt-engineering-skill-reviewer"
DAILY_SOURCE_ROOT = Path("/Users/sakana/Desktop/Work/2026")
DAILY_SOURCE_SUFFIX = Path("淘宝闪购/素材/Codex")
DEFAULT_DAILY_MEDIA_ROOT = Path("/Users/sakana/Desktop/Work/2026")
DAILY_MEDIA_ROOT = DEFAULT_DAILY_MEDIA_ROOT
DAILY_MEDIA_SUFFIX = Path("淘宝闪购/素材")
DATE_DIRECTORY_PATTERN = re.compile(r"^\d{2}\.\d{2}$")
SOURCE_FILE_SUFFIXES = {".csv", ".db", ".sqlite", ".sqlite3"}
SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
DATABASES: dict[str, Path] = {}
SOURCE_FILES: dict[str, Path] = {}
DEFAULT_LEARNING_ROOT = Path(__file__).resolve().parents[2] / "learning"
LEARNING_ROOT = DEFAULT_LEARNING_ROOT
MAX_JSON_BODY_BYTES = 1024 * 1024
MAX_MEDIA_SELECTION = 100


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _source_file_type(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        return "csv"
    return "sqlite"


def _is_csv_path(path: Path) -> bool:
    return path.suffix.lower() == ".csv"


def _is_sqlite_path(path: Path) -> bool:
    return path.suffix.lower() in SQLITE_SUFFIXES


def _is_allowed_source_path(path: Path) -> bool:
    try:
        path.resolve().relative_to(DAILY_SOURCE_ROOT.resolve())
    except ValueError:
        return False
    return path.suffix.lower() in SOURCE_FILE_SUFFIXES


def _source_id(path: Path) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, str(path.resolve())).hex


def _name_tokens(path: Path) -> set[str]:
    ignored = {
        "csv",
        "db",
        "fix",
        "flash",
        "jobs",
        "jichuang",
        "sqlite",
        "sqlite3",
        "taobao",
        "tb",
    }
    return {
        token
        for token in re.split(r"[^0-9A-Za-z]+", path.stem.lower())
        if len(token) > 1 and not token.isdigit() and token not in ignored
    }


def _clean_note_label(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    for separator in ("+", "\uff0b"):
        if separator in normalized:
            normalized = normalized.split(separator, maxsplit=1)[0].strip()
            break
    return normalized


def _csv_note_summary(path: Path) -> tuple[str, dict[str, int]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = csv.DictReader(handle)
            counts: dict[str, int] = {}
            for row in rows:
                label = _clean_note_label(row.get("notes", ""))
                if not label:
                    continue
                counts[label] = counts.get(label, 0) + 1
    except (OSError, csv.Error, UnicodeDecodeError):
        return "", {}

    summary = " ".join(f"{label}x{count}" for label, count in counts.items())
    return summary, counts


def _find_related_database(path: Path) -> Path | None:
    if not _is_csv_path(path):
        return None

    candidates = [
        item
        for item in path.parent.iterdir()
        if item.is_file() and _is_sqlite_path(item) and _is_allowed_source_path(item)
    ]
    if not candidates:
        return None

    for candidate in candidates:
        if candidate.stem == path.stem:
            return candidate

    csv_tokens = _name_tokens(path)
    if not csv_tokens:
        return None
    scored = [
        (len(csv_tokens & _name_tokens(candidate)), candidate.stat().st_mtime, candidate)
        for candidate in candidates
    ]
    score, _, candidate = max(scored, key=lambda item: item[:2])
    if score < 2:
        return None
    return candidate


def _source_file_payload(
    path: Path,
    date_label: str,
    related_database: Path | None = None,
) -> dict[str, object]:
    stat = path.stat()
    file_id = _source_id(path)
    SOURCE_FILES[file_id] = path
    label, note_counts = _csv_note_summary(path) if _is_csv_path(path) else ("", {})
    payload: dict[str, object] = {
        "id": file_id,
        "label": label or path.stem,
        "name": path.name,
        "note_counts": note_counts,
        "type": _source_file_type(path),
        "date": date_label,
        "path": str(path),
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }
    if related_database is not None:
        database_id = _source_id(related_database)
        SOURCE_FILES[database_id] = related_database
        payload["database"] = {
            "id": database_id,
            "name": related_database.name,
            "path": str(related_database),
        }
    return payload


def _daily_source_files() -> list[dict[str, object]]:
    if not DAILY_SOURCE_ROOT.is_dir():
        return []

    files: list[dict[str, object]] = []
    for date_directory in DAILY_SOURCE_ROOT.iterdir():
        if not date_directory.is_dir() or not DATE_DIRECTORY_PATTERN.fullmatch(date_directory.name):
            continue
        source_directory = date_directory / DAILY_SOURCE_SUFFIX
        if not source_directory.is_dir():
            continue
        for path in sorted(source_directory.iterdir(), key=lambda item: item.name):
            if path.is_file() and _is_allowed_source_path(path) and _is_csv_path(path):
                files.append(
                    _source_file_payload(
                        path,
                        date_directory.name,
                        related_database=_find_related_database(path),
                    )
                )

    return sorted(
        files,
        key=_source_sort_key,
        reverse=True,
    )


def _source_sort_key(item: dict[str, object]) -> tuple[str, float, str]:
    modified = item["modified"]
    if isinstance(modified, bool) or not isinstance(modified, (int, float)):
        modified_value = 0.0
    else:
        modified_value = float(modified)
    return str(item["date"]), modified_value, str(item["name"])


def _source_path_from_query(query: str) -> Path | None:
    params = parse_qs(query)
    source_id = params.get("id", [""])[0]
    path = SOURCE_FILES.get(source_id)
    if path is None:
        _daily_source_files()
        path = SOURCE_FILES.get(source_id)
    if path is None or not _is_allowed_source_path(path):
        return None
    return path


def _learning_media_date(value: str) -> date:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise LearningValidationError("date 必须是有效的 YYYY-MM-DD") from exc
    configured_year = DAILY_MEDIA_ROOT.name
    if configured_year.isdigit() and parsed.year != int(configured_year):
        raise LearningValidationError(f"date 必须位于每日素材年份 {configured_year}")
    return parsed


def _learning_media_directory(source_date: date) -> Path:
    return DAILY_MEDIA_ROOT / source_date.strftime("%m.%d") / DAILY_MEDIA_SUFFIX


def _is_allowed_learning_media(path: Path, directory: Path) -> bool:
    resolved = path.expanduser().resolve()
    return (
        resolved.parent == directory.expanduser().resolve()
        and resolved.is_file()
        and resolved.suffix.lower() in SUPPORTED_MEDIA_SUFFIXES
    )


def _discover_learning_media(source_date: date) -> tuple[tuple[str, Path], ...]:
    directory = _learning_media_directory(source_date).expanduser().resolve()
    if not directory.is_dir():
        return ()
    discovered: list[tuple[str, Path]] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
        if not _is_allowed_learning_media(path, directory):
            continue
        resolved = path.resolve()
        media_id = uuid.uuid5(uuid.NAMESPACE_URL, str(resolved)).hex
        discovered.append((media_id, resolved))
    return tuple(discovered)


def _learning_media_payload(source_date: date, service: LearningService) -> dict[str, object]:
    directory = _learning_media_directory(source_date).expanduser().resolve()
    candidates_by_source: dict[Path, dict[str, object]] = {}
    for candidate in service.list(CandidateKind.COPY):
        data = candidate.to_dict()
        source_media = data.get("source_media")
        if isinstance(source_media, str):
            candidates_by_source[Path(source_media).expanduser().resolve()] = data

    media: list[dict[str, object]] = []
    for media_id, resolved in _discover_learning_media(source_date):
        stat = resolved.stat()
        item: dict[str, object] = {
            "id": media_id,
            "name": resolved.name,
            "suffix": resolved.suffix.lower(),
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }
        candidate = candidates_by_source.get(resolved)
        if candidate is not None:
            item["candidate"] = {
                "candidate_id": candidate["candidate_id"],
                "status": candidate["status"],
                "revision": candidate["revision"],
            }
        media.append(item)
    return {
        "schema_version": "1.0",
        "date": source_date.isoformat(),
        "root": str(directory),
        "exists": directory.is_dir(),
        "count": len(media),
        "media": media,
    }


def _resolve_learning_media(source_date: date, media_ids: tuple[str, ...]) -> tuple[Path, ...]:
    if not media_ids:
        raise LearningValidationError("media_ids 至少选择一项")
    if len(media_ids) > MAX_MEDIA_SELECTION:
        raise LearningValidationError(f"单次最多选择 {MAX_MEDIA_SELECTION} 个媒体")
    if len(set(media_ids)) != len(media_ids):
        raise LearningValidationError("media_ids 不得重复")
    directory = _learning_media_directory(source_date).expanduser().resolve()
    available = dict(_discover_learning_media(source_date))
    resolved: list[Path] = []
    for media_id in media_ids:
        path = available.get(media_id)
        if path is None or not _is_allowed_learning_media(path, directory):
            raise LearningValidationError("媒体选择已失效，请刷新素材列表后重试")
        resolved.append(path)
    return tuple(resolved)


def _database_tables(path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT name, type
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ).fetchall()
        tables: list[dict[str, object]] = []
        for row in rows:
            table_name = str(row["name"])
            quoted_name = _quote_identifier(table_name)
            count = connection.execute(f"SELECT COUNT(*) FROM {quoted_name}").fetchone()[0]
            columns = [
                str(column["name"])
                for column in connection.execute(f"PRAGMA table_info({quoted_name})")
            ]
            tables.append(
                {
                    "name": table_name,
                    "type": str(row["type"]),
                    "row_count": int(count),
                    "columns": columns,
                }
            )
        return tables


def _database_rows(path: Path, table: str, limit: int, offset: int) -> dict[str, object]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        table_names = {
            str(row["name"])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type IN ('table', 'view')
                  AND name NOT LIKE 'sqlite_%'
                """
            )
        }
        if table not in table_names:
            raise ValueError(f"Unknown table: {table}")
        quoted_table = _quote_identifier(table)
        count = int(connection.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0])
        cursor = connection.execute(
            f"SELECT * FROM {quoted_table} LIMIT ? OFFSET ?",
            (limit, offset),
        )
        columns = [description[0] for description in cursor.description or ()]
        rows = [dict(row) for row in cursor.fetchall()]
        return {"columns": columns, "rows": rows, "row_count": count}


def _database_statuses(path: Path) -> dict[str, str]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        table_names = {
            str(row["name"])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            )
        }
        if "jobs" not in table_names:
            return {}
        columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(jobs)")}
        if "task_id" not in columns or "status" not in columns:
            return {}
        rows = connection.execute("SELECT task_id, status FROM jobs").fetchall()
        return {str(row["task_id"]): str(row["status"]) for row in rows}


class SkillReviewerHandler(SimpleHTTPRequestHandler):
    server_version = "SkillReviewer/1.0"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        requested = parsed.path.lstrip("/") or "index.html"
        return str(APP_DIR / requested)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/sources":
            self._handle_sources()
            return
        if parsed.path == "/api/source/csv":
            self._handle_source_csv(parsed.query)
            return
        if parsed.path == "/api/sqlite/table":
            self._handle_sqlite_table(parsed.query)
            return
        if parsed.path == "/api/learning/candidates":
            self._handle_learning_list(parsed.query)
            return
        if parsed.path == "/api/learning/media":
            self._handle_learning_media(parsed.query)
            return
        learning_route = _learning_candidate_route(parsed.path)
        if learning_route is not None and learning_route[2] == "":
            self._handle_learning_detail(learning_route[0], learning_route[1])
            return
        if parsed.path.startswith("/api/"):
            self._send_json({"error": "Unknown API route"}, HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/sqlite/open":
            self._handle_sqlite_open()
            return
        if parsed.path == "/api/learning/person-candidates":
            self._handle_learning_create_person()
            return
        if parsed.path == "/api/learning/transcribe":
            self._handle_learning_transcribe()
            return
        learning_route = _learning_candidate_route(parsed.path)
        if learning_route is not None and learning_route[2]:
            self._handle_learning_action(*learning_route)
            return
        self._send_json({"error": "Unknown API route"}, HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        learning_route = _learning_candidate_route(parsed.path)
        if learning_route is not None and learning_route[2] == "":
            self._handle_learning_update(learning_route[0], learning_route[1])
            return
        self._send_json({"error": "Unknown API route"}, HTTPStatus.NOT_FOUND)

    def guess_type(self, path: str | os.PathLike[str]) -> str:
        rendered = os.fspath(path)
        if rendered.endswith(".js"):
            return "text/javascript; charset=utf-8"
        if rendered.endswith(".css"):
            return "text/css; charset=utf-8"
        return mimetypes.guess_type(rendered)[0] or "application/octet-stream"

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise LearningValidationError("Content-Length 无效") from exc
        if length < 0 or length > MAX_JSON_BODY_BYTES:
            raise LearningValidationError("JSON body 超过大小限制")
        return self.rfile.read(length)

    def _read_json_object(self) -> dict[str, object]:
        body = self._read_body()
        if not body:
            raise LearningValidationError("请求 body 不能为空")
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LearningValidationError("请求 body 必须是 UTF-8 JSON 对象") from exc
        if not isinstance(value, dict):
            raise LearningValidationError("请求 body 顶层必须是 JSON 对象")
        return {str(key): item for key, item in value.items()}

    def _learning_service(self) -> LearningService:
        return LearningService.from_root(LEARNING_ROOT)

    def _handle_learning_error(self, error: Exception) -> None:
        if isinstance(error, RevisionConflictError):
            status = HTTPStatus.CONFLICT
            message = "revision 冲突，请重新加载候选后再保存"
        elif isinstance(error, CandidateNotFoundError):
            status = HTTPStatus.NOT_FOUND
            message = "候选不存在"
        elif isinstance(error, LearningValidationError):
            status = HTTPStatus.UNPROCESSABLE_ENTITY
            message = str(error)
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            message = "学习审核操作失败"
        self._send_json({"error": message}, status)

    def _handle_learning_list(self, query: str) -> None:
        try:
            params = parse_qs(query)
            kind = CandidateKind(params.get("kind", ["copy"])[0])
            status_value = params.get("status", [""])[0]
            status = LearningStatus(status_value) if status_value else None
            candidates = self._learning_service().list(kind, status=status)
            self._send_json(
                {
                    "schema_version": "1.0",
                    "kind": kind.value,
                    "count": len(candidates),
                    "candidates": [candidate.to_dict() for candidate in candidates],
                }
            )
        except (ValueError, LearningValidationError) as error:
            self._handle_learning_error(_as_learning_error(error, "kind/status 参数无效"))

    def _handle_learning_detail(self, kind_value: str, candidate_id: str) -> None:
        try:
            candidate = self._learning_service().get(CandidateKind(kind_value), candidate_id)
            self._send_json(candidate.to_dict())
        except (ValueError, LearningValidationError, CandidateNotFoundError) as error:
            self._handle_learning_error(_as_learning_error(error, "kind 参数无效"))

    def _handle_learning_media(self, query: str) -> None:
        try:
            params = parse_qs(query)
            date_value = params.get("date", [datetime.now().astimezone().date().isoformat()])[0]
            source_date = _learning_media_date(date_value)
            self._send_json(_learning_media_payload(source_date, self._learning_service()))
        except (OSError, LearningValidationError) as error:
            self._handle_learning_error(
                error
                if isinstance(error, LearningValidationError)
                else LearningValidationError("读取每日素材目录失败")
            )

    def _handle_learning_transcribe(self) -> None:
        try:
            data = self._read_json_object()
            _strict_keys(data, allowed={"date", "media_ids"}, required={"date", "media_ids"})
            source_date = _learning_media_date(_body_string(data, "date"))
            media_ids = _body_string_tuple(data, "media_ids")
            inputs = _resolve_learning_media(source_date, media_ids)
            result = self._learning_service().transcribe(inputs, source_date=source_date)
            self._send_json(result)
        except (OSError, LearningValidationError) as error:
            self._handle_learning_error(
                error
                if isinstance(error, LearningValidationError)
                else LearningValidationError("每日素材转写准备失败")
            )

    def _handle_learning_create_person(self) -> None:
        try:
            data = self._read_json_object()
            _strict_keys(data, allowed={"text", "source_label"}, required={"text"})
            text = _body_string(data, "text")
            source_label = _body_string(data, "source_label", default="用户人工样本")
            candidate = self._learning_service().add_person_prompt(text, source_label=source_label)
            self._send_json(candidate.to_dict(), HTTPStatus.CREATED)
        except (LearningValidationError, RevisionConflictError) as error:
            self._handle_learning_error(error)

    def _handle_learning_update(self, kind_value: str, candidate_id: str) -> None:
        try:
            data = self._read_json_object()
            allowed = {
                "expected_revision",
                "edited_text",
                "category_family",
                "consumption_need",
                "season",
                "source_usage",
                "identity_traits",
                "hair_traits",
                "outfit_traits",
                "scene_traits",
                "forbidden_traits",
            }
            _strict_keys(
                data,
                allowed=allowed,
                required={"expected_revision", "edited_text"},
            )
            kind = CandidateKind(kind_value)
            fields: dict[str, tuple[str, ...] | str] = {}
            string_fields = {"category_family", "consumption_need", "season"}
            tuple_fields = {
                "source_usage",
                "identity_traits",
                "hair_traits",
                "outfit_traits",
                "scene_traits",
                "forbidden_traits",
            }
            for field in string_fields & data.keys():
                fields[field] = _body_string(data, field)
            for field in tuple_fields & data.keys():
                fields[field] = _body_string_tuple(data, field)
            candidate = self._learning_service().update(
                kind,
                candidate_id,
                expected_revision=_body_revision(data),
                edited_text=_body_string(data, "edited_text"),
                structured_fields=fields,
            )
            self._send_json(candidate.to_dict())
        except (
            ValueError,
            LearningValidationError,
            CandidateNotFoundError,
            RevisionConflictError,
        ) as error:
            self._handle_learning_error(_as_learning_error(error, "kind 参数无效"))

    def _handle_learning_action(
        self,
        kind_value: str,
        candidate_id: str,
        action: str,
    ) -> None:
        try:
            data = self._read_json_object()
            required = (
                {"expected_revision", "reason"} if action == "reject" else {"expected_revision"}
            )
            allowed = required
            _strict_keys(data, allowed=allowed, required=required)
            kind = CandidateKind(kind_value)
            revision = _body_revision(data)
            service = self._learning_service()
            if action == "submit-review":
                candidate = service.submit_review(kind, candidate_id, expected_revision=revision)
            elif action == "approve":
                candidate = service.approve(kind, candidate_id, expected_revision=revision)
            elif action == "reject":
                candidate = service.reject(
                    kind,
                    candidate_id,
                    expected_revision=revision,
                    reason=_body_string(data, "reason"),
                )
            else:
                self._send_json({"error": "Unknown learning action"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(candidate.to_dict())
        except (
            ValueError,
            LearningValidationError,
            CandidateNotFoundError,
            RevisionConflictError,
        ) as error:
            self._handle_learning_error(_as_learning_error(error, "kind 参数无效"))

    def _handle_sqlite_open(self) -> None:
        body = self._read_body()
        if not body:
            self._send_json({"error": "Empty upload"}, HTTPStatus.BAD_REQUEST)
            return

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        database_id = uuid.uuid4().hex
        upload_path = UPLOAD_DIR / f"{database_id}.sqlite"
        upload_path.write_bytes(body)

        try:
            tables = _database_tables(upload_path)
        except sqlite3.DatabaseError as error:
            upload_path.unlink(missing_ok=True)
            self._send_json({"error": f"SQLite open failed: {error}"}, HTTPStatus.BAD_REQUEST)
            return

        DATABASES[database_id] = upload_path
        self._send_json({"database_id": database_id, "tables": tables})

    def _handle_sources(self) -> None:
        files = _daily_source_files()
        self._send_json(
            {
                "root": str(DAILY_SOURCE_ROOT / "<MM.DD>" / DAILY_SOURCE_SUFFIX),
                "files": files,
            }
        )

    def _handle_source_csv(self, query: str) -> None:
        source_path = _source_path_from_query(query)
        if source_path is None or source_path.suffix.lower() != ".csv":
            self._send_json({"error": "Unknown CSV source"}, HTTPStatus.NOT_FOUND)
            return
        try:
            text = source_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = source_path.read_text(encoding="utf-8")
        except OSError as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        related_database = _find_related_database(source_path)
        statuses: dict[str, str] = {}
        database_name = ""
        if related_database is not None:
            database_name = related_database.name
            try:
                statuses = _database_statuses(related_database)
            except sqlite3.DatabaseError:
                statuses = {}
        self._send_json(
            {
                "label": _csv_note_summary(source_path)[0] or source_path.stem,
                "name": source_path.name,
                "path": str(source_path),
                "text": text,
                "status_by_task_id": statuses,
                "database": database_name,
            }
        )

    def _handle_sqlite_open_source(self, query: str) -> None:
        source_path = _source_path_from_query(query)
        if source_path is None or source_path.suffix.lower() == ".csv":
            self._send_json({"error": "Unknown SQLite source"}, HTTPStatus.NOT_FOUND)
            return
        try:
            tables = _database_tables(source_path)
        except sqlite3.DatabaseError as error:
            self._send_json({"error": f"SQLite open failed: {error}"}, HTTPStatus.BAD_REQUEST)
            return
        database_id = _source_id(source_path)
        DATABASES[database_id] = source_path
        self._send_json(
            {
                "database_id": database_id,
                "name": source_path.name,
                "path": str(source_path),
                "tables": tables,
            }
        )

    def _handle_sqlite_table(self, query: str) -> None:
        params = parse_qs(query)
        database_id = params.get("id", [""])[0]
        table = params.get("table", [""])[0]
        try:
            limit = max(1, min(int(params.get("limit", ["200"])[0]), 1000))
            offset = max(0, int(params.get("offset", ["0"])[0]))
        except ValueError:
            self._send_json({"error": "Invalid limit or offset"}, HTTPStatus.BAD_REQUEST)
            return

        database_path = DATABASES.get(database_id)
        if database_path is None:
            self._send_json({"error": "Unknown database upload"}, HTTPStatus.NOT_FOUND)
            return

        try:
            payload = _database_rows(database_path, table, limit, offset)
        except (sqlite3.DatabaseError, ValueError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json(payload)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[skill-reviewer] {self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local Skill CSV/SQLite reviewer.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--learning-root", type=Path, default=DEFAULT_LEARNING_ROOT)
    parser.add_argument("--daily-media-root", type=Path, default=DEFAULT_DAILY_MEDIA_ROOT)
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("审核台只允许绑定 loopback host")
    global DAILY_MEDIA_ROOT, LEARNING_ROOT
    LEARNING_ROOT = args.learning_root.expanduser().resolve()
    DAILY_MEDIA_ROOT = args.daily_media_root.expanduser().resolve()

    server = ThreadingHTTPServer((args.host, args.port), SkillReviewerHandler)
    print(f"Skill reviewer: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping skill reviewer.")


def _learning_candidate_route(path: str) -> tuple[str, str, str] | None:
    match = re.fullmatch(
        r"/api/learning/candidates/(copy|person)/([A-Za-z0-9][A-Za-z0-9_-]{7,95})(?:/(submit-review|approve|reject))?",
        path,
    )
    if match is None:
        return None
    return match.group(1), match.group(2), match.group(3) or ""


def _strict_keys(
    data: dict[str, object],
    *,
    allowed: set[str],
    required: set[str],
) -> None:
    unknown = set(data) - allowed
    missing = required - set(data)
    if unknown:
        raise LearningValidationError("请求包含未知字段：" + "、".join(sorted(unknown)))
    if missing:
        raise LearningValidationError("请求缺少字段：" + "、".join(sorted(missing)))


def _body_string(data: dict[str, object], field: str, *, default: str = "") -> str:
    value = data.get(field, default)
    if not isinstance(value, str):
        raise LearningValidationError(f"{field} 必须是字符串")
    return value


def _body_string_tuple(data: dict[str, object], field: str) -> tuple[str, ...]:
    value = data.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LearningValidationError(f"{field} 必须是字符串数组")
    return tuple(value)


def _body_revision(data: dict[str, object]) -> int:
    value = data.get("expected_revision")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise LearningValidationError("expected_revision 必须是正整数")
    return value


def _as_learning_error(error: Exception, fallback: str) -> Exception:
    if isinstance(
        error,
        (LearningValidationError, CandidateNotFoundError, RevisionConflictError),
    ):
        return error
    return LearningValidationError(fallback)


if __name__ == "__main__":
    main()
