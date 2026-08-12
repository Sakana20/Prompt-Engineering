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

    assert "/Users/sakana/Desktop/Work/2026/MM.DD/淘宝闪购/素材" in index
    assert "明确启动转写" in index
    assert "learning-transcribe" not in index


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

        status, sources = _request(port, "GET", "/api/sources")
        assert status == 200
        assert "files" in sources
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
        reviewer.__dict__["LEARNING_ROOT"] = previous_root
