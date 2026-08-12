import http.client
import importlib.util
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest


def _load_reviewer() -> ModuleType:
    path = Path(__file__).parents[2] / "tools/skill_reviewer/server.py"
    spec = importlib.util.spec_from_file_location("skill_reviewer_test_server", path)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load skill reviewer server")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


reviewer = _load_reviewer()


def test_learning_kind_change_refreshes_dataset_heading() -> None:
    app_js = (Path(__file__).parents[2] / "tools/skill_reviewer/app.js").read_text(encoding="utf-8")
    handler_start = app_js.index("document.querySelectorAll('input[name=\"learning-kind\"]')")
    handler_end = app_js.index("elements.learningStatusFilter.addEventListener", handler_start)

    assert "renderLearningHeader();" in app_js[handler_start:handler_end]


def test_learning_workbench_shows_daily_media_default_without_transcribe_action() -> None:
    index = (Path(__file__).parents[2] / "tools/skill_reviewer/index.html").read_text(
        encoding="utf-8"
    )

    assert "等待扫描当天素材目录" in index
    assert 'id="learning-media-list"' in index
    assert 'id="learning-media-transcribe"' in index
    assert 'id="learning-copy-browser"' in index
    assert index.index('id="learning-copy-browser"') < index.index('id="learning-list"')
    assert index.index('id="learning-media-list"') > index.index('id="learning-workspace"')
    assert "learning-transcribe" not in index
    assert 'id="learning-media-back"' in index
    assert 'id="learning-media-directory"' in index
    assert "可进入文件夹并选择其中媒体" in index
    assert "app.js?v=20260812-11" in index
    assert "styles.css?v=20260812-11" in index

    app_js = (Path(__file__).parents[2] / "tools/skill_reviewer/app.js").read_text(encoding="utf-8")
    styles = (Path(__file__).parents[2] / "tools/skill_reviewer/styles.css").read_text(
        encoding="utf-8"
    )
    assert '"/api/learning/media"' in app_js
    assert '"/api/learning/transcribe"' in app_js
    assert '"/api/learning/media-content"' not in app_js
    assert "/api/learning/media-content?date=" in app_js
    assert "learning-media-player" in app_js
    assert "失败素材已保留勾选" in app_js
    assert "learning-failure-list" in app_js
    assert "data-learning-directory-id" in app_js
    assert 'url.searchParams.set("directory_id", directoryId)' in app_js
    assert "learningState.parentDirectoryId" in app_js
    assert ".learning-directory-item" in styles
    assert "不会改字、猜测标点或改变原始时间轴" in app_js
    assert "删除候选" in app_js
    assert "data-learning-delete-id" in app_js
    assert "learningStatusHelp" in app_js
    assert "positionLearningStatusTooltip" in app_js
    assert "pending / editing：" in app_js
    assert "ready_for_review：" in app_js
    assert "approved：" in app_js
    assert "published：" in app_js
    assert "learning-actions-primary" in app_js
    assert 'data-learning-action="submit-learning"' in app_js
    assert 'data-learning-action="approve"' not in app_js
    assert 'data-learning-action="reject"' not in app_js
    assert "提交学习" in app_js
    assert "copy-learning-structured" in app_js
    assert ".row-card-shell.active" in styles
    assert ".status-help-tooltip" in styles
    assert "position: fixed" in styles
    assert ".learning-actions-primary" in styles
    assert ".copy-learning-structured" in styles
    assert "repeat(auto-fit, minmax(220px, 1fr))" in styles
    assert ".learning-field > .field" in styles
    assert "font-size: 1rem" in styles
    assert 'method = "DELETE"' in app_js
    assert "learningSelectField" in app_js
    assert "learningMultiChoiceField" in app_js
    assert "来源块用途\uff08可多选\uff09" in app_js
    assert "data-learning-description-for" in app_js
    assert "当前审核台服务版本过旧" in app_js
    assert "payload.directory_navigation !== true" in app_js
    assert "当前审核台后端仍是旧进程" in app_js
    assert 'cache: "no-store"' in app_js


def _request(
    port: int,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    data = json.loads(response.read().decode("utf-8"))
    connection.close()
    return response.status, data


@pytest.mark.integration
def test_learning_media_api_browses_directories_and_transcribes_selected_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    media_root = tmp_path / "2026"
    media_directory = media_root / "08.12" / "淘宝闪购" / "素材"
    media_directory.mkdir(parents=True)
    first = media_directory / "第一条.mp4"
    second = media_directory / "第二条.wav"
    first.write_bytes(b"video-one")
    second.write_bytes(b"audio-two")
    (media_directory / "忽略.txt").write_text("not media", encoding="utf-8")
    nested = media_directory / "子目录"
    nested.mkdir()
    (nested / "不递归.mp4").write_bytes(b"nested")

    transcribe_calls: list[tuple[tuple[Path, ...], str]] = []

    class FakeLearningService:
        @classmethod
        def from_root(cls, root: Path) -> "FakeLearningService":
            del root
            return cls()

        def list(self, kind: object, *, status: object = None) -> tuple[object, ...]:
            del kind, status
            return ()

        def transcribe(self, inputs: tuple[Path, ...], *, source_date: object) -> dict[str, object]:
            rendered_date = str(source_date)
            transcribe_calls.append((inputs, rendered_date))
            return {
                "schema_version": "1.0",
                "kind": "copy",
                "date": rendered_date,
                "succeeded": len(inputs),
                "reused": 0,
                "failed": 0,
                "candidate_ids": [],
                "succeeded_candidate_ids": [],
                "reused_candidate_ids": [],
                "failures": [],
            }

    previous_media_root = cast(Path, reviewer.__dict__["DAILY_MEDIA_ROOT"])
    monkeypatch.setitem(reviewer.__dict__, "DAILY_MEDIA_ROOT", media_root)
    monkeypatch.setitem(reviewer.__dict__, "LearningService", FakeLearningService)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), reviewer.SkillReviewerHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(httpd.server_address[1])
        status, listing = _request(port, "GET", "/api/learning/media?date=2026-08-12")
        assert status == 200
        assert listing["exists"] is True
        assert listing["directory_navigation"] is True
        assert listing["count"] == 2
        assert listing["directory_count"] == 1
        assert listing["at_root"] is True
        assert listing["parent_id"] == ""
        media = cast(list[dict[str, object]], listing["media"])
        assert {str(item["name"]) for item in media} == {"第一条.mp4", "第二条.wav"}
        assert all("path" not in item for item in media)
        directories = cast(list[dict[str, object]], listing["directories"])
        assert [str(item["name"]) for item in directories] == ["子目录"]
        assert all("path" not in item for item in directories)

        status, invalid_directory = _request(
            port,
            "GET",
            "/api/learning/media?date=2026-08-12&directory_id=not-a-server-directory-id",
        )
        assert status == 422
        assert "文件夹选择已失效" in str(invalid_directory["error"])

        directory_id = str(directories[0]["id"])
        status, nested_listing = _request(
            port,
            "GET",
            f"/api/learning/media?date=2026-08-12&directory_id={directory_id}",
        )
        assert status == 200
        assert nested_listing["at_root"] is False
        assert nested_listing["parent_id"] == listing["directory_id"]
        assert nested_listing["relative_directory"] == "子目录"
        nested_media = cast(list[dict[str, object]], nested_listing["media"])
        assert [str(item["name"]) for item in nested_media] == ["不递归.mp4"]
        nested_id = str(nested_media[0]["id"])

        status, stale_nested = _request(
            port,
            "POST",
            "/api/learning/transcribe",
            {"date": "2026-08-12", "media_ids": [nested_id]},
        )
        assert status == 422
        assert "媒体选择已失效" in str(stale_nested["error"])

        status, nested_result = _request(
            port,
            "POST",
            "/api/learning/transcribe",
            {
                "date": "2026-08-12",
                "directory_id": directory_id,
                "media_ids": [nested_id],
            },
        )
        assert status == 200
        assert nested_result["succeeded"] == 1
        assert transcribe_calls == [((nested / "不递归.mp4",), "2026-08-12")]
        transcribe_calls.clear()

        selected_id = str(media[0]["id"])
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "GET",
            f"/api/learning/media-content?date=2026-08-12&id={selected_id}",
            headers={"Range": "bytes=1-4"},
        )
        preview = connection.getresponse()
        preview_body = preview.read()
        assert preview.status == 206
        assert preview.getheader("Accept-Ranges") == "bytes"
        assert preview.getheader("Content-Range") == "bytes 1-4/9"
        assert preview.getheader("Content-Type") == "video/mp4"
        assert preview_body == b"ideo"
        connection.close()

        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "GET",
            f"/api/learning/media-content?date=2026-08-12&directory_id={directory_id}&id={nested_id}",
            headers={"Range": "bytes=0-5"},
        )
        nested_preview = connection.getresponse()
        assert nested_preview.status == 206
        assert nested_preview.read() == b"nested"
        connection.close()

        status, invalid_preview = _request(
            port,
            "GET",
            "/api/learning/media-content?date=2026-08-12&id=not-a-server-media-id",
        )
        assert status == 422
        assert "媒体选择已失效" in str(invalid_preview["error"])

        status, result = _request(
            port,
            "POST",
            "/api/learning/transcribe",
            {"date": "2026-08-12", "media_ids": [selected_id]},
        )
        assert status == 200
        assert result["succeeded"] == 1
        assert transcribe_calls == [((media_directory / str(media[0]["name"]),), "2026-08-12")]

        status, invalid = _request(
            port,
            "POST",
            "/api/learning/transcribe",
            {
                "date": "2026-08-12",
                "media_ids": [selected_id],
                "path": str(first),
            },
        )
        assert status == 422
        assert "未知字段" in str(invalid["error"])

        class FakeFailureService(FakeLearningService):
            def transcribe(
                self, inputs: tuple[Path, ...], *, source_date: object
            ) -> dict[str, object]:
                return {
                    "schema_version": "1.0",
                    "kind": "copy",
                    "date": str(source_date),
                    "succeeded": 0,
                    "reused": 0,
                    "failed": 1,
                    "candidate_ids": [],
                    "succeeded_candidate_ids": [],
                    "reused_candidate_ids": [],
                    "failures": [
                        {
                            "source_media": str(inputs[0]),
                            "error": "FunASR 环境预检失败：测试错误",
                        }
                    ],
                }

        monkeypatch.setitem(reviewer.__dict__, "LearningService", FakeFailureService)
        status, failed = _request(
            port,
            "POST",
            "/api/learning/transcribe",
            {"date": "2026-08-12", "media_ids": [selected_id]},
        )
        assert status == 200
        failures = cast(list[dict[str, object]], failed["failures"])
        assert failures == [
            {
                "name": str(media[0]["name"]),
                "error": "FunASR 环境预检失败：测试错误",
            }
        ]
        assert "source_media" not in failures[0]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        reviewer.__dict__["DAILY_MEDIA_ROOT"] = previous_media_root


@pytest.mark.integration
def test_reviewer_static_assets_disable_browser_cache(tmp_path: Path) -> None:
    previous_root = cast(Path, reviewer.__dict__["LEARNING_ROOT"])
    reviewer.__dict__["LEARNING_ROOT"] = tmp_path / "learning"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), reviewer.SkillReviewerHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(httpd.server_address[1])
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", "/app.js?v=20260812-11")
        response = connection.getresponse()
        response.read()
        assert response.status == 200
        assert response.getheader("Cache-Control") == "no-store, max-age=0"
        assert response.getheader("Pragma") == "no-cache"
        connection.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        reviewer.__dict__["LEARNING_ROOT"] = previous_root


@pytest.mark.integration
def test_learning_api_create_save_conflict_and_review(tmp_path: Path) -> None:
    previous_root = cast(Path, reviewer.__dict__["LEARNING_ROOT"])
    reviewer.__dict__["LEARNING_ROOT"] = tmp_path / "learning"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), reviewer.SkillReviewerHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(httpd.server_address[1])
        status, created = _request(
            port,
            "POST",
            "/api/learning/person-candidates",
            {"text": "年轻鹅蛋脸女生，黑色短发，简约通勤服装", "source_label": "测试"},
        )
        assert status == 201
        candidate_id = str(created["candidate_id"])
        status, copy_listing = _request(port, "GET", "/api/learning/candidates?kind=copy")
        assert status == 200
        field_options = cast(dict[str, list[dict[str, str]]], copy_listing["field_options"])
        assert {item["value"] for item in field_options["category_family"]} == {
            "",
            "beverage",
            "other",
        }
        assert {item["value"] for item in field_options["source_usage"]} == {
            "source_fill",
            "human_rewrite",
        }
        status, updated = _request(
            port,
            "PUT",
            f"/api/learning/candidates/person/{candidate_id}",
            {
                "expected_revision": 1,
                "edited_text": "年轻圆脸女生，栗棕短发，简约通勤服装",
                "identity_traits": ["圆脸", "清爽"],
                "hair_traits": ["栗棕短发"],
                "outfit_traits": ["简约通勤"],
                "scene_traits": [],
                "forbidden_traits": [],
            },
        )
        assert status == 200
        assert updated["revision"] == 2
        status, conflict = _request(
            port,
            "PUT",
            f"/api/learning/candidates/person/{candidate_id}",
            {"expected_revision": 1, "edited_text": "过期覆盖"},
        )
        assert status == 409
        assert "重新加载" in str(conflict["error"])
        status, ready = _request(
            port,
            "POST",
            f"/api/learning/candidates/person/{candidate_id}/submit-review",
            {"expected_revision": 2},
        )
        assert status == 200
        assert ready["status"] == "ready_for_review"
        status, approved = _request(
            port,
            "POST",
            f"/api/learning/candidates/person/{candidate_id}/approve",
            {"expected_revision": ready["revision"]},
        )
        assert status == 200
        assert approved["status"] == "approved"

        status, direct_created = _request(
            port,
            "POST",
            "/api/learning/person-candidates",
            {"text": "年轻女生，栗棕短发，浅色针织衫", "source_label": "直接提交测试"},
        )
        assert status == 201
        direct_id = str(direct_created["candidate_id"])
        status, direct_approved = _request(
            port,
            "POST",
            f"/api/learning/candidates/person/{direct_id}/submit-learning",
            {"expected_revision": direct_created["revision"]},
        )
        assert status == 200
        assert direct_approved["status"] == "approved"
        assert direct_approved["revision"] == 2

        status, reject_created = _request(
            port,
            "POST",
            "/api/learning/person-candidates",
            {"text": "年轻男性，黑色短发，深色夹克", "source_label": "驳回测试"},
        )
        assert status == 201
        reject_id = str(reject_created["candidate_id"])
        status, reject_ready = _request(
            port,
            "POST",
            f"/api/learning/candidates/person/{reject_id}/submit-review",
            {"expected_revision": reject_created["revision"]},
        )
        assert status == 200
        status, rejected = _request(
            port,
            "POST",
            f"/api/learning/candidates/person/{reject_id}/reject",
            {
                "expected_revision": reject_ready["revision"],
                "reason": "人物信息不够完整",
            },
        )
        assert status == 200
        assert rejected["status"] == "rejected"
        assert rejected["rejection_reason"] == "人物信息不够完整"

        status, delete_created = _request(
            port,
            "POST",
            "/api/learning/person-candidates",
            {"text": "年轻女生，黑色长发，蓝色针织衫", "source_label": "删除测试"},
        )
        assert status == 201
        delete_id = str(delete_created["candidate_id"])
        status, deleted = _request(
            port,
            "DELETE",
            f"/api/learning/candidates/person/{delete_id}",
            {"expected_revision": delete_created["revision"]},
        )
        assert status == 200
        assert deleted["deleted"] is True
        assert deleted["recoverable"] is True
        assert (tmp_path / "learning" / "person" / "trash" / delete_id).is_dir()
        status, missing = _request(
            port,
            "GET",
            f"/api/learning/candidates/person/{delete_id}",
        )
        assert status == 404
        assert missing["error"] == "候选不存在"

        status, protected = _request(
            port,
            "DELETE",
            f"/api/learning/candidates/person/{candidate_id}",
            {"expected_revision": approved["revision"]},
        )
        assert status == 422
        assert "不能删除" in str(protected["error"])

        status, sources = _request(port, "GET", "/api/sources")
        assert status == 200
        assert "files" in sources
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        reviewer.__dict__["LEARNING_ROOT"] = previous_root
