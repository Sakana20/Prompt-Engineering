from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import re
import sqlite3
import tempfile
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(tempfile.gettempdir()) / "prompt-engineering-skill-reviewer"
DAILY_SOURCE_ROOT = Path("/Users/sakana/Desktop/Work/2026")
DAILY_SOURCE_SUFFIX = Path("淘宝闪购/素材/Codex")
DATE_DIRECTORY_PATTERN = re.compile(r"^\d{2}\.\d{2}$")
SOURCE_FILE_SUFFIXES = {".csv", ".db", ".sqlite", ".sqlite3"}
SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
DATABASES: dict[str, Path] = {}
SOURCE_FILES: dict[str, Path] = {}


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
        key=lambda item: (str(item["date"]), float(item["modified"]), str(item["name"])),
        reverse=True,
    )


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
        if parsed.path.startswith("/api/"):
            self._send_json({"error": "Unknown API route"}, HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/sqlite/open":
            self._handle_sqlite_open()
            return
        self._send_json({"error": "Unknown API route"}, HTTPStatus.NOT_FOUND)

    def guess_type(self, path: str) -> str:
        if path.endswith(".js"):
            return "text/javascript; charset=utf-8"
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length)

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
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), SkillReviewerHandler)
    print(f"Skill reviewer: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping skill reviewer.")


if __name__ == "__main__":
    main()
