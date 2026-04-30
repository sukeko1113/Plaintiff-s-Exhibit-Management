# -*- coding: utf-8 -*-
"""
metadata_router のテスト。

SPEC.md §10.6.1 / §10.6.2 / §10.6.4 / §10.8 に準拠した10ケースを検証する。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.merge_service import MASTER_DIRNAME
from app.metadata_service import METADATA_DIRNAME, METADATA_FILENAME


ISO8601_JST_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$"
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("KOGO_KANRI_SETTINGS_PATH", str(tmp_path / "settings.json"))
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/metadata
# ---------------------------------------------------------------------------

def test_get_metadata_returns_empty_when_file_missing(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "case"
    root.mkdir()

    r = client.get("/api/metadata", params={"root_folder": str(root)})
    assert r.status_code == 200
    assert r.json() == {"version": 1, "entries": {}}


def test_get_metadata_returns_existing_content(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "case"
    metadata_dir = root / METADATA_DIRNAME
    metadata_dir.mkdir(parents=True)
    payload = {
        "version": 1,
        "entries": {
            "甲第００１号証": {
                "title": "保護者説明会配布資料",
                "created_date": "令和○年○月○日",
                "author": "被告",
                "purpose": "立証趣旨",
                "updated_at": "2026-04-30T12:34:56+09:00",
                "source": "ai_then_user",
            }
        },
    }
    (metadata_dir / METADATA_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    r = client.get("/api/metadata", params={"root_folder": str(root)})
    assert r.status_code == 200
    assert r.json() == payload


def test_get_metadata_returns_400_when_root_missing(
    client: TestClient, tmp_path: Path
) -> None:
    missing = tmp_path / "no_such_root"
    r = client.get("/api/metadata", params={"root_folder": str(missing)})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# PUT /api/metadata/{normalized_key}
# ---------------------------------------------------------------------------

def test_put_metadata_creates_new_entry_with_updated_at(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "case"
    root.mkdir()

    r = client.put(
        "/api/metadata/甲第００１号証",
        json={
            "root_folder": str(root),
            "title": "保護者説明会配布資料",
            "created_date": "令和○年○月○日",
            "author": "被告",
            "purpose": "立証趣旨",
            "source": "user",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["normalized_key"] == "甲第００１号証"
    assert body["title"] == "保護者説明会配布資料"
    assert body["source"] == "user"
    assert ISO8601_JST_RE.match(body["updated_at"])

    # ディスクにも書き込まれている
    on_disk = json.loads(
        (root / METADATA_DIRNAME / METADATA_FILENAME).read_text(encoding="utf-8")
    )
    assert on_disk["entries"]["甲第００１号証"]["title"] == "保護者説明会配布資料"


def test_put_metadata_updates_existing_and_keeps_others(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "case"
    metadata_dir = root / METADATA_DIRNAME
    metadata_dir.mkdir(parents=True)
    initial = {
        "version": 1,
        "entries": {
            "甲第００１号証": {
                "title": "古いタイトル",
                "created_date": "",
                "author": "",
                "purpose": "",
                "updated_at": "2026-01-01T00:00:00+09:00",
                "source": "user",
            },
            "甲第００２号証": {
                "title": "保持されるエントリ",
                "created_date": "",
                "author": "",
                "purpose": "",
                "updated_at": "2026-01-02T00:00:00+09:00",
                "source": "ai_then_user",
            },
        },
    }
    (metadata_dir / METADATA_FILENAME).write_text(
        json.dumps(initial, ensure_ascii=False), encoding="utf-8"
    )

    r = client.put(
        "/api/metadata/甲第００１号証",
        json={
            "root_folder": str(root),
            "title": "新しいタイトル",
            "created_date": "令和○年○月○日",
            "author": "原告",
            "purpose": "新しい立証趣旨",
            "source": "ai_then_user",
        },
    )
    assert r.status_code == 200

    on_disk = json.loads(
        (metadata_dir / METADATA_FILENAME).read_text(encoding="utf-8")
    )
    assert on_disk["entries"]["甲第００１号証"]["title"] == "新しいタイトル"
    assert on_disk["entries"]["甲第００１号証"]["source"] == "ai_then_user"
    # 他エントリは保持されている
    assert on_disk["entries"]["甲第００２号証"] == initial["entries"]["甲第００２号証"]


def test_put_metadata_returns_422_on_invalid_source(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "case"
    root.mkdir()
    r = client.put(
        "/api/metadata/甲第００１号証",
        json={
            "root_folder": str(root),
            "title": "",
            "created_date": "",
            "author": "",
            "purpose": "",
            "source": "robot",  # 許可値外
        },
    )
    assert r.status_code == 422


def test_put_metadata_decodes_url_encoded_full_width_key(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "case"
    root.mkdir()

    key = "甲第００１号証その２"
    encoded = quote(key, safe="")
    r = client.put(
        f"/api/metadata/{encoded}",
        json={
            "root_folder": str(root),
            "title": "枝番付き標目",
            "created_date": "",
            "author": "",
            "purpose": "",
            "source": "user",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["normalized_key"] == key

    on_disk = json.loads(
        (root / METADATA_DIRNAME / METADATA_FILENAME).read_text(encoding="utf-8")
    )
    assert key in on_disk["entries"]
    assert on_disk["entries"][key]["title"] == "枝番付き標目"


# ---------------------------------------------------------------------------
# POST /api/master/open
# ---------------------------------------------------------------------------

def test_master_open_happy_path(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "case"
    master = root / MASTER_DIRNAME
    master.mkdir(parents=True)
    target = master / "甲第００１号証.docx"
    target.write_bytes(b"dummy docx")

    with patch("app.routers.metadata_router.subprocess.run") as mock_run, \
         patch("app.routers.metadata_router.os.startfile", create=True) as mock_startfile:
        r = client.post(
            "/api/master/open",
            json={"root_folder": str(root), "normalized_key": "甲第００１号証"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["opened"] is True
    assert Path(body["path"]) == target.resolve()
    # OS 別に少なくとも1回はファイル起動コールが行われる
    assert mock_run.called or mock_startfile.called


def test_master_open_returns_404_when_file_missing(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "case"
    (root / MASTER_DIRNAME).mkdir(parents=True)
    # ファイルは作成しない

    with patch("app.routers.metadata_router.subprocess.run") as mock_run, \
         patch("app.routers.metadata_router.os.startfile", create=True) as mock_startfile:
        r = client.post(
            "/api/master/open",
            json={"root_folder": str(root), "normalized_key": "甲第００１号証"},
        )

    assert r.status_code == 404
    # ファイルを開く処理は実行されない
    assert not mock_run.called
    assert not mock_startfile.called


def test_master_open_rejects_path_traversal(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "case"
    (root / MASTER_DIRNAME).mkdir(parents=True)

    with patch("app.routers.metadata_router.subprocess.run") as mock_run, \
         patch("app.routers.metadata_router.os.startfile", create=True) as mock_startfile:
        r = client.post(
            "/api/master/open",
            json={
                "root_folder": str(root),
                "normalized_key": "../../etc/passwd",
            },
        )

    assert r.status_code == 400
    # ファイルを開く処理は実行されない
    assert not mock_run.called
    assert not mock_startfile.called
